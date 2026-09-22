# Stage 1 content quality and limits

What the product stores for each news item, how reliable each field is, and what
is still missing. Live counts come from `GET /api/v1/stats/content`.

## The field model

Every item carries five content fields, each with its own state. A field is
never filled with a guess: if nothing produced it, it reports `pending`, and the
interface says so next to the field.

| Field | Table | States |
| --- | --- | --- |
| English body text | `news_item_content.original_text` | `available`, `summary_only`, `unavailable`, `not_processed`, `error` |
| Persian title | `news_item_translations` (`field='title'`) | `available`, `pending`, `unavailable`, `error` |
| Persian summary | `news_item_translations` (`field='summary'`) | same |
| Persian body | `news_item_translations` (`field='body'`) | same |
| Images and documents | `news_item_media` | `article_image`, `article_media`, `linked_document`, or a `rejected_*` state with the rule that rejected it |

`not_processed` is not the same as `unavailable`. The first means the record
predates body extraction; the second means the feed carried nothing to extract.
Conflating them would turn a gap in our pipeline into a claim about the source.

## Where the text comes from

Extraction reads **only the bytes the collector already fetched for the feed**.
No article page, image or document is requested. This is a deliberate limit: it
means no source's access policy can be bypassed by the content pipeline, and it
keeps one cycle at exactly one HTTP request per source.

The consequence is that body coverage depends on what each publisher puts in its
own feed:

- A feed with `content:encoded` or Atom `content` carries the article body. The
  item gets `display_policy = full_syndicated` and the body is rendered.
- A feed with only `description` carries a teaser. The item gets
  `display_policy = summary_only`: the product shows the summary, the metadata
  and a link to the original, and **withholds the body with the reason shown**.
- A feed with neither gets `link_only`.

Fetching the article page would raise body coverage. It is not implemented
because it needs a per-source policy review: being able to retrieve a page is
not permission to republish it.

## Image and document selection

Images are taken from the feed's own markup and filtered by rule. Each rejected
image keeps the rule that rejected it, visible under technical details, so the
filter can be audited rather than trusted.

| Rule | Rejects |
| --- | --- |
| `rejected_chrome` | URL or class contains a chrome marker: logo, icon, favicon, avatar, sprite, spacer, placeholder, advert, beacon, tracking, share, subscribe, and similar |
| `rejected_tracking_pixel` | Declared 2x2 or smaller |
| `rejected_too_small` | Declared width or height under 200px |
| `rejected_type` | Not a supported raster image type; SVG is excluded as almost always iconography |

The lead image is the **first image that survives filtering**, not the first in
the markup — feeds routinely open with a masthead or a pixel. `srcset` resolves
to the widest candidate. `data:`, `javascript:` and credentialed URLs are
dropped. Tracking query parameters are stripped.

### Known limits of image handling

- **Media rows are `unverified`.** MIME type is inferred from the URL
  extension; byte size and real dimensions are unknown because nothing is
  downloaded. Verifying them needs a separate, bounded, policy-aware pass that
  is **not implemented**.
- The interface loads images directly from the publisher's CDN with
  `referrerPolicy="no-referrer"`. A broken image is reported as unavailable
  rather than replaced with a substitute.
- Filtering is rule-based, not visual. An editorial image whose filename
  contains a chrome word will be rejected, and a decorative image with a neutral
  filename and no declared size will pass. The rejection list makes both
  auditable.
- **Right to redisplay an image is not established by the ability to load it.**
  Hotlinking a publisher's image is a licensing question that has not been
  settled for any source.

## Persian translation and summary

**No translation provider is configured, so every Persian field is `pending`
and no Persian text exists.** This is the single largest gap between the current
product and the brief, and it is blocked on a commercial decision, not on
engineering.

Everything around it is built and tested:

- `translate.py` — provider interface with OpenAI-compatible, Azure OpenAI and
  Anthropic implementations, selected by `NEWS_TRANSLATION_PROVIDER`.
- `translate_worker.py` — bounded, resumable pass. Each field is committed on
  its own, so the run can be stopped and restarted without repeating finished
  work. `--dry-run` reports the plan without calling a provider.
- Output that is not Persian is rejected as `error`, so a provider echoing the
  English input back can never reach the product.
- Provider errors are sanitized of key material before storage.
- Provenance per field: provider, model, content version, source character
  count, latency and timestamp.

Prompts require that names, numbers, dates and the source's own hedging survive
translation, and that the summary use only facts present in the supplied text.

### The decision required

Pick a provider and supply a credential. Estimates below use the measured feed:
**30–55 new items per day** across 12 sources, average summary 1,433
characters, so roughly **1,800 items per month**.

| Option | Scope | Estimated monthly cost |
| --- | --- | --- |
| Persian title + summary only | What the news flow and home page need | **$4–9** |
| Title + summary + full body translation | Adds the side-by-side body on the detail page | **$25–50** |

Ranges span Claude Haiku 4.5 (`claude-haiku-4-5`, $1/$5 per million input/output
tokens) at the low end and Claude Sonnet 5 (`claude-sonnet-5`, $2/$10) at the
high end. Batch processing halves either figure for this workload, which is not
latency-sensitive. A one-time backfill of the 352 existing items costs under a
fifth of one month.

These are estimates from measured volume and assumed token ratios, not
quotations. The first real batch will produce exact figures, which is why the
worker starts at `--limit 5`.

| What also needs deciding | Why |
| --- | --- |
| Where data may be processed | Article text leaves the machine and goes to the provider. If processing must stay in a jurisdiction or on-premises, that rules out the hosted options above and changes the cost materially. |
| Credential handling | The key is read from the environment and never logged or committed. Who holds it and how it is rotated is not yet decided. |
| Quality bar for publication | Translations are machine-produced. Whether they are published directly, labelled as machine translation, or reviewed before publication is an editorial decision. |

Rate limits are handled by `NEWS_TRANSLATION_SLEEP_SECONDS` between calls; the
value needs tuning to whichever tier is purchased.

## Honest summary of the current state

| Requirement from the brief | State |
| --- | --- |
| English text kept and visible | **Done** where the publisher syndicates it; withheld with a stated reason otherwise |
| Persian translation beside the original | **Blocked** — pipeline built and tested, no provider configured |
| Short Persian summary beside the headline | **Blocked** — same |
| Related image shown | **Partly done** — selected and filtered from the feed, but unverified and with redisplay rights unresolved |
| Related document shown | **Partly done** — linked documents are captured and listed, unverified |
| Adverts, logos, default and unrelated images removed | **Done** by rule, with every rejection auditable |
| Usable where the source site is unreachable for the user | **Partly done** — summary, metadata and evidence are stored and shown; full text only where the publisher syndicated it |

No field in this table is described as finished on the strength of code existing.
Where it says blocked, no Persian text is in the database.

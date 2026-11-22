# Stories and Briefing Contract

Both are derived views that `apps/api/experience.py` builds from PostgreSQL.
They run in the API's job loop: new items get topics every 60 s; clustering,
the briefing and stories run every 900 s. A PostgreSQL advisory lock
(772031) ensures that only one API instance runs the jobs.

## Stories (`stories_v1`)

Table `stories`: `story_id` (kind:ref, stable), `kind`, `position`,
`title_fa`, `subtitle_fa`, `collection_label`, `target_type`, `target_ref`,
`target_href`, `frames` (jsonb), `visual` (image_url | category_id |
monogram), `rule_id`, `rule_version`, `evidence` (jsonb),
`content_updated_at`, `generated_at`, `retired_at`.

| Kind | Rule | Target |
|---|---|---|
| `today` | Up to 5 items from the last 24 h, by importance, excluding "other" | Lead item |
| `breaking` | Items meeting `breaking_v1` in the last 24 h (max 6) | `/news?importance=high&window=24h` |
| `events` | Events updated in 72 h, by source count | `/events` |
| `topic` × ≤3 | Top 3 non-"other" categories by 24 h volume; subtitle gives the delta vs the previous 24 h | `/topics/{id}` |
| `briefing` | Key developments of the latest briefing | `/briefing` |
| `sources` | Top 5 sources by 24 h items | `/sources` |
| `weak_signals` | Top 5 weak signals (see below) | `/foresight/weak-signals` |
| `dossier` | `iran_axis` subtopic, last 7 days | `/topics/iran_axis` |

- A story with no frames is not created.
- Stories that disappear from a run are retired (`retired_at`), not deleted.
- The visual is the first real article image among the frames; otherwise the category artwork is used.
- Headlines are the stored Persian translation when one exists, else the original English, marked LTR.

**Viewer:** a modal dialog with a per-frame progress bar (6.5 s per frame).
- **Navigation:** ←/→ keys, tap zones or buttons move between frames; after the last frame it continues to the next story.
- **Pausing:** Space, the pause button, hovering or focusing the text, or press-and-hold on touch.
- **Closing:** Esc closes and returns focus to the story that opened it.
- **Seen state:** stored per browser as story id → `content_updated_at`, so the ring turns "new" again when the content changes.

## Importance (`importance_v1`)

`score = 3 × min(3, event_sources − 1) + category weight + 1 (confidence ≥ 0.7) + 2 (title starts "BREAKING")`

Category weight: security & defence or regional = 2; other thematic
categories = 1; "other" = 0; off-mission "other" = −2. Levels: high ≥ 6,
medium ≥ 3, otherwise low. The rule text is returned by `/api/v1/rules` and
shown on every detail page.

## Breaking (`breaking_v1`)

An item counts as breaking when it was published within the last 24 h (and is
not future-dated) and **at least one** of these holds: its importance is high,
its event has ≥ 2 independent sources, or the publisher titled it
"BREAKING". If nothing qualifies, `/api/v1/breaking` returns
`mode: latest_fallback`, and the ticker labels those items "تازه‌ترین"
(latest), never "فوری" (breaking).

## Daily briefing (`rule_briefing_v1`)

Table `daily_briefings` is append-only. A new row is written only when the
payload digest changes. Payload:

- `narrative_fa`: a fixed template filled with counts only, with its method stated.
- `totals`: 24 h items, previous 24 h, change %, active sources, events.
- `key_developments`: 5–8 items by importance, excluding "other", one per event, each linking to its evidence item and event.
- `rising_topics` / `falling_topics`: category deltas, 24 h vs the previous 24 h.
- `top_sources`.
- `coverage_gaps`: silent sources, untranslated items, items without a summary, "other" items, failing sources.
- `rules`: importance, taxonomy and clustering versions.

**AI fields** (`ai_generated`, `ai_status`, `ai_provider`, `ai_model`,
`ai_prompt_version`, `executive_summary_fa`) are recorded honestly.
`ai_status` comes from the gateway configuration and the last
`ai_requests_log` row: `provider_not_configured`, `provider_unavailable` or
`configured`. On 2026-09-28 it was `provider_unavailable` (OpenRouter
configured; the last request failed with an insufficient-credit error). No AI
text has been generated. When an AI summary is added, it must go in
`executive_summary_fa` with model and prompt version, and be shown with the AI
label as "needs review".

**Freshness:** `fresh` ≤ 1 h, `stale` ≤ 24 h, `outdated` > 24 h, or
`not_generated`.

## Weak signals (descriptive)

Capitalised names that are not ordinary vocabulary in the corpus, appear in
≥ 2 items in the last 7 days, and appear in none of the 30 days before. They
are sorted by number of independent sources. This is a count of novelty, not
a prediction.

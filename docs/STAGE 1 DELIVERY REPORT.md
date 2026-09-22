# Stage 1 delivery report

Written for the client. Covers what was verified on handover, what changed, what
is measured, and what still needs a decision.

Date: 2026-09-22. Every figure comes from the running system.

## 1. Verification of the previous report

Each prior claim was re-tested rather than accepted.

| Claim | Verdict |
| --- | --- |
| `sites.docx` SHA-256 `3F7522C9…C47980` | **Confirmed**, exact match |
| Registry: 62 canonical sources from 64 raw entries — 17 news, 9 think tanks, 36 X accounts | **Confirmed**, exact match |
| 11 RSS URLs verified for execution | **Confirmed** — and a twelfth was found and activated, see §3 |
| 6 sitemap, 2 HTML, 7 blocked | **Confirmed** with one correction: one of the six "sitemap" sources already had working RSS |
| OpenCTI separate on `127.0.0.1:8080`, 14 containers, no news data | **Confirmed**. Untouched throughout |
| Database: 352 items, 11 sources, 352 provenance rows | **Confirmed**, exact match |
| Run `6310f77f…` — 11/11 sources, 11 requests, 0 retries, 70 new items | **Confirmed**, present with those exact figures |
| Collector stopped, scheduler disabled | **Confirmed — 24-hour monitoring was not running** |
| Image tests 38/38 | **Confirmed**. Now 68 with the tests added here |
| Content incomplete: body, Persian translation, summary, images, documents | **Confirmed**. None existed |

Nothing in the previous report was found to be false.

## 2. Monitoring now runs

The scheduler is armed and the stack is healthy. All four containers report
healthy, including new healthchecks on the API and web services, which
previously had none — a wedged process looked identical to a working one.

First successful scheduled cycle: **12 of 12 sources, 12 HTTP requests, 143 new
items, 95 updates, 22 duplicates, no errors.**

Verified properties:

- **Failure isolation** — proven under a real fault. A defect introduced during
  this work failed all 12 sources in one cycle. Each failed independently, the
  run finalized as `failed` rather than hanging in `running`, and all 352 items
  stored at the time were untouched. Fixed, and the offline tests now catch that
  class of error before an image can be built.
- **No duplicates** — 495 items, 495 distinct canonical URLs.
- **Restart recovery** — 11 of 11 checks pass: nothing lost, 14 checkpoints
  survived, scheduling resumed, image revision still matched its pin.
- **Overlap prevention** — a PostgreSQL advisory lock; a second cycle records
  `skipped_locked` rather than running concurrently.

**Not yet proven:** four consecutive successful cycles, and discovery latency.
One cycle has completed; the window has been open under an hour and every
deployment restarts the interval. Latency has nothing to measure yet because no
source has published since the scheduler was armed. A figure is available from
the first cycle but it measures how old each feed's backlog was, not our lag, so
it is not reported as latency.

**Therefore this system is not yet declared ready for 24-hour operation.** The
remaining evidence is a matter of leaving it running.

## 3. Source coverage

Three counts that were previously reported as one, now separated in the API and
shown on the sources page:

| Count | Value |
| --- | --- |
| Registered in `sites.docx` | **62** |
| Executable — validated, permitted collection path | **12** |
| Monitored — has completed a real fetch | **12** |

Breakdown: 12 active RSS, 5 sitemap candidates, 2 HTML candidates, 7 blocked,
36 X accounts not covered. Full per-source detail in
[source coverage](STAGE%201%20SOURCE%20COVERAGE.md).

**rusi.org was raised from candidate to active.** Discovery had already recorded
four working RSS feeds for it, but it had been filed as a sitemap candidate. On
revalidation the documented URL now returns 301 to the `www` host, which serves
200 `application/xml`; robots.txt permits the feed path; the project parser reads
60 items with none rejected. That is the bar for activation, and nothing else
currently meets it.

The 7 blocked publishers return 403 or disallow automated access. No attempt is
made to work around that. The 36 X accounts have no authorised collection path
and are **not** presented as monitored anywhere in the product.

## 4. Content

Article bodies, images and documents are now extracted — using **only bytes the
collector already fetched**. No article page, image or document is requested, so
the content pipeline cannot bypass any source's access policy, and a cycle is
still exactly one request per source.

| Field | Coverage across 495 items |
| --- | --- |
| English body, publisher-syndicated | 170 items, average 5,082 characters |
| English body, summary only | 90 items |
| Not yet processed | 235 items collected before extraction existed |
| Lead article image | 94 items |
| Further article images | 259 |
| Linked documents | 17 across 13 items |
| Images rejected by rule | 24 |
| **Persian title, summary, body** | **0 — no provider configured** |

Where a publisher does not syndicate the body, the product shows the summary,
the metadata and a link to the original, and states why the body is withheld.
Every rejected image keeps the rule that rejected it, so the filter can be
audited rather than trusted; a spot check found WordPress emoji sprites
correctly filtered and lead images resolving to real article photography.

**Publisher names now come from the feeds themselves.** The source document
contains only URLs, so sources previously displayed as hostnames. All 12 now
show their own published names — "USNI News", "Breaking Defense", "Jerusalem
Center for Security and Foreign Affairs". No UUID or bare hostname is displayed.

Limits stated plainly: media rows are **unverified** — MIME is inferred from the
URL and nothing is downloaded — and the right to redisplay a publisher's image
is not established by being able to load it. Neither is claimed as resolved.

## 5. Defects found and fixed

Beyond the work requested, three defects were found in the existing system:

1. **Every collector-inserted item recorded the wrong category.** The
   classification loop's last value leaked into the database loop, so
   `item_classifications` stored the final feed item's category for all of them
   while `news_items` kept the correct one. 78 of 495 rows disagreed, and
   because the topics page reads one table and the news filter the other, a
   subject drill-down showed a different count than the subject it was opened
   from. Fixed; the migration now recomputes classification rather than
   preserving whatever was written first, and repaired all 78 on the next start.
   Drift is now 0 of 495.
2. **`sources_planned` was the constant 11.** Adding any source would have
   marked every subsequent run `partial` and made the scheduler look broken.
3. **The README described a configuration-only phase** and stated OpenCTI had
   never been started, which had long since stopped being true. It never
   mentioned the news product at all.

Also corrected: the home page advertised a developments map, an alerts centre
and settings that do not exist — stage 2 and 3 capabilities presented as
features — and linked "subjects" to the wrong page. A filtered link painted the
unfiltered feed before replacing it, and logged a hydration error on every
filtered page.

## 6. Test results

| Suite | Result |
| --- | --- |
| Collector tests, inside the runtime image | **68 / 68** |
| Browser acceptance across desktop and mobile | **40 / 40** |
| API smoke | **pass** |
| Database probes | **pass** |
| Restart recovery | **11 / 11** |
| Backup and verified restore | **pass** |

The image build runs the test suite, so a failing test cannot produce a
deployable image, and the collector refuses to start unless the image revision
matches its pin.

## 7. What still needs your decision

**One decision blocks the largest remaining gap.**

### Persian translation and summary

No provider is configured, so every Persian field is `pending` and no Persian
text exists. The pipeline is built and tested: provider interface, bounded
resumable worker, per-field provenance, and rejection of any output that is not
Persian so an untranslated echo cannot reach the product.

| Option | Scope | Estimated monthly cost |
| --- | --- | --- |
| Persian title + summary | What the news flow and home page need | **$4–9** |
| Adds full body translation | Side-by-side body on the detail page | **$25–50** |

Estimated from measured volume, not quoted. Three questions go with it: where
the data may be processed (article text leaves this machine), who holds and
rotates the credential, and whether machine translation is published directly,
labelled, or reviewed first.

### Not built, and not claimed

| Item | State |
| --- | --- |
| Alerting when collection stops | A health endpoint returns 503 on stall, so any monitor you already run can poll it. Nothing notifies anyone by itself. |
| User accounts and roles | No authentication. The stack binds to `127.0.0.1` only. |
| API rate limiting | None. Local-only binding is the current control. |
| Data retention policy | Nothing is deleted. No rule is implemented. |
| Media verification | Rows are `unverified`; MIME, size and rights are unchecked. |
| Right to redisplay content | Unresolved for every source. |
| Sitemap and HTML sources | 7 candidates need per-source parsers and validation. |
| Blocked publishers and X accounts | 43 sources need permission or a paid API tier, not engineering. |

Until the translation decision is made and four consecutive cycles plus
discovery latency are observed, neither "ready for 24-hour operation" nor
"commercially complete" should be used.

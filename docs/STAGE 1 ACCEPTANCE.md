# Stage 1 acceptance criteria

Each criterion names the command that decides it, so "ready" is a test result
rather than an opinion. Anything not yet measured is marked as such; nothing is
recorded as passing on the strength of the code existing.

## How to run the whole set

```powershell
cd 'E:\Iran monitor'
docker run --rm -e DATABASE_URL="postgresql://offline_test:offline_test@127.0.0.1:1/collector_test" `
  iran-monitor-news-collector:$(git rev-parse HEAD) sh -c "PYTHONPATH=/app python -m pytest -q /app/tests/monitoring"
node tests/ui/stage1-qa.cjs
./scripts/backup.ps1 -Action backup
./scripts/backup.ps1 -Action verify -Path runtime/backups/<newest>.dump
Invoke-RestMethod http://127.0.0.1:3001/api/v1/collection/status
Invoke-RestMethod http://127.0.0.1:3001/api/v1/sources/coverage | Select-Object registered,executable,monitored
Invoke-RestMethod http://127.0.0.1:3001/api/v1/stats/content
```

## Measured results, 2026-09-22

Run against the live stack, not inferred from code.

| Suite | Result |
| --- | --- |
| Collector unit and integration tests, inside the runtime image | **68 / 68 pass** |
| Browser acceptance, `tests/ui/stage1-qa.cjs` | **40 / 40 pass** |
| API smoke, `tests/monitoring/smoke_api.py` | **pass** — 12 sources, 495 items, 62 registered, 11 monitored |
| Database probes, `tests/monitoring/smoke_database.py` | **pass** — migration rollback, advisory lock, content foreign keys, no stuck runs |
| Restart recovery, `scripts/restart-recovery-test.ps1` | **11 / 11 pass** — nothing lost, 14 checkpoints survived, scheduling resumed |
| Backup and restore, `scripts/backup.ps1 -Action verify` | **pass** — restored row counts match the live database |

Collection state at the time of writing:

- Scheduler armed, all four containers healthy, 12 of 12 sources `healthy`, zero consecutive failures.
- First successful scheduled cycle `12/12` sources, 12 HTTP requests, 143 new items, 95 updates, 22 duplicates, no errors.
- 495 items stored, 495 distinct canonical URLs — **no duplicates**.
- Body text extracted for 260 items: 170 `full_syndicated` (average 5,082 characters) and 90 `summary_only`.
- Media: 94 items with a lead article image, 259 further article images, 17 documents across 13 items, 24 images rejected by rule.
- Publisher names captured from the feeds themselves for all 12 sources; no UUID or bare hostname is displayed.
- Classification drift between `news_items` and `item_classifications`: **0 of 495**.

Not yet measured:

| Criterion | Why |
| --- | --- |
| A4 — four consecutive successful cycles | One observed so far. The window has been open under an hour and every deployment restarts the interval. |
| A11 — discovery latency | No source has published anything since the scheduler was armed, so there is nothing to measure. Figures taken over the first cycle measure how old the feed backlog was, not our lag, and are not reported as latency. |

## A. Collection

| # | Criterion | Threshold | How it is measured |
| --- | --- | --- | --- |
| A1 | Unit and integration tests pass in the runtime image | 100% | pytest inside the image; the build fails otherwise |
| A2 | Image revision matches the code revision | exact match | `BUILD_INFO.json` vs `COLLECTOR_REVISION`; the collector exits otherwise |
| A3 | Scheduler is armed and beating | `scheduler_enabled: true`, `collector_health: healthy` | `/api/v1/collection/status` |
| A4 | Consecutive scheduled cycles succeed | **at least 4 in a row**, `sources_failed: 0` | `/api/v1/collection/runs`, `trigger_type: scheduled` |
| A5 | Requests per cycle equal the executable source count | exactly one per source | `http_requests` on each run |
| A6 | One failing source does not corrupt the cycle | other sources still `succeeded` | Per-source rows in `/api/v1/collection/runs/{id}` |
| A7 | No run is left `running` | zero | `SELECT count(*) FROM collection_runs WHERE status='running' AND started_at < now()-interval '1 hour'` |
| A8 | Overlapping cycles are prevented | a second cycle records `skipped_locked` | PostgreSQL advisory lock |
| A9 | Collection survives a container restart | cycles resume, no duplicate items | Restart, then compare `news_items` count and the next run |
| A10 | No duplicate items | `news_items_canonical_url_key` and `item_id` unique, both held | Repeated cycles report `duplicates`/`updates`, not inserts |
| A11 | Discovery latency | median under one interval (15 min) | `published_at` to `fetched_at` across a day of scheduled cycles |

## B. Coverage

| # | Criterion | Threshold | How it is measured |
| --- | --- | --- | --- |
| B1 | Registered, executable and monitored reported separately | three distinct numbers | `/api/v1/sources/coverage` |
| B2 | Every registered source has a coverage state and a reason | 62 of 62 | Same endpoint |
| B3 | No blocked source is collected | zero requests to a 403 or robots-disallowed host | Executable set excludes them by construction |
| B4 | X accounts are not shown as monitored | `not_covered` for all 36 | Same endpoint |
| B5 | A source with no successful fetch is not counted as monitored | `health_status: not_run` | Same endpoint |

## C. Content

| # | Criterion | Threshold | How it is measured |
| --- | --- | --- | --- |
| C1 | Every content field reports its own state | no silent blanks | `/api/v1/stats/content` |
| C2 | `pending` is never rendered as text | zero generated placeholders | No provider writes text; enforced by `NullProvider` |
| C3 | Non-Persian provider output is rejected | status `error`, no text stored | `test_english_output_is_rejected...` |
| C4 | Body extracted where the publisher syndicates it | `display_policy: full_syndicated` for feeds carrying `content:encoded` | `/api/v1/stats/content` `display_policy` counts |
| C5 | Body withheld with a stated reason otherwise | reason visible in the interface | Browser QA `withheld body states its reason` |
| C6 | Chrome images rejected with an auditable rule | every rejection carries a reason | `news_item_media.rejection_reason`; nine extraction tests |
| C7 | Lead image is the first surviving image | not the first in markup | `test_lead_image_is_the_first_surviving_image...` |
| C8 | Names, numbers and dates survive extraction | preserved | `test_body_text_keeps_names_numbers_and_dates` |
| C9 | Persian translation present | **not met** — no provider configured | `/api/v1/stats/content` `translations_fa` |
| C10 | Media verified for MIME, size and rights | **not met** — not implemented | Rows report `unverified` |

## D. Product

| # | Criterion | Threshold | How it is measured |
| --- | --- | --- | --- |
| D1 | News flow is populated, paginated and searchable | card count matches API | `tests/ui/stage1-qa.cjs` |
| D2 | Displayed total matches the API total | exact | Same |
| D3 | Source, category and window filters work and the URL is shareable | filtered results match the API | Same |
| D4 | Category drill-down count matches the API | exact | Same |
| D5 | No UUID shown in place of a source name | zero | Same |
| D6 | Source page shows type, monitoring state, last success and its own items | present | Same |
| D7 | News page shows original text, translation state, evidence and the original link | present | Same |
| D8 | RTL and Vazirmatn render | both | Same |
| D9 | No horizontal overflow on desktop or mobile | zero | Same at 1440px and 390px |
| D10 | No console errors, no failed local requests | zero | Same |

## E. Operations

| # | Criterion | Threshold | How it is measured |
| --- | --- | --- | --- |
| E1 | Backup produces a restorable archive | row counts match | `backup.ps1 -Action verify` |
| E2 | Restore is guarded and stops the collector first | requires typing `RESTORE` | `backup.ps1 -Action restore` |
| E3 | Migrations are additive and need no rollback | new columns and tables only | `DDL` in `ops.py` |
| E4 | Image rollback works by revision tag | earlier tag starts | Set `COLLECTOR_REVISION`, restart |
| E5 | Secrets never reach logs, commits or evidence | zero | `.env` git-ignored; errors sanitized before storage |
| E6 | Stalled monitoring is visible | `collector_health` and per-source `delayed` | `/api/v1/collection/status`, `/api/v1/sources` |
| E7 | Alerting when collection stops | **not met** — no external alert channel | Health is exposed; nothing notifies anyone |
| E8 | User accounts and roles | **not met** — no authentication | The stack binds to `127.0.0.1` only |
| E9 | API rate limiting | **not met** | Local-only binding is the current control |
| E10 | Data retention policy | **not met** — nothing is deleted | No retention rule is implemented |

## Declaring readiness

"Ready for 24-hour operation" requires every criterion in A and B, plus D, to
pass, with A4, A9 and A11 measured over a continuous observation window rather
than inferred. "Commercially complete" additionally requires C9, C10 and E7
through E10, each of which needs either a purchasing decision or work that has
not started.

Until those are measured and passing, neither phrase should be used.

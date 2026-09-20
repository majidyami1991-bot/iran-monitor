# Phase 8A bounded live RSS pilot

Completed on 2026-09-20 from commit `ffced951e9196c5dafa59c060353c9788adef7f3`.
Exactly one collector invocation requested the 11 executable readiness URLs,
once each, sequentially. All returned HTTP 200. The database now contains
282 news items, 11 sources and 282 provenance records: 178 new items and
31 unchanged duplicates among 209 feed entries. No updates or rejections.

## Gates and request limits

The initial worktree was clean. DB/API/dashboard all matched 104 items and
11 sources. The source document SHA-256 matched registry metadata:
`3F7522C94952DD85254F45CADF600A64EE6F264D27E30E3D2BF3297D59C47980`.
Manifest URLs were unique HTTPS URLs, ordered by source_id, with exact boolean
executable status and verified Tier-1 classification. Registry values were not
changed, including the news/think_tank classifications and disabled flags.

RSS request count is 11; local DB/API/UI verification traffic is separate.
curl configuration-file loading was disabled, redirects were not followed,
retry was zero, total timeout 30 seconds, connection timeout 15 seconds and
each response limited to 2 MiB. User-Agent:
`IranMonitor/1.0 (bounded RSS pilot; no article crawling)`.
Total feed response bytes: 2,008,013. No homepage, article, sitemap or X requests.
No image pull, migration, service recreation, scheduler or OpenCTI operation.

## Data integrity

All feed payloads were validated before import. The runner reused the existing
URL normalization and deterministic source_id/URL SHA-256 item ID algorithm.
Only supported RSS was parsed; unsupported formats would fail without fallback.
Publication timestamps were parsed from feed pubDate with timezone validation;
missing dates would stay null. Feed summaries/article content were not imported,
consistent with the existing pipeline. Response bodies were processed in memory;
only normalized records, response hashes and request evidence were retained.

Each source used its own PostgreSQL transaction, inserting news and provenance
together with existing unique constraints and ON CONFLICT protection. Existing
items were never overwritten; update candidates would be retained for review.
Checkpoints were written only after successful database commit confirmation,
under the new ignored cycle directory. All 11 transactions committed.

All 104 existing item rows, 104 provenance rows, all source rows and the hashes
of prior staging/checkpoint/configuration files remain identical to baseline.
No duplicate item_id or canonical URL exists. Each of the 178 new records has
feed URL, collection timestamp, response hash and references to local execution,
normalized staging and post-commit checkpoint evidence.

## Validation

- Dry-run explicitly blocked sockets and subprocesses: zero requests/DB writes.
- Offline replay against committed data classified every stored cycle item as
  an unchanged duplicate; no second live fetch and no second DB write.
- Existing item_id and canonical_url unique constraints were verified.
- The exact importer code passed an offline mocked transaction failure test:
  failure during provenance insertion rolled back its item and left the other
  two source transactions intact. No live transaction failed; real PostgreSQL
  failure recovery was therefore not exercised.
- Browser checks on 3001 confirmed 282/11 KPIs, new-item visibility, search,
  source filtering and newest ordering, with zero browser errors.
- DB/API/dashboard counts agree. HTTP is 200. All 38 container snapshots match
  baseline, including IDs, state, StartedAt, RestartCount, image and bindings.
  Preview remains stopped; 3002 is free. News Monitor publishes only
  127.0.0.1:3001. No collector remains running.

## Evidence and stop condition

All operational scripts, payloads, manifests, checkpoints, snapshots, screenshot
and results are ignored under `runtime/live-rss/phase-8a/`; none are committed.
The single-use invocation marker prevents rerunning this cycle. No secrets were
printed or written to the report. Root `.env` was passed to Compose; database
credentials were consumed only inside the existing API container.

Status: **PASS**. Stop after this cycle. Scheduling requires separate explicit
authorization. This commit contains only this sanitized report.

## Per-source results

| source_id | HTTP | bytes | observed | inserted |
|---|---:|---:|---:|---:|
| 02125465-dc6c-5355-823c-989b485ed491 | 200 | 143641 | 10 | 8 |
| 07edfccb-57c6-5dc0-8ea3-7951798ec9e8 | 200 | 5955 | 5 | 5 |
| 1c638686-e35b-53e9-959c-dc122aa9079f | 200 | 1003737 | 50 | 40 |
| 3bef586c-ca0d-5ee7-a837-beb5f31f510a | 200 | 181689 | 50 | 50 |
| 516b4133-492d-5c4d-b021-b1113c54b756 | 200 | 35759 | 10 | 10 |
| 6efbeadb-ebe5-55da-9c78-f7f51a1a4860 | 200 | 37731 | 10 | 0 |
| 70e9a720-f949-5641-a178-fb439bad0e5b | 200 | 363391 | 30 | 21 |
| 854ac2a3-ba0c-5f95-a62b-6d296294960a | 200 | 21106 | 10 | 10 |
| a7040487-3b56-54d0-aa0a-a86ee5eac297 | 200 | 53514 | 10 | 10 |
| c1781f8f-c222-5fc4-99a9-5fcc73e5f537 | 200 | 127817 | 9 | 9 |
| e4180227-092a-579e-b192-015a969d24f3 | 200 | 33673 | 15 | 15 |

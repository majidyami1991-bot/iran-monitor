# Phase 8B-R2 live collector validation

Status: **BLOCKED**. The baseline and offline plan passed, but the single permitted live cycle stopped on its first source because the API container mounts `/state` read-only. No retry or second cycle was run.

## Baseline and plan

- Project HEAD before execution: `fe386b70f3828ceb60d988bd7eb899dd4b8741c6`; worktree was clean.
- Database before: 282 items, 11 sources, 282 provenance rows, 282 historical summaries still marked unknown, and no granted advisory lock.
- Readiness manifest: 11 executable, unique source IDs and 11 unique HTTPS RSS URLs; IDs exactly matched the database. All six previously failing source IDs were listed in the ignored one-time execution manifest.
- Docker Engine and News Monitor DB/API/Web were healthy; dashboard returned HTTP 200. Collector container was exited, scheduler disabled, port 3002 free, and only `127.0.0.1:3001` was published by News Monitor.
- Fourteen OpenCTI containers and 34 other non-News-Monitor containers were snapshotted. Disk had approximately 989 GB free.
- Offline dry-run planned 11 sequential requests and recorded zero network requests, database writes, and collector checkpoint writes.

The first attempted one-off process exited before importing the collector because it looked for the readiness file at an unmounted `/metadata` path. It performed no request, cycle, or write. The single actual cycle was then executed inside the existing API service from the bundled `/app` readiness file. This setup failure did not trigger a feed retry.

## Single live cycle

Execution ID: `phase-8b-r2-20260921T111349Z`
Collection run: `c8ab7a29-9832-434b-9607-ab0dffdcbebf`
Trigger: `manual_validation`
Collector version: `1.1.0`

| Source ID | Result |
| --- | --- |
| `02125465-dc6c-5355-823c-989b485ed491` | One HTTPS RSS GET returned HTTP 200 (143,641 bytes); 10 entries observed. Its database transaction completed with 0 inserts. Checkpoint write then failed because `/state` is read-only. |
| Remaining 10 sources | Not attempted; execution stopped on the first source failure. This includes all six sources that had failed previously. |

The source transaction stored a `succeeded` source-result row before trying to write its checkpoint. The checkpoint raised `OSError: Read-only file system`. The exception handler then attempted to insert a second result for the same `(run_id, source_id)` and raised `UniqueViolation`, so the cycle aggregate stayed `running` instead of being finalized. This inconsistency is preserved as evidence; no database row was edited to mask it.

The first source's checkpoint still matches its pre-cycle SHA-256 and still references the previous run. No R2 checkpoint was written. The PostgreSQL advisory lock was released when the process exited. Retry count was zero; article, homepage, sitemap, HTML, Tier 2, and X requests were zero. No TypeError occurred, but the six previously failing sources were not reached, and this cycle did not establish live content-hash serialization for a new item.

## Data and runtime after execution

- Database remains at 282 items, 11 sources, and 282 provenance records. The aggregate signature over all historical item IDs and content fields is unchanged from baseline; duplicate item IDs and canonical URLs remain zero. No item or provenance was inserted, and the 70 previously reported update candidates remain preserved.
- The first source's 10 observed entries were not retained individually as comparison outcomes because the collector aborted before returning its per-cycle result. The database source-result row reports 0 inserted and 0 duplicates; update-candidate count for this partial run is therefore not recorded.
- All 282 historical summaries remain `historical_not_captured`. There are no new summaries or classifications from this cycle.
- API health, news, sources, overview, topics, quality, collection status, and runs endpoints returned HTTP 200. API reports 282 items and 11 sources. Dashboard returned HTTP 200; browser regression checks were not run after the blocking collector failure.
- Scheduler remains disabled; collector service remains exited; no background collector remains. The one active command exited. Port 3002 remains free.
- All 39 Docker containers retained the same IDs, states, restart counts, start times, images, and published ports as baseline. All 14 OpenCTI and all 34 other non-News-Monitor containers are unchanged.
- `sites.docx` SHA-256 remains `3F7522C94952DD85254F45CADF600A64EE6F264D27E30E3D2BF3297D59C47980`; source-registry SHA-256 remains `BC2F33D9F3067346B021B979AEC09DC7ED1EF35A02B9425733CC647A7FFF1969`.
- No OpenCTI mutation occurred. No secrets were printed or stored. Runtime evidence remains Git-ignored.

## Required follow-up

Make the shared collector state volume writable for the one-off API process, and make post-commit checkpoint failure handling preserve one unambiguous source result and finalize the run safely. Validate those changes offline first. Do not enable the scheduler or repeat a live cycle without separate authorization; this phase's one-cycle allowance has been consumed.

## R2A root-cause correction

The follow-up diagnosis is now precise: `/state` itself and the named volume are healthy. The live cycle was invoked inside `news-api`, whose root filesystem is read-only and whose `/state` mount is intentionally read-only for health-file reads. The stopped `news-collector` service already mounts the same dedicated named volume read-write as UID/GID `65532:65532`; the volume directory is owned by that identity with mode `0755`, and the collector root filesystem remains read-only. No volume permission or Compose mount change is needed. A future one-shot cycle must execute through the collector service, never the API service.

R2A preserves the original one-request results, the previous valid checkpoint and all R2 runtime evidence. Its repair does not advance the checkpoint: the current response digest was not persisted by the old collector, so the old checkpoint remains authoritative until a later separately authorized collection.

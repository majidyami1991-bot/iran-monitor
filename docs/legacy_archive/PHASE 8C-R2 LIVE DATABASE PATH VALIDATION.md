# Phase 8C-R2 live database path validation

Status: **BLOCKED**.

The single permitted live cycle was executed exactly once with `manual_validation`, 11 sequential RSS requests, retry 0, and no article, homepage, sitemap, image, document, X, HTML or scheduler activity. The cycle ended as `partial`: 11 attempted, 4 succeeded and 7 failed. No second cycle or retry was run.

## Gates

HEAD was `205d769`; the worktree was clean before execution. Readiness contained exactly 11 executable HTTPS feeds with 11 unique URLs. Baseline counts were 282 items, 11 sources and 282 provenance rows; no running run or advisory lock existed. API and dashboard were HTTP 200, collector was exited, scheduler was false, `.env` was ignored, port 3002 was free, disk space was sufficient, and 39 containers were snapshotted. The 38 offline tests and the real psycopg JSONB temporary-table rollback test passed. The execution manifest and dry-run recorded zero network requests, DB writes, checkpoint writes and run records.

## Live result

Run: `309cb859-2a3e-4d54-a9ce-6a47bd4637a5`. It made 11 RSS requests and received 1,760,114 bytes, observing 199 entries. Four sources followed the duplicate/update path successfully (55 updates, no overwrite). Seven sources reached `database_insert` and failed with `TypeError: Object of type datetime is not JSON serializable`; each was finalized as `failed_finalize`. The error occurred before PostgreSQL executed the insert, at psycopg JSON adaptation. No item or provenance was inserted, and no checkpoint failure or UniqueViolation occurred.

The failure is not treated as a successful validation. The collector invocation used the existing `defence-monitor-news-news-collector:latest` image, which still contained the pre-R1 collector code; the R1 serializer had only been validated in the candidate API image. This explains why the live result cannot establish the repaired path. No code was changed during the cycle and no retry was attempted.

## Post-cycle preservation

The run is finalized `partial`; no run remains `running` and the advisory lock is free. Database counts remain 282 items, 11 sources and 282 provenance rows. API and dashboard remain HTTP 200; collector remains exited with restart count 0 and scheduler remains disabled. The original Phase 8C report and all prior evidence remain unchanged. `sites.docx` and source registry hashes remain unchanged. OpenCTI and all unrelated containers remain unchanged.

No commit was created for a successful validation. The next safe action is a separate offline image parity correction: build and verify the R1 collector image, then request authorization for a new bounded RSS cycle. Translation, summary, media, document and scheduler work remain blocked.

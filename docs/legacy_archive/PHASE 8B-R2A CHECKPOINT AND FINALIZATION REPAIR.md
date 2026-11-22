# Phase 8B-R2A checkpoint and finalization repair

Status: **COMPLETE — OFFLINE CODE REPAIR AND EVIDENCE-BOUND RUN RECOVERY**. No RSS or other news source was requested during this phase.

## Diagnosis

The Phase 8B-R2 one-off cycle ran inside `news-api`. That service has a read-only root filesystem and mounts `/state` read-only. The RSS response and source transaction committed before checkpoint writing failed with a read-only filesystem error. The old exception path then inserted a second `source_run_results` row for the same `(run_id, source_id)`, violating `source_run_results_pkey`; the cycle therefore left its aggregate run in `running`.

The dedicated stopped `news-collector` service already runs as UID/GID `65532:65532`, keeps its root filesystem read-only, and mounts the dedicated checkpoint volume read-write. No Compose permission change is required. Future collector execution must use that service, not the API container.

## Code repair

- Checkpoint writes now use a same-directory temporary file, flush and fsync it, atomically replace the target, and clean partial temporary files on failure.
- A source-result row is created once in `running` before the one bounded request. Success and failure paths update that row by its explicit composite key; an exception handler cannot create a duplicate result.
- Committed item/provenance work stores the response digest and checkpoint payload in the same DB transaction. A later checkpoint recovery can write the saved payload without fetching a source or inserting news items again.
- Run finalization aggregates persisted source results, marks interrupted open sources explicitly, and is idempotent.
- Additive schema migration records HTTP request count, response digest, checkpoint recovery payload, and repair metadata. It does not backfill application rows.
- A dedicated repair command defaults to read-only evidence validation and permits apply only for the exact R2 run, exact source-result evidence, stopped collector, released advisory lock, stable item/source/provenance counts, expected primary key, and unchanged prior checkpoint.

## Exact R2 recovery

The additive migration completed. The repair dry-run matched the target run `c8ab7a29-9832-434b-9607-ab0dffdcbebf` and sole source result `02125465-dc6c-5355-823c-989b485ed491`: HTTP 200, one request, 143,641 bytes, 10 observed entries, zero inserted, duplicates, or rejected entries. Update count was not persisted and remains unknown. Database counts before and after were 282 news items, 11 sources, and 282 provenance rows; no advisory lock was held.

The single evidence-bound apply changed the source result to `committed_checkpoint_failed` and finalized the run as `failed`, recording the primary checkpoint error and secondary unique-constraint failure. A second apply returned an idempotent no-op. No item, classification, provenance, source registry, checkpoint, or prior run evidence was edited. The old checkpoint remains authoritative: it still references run `0f800369-f4b3-4e3b-9065-11122462daa6` and SHA-256 `d1e1ba9196eb8db84ec0aa20e894bd8b80ec63b3c9700d609be67be7a7ebd371`. The R2 response digest was not persisted by the old collector, so advancing the checkpoint is not justified.

## Validation and runtime

- All 35 monitoring unit tests passed inside a read-only container with `--network none`, including six historical TypeError fixtures, bounded single-request behavior, checkpoint atomicity/recovery, duplicate-result prevention, finalization idempotence, and targeted-repair safeguards.
- Python compilation and `git diff --check` passed.
- Migration ran in a one-off API container; no API or collector service was restarted, and no scheduler or collector cycle was started.
- API health and dashboard returned HTTP 200. API reported 282 items, 11 sources, and 282 complete provenance records.
- All 39 container IDs, states, restart counts, start times, configured images, and published ports matched the pre-change snapshot. The collector remains stopped, the scheduler remains disabled, only News Monitor port `127.0.0.1:3001` is published, and no unrelated or OpenCTI container changed.
- All five Phase 8B-R2 runtime evidence files retain their original SHA-256 hashes. `sites.docx` and the source registry retain their baseline hashes.
- No secrets were staged, committed, or included in this report. Runtime evidence and offline Docker build recipes remain Git-ignored.

No new live cycle was run. Any future live cycle requires separate authorization; use the dedicated collector service and its writable state-volume mount.

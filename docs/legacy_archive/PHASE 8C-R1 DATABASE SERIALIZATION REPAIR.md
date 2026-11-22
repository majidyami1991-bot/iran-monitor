# Phase 8C-R1 database serialization repair

Status: **OFFLINE REPAIR COMPLETE; LIVE RSS BLOCKED BY PRIOR PHASE RESULT**.

## Reproduction and root cause

Phase 8C consumed its one permitted live cycle (`407d29ed-4ce9-45bc-abdc-61a6c2dfc938`). Eleven RSS responses were fetched once. Four sources contained only existing items and completed through the duplicate/update path. Seven sources reached the new-item insert path and failed seven times before SQL execution, while psycopg was adapting a JSONB parameter:

`collector.source_run` → `database_insert` → `news_item_provenance.evidence_json` → `provenance_payload.received_at`.

`received_at` was assigned `normalized_item.collected_at`, a timezone-aware parser datetime. The SQL statement was the `INSERT INTO news_item_provenance(..., evidence_json)` in `apps/api/collector.py`; psycopg's JSON dumper raised `TypeError` before PostgreSQL received the statement. The same item payload also crossed the `news_items.topics` and `item_classifications.topics` JSONB boundaries, so all JSONB boundaries are now normalized centrally. The four successful sources had no new insert candidate; they took the existing-item path and never bound the provenance JSONB payload. No update candidate was overwritten.

## Serializer contract

`apps/api/ops.py` now provides `to_json_compatible`, `canonical_json_dumps`, and `database_json`. They recursively preserve JSON scalar types, convert aware datetimes to UTC ISO-8601 `Z`, dates to ISO dates, UUIDs to lowercase canonical strings, Decimal values to exact fixed strings, Enums to their values, dataclasses and Pydantic models through controlled dumps, and lists/dicts recursively. Dictionary keys must be strings. Naive datetime/time, bytes, non-finite floats, unknown objects, and non-string keys fail closed with an object path such as `provenance_payload.received_at` without including the value.

Canonical hash serialization is separate from database JSON serialization. Both share the recursive normalizer; hashing fixes sorted keys, compact separators and Unicode handling, while database binding receives a schema-shaped normalized object through `Jsonb`. Existing fields are not deleted or stringified blindly. `default=str` is not used.

## Validation

- Seven evidence-faithful live source shapes were reproduced offline from the existing Phase 8A snapshots and the six historical failure fixtures. Before the repair, the provenance JSONB bind raises the same datetime TypeError; after the repair, all seven pass normalization and adapter binding in rollback transactions.
- One of the four previously successful duplicate-path sources was also forced through the insert/provenance path and passed.
- Temporal coverage includes UTC and non-UTC aware datetimes, DST edge time, microseconds, dates, nested dict/list/dataclass/Pydantic-compatible values, provenance, metadata, classification, source-result and checkpoint payloads, nulls, invalid objects, NaN/Infinity, UUID, Decimal, Enum and bytes.
- The offline monitoring suite and serialization suite pass in a network-disabled read-only container. A real PostgreSQL adapter test creates a temporary schema/table, binds `Jsonb(database_json(...))`, inserts and rolls back; production tables are never written.

No RSS, article, image, document or X request was made in this repair phase. The Phase 8C report and evidence remain unchanged. Production counts remain 282 items, 11 sources and 282 provenance rows; the prior run remains finalized `partial`, the collector remains stopped, scheduler remains disabled, and no new collection run is created.

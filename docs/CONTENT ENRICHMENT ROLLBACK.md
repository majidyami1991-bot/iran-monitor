# Content Enrichment Pilot — Rollback Guide

## Why rollback is low-risk here

Every schema change in this phase is additive (`CREATE TABLE IF NOT EXISTS`,
`ALTER TABLE ... ADD COLUMN IF NOT EXISTS` — all in the single `DDL` string in
`apps/api/ops.py`, run by `migrate()` at API startup). The pre-phase-3 code
(commit `59f309b`) never reads any of the new columns or tables, so it is
unaffected by their presence. This means rollback does **not** require a
database restore in the common case — stopping the new code is sufficient.

## Rollback levels

### Level 1 — stop the enrichment worker only

The worker (`apps/api/enrichment_worker.py`) is not a long-running service in
this pilot; it was invoked on demand (`docker exec ... python -c
"enrichment_worker.run_stage(...)"` / direct function calls). There is nothing
to "stop" beyond not invoking it again. RSS collection (`news-collector`) and
the existing news API/UI are on a fully separate code path and were never
restarted or otherwise touched by any enrichment run in this phase — verified
by continuous `news-collector` uptime throughout (42h+, unbroken).

### Level 2 — revert the API/web image to the pre-phase-3 commit

```
git checkout 59f309b -- apps/api apps/web-next
docker build -f apps/api/Dockerfile -t iran-monitor-news-news-api:rollback-pre-content-pilot .
docker build -f apps/web-next/Dockerfile -t iran-monitor-news-news-web:rollback-pre-content-pilot apps/web-next
docker compose -p iran-monitor-news -f deployment/news-monitor/compose.yml up -d --no-deps news-api news-web
```

(Substitute the built `:rollback-pre-content-pilot` tags into `compose.yml`'s
`image:` reference, or `docker tag` them onto `:latest`, matching the pattern
used for `iran-monitor-news-web:rollback-8b` in an earlier phase.) The
pre-phase-3 API never queries `news_item_content`, `news_item_translations`,
`news_item_media`, `item_classifications`, `news_events`,
`news_event_members`, or `enrichment_jobs` — those tables simply become
inert. `news_items` itself (the pre-existing table) is untouched by this
phase's schema changes.

### Level 3 — remove the enrichment data entirely

Only needed if the rolled-back product must not even store this phase's data
(e.g. a compliance requirement, not a technical one):

```sql
DROP TABLE IF EXISTS enrichment_jobs;
DROP TABLE IF EXISTS news_event_members;
DROP TABLE IF EXISTS news_events;
-- item_classifications predates this phase (used by v1 classification too) —
-- do not drop it; instead:
DELETE FROM item_classifications WHERE taxonomy_version LIKE '2.%';
ALTER TABLE news_item_content DROP COLUMN IF EXISTS content_type, DROP COLUMN IF EXISTS copyright_status, DROP COLUMN IF EXISTS unavailable_reason;
-- (repeat per column added this phase; see the DDL diff in ops.py for the full list)
```

Not exercised in this phase (rollback was never triggered — this section
documents the path, per the brief's requirement, without performing it against
production).

## Known defects found and fixed during this phase (informational — already fixed, not a rollback trigger)

These were found by running the pilot against real production data and are
already fixed and committed; listed here because a future rollback to any
intermediate commit *within* this phase's history (rather than to `59f309b`)
would reintroduce them:

1. **Article-extraction chrome misdetection** (5 bugs — void-element stack
   desync, two-stack desync, substring vs token class matching, `widget` and
   `banner` too generic) — `apps/api/article_extract.py`.
2. **Publisher-boilerplate false event clustering** — entity extraction scanned
   body text and picked up repeated bylines — `apps/api/clustering.py`.
3. **Generic-word false event clustering** — "netanyahu"/"reporter" shared
   between two unrelated stories — `apps/api/clustering.py`.
4. **Clustering's category-agreement dependency** — a true-positive pair
   scored below threshold once the classifier assigned it two different
   (legitimately independent) categories — `apps/api/clustering.py`.
5. **Orphaned event rows after a re-cluster** — a stale `news_events` row with
   a wrong `member_count` survived after its members were reassigned —
   `apps/api/enrichment_worker.py`.
6. **Startup migration clobbering v2 classification** — `ops.py:migrate()`
   unconditionally reclassified every item with the old v1 classifier on every
   API restart, silently reverting the pilot's v2 confidence/subtopic data.
   Confirmed live (two routine restarts during this phase actually reverted
   production data) and fixed.
7. **A classification-correction endpoint 500** — the write path reused a
   `fetchall()`-based read helper against a plain `INSERT`/`UPDATE` with no
   `RETURNING` clause.

All seven have a regression test or were re-verified live after the fix; see
`docs/CONTENT ENRICHMENT PILOT.md` §7 and `docs/EVENT CLUSTERING ALGORITHM.md`.

## Verification before declaring a rollback complete

- `GET /api/v1/health` returns `200` with the expected item count.
- `GET /api/v1/news` and `GET /api/v1/news/{id}` return `200` (the pre-phase-3
  shape if rolled back to Level 2, or the current shape with `pending`/absent
  enrichment fields if only Level 1).
- `news-collector` container uptime is unbroken across the rollback (confirms
  RSS collection was never affected).

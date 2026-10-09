# Local AI — incremental news sync 3001 → 3003 (2026-10-09)

## Status

| | |
|---|---|
| Sync tool | `scripts/news_sync.py` (commit `47a8dd7`), manual only |
| Runs so far | 2 dry runs, 1 trial (`--limit-new 20`), 1 full run, 1 idempotency re-run — all `succeeded`, executed 2026-10-09 13:29–13:35 UTC |
| Clustering-cycle check | **Complete.** 3003 re-clusters the synced items itself and is consistent with Production on every common event. |
| Scheduled sync | **Not enabled.** Proposal in §6 is waiting for permission. |
| Production / OpenCTI | **Read-only.** Nothing restarted, changed or written. |

## 1. Root cause of "no new news on 3003"

- 3003 had no collector and no sync.
- Its DB is a one-time `pg_dump` restore from 2026-10-07, on its own
  network and volume.
- Production kept collecting throughout: 82/82 runs succeeded in 24 h.
- The local-AI tests caused no collector failures.

## 2. Design

**Access**
- Host-mediated `docker exec psql`. No network link between the stacks.
- The Production session is read-only twice over:
  `PGOPTIONS=-c default_transaction_read_only=on` plus `BEGIN READ ONLY`.

**Change detection**
- `md5(row::text)` per natural key. Both databases are PostgreSQL 16.14
  with identical schemas.

**Transaction**
- All writes to 3003 happen in **one REPEATABLE READ transaction**.
- Inside that transaction, the protected tables are fingerprinted again.
  On any difference a `DO` block raises, so everything rolls back.

**One writer per table**

| Policy | Tables |
|---|---|
| Copied (upsert) | `sources`, `news_items`, `news_item_content`, `news_item_provenance` |
| Copied (upsert), never over a human lock | `item_classifications` (never overwrites `human_locked`) |
| Copied (insert only) | `news_item_media`, `collection_runs`, `source_run_results` |
| **Never written; 3003 computes them itself** | topics, topic history, `news_events`, `news_event_members`, `geo_mentions`. 3003's `experience.py` runs taxonomy 3.0.0 and clustering v2 2.0.0, plus briefings, stories and media v2 |
| **Protected (fingerprinted, must stay identical)** | translations and their history, assistant sessions and messages, AI logs and caches, X/social, key points, enrichment jobs, briefings, stories, alert rules, integrations, commodity prices, import runs, `schema_migrations` |

**Guards and records**
- `VERSION_GUARD` aborts if the `taxonomy_version` differs.
- Each run writes `news_sync_runs` (ai-db), plus
  `runtime/news-sync/<run>/run.json` and a backup CSV of every
  overwritten row (gitignored).

## 3. Runs

| Run | Mode | Result |
|---|---|---|
| `20261009T132933Z-ca7ae7`, `…133333Z-a5ea03` | dry-run | 290 new items. Changed: 12 sources (timestamps), 1 content (re-extraction), 22 classifications (`classified_at` only). 0 local-only rows, 0 translations whose source changed. |
| `20261009T133400Z-84b363` | apply `--limit-new 20` | +20 items, +20 content, +3 media, +20 provenance, +20 classifications; 6.6 s |
| `20261009T133457Z-c8f49f` | apply | +270 items, +270 content, +178 media, +270 provenance, +270 classifications, +156 collection runs, +1,872 source run results; updated 12 sources, 1 content, 22 classifications; residual 0 in every table; 6.9 s |
| `20261009T133518Z-9375d8` | apply (re-run) | **0 changes**, so the sync is idempotent; 5.9 s |

## 4. Verification after the runs

| Check | Result |
|---|---|
| Item count | 3003: 2,436 = Production: 2,436. Latest `collected_at` 13:31:56 UTC on both. |
| Duplicates | 0 duplicate `item_id`s, 0 duplicate URLs |
| Translations | 89 rows, md5 `4f530c47…`: identical before and after |
| Other protected tables | translation history 16, assistant sessions 11, messages 21: identical |
| Model contract | `apps/api/model_approvals.json` sha `c0b5b70f…`: unchanged |
| 3003 API | serves today's news |
| Production and OpenCTI containers | not restarted; healthy ("Up 21 hours") |

## 5. Clustering-cycle check

**3003 (what the sync feeds)**
- 3003's own jobs ran:
  - classified 20 items, then 270;
  - converted 117 legacy media rows to media v2;
  - re-clustered at 13:40:55 UTC → 80 events.
- Every item has a 3.0.0 topic (0 missing).
- Compared with Production's 67 events:

  | | Count |
  |---|---|
  | Events in both | **64, member sets identical in all 64** |
  | Only in 3003 | 16 (new items) |
  | Only in Production | 3 (their membership changed in 3003, so new event id) |

- Conclusion: the sync plus 3003's own clustering cycle produce consistent
  derived data.

**Production — separate finding, not changed**
- Production's events were last updated **2026-10-08 07:39:45 UTC**.
- 189 Production items have no topic assignment.
- **Cause, confirmed read-only:**
  - since the restart at **2026-10-08 16:46:54 UTC**, `news-api` has run
    image `9d1ee6d5`, the one tagged `rollback-pre-redesign` (built
    2026-09-27);
  - that image has **no `experience.py`**, so Production runs no topic,
    clustering, briefing or story jobs.
- This does not affect the sync: derived tables are never read from
  Production. It is a Production regression for its owner to decide on;
  nothing was changed.

## 6. Proposed schedule — NOT enabled, waiting for permission

| Item | Proposal |
|---|---|
| Interval | every 15 min, at :05/:20/:35/:50, i.e. a few minutes after each collector run |
| Mechanism | Windows Task Scheduler on the host, running `python scripts\news_sync.py apply` |
| Single instance | the task runs alone; a lock file prevents overlap |
| Stop on failure | any `failed` run disables the task; no automatic retry loop |
| Retention | keep `runtime/news-sync` run folders for 14 days |
| Safety | the `--limit-new 500` cap means an unexpected burst needs a manual run |
| Alerting | a weekly review of `news_sync_runs` |

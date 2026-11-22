# Iran Monitor Local AI — final acceptance (2026-10-09)

**System:** http://localhost:3003 (isolated stack `iran-monitor-local-ai`: `ai-db`, `ai-api`, `ai-web`, `ai-translator`).

**Result: `PARTIAL_WITH_BLOCKERS`.**
- Every feature runs and passed real tests.
- Automatic news intake every 15 minutes, plus the scheduled health monitor and backup, are not active. Registering Windows scheduled tasks was **denied** in this session ("Access is denied"). A ready, dry-run-tested script is waiting for the owner (§9).
- The translation model's quality remains below the automatic gate (disclosed in §4).

All figures were read from the live system at 2026-10-09 ~18:30 UTC (`runtime/final-acceptance/`, gitignored).

## 1. What is operational

| Capability | State | Evidence |
|---|---|---|
| News intake Production → 3003 | `news_sync` v1.1.0, read-only on Production, incremental, idempotent, capped (`--max-new`), schema guard, failures recorded | §2 |
| Ordered, up-to-date news, search, filters | home, `/news` (search, source, topic, window, translation status), detail | browser test D |
| English original + Persian translation | fa / EN / **bilingual** toggle (desktop header, mobile drawer); original always visible | D |
| Automatic local translation of new items | `ai-translator` (TranslateGemma 27B, pipeline v2.1 without placeholders), persistent queue, recovery after restart | §3, E |
| Translation status and quality shown | labels: «ترجمه خودکار ـ تأیید انسانی نشده», «ترجمه با هشدار کیفیت», «ترجمه رد شد», pending, error | D |
| Assistant on real news | v1.3.2, qwen3:8b, verbatim citations, controlled refusals, label «آزمایشی ـ پاسخ مبتنی بر منابع خبری موجود» | §5, C |
| Topics, event clusters, related news | 3003's own jobs (taxonomy 3.0.0, clustering v2): 82 events, 0 items without a topic | §6 |
| Admin panel `/admin` | sync, translation queue, models, assistant, clustering, backup, host health, alerts; real values only, "unknown" when absent | D |
| Health, backup, logs | scripts verified; manual backup `VERIFIED`; **schedules not registered** | §8 |
| Persian RTL, responsive | `dir=rtl`, `lang=fa`; no horizontal overflow at 1440 and 390 px | D |

## 2. News sync

**`scripts/news_sync.py` v1.1.0**

| Feature | Detail |
|---|---|
| Read-only on Production | Every Production session runs in read-only mode |
| Atomic apply | One REPEATABLE READ transaction in 3003 |
| Protected tables | Translations, history, assistant, X/social, AI logs, contracts and derived tables are fingerprinted inside the transaction; any difference rolls everything back |
| Change detection | Natural keys + row hashes, so a re-run is idempotent |
| Schema guard (new) | Column layout must match on both sides, else stop |
| `--max-new N` (new) | All changes applied, at most N new items (oldest first), the rest deferred to the next run |
| Backup (new) | Pre-images only of the rows an apply updates; a no-op run writes no data file. Earlier each run wrote 28 MB; now about 0.8 MB, and 0 for a no-op |
| Failure recording (new) | Failed runs are recorded in `news_sync_runs` |

**Wrapper `scripts/news_sync_scheduled.py`**
- Lock file: concurrent runs skipped, a stale lock taken over.
- "Docker unreachable" is skipped and logged.
- A 15-minute timeout.
- JSONL log.

**Runs, all real**

| Run | Result |
|---|---|
| Cap test `--max-new 5` | 5 inserted, 12 deferred |
| Catch-up | 12 inserted |
| Re-run | 0 changes |
| 18:07 UTC | 12 new items |
| Total | 3003 holds 2,465 items, 116 in the last 24 h |

Last successful sync: 18:07:11 UTC; 0 failures in 24 h.

**Tests:** `tests/scripts/test_news_sync.py` 6/6 (schema guard add/type change, cap, exclusive flags, failure recorded only in 3003).

**Schedule:** **not active.** Task Scheduler registration was denied twice (`Register-ScheduledTask` and `schtasks`, "Access is denied"). No workaround was attempted. The owner registers it with `scripts/register_local_ai_tasks.ps1` (§9).

## 3. Translation (TranslateGemma 27B, pipeline V2 without placeholders)

**Model and contract (append-only)**
- `translategemma-27b-ollama0401-llamacpp-90696e5eca44`.
- It remains `rejected_quality_gate` as a quality verdict.
- On the owner's instruction it received a separate event, `lab_activated`. That is **not a quality approval**.
- It is servable only where `LOCAL_AI_LAB_MODE=true` (the 3003 stack). Outside lab mode no translation model is active (unit test).
- Re-attested with reload on 2026-10-09 (all checks passed).

**Pipeline v2.1** (`translation_v21.py`; the frozen v2.0 file is unchanged)

| Addition | Detail |
|---|---|
| Terminology | mobilisation → «بسیج», mechanised → «مکانیزه» |
| Number forms | Persian number words, «N هزار» forms and ordinals are read as numbers |
| Scale | an added scale is now a conflict |

Regression on the 175 stored 27B outputs (no new model run):

| | Accept | Uncertain | Critical |
|---|---|---|---|
| v2.0 | 90 | 50 | 35 |
| v2.1 | 92 | 51 | 32 |

- Both errors v2.0 accepted (H25, M01) are now rejected.
- All 8 audited genuine critical errors are still rejected.
- The 4 newly accepted items are exactly the 4 the earlier audit identified as correct translations falsely failed.
- **Caveat:** these rules were derived from the same audited items, so this is not independent evidence.

**Worker `translation_worker_v2.py`** (service `ai-translator`, `restart: unless-stopped`)

| Aspect | Detail |
|---|---|
| Fields translated | title + **lead of the summary** (whole sentences up to 600 characters) |
| Why only the lead | a full 2,000-character summary took 254 s and mostly failed QC; the UI says when only the lead is translated, and the full English text stays visible |
| Queue order | on-demand requests > items from the last 24 h > 3-day backfill; older items only on demand (button on the detail page) |
| Concurrency | one inference at a time; the inference lock is shared with the assistant, with a gap between calls |
| Retries | `translation_error` retried after 2^n minutes, at most 3 times |
| QC crash on one item | becomes an error for that item only |
| Database errors | back off and are recorded in the heartbeat |
| Statuses | `translated_auto` (ACCEPT), `qc_warning` (REJECT_UNCERTAIN), `qc_failed` (REJECT_CRITICAL), `translation_pending`, `translation_error`, `not_required` |
| History | every outcome appends to `news_item_translation_history` |

**Display policy (API-side, tested in the browser)**

| Status | Shown where |
|---|---|
| `translated_auto` | as the translation, labelled «ترجمه خودکار ـ تأیید انسانی نشده» |
| `qc_warning` | only next to the original, with a warning |
| `qc_failed` | its text **never leaves the API**; the English original is shown with «ترجمه رد شد» |

A legacy cloud-pilot translation that the API still showed as `available` was re-queued through 27B v2.1; its old text remains in the history.

**Live results so far** (177 model calls since 16:05 UTC; average **36.6 s per call**, about 46 items per hour)

| Field | translated_auto | qc_warning | qc_failed | pending |
|---|---|---|---|---|
| Title | 7 | 52 | 30 | 355 |
| Summary (lead) | 4 | 39 | 45 | 355 |

**Read honestly:** only about 8 % of titles pass QC without objection. Most outputs are uncertain or rejected, so in Persian mode most items still show their English original. QC acceptance is not proof of correctness, and nothing has been human-reviewed.

## 4. Translation quality status

`AUTO_GATE_FAIL` / `BLOCKED_MODEL_QUALITY` as a quality verdict, unchanged. It operates as `LAB_ACTIVATED` behind the v2.1 QC filter, labelled "not human-verified", in 3003 only. Nothing was moved to 3001.

## 5. Assistant v1.3.2 (qwen3:8b, extractive)

**Changes, with v1.3.1 and its evidence kept**
1. **Same-event link through a rare shared code** (≤ 5 corpus titles, e.g. FP-7) when **every** other same-event condition holds: ≤ 72 h, shared event type, ≥ 2 entities with ≥ 1 non-country, no place conflict.
2. Broad coverage questions list up to 8 verified events (was 5).
3. In `entity_lookup` only: an extraction containing an altered quote is discarded whole (validator unchanged), and one fresh extraction runs without that record; the answer discloses it.

Versions: relevance gate v1.1.0, validator v1.3.2. Contract: v1.3.1 `superseded`; v1.3.2 `proposed` → `pending_human_review` → `lab_activated` (owner).

**Gates (same harness and model; translator paused during the gate)**

| Gate | Result |
|---|---|
| Synthetic | **14/14**, including the false-merge guards S02–S04 |
| Real DB, first run | 18/19: R14 refused because the model altered a number (€75,000 million) while quoting; safety held |
| Real DB, after fix 3 | **19/19** |
| Citations | **48/48** quotes verbatim against the original records |

- R12 FP-7, refused in v1.3.1, is now answered from both outlets.
- R01 F/A-XX cites 4 sources.
- R03, R10 and R11 still refuse.

**Unit tests:** 99/99 assistant tests. The place-conflict test uses a real geographic conflict: Michigan vs Spangdahlem, with a same-place control. The earlier vacuous assertion was removed.

**Known limitation:** the Persian lexicon (v1.1.0) lacks some words. For example, a question containing «بمب‌افکن» or «مجهز» is refused with `unresolved_terms` (a safe refusal, not a wrong answer). Expanding it needs v1.3.3 and a new gate.

## 6. Classification and clustering (3003)

**Classification**
- 3003's hidden startup reclassification is **disabled** (`CLASSIFICATION_STARTUP_BACKFILL=false`).
- `item_classifications` mirrors Production's collector via the sync.
- The new append-only `item_classification_history` (trigger) records every change and its writer, e.g. `news_sync:<run_id>`: 12 rows so far, all from the 18:07 sync.
- Human-locked rows are never overwritten (sync rule).

**Topics and events:** computed locally (taxonomy 3.0.0, clustering v2): 82 events, last update 18:16 UTC, 0 items without a topic.

## 7. End-to-end tests (real data, no fabricated news)

| Test | Result |
|---|---|
| **A — intake** | Production item `a93b6ee1…` (TWZ, "B-52 To Get Stealthy AGM-158C Long-Range Anti-Ship Missiles", collected 18:01:44) arrived in 3003 in the 18:07 sync. Id, source, times and title/summary hashes are identical in both DBs. **PASS** |
| **B — translation** | Same item, queued by the UI's priority request and translated by 27B v2.1 in about 2 minutes. Both fields `qc_failed`: codes transliterated, an added number; summary with added entities. The page shows the English original with the rejection notice, and **no rejected Persian text appears anywhere** (browser check). Correct behaviour; **PASS** (a failure is not marked as success). For display, `translated_auto` (`09d3bb16…`) and `qc_warning` (`67341dd3…`) items were checked in fa and bilingual modes. |
| **C — assistant** | «درباره موشک AGM-158C و B-52 چه گزارش شده است؟» → an answer citing exactly `a93b6ee1…` (TWZ) with a quote verified verbatim in the stored summary. Unsupported «سقوط F-35 در آلاسکا» → exact refusal sentence (`no_relevant_record`); prediction question → `out_of_contract_prediction`. **PASS.** Note: two earlier test questions sent with a wrong encoding (Persian lost) remain as sessions in the 3003 DB; nothing was deleted. |
| **D — browser** (real Edge, 1440 and 390 px) | `tests/ui/final-acceptance-qa.cjs`: **41/41**. Home, search (every result contains the term), filter labels, detail in three statuses, language toggle (mobile via the drawer), assistant answer and refusal, admin panel, RTL, no overflow, **0 console errors, 0 failed local requests**. Two real defects found by the test and fixed (legacy translation shown as valid; mobile toggle). Two vacuous assertions in the test itself were replaced. |
| **E — recovery** | `docker kill` of the translator mid-call → on start `recovered: ['6cca2c08…']`; the item completed. Graceful stop → 0 rows left in `processing`. Sync with Docker unreachable → `skipped: docker_unreachable`. Failed apply → recorded `failed` in 3003 (unit test). **PASS** |
| **F — no disruption** | 20 Production/OpenCTI containers identical to the baseline (image, state, StartedAt, RestartCount). 3001 → 200/200. OpenCTI healthy. Collector: 11 runs since the mission start, all `succeeded`. 23/25 Production fingerprints unchanged; `sources` and `news_item_content` changed only through the collector's own runs, as in earlier phases. **PASS** |

## 8. Monitoring and backup

**Monitoring**
- `health_monitor.ps1` (read-only) ran manually into `runtime/ops-status/health`, and the admin panel reads it.
- **Not scheduled** (permission). The admin panel therefore shows `health_monitor_not_running` once the output is older than 10 minutes. This is honest, not hidden.

**Backup of 3003**
- `scripts/backup_local_ai.py` produced a `pg_dump` (sha256 `472caafd…`).
- The **restore test in an isolated throwaway container** (no network) gave `VERIFIED`: 0 errors, row counts identical.
- Second copy on `D:\IranMonitorBackups\local-ai` re-hashed OK.
- Nothing deleted. **Not scheduled** (permission).
- D: is the same host, so this is **not off-site**.
- An earlier full dump (`ai-db-20261009T154313Z.dump`, sha `34fcbe6b…`) was taken before any change.

**External heartbeat / off-site storage:** not connected (needs an account or credential; none invented).

**Open infrastructure risks (not fixed, no claim otherwise)**
- Docker Desktop runs only after the Administrator signs in.
- 16 unclean host resets in 47 days, plus WHEA-17 PCIe errors; cause unknown.
- BIOS, firmware, PCIe, memory and auto-logon were not touched.

## 9. Actions for the owner

1. Run `scripts/register_local_ai_tasks.ps1` (dry-run with `-WhatIf` verified). This activates:
   - the 15-minute news sync;
   - the 2-minute health monitor;
   - the daily 3003 backup at 03:30.

   All tasks run only while the user is signed in, the same as Docker Desktop. This removes the main blocker for `PASS_WITH_DISCLOSED_LIMITATIONS`.
2. Human review of translations and assistant answers. Both are labelled as not human-verified.
3. Decisions on the external heartbeat and off-site backup, and on the infrastructure plan's phase 2 (hardware/firmware, Docker auto-start).

## 10. Rollback (3003 only)

| What | How |
|---|---|
| Images | `iran-monitor-local-ai-{api,web}:pre-final-20261009` (previous `:dev`) |
| Database | dump `runtime/final-acceptance/backup/ai-db-20261009T154313Z.dump` |
| Code | `git revert 90ee50e` |
| Models | append a `revoked` event for either approval; outside lab mode nothing is servable anyway |

## 11. Commits (branch `feature/local-gemma-translation-assistant`, local only, no push or merge)

- `90ee50e` — operational 3003 lab (sync v1.1.0, translation worker + v2.1, contract events, assistant v1.3.2, API/UI, admin, classification history, backup script, tests)
- this report (next commit)

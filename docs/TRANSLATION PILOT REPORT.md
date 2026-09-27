# Stage B — Controlled Title and Summary Translation Pilot

Branch `feature/iran-monitor-foresight-platform`. Stage A commit `b7d63a4`.
This report covers Stage B only: proving the real, end-to-end path
`translate_worker → ai_gateway → anthropic_adapter → validation →
PostgreSQL → API → UI → review queue` for title and summary translation of
up to 20 items.

## Outcome: BLOCKED_PROVIDER_NOT_CONFIGURED

No Anthropic API key is configured anywhere in this environment. Per this
stage's own explicit rule ("اگر کلید موجود یا معتبر نیست ... هیچ
provider call اجرا نکن ... وضعیت را BLOCKED_PROVIDER_NOT_CONFIGURED ثبت
کن ... متوقف شو"), **zero provider calls were made and zero translation
records were written.** This is the correct, valid outcome for the current
environment state, not a failure — the same standard already applied and
accepted in the Content Intelligence phase's own pilot.

Live confirmation (`GET /api/v1/ai/provider-status`, 2026-09-27):
```json
{"mode": "disabled", "provider": null, "api_key_configured": false,
 "models": {"translation": ""}, "daily_budget_usd": null}
```
`.env` was checked directly for variable **names only** (never values):
`AI_PROVIDER` and `AI_API_KEY` are both absent/empty. No value was printed,
requested from the user in chat, logged, or committed at any point.

**To unblock**: set `AI_PROVIDER=anthropic` and a real `AI_API_KEY` in
`E:\Iran monitor\.env` (already gitignored), plus `AI_MODEL_TRANSLATION` to
an approved Anthropic model — see `docs/AI PROVIDER CONFIGURATION.md`. No
other action is needed on the user's part; this document and
`docs/TRANSLATION OPERATIONS RUNBOOK.md` describe exactly what runs next
once that's done.

## 1. Baseline (recorded before any change)

| Metric | Value |
| --- | --- |
| Branch / HEAD at start | `feature/iran-monitor-foresight-platform` / `b7d63a4` |
| Git status at start | clean |
| `news_items` | 1,057 (grew to 1,059 by report time — normal collector activity, 900s interval, zero manual RSS cycles) |
| `sources` | 12 |
| `news_item_translations` | 80 rows, all `status='pending'` (pre-existing, from a phase before the AI Gateway existed) |
| `collection_runs` | 371 |
| Collector scheduler | `NEWS_COLLECTION_ENABLED=true`, interval 900s — unchanged throughout |
| `ai_requests_log` / `ai_response_cache` | 0 / 0 |
| Docker (news stack) | 4/4 healthy |
| OpenCTI (14 containers) / `mlw-*` (2) / `plane-preview-*` (7) | All running, untouched |
| Ports | `127.0.0.1:3001` (web) unchanged; no new port opened |

Baseline file hashes (SHA-256) recorded before any edit:
`translate_worker.py 3d15f3b8…`, `ai_gateway.py 3721a232…`,
`content_intelligence.py d1e3ba18…`, `content_validator.py 2ab435f8…`,
`ops.py 1b3c47e3…`, `compose.yml 320c65ac…`, `.env.example 7904a552…`
(full 64-char digests in the session's command log; truncated here per this
stage's "no need for the full public report to carry secrets or excess
detail" framing — none of these are secrets, this is just a readability
choice).

## 2. Architecture check (§3)

Searched `apps/api/*.py` for any direct Anthropic/OpenAI call outside
`ai_gateway.py`: **none found.** Every generative call site
(`content_intelligence.py`, `enrichment_worker.py`, `translate_worker.py`)
imports `ai_gateway`/`content_intelligence` only.

**One real defect found and fixed (minimal, per §3's own instruction to fix
before the pilot):**

1. **`deployment/news-monitor/compose.yml` never passed `AI_*` variables
   into `news-api` or `news-translate`.** `news-api`'s environment block
   only set `DATABASE_URL`; `news-translate`'s block still passed the
   retired pre-Gateway names (`NEWS_TRANSLATION_PROVIDER`,
   `NEWS_TRANSLATION_API_KEY`, …) that `translate_worker.py` no longer
   reads since the Content Intelligence phase's migration onto the Gateway.
   Practically: **setting `AI_API_KEY` in `.env` would have had zero effect**
   on the running containers until this was fixed. Fixed by passing through
   `AI_PROVIDER`/`AI_BASE_URL`/`AI_API_KEY`/`AI_MODEL_TRANSLATION`/
   `AI_MODEL_SUMMARY`/`AI_REQUEST_TIMEOUT`/`AI_MAX_CONCURRENCY`/
   `AI_DAILY_BUDGET_LIMIT` to both services (the full model set also to
   `news-api`, since its `/api/v1/ai/status` and `/review/content/.../regenerate`
   endpoints need the same config); removed the dead `NEWS_TRANSLATION_*`
   mapping from `news-translate`.
2. **`translate_worker.py`'s `summary` field mixed translation with
   summarization.** `source_text()` returned `(item['body'] or
   item['summary'] or '')` — preferring the *extracted article body* over
   the source's own summary — and `main()` called `ci.summarize_news()`
   (an AI-composed summary from whatever text it got) rather than
   `ci.translate_to_persian()`. A field named `translated_summary_fa` was
   therefore capable of silently being an AI-authored rewrite of the full
   article, not a faithful translation of `original_summary` — a direct
   violation of this stage's own rule ("ترجمه با خلاصه‌سازی مخلوط نشود").
   Fixed: `source_text()` now returns the source's own summary only (never
   falls back to body); `main()` now calls `translate_to_persian()` for the
   `summary` field; when the source has no real summary, the field is
   recorded as `status='source_summary_missing'` with **zero Gateway calls**
   rather than inventing content from the body.

Both fixes are contained to `translate_worker.py` and `compose.yml` —
`enrichment_worker.py` (the general, already-approved content-enrichment
pipeline, which legitimately does use body text for its own `summary`/
`executive_summary`/`why_it_matters` fields, per
`docs/CONTENT INTELLIGENCE ARCHITECTURE.md`) was not touched, since Stage B
names the Translation Worker specifically and restricts input to
title+original_summary only.

**Regression test added**: `tests/monitoring/test_translate_worker.py` (5
tests), reproducing the exact defect (body preferred over summary) and
proving the fix. Full offline suite: **222/222 passing** (up from 217),
verified via the Docker `test` build stage — a hard gate, not a claim.

Neither fix was deployed to the running production containers this stage —
committed and test-verified, but redeploying `news-api`/`news-translate`
now would be an unnecessary restart with no operational benefit while the
provider remains unconfigured (per §13's explicit rule against unnecessary
restarts). Deployment happens naturally the next time this environment is
rebuilt, or explicitly when Stage B resumes with a real key.

## 3. Content contract (§4)

For this pilot: `title` → `translate_to_persian(original_title)`. `summary`
→ `translate_to_persian(original_summary)` **only when `original_summary`
is genuinely present**; otherwise `status=source_summary_missing`, no call,
no fabrication. `executive_summary_fa` and `key_points_fa` are **not
generated this pilot** — both require body text as their evidence source
per their existing design (`docs/CONTENT INTELLIGENCE ARCHITECTURE.md`),
and Stage B's content contract explicitly restricts processing to
`original_title`/`original_summary` only ("متن کامل مقاله ترجمه نشود"). This
is a scope boundary, not an oversight.

Required metadata (`provider`, `model`, `prompt_version`,
`output_schema_version`, `input_hash`, `generated_at`, `latency`, token
usage, estimated cost, `quality_score`, `quality_flags`,
`validation_status`, `review_status`, `supersedes`) is already carried by
the existing `news_item_translations` / `news_item_translation_history`
schema from the Content Intelligence phase — no new columns were needed for
this pilot's scope.

## 4. Candidate selection (§5)

Deterministic, reproducible, logged query executed live against production
(read-only): source-spread round robin (one item per source before a second
pass), deduplicated by `canonical_url`, excluding items with an existing
`status='available'` translation, filtered to English titles via the
deterministic `content_intelligence.detect_language()` (confidence ≥ 0.6 —
no AI call), summary-present items prioritized over summary-missing ones,
`item_id` as the final tiebreak. Full query and result set:
`runtime/evidence/translation-pilot/candidate-manifest.json` (gitignored,
per §5's instruction — contains `item_id`/`source_id`/`hostname`/
`original_language`/`summary_present`/`input_hash` only, no full headline
text, no secrets).

| | |
| --- | --- |
| Candidate pool after SQL + language filter | 1,059 |
| Selected | **20** |
| Distinct sources represented | **12** (all of them) |
| Items with a real source summary | 19 |
| Items with no source summary | 1 (`www.missiledefenseadvocacy.org`, `source_summary_missing` expected) |
| Duplicate `canonical_url` in the selection | 0 |

## 5. Dry run (§6)

Full report: `runtime/evidence/translation-pilot/dry-run-report.json`.
Summary:

| | |
| --- | --- |
| Provider calls made | **0** |
| Database writes made | **0** |
| Estimated calls if run | 39 (20 title + 19 summary; 1 skipped as `source_summary_missing`) |
| Estimated token ceiling / max cost | **null — cannot be honestly estimated.** `AI_MODEL_TRANSLATION` is unset; cost estimation requires a recognized model name (see `docs/AI GATEWAY.md`, Cost tracking) — an unrecognized/absent model estimates `None`, never a guessed number. |
| Daily budget remaining | not_configured |
| Prompt / schema version (translation) | `1.0.0` / `1.0.0` |
| Cache hits / misses if run today | 0 / 39 (`ai_response_cache` is empty) |
| Input-hash reproducibility | verified (`content_hash()` called twice on identical input produced identical output) |
| Rollback readiness | ready — no schema change this stage; the append-only + `human_reviewed`-lock write pattern was already proven in the Content Intelligence phase |
| Provider contract validity | valid — the full call chain is wired and offline-tested; the only missing piece is a real key |

None of §6's explicit stop conditions (invalid schema, insufficient budget,
incomplete cache key, non-reproducible input hash, rollback not ready,
invalid provider contract) are true. **The only blocker is the Provider
Gate itself (§2)** — which independently and unconditionally requires
stopping before any real call regardless of dry-run readiness.

## 6. Sections not reached this run

Because of the Provider Gate, the following sections were **not**
performed, per this stage's own explicit instruction not to fabricate a
substitute for them:

- §7 Quality control on real output — no real output exists.
- §8 The single pilot invocation — not run.
- §9 Publish policy — nothing was published.
- Five-sample human evaluation (§12) — no real translation exists to
  evaluate; evaluating a deterministic/placeholder output and calling it a
  translation-quality assessment would violate this stage's core rule.

## 7. Production control (§13) — verified after this work

| Check | Result |
| --- | --- |
| `news_items` count | 1,057 → 1,059 (normal collector growth only) |
| `sources` count | 12 → 12 (unchanged) |
| `news_item_translations` | 80 rows, unchanged (all still the pre-existing `pending` rows) |
| `ai_requests_log` / `ai_response_cache` | 0 / 0 (unchanged) |
| Collector scheduler | unchanged, never paused or reconfigured |
| Manual RSS cycles started | 0 |
| Translation scheduler enabled | No (`news-translate` remains `profiles: [tools]`, never auto-run) |
| OpenCTI (14 containers) | unchanged, running |
| `mlw-*` / `plane-preview-*` | unchanged, running |
| Unnecessary restarts | 0 — `news-api`/`news-web`/`news-collector`/`news-db` were never restarted this stage |

## 8. Final report fields (§16)

```
BASELINE_GATE_PASSED: true
HEAD_BEFORE: b7d63a4
PROVIDER_CONFIGURED: false
PROVIDER_MODE: disabled
PROVIDER_NAME: null
MODEL: null (AI_MODEL_TRANSLATION unset)
PROMPT_VERSION: 1.0.0 (translation, ready)
OUTPUT_SCHEMA_VERSION: 1.0.0 (translation, ready)
PILOT_CANDIDATE_COUNT: 20
PILOT_ATTEMPTED_COUNT: 0
PROVIDER_CALL_COUNT: 0
RETRY_COUNT: 0
CACHE_HIT_COUNT: 0
CACHE_MISS_COUNT: 0
TITLE_TRANSLATED_COUNT: 0
SUMMARY_TRANSLATED_COUNT: 0
SOURCE_SUMMARY_MISSING_COUNT: 1 (identified in candidate set; not yet written to DB)
TRANSLATION_SUCCEEDED_COUNT: 0
TRANSLATION_FAILED_COUNT: 0
TRANSLATION_REJECTED_COUNT: 0
NEEDS_REVIEW_COUNT: 0
MACHINE_PUBLISHED_COUNT: 0
HUMAN_REVIEWED_COUNT: 0
NUMBER_PRESERVATION_PASSED: n/a (no real output)
ENTITY_PRESERVATION_PASSED: n/a (no real output)
NEGATION_PRESERVATION_PASSED: n/a (no real output)
UNSUPPORTED_CLAIM_COUNT: n/a (no real output)
SCHEMA_VALIDATION_PASSED: n/a (no real output; validator itself is offline-tested, 23 fault-injection tests, unchanged this stage)
AVERAGE_LATENCY_MS: n/a
INPUT_TOKEN_COUNT: 0
OUTPUT_TOKEN_COUNT: 0
ESTIMATED_COST: 0 (no calls made)
DAILY_BUDGET_REMAINING: not_configured
DATABASE_ITEM_COUNT_BEFORE: 1057
DATABASE_ITEM_COUNT_AFTER: 1059 (normal collector growth, not from this pilot)
DATABASE_TRANSLATION_COUNT_BEFORE: 80
DATABASE_TRANSLATION_COUNT_AFTER: 80 (unchanged)
ORIGINAL_FIELDS_UNCHANGED: true
TRANSLATION_HISTORY_APPEND_ONLY: true (no writes attempted, therefore none violated; pattern proven in the Content Intelligence phase)
REVIEW_QUEUE_READY: true (built and verified in the Content Intelligence phase; nothing new to review from this run)
UI_MACHINE_TRANSLATION_LABEL_VERIFIED: true (existing; no new output to display this run)
RSS_MANUAL_CYCLES_STARTED: 0
COLLECTION_SCHEDULER_CHANGED: false
TRANSLATION_SCHEDULER_ENABLED: false
OPENCTI_UNCHANGED: true
UNRELATED_CONTAINERS_UNCHANGED: true
SECRETS_EXPOSED: none
TEST_COUNT: 222
TESTS_PASSED: 222
PLAYWRIGHT_STATUS: not run (no new UI output to verify this stage; existing UI states were already verified in the Content Intelligence phase and are unchanged)
GIT_COMMIT_CREATED: true
GIT_COMMIT_HASHES: see docs — recorded at commit time
STAGE_B_STATUS: BLOCKED_PROVIDER_NOT_CONFIGURED
NEXT_SAFE_ACTION: set AI_PROVIDER=anthropic and a real AI_API_KEY in .env (never in chat), then re-run Stage B's dry run and, if it stays green, the single pilot invocation
```

## 9. Five-sample manual evaluation

Not performed — no real translation output exists. §12 explicitly asks for
manual evaluation of pilot *outputs*; evaluating placeholder or
deterministic-mode text and presenting it as translation quality would
violate this stage's core rule against manufacturing evidence of success.
This section will be completed the moment a real pilot run produces output.

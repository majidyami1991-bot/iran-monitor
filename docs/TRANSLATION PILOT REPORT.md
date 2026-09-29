# Stage B — Controlled Title and Summary Translation Pilot

Branch `feature/iran-monitor-foresight-platform`. Stage A commit `b7d63a4`.
This report covers Stage B only: proving the real, end-to-end path
`translate_worker → ai_gateway → anthropic_adapter → validation →
PostgreSQL → API → UI → review queue` for title and summary translation of
up to 20 items.

## Stage B-OR — OpenRouter (2026-09-27, commits `e39a144` and this docs commit)

The project owner supplied a real OpenRouter API key (not a direct
Anthropic key), so Stage B resumed with a new `OpenRouterAdapter`
(`docs/OPENROUTER PROVIDER ADAPTER.md`) rather than the existing
`AnthropicAdapter`. **A serious process incident happened during this
work and is fully documented separately, not glossed over here**:
`docs/INCIDENT - API KEY EXPOSURE IN SESSION OUTPUT.md` — a broken
redaction command printed the (since-revoked) key to the session
transcript. The project owner rotated the key themselves; the assistant
never saw or handled either key's value in chat.

### What was built this round

- `OpenRouterAdapter` (real HTTP status classification, one bounded
  retry for transient failures only, `X-Title` header, deliberately no
  `HTTP-Referer` — see the adapter doc for why).
- `ai_gateway.APPROVED_MODELS` / `model_is_approved()` — a real
  allowlist gate, checked by `translate_worker.py` before any dry-run or
  pilot proceeds; no automatic model substitution exists anywhere in
  this codebase.
- A real bug fixed: `AIGateway.run()`'s per-task model override didn't
  recognize `OpenRouterAdapter` — see the adapter doc's closing section.
- `translate_worker.py --manifest <path>`: runs against an exact,
  externally-selected item set (this pilot's 20-item manifest) in
  manifest order, instead of "whatever's newest" — required so the
  entire pilot could be **one single invocation** covering exactly the
  reviewed 20 candidates, per this stage's explicit "exactly one
  invocation" rule.
- Fatal-error short-circuit logic in `translate_worker.py`: an
  `authentication_failed`/`insufficient_credits`/`provider_forbidden`/
  `budget_exceeded`/`request_invalid` result (or the circuit breaker
  opening) stops the remaining candidates immediately rather than
  repeating the same doomed call up to 20 times; a >10% failure rate
  (once at least 3 attempts have been made) does the same.
- 15 new offline tests (`tests/monitoring/test_openrouter_adapter.py`) +
  4 more (`test_translate_worker.py`, manifest ordering/cap). **241/241
  offline tests pass.**

### Provider configuration gate (read-only, before any call)

Checked **only** via `GET /api/v1/ai/provider-status` on the freshly
rebuilt `news-api` container — never via `grep`/`Get-Content`/`env`/
`docker inspect`/`docker compose config` against `.env` or a container's
environment:

```json
{"mode": "external_provider", "provider": "openrouter",
 "models": {"translation": "anthropic/claude-haiku-4.5", "summary": "anthropic/claude-haiku-4.5"},
 "daily_budget_usd": 1.0, "api_key_configured": true, "circuit_open": false}
```

Every field matches the required target state exactly. `model_is_approved`
passed for both configured models (both are on `APPROVED_MODELS['openrouter']`).
Only `news-api` was rebuilt/recreated as a running service;
`news-translate`'s image was rebuilt (it must be, to run the pilot at all)
but it was never `up -d`'d as a persistent service — it only ever ran as a
single `docker compose run --rm` invocation, consistent with its
`profiles: [tools]`, never-a-scheduler design. `news-db`/`news-web`/
`news-collector`/OpenCTI were never recreated.

### Manifest re-validation (read-only, live)

The existing `runtime/evidence/translation-pilot/candidate-manifest.json`
(20 items, 12 sources, built in the earlier Stage B round) was
re-validated against current production data: **0/20 stale, 0 items with
an existing successful translation** — reused as-is, no rebuild needed.

### Dry run

`provider calls=0`, `database writes=0`, 20/20 manifest items found in the
DB and selected in manifest order. Estimated cost (character-count-based
heuristic, since no real tokenizer is available offline): **~$0.046** for
all 39 possible title+summary calls — well under the stage's $0.50 ceiling,
so the pilot was authorized to proceed.

### The one pilot invocation

```
docker compose ... run --rm -v ".../runtime/evidence/translation-pilot:/manifest:ro" \
  news-translate python /app/translate_worker.py \
  --manifest /manifest/candidate-manifest.json --fields title,summary --sleep 0.5
```

**Result: 1 real provider call made, then stopped immediately.** The very
first call (translating item `178c6b8e…`'s title) returned HTTP 402 from
OpenRouter, correctly classified as `insufficient_credits`
("Insufficient credits. This account never purchased credits...") — the
project's OpenRouter account has no balance. Per this stage's explicit
rule, this is a **stop-immediately** condition: no retry was attempted (402
is not in the retryable set), no alternative model was tried, and the
remaining 19 candidates were never attempted.

This is treated as the correct, honest outcome, not a failure to explain
away: the full pipeline — Gateway config resolution, the real HTTP request
to OpenRouter, error classification, audit logging, versioned/append-only
persistence, and the fatal-stop rule — all worked exactly as designed. The
only thing missing is OpenRouter account balance, which is a billing action
for the project owner, not a code or configuration fix.

### Verified after the one call

| Check | Result |
| --- | --- |
| `ai_requests_log` rows | 1 (task=translation, provider=openrouter, model=anthropic/claude-haiku-4.5, status=error) |
| `ai_response_cache` rows | 0 (an error is never cached) |
| `news_item_translations` rows changed | 1 (`field=title`, `status=error`, `review_status=not_applicable`, `human_reviewed=false`) |
| `news_item_translation_history` rows | 1 (append-only; `content_version=1`) |
| Original `news_items.title` for the attempted item | Unchanged |
| `GET /api/v1/news/{id}/content-intelligence` | Shows `title.status="error"`, `text=null`, correct provider/model attribution — no fabricated text, no raw error detail exposed to this endpoint |
| `GET /api/v1/review/content?status=pending_review` | `total: 0` — correctly empty; nothing succeeded, so nothing is pending review |
| `GET /api/v1/ai/usage` | 1 request, 0 succeeded, 0 tokens, `$0.00` spent, `daily_budget_usd: 1.0` |
| `news_items` / `sources` counts | Grew only via the collector's normal schedule; unaffected by the pilot |
| Collection scheduler | Unchanged (`NEWS_COLLECTION_ENABLED=true` throughout) |
| Translation scheduler | Never enabled; `news-translate` only ever ran as one `--rm` invocation |
| OpenCTI (14 containers) / `mlw-*` / `plane-preview-*` | Unchanged, running |
| Secrets scan (`git diff` across this round's commits) | Clean — the only key-shaped string is a synthetic test fixture, and even that was caught and replaced after it was found to too closely resemble the (already revoked) leaked key — see the incident report |
| `git diff --check` | Clean |

### Five-sample manual evaluation

**Not performed.** Only one real call was made and it failed before
producing any translated text — there is no successful output to evaluate.
This section will be completed once a pilot run actually produces text.

### Report fields

```
PROVIDER_PROBE_COUNT: 0 (no separate probe mechanism exists in this project;
  per this stage's own fallback rule, the first real pilot request served
  as the de facto probe, under the same circuit-breaker/stop-on-failure
  discipline as any other call)
PROVIDER_PROBE_STATUS: n/a (see above — folded into the pilot's first call)
MANIFEST_REUSED: true
MANIFEST_REBUILT: false
STALE_CANDIDATE_COUNT: 0
PILOT_INVOCATION_COUNT: 1
PILOT_CANDIDATE_COUNT: 20
PILOT_ATTEMPTED_COUNT: 1
PROVIDER_CALL_COUNT: 1
RETRY_COUNT: 0
CACHE_HIT_COUNT: 0
CACHE_MISS_COUNT: 1
TITLE_TRANSLATED_COUNT: 0
SUMMARY_TRANSLATED_COUNT: 0
SOURCE_SUMMARY_MISSING_COUNT: 0 (never reached — stopped on the first item's title)
TRANSLATION_SUCCEEDED_COUNT: 0
TRANSLATION_FAILED_COUNT: 1
TRANSLATION_REJECTED_COUNT: 0
NEEDS_REVIEW_COUNT: 0
MACHINE_PUBLISHED_COUNT: 0
AUTH_ERROR_COUNT: 0
INSUFFICIENT_CREDITS_ERROR_COUNT: 1
RATE_LIMIT_ERROR_COUNT: 0
TRANSIENT_ERROR_COUNT: 0
VALIDATION_ERROR_COUNT: 0
NUMBER_PRESERVATION_PASSED: n/a (no real output)
ENTITY_PRESERVATION_PASSED: n/a (no real output)
NEGATION_PRESERVATION_PASSED: n/a (no real output)
UNSUPPORTED_CLAIM_COUNT: n/a (no real output)
AVERAGE_LATENCY_MS: not separately timed for the single failed call (no successful call to average)
INPUT_TOKEN_COUNT: 0
OUTPUT_TOKEN_COUNT: 0
ESTIMATED_COST: 0.00 (confirmed via GET /api/v1/ai/usage)
DAILY_BUDGET_REMAINING: 1.00 (of 1.00 configured — nothing spent)
DATABASE_ITEM_COUNT_BEFORE: 1061
DATABASE_ITEM_COUNT_AFTER: 1082 (normal collector growth only)
DATABASE_TRANSLATION_COUNT_BEFORE: 80
DATABASE_TRANSLATION_COUNT_AFTER: 81 (the one error row)
TRANSLATION_HISTORY_COUNT_BEFORE: 0
TRANSLATION_HISTORY_COUNT_AFTER: 1
ORIGINAL_FIELDS_UNCHANGED: true
TRANSLATION_HISTORY_APPEND_ONLY: true
REVIEW_QUEUE_READY: true (correctly shows 0 pending — nothing succeeded)
UI_MACHINE_TRANSLATION_LABEL_VERIFIED: n/a (no successful translation exists to label yet)
COLLECTION_SCHEDULER_UNCHANGED: true
TRANSLATION_SCHEDULER_ENABLED: false
WORKER_RUNNING_AFTER: false
OPENCTI_UNCHANGED: true
UNRELATED_CONTAINERS_UNCHANGED: true
SECRETS_EXPOSED: one, during preparation (not during the pilot call itself)
  — fully documented in docs/INCIDENT - API KEY EXPOSURE IN SESSION OUTPUT.md;
  contained, old key revoked, new key never exposed
OFFLINE_TEST_COUNT: 241
OFFLINE_TESTS_PASSED: 241
GIT_COMMIT_CREATED: true
GIT_COMMIT_HASHES: e39a144 (adapter/config/tests), plus this docs commit
STAGE_B_OR_STATUS: PARTIAL — real end-to-end path proven against the live
  provider; blocked short of a successful translation by the OpenRouter
  account's own credit balance, not by this project's code
NEXT_SAFE_ACTION: add credit to the OpenRouter account, then request a
  fresh, separately-approved pilot invocation (not an automatic retry) —
  the manifest, code, and dry-run are all already ready
```

## Continuation (2026-09-27, commit `acfea29`)

A resume was authorized to attempt the actual pilot invocation. A fresh
baseline was recorded, the manifest from `runtime/evidence/translation-pilot/`
was re-validated **live against production** (recomputed every title/summary
`content_hash`, re-checked every item still exists): **0/20 stale, 0 items
with an existing successful translation** — the manifest was reused as-is,
no rebuild needed (`MANIFEST_REUSED=true`, `MANIFEST_REBUILT=false`,
`STALE_CANDIDATE_COUNT=0`).

The read-only provider gate check was re-run and **still fails**: `.env` was
checked for the *names/presence* of `AI_PROVIDER` and `AI_API_KEY` only —
neither is set, and no value was read, printed, or logged at any point.
`GET /api/v1/ai/provider-status` independently confirms
`api_key_configured: false`. Per this stage's own rule, the run stopped
**before any provider call** — full gate detail in
`runtime/evidence/translation-pilot/dry-run-report-v2.json`.

**A second real defect was found and fixed during this continuation's
read-only architecture re-check** (before any provider call, exactly as
required): `translate_worker.py`'s `record()` wrote only the fast-read
current row via its own hand-rolled `INSERT` — it never wrote an append-only
`news_item_translation_history` row, and never set `review_status` at all
(it would have stayed at the column default `not_applicable` forever,
regardless of whether validation passed). `enrichment_worker.py` already
had the correct implementation (`_persist_translation_field`); rather than
fix the duplicate logic in two places, `translate_worker.py` now calls that
one implementation directly. 222/222 offline tests still pass. See commit
`acfea29`.

**Outcome of this continuation: still `BLOCKED_PROVIDER_NOT_CONFIGURED`.**
Nothing else in §§1–8 below changes; they're preserved as the original
Stage B record.

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

## Stage B-Free — OpenRouter Free Router only (2026-09-29)

Configuration: `AI_PROVIDER=openrouter`, `AI_BASE_URL=https://openrouter.ai/api/v1`,
`AI_MODEL_TRANSLATION=openrouter/free`, `AI_MODEL_SUMMARY=openrouter/free`,
`AI_FREE_ONLY=true`. The key's presence was checked; its value was not read.

Free-only guard, in `ai_gateway.py` (13 new offline tests, 274 total pass):

- **Allowlist:** `openrouter/free` was added. It is the only model the guard
  lets through; any other model is refused before any network call.
- **Request body:** always exactly `model: openrouter/free`, with no `models`
  fallback list and no `route`, plus `usage.include=true` so OpenRouter
  reports the cost.
- **Cost:** a reported cost above 0 opens the circuit breaker at once.
  A **missing** cost report also stops the run (fail closed).
- **Retries:** the adapter's single retry is disabled in free mode.
- **Audit columns:** the model that actually served each call is recorded in
  `ai_requests_log`, `news_item_translations` and the history table, via
  additive migration 2026.09.29-01.
- **Stop rules:** the worker now stops at the first rate limit, timeout,
  schema error or invalid translation.

**Smoke test (1 item: title + summary, no article body):** 2 provider calls,
2 responses, reported cost $0.00 each, no retries.
- The title was served by `google/gemma-4-31b-it:free`. It is accurate and
  fluent; NORTHCOM is kept, and the place and command names are correct.
- The summary was served by `dots-studio/dots-3-note-preview:free`. It left
  whole English quotations and many ordinary English words untranslated.
  The existing validator scored it 1.0.

A new hard-fail check (`untranslated_english`) now rejects that output. The
stored summary row was re-validated and set to `needs_review`, so the UI does
not display it. The append-only history is unchanged.

Because one smoke output was an invalid translation, **the 20-item pilot was
not run**.

**Recommendation (not applied):** pin `google/gemma-4-31b-it:free`, one of 16
`:free` models in the official `/api/v1/models` list. It supports JSON output
and produced the good title. The Free Router picks a different model per call,
and one of its picks failed; pinning one model makes quality repeatable.
Applying it requires the owner's approval, plus an allowlist and FREE_MODELS
entry with a test.

## Stage B-Pinned — google/gemma-4-31b-it:free on preview only (2026-09-29)

Owner-approved pin, preview-scoped (`PREVIEW_AI_MODEL_*` in `.env`,
consumed only by `compose.redesign-preview.yml`; production :3001 untouched).

**Guard (tightened).** In free-only mode:
- The model must end in `:free` and be on the allowlist; the router
  `openrouter/free` is refused.
- The response must name exactly the requested model.
- A cost must be reported, and it must be exactly 0.
- Retry is disabled.
- Any violation opens the breaker and stops the run.
- The translation JSON schema is exact (no extra keys).

**Validator (hard fails).**
- Entity-aware untranslated-English check: names and acronyms such as
  NORTHCOM pass; English prose and quotes fail.
- Numbers must be preserved; Persian separators and the percent sign are
  normalised.
- No added numbers.
- Dates and model codes must be preserved.
- Output no longer than 3× the source.
- No Markdown or model commentary.

**Status semantics fixed.** A validation-failed translation is now stored as
`status='needs_review'`, not `available` (versioned correction 2026.09.29-02;
history untouched). `available` now means validated and displayable: 1 after
the fix, versus "2 (1 shown)" before.

**Smoke (3 deterministic items: short summary; long summary with quotes and
names; numbers + date + acronym).** The first call returned **HTTP 429**:
"google/gemma-4-31b-it:free is temporarily rate-limited upstream". The run
stopped at once (no retry, no other model). The 20-item pilot was **not**
run. The error is recorded (1 translation row `error`, history +1) and
nothing was displayed. Tests: 281 passed.

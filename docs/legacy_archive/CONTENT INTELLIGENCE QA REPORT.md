# Content Intelligence — QA Report

Phase: `CONTENT INTELLIGENCE — ترجمه، خلاصه‌سازی، کنترل کیفیت و بازبینی
انسانی`. Branch: `feature/iran-monitor-foresight-platform`. Commits this
phase: `0140504`, `d83b132`, `64d4efa` (built on top of the prior AI Gateway
phase's `29b1a4f`, which this phase migrated onto).

## Baseline (recorded before any change)

| Metric | Value |
| --- | --- |
| News items | 1,008 |
| Sources | 12, all healthy |
| Translation rows (pre-existing, from an earlier phase) | 80, all `status=pending` |
| Provenance complete | 1,008 / 1,008 |
| Item-set hash | `170d4a793607a199453dd0eaf0895939` |
| AI provider | disabled, no key configured |
| Git worktree | clean, `feature/iran-monitor-foresight-platform` |

## Migration

**Forward**: applied via the existing idempotent `migrate()` (runs on every
API startup) — 6 new columns on `news_item_translations`, 2 new tables
(`news_item_translation_history`, `content_key_points`). Verified: item-set
hash identical before and after (`170d4a79...`), 1,008 items and 80
pre-existing translation rows untouched.

**Rollback safety**: an INSERT using the *exact* pre-migration column list
(no new columns mentioned) was executed against the migrated schema and
succeeded, with all new columns correctly defaulting to `NULL` /
`'not_applicable'` / `'[]'`. This proves a rollback to pre-phase code would
continue to work against this schema without modification.

**Real defect found and fixed via this process**: the write endpoints
referenced a `reviewed_at` column that was never added to the migration
(`reviewed_by` was added, `reviewed_at` was missed). A live request against
a real item returned `UndefinedColumn` immediately. Fixed, rebuilt,
redeployed, and the full workflow re-verified end-to-end.

## Eligible / generated / validated / rejected / reviewed counts

| Count | Value | Why |
| --- | --- | --- |
| Eligible items (pilot manifest) | 20 | Deterministic selection from the earlier content-enrichment phase, reused for reproducibility |
| Generated | 0 | Pilot halted at the pre-flight provider check, per the brief's explicit stop rule |
| Validated | 0 | Nothing was generated to validate |
| Rejected | 0 | Nothing was generated to reject |
| Reviewed | 0 (production) / 1 field (synthetic, cleaned up) | The full review workflow (edit → approve → reject → regenerate) was proven against one synthetic throwaway item, then fully deleted — see "Live verification" below |

This is the **correct** outcome given the provider is not configured, not a
shortfall — see "Stop rule applied" below.

## Provider status

```json
{"mode": "disabled", "provider": null, "api_key_configured": false}
```
(`GET /api/v1/ai/status`, live, at report time.)

## Stop rule applied

Per the brief: *"اگر provider واقعی تنظیم نشده، هیچ خروجی جعلی نساز و pilot
را با PROVIDER_NOT_CONFIGURED متوقف کن."* The pilot pre-flight check was run
against all 20 manifest items and halted immediately:

```json
{
  "candidate_item_count": 20,
  "ai_mode": "disabled",
  "status": "STOPPED",
  "reason": "PROVIDER_NOT_CONFIGURED",
  "note": "No real AI provider is configured. Per the stop rule, the pilot halts before any generation is attempted. No translation, summary, or key-point output was created for any of the 20 candidate items."
}
```

Full output: `runtime/evidence/content-intelligence/pilot-report.json`.

## Cost and call count

Zero real calls were made against a paid provider (none configured). Two
synthetic smoke tests (fake adapters, no network access, no cost) proved the
Gateway's audit log and cache persistence work correctly against the real
database; both were deleted from `ai_requests_log` / `ai_response_cache`
immediately after verification. `GET /api/v1/ai/usage` reports `spent_today_usd:
0.0` accurately.

## Evaluation results

Versioned set: `config/evaluation/content-intelligence-eval-v1.json` (v1.0.0,
sanitized — public headlines and generic Persian sentences only, no article
bodies, no PII). Acceptance thresholds were recorded in the file **before**
running the evaluation, per the brief's explicit rule against issuing a PASS
after the fact.

| Metric | Threshold | Result | Status |
| --- | --- | --- | --- |
| `language_detection_accuracy` | ≥ 0.95 | **1.00** (15/15) | **PASS** — genuinely measurable today; `detect_language()` is fully deterministic (Unicode-range based), needs no AI provider |
| `cache_correctness` | n/a (behavioral) | Verified — 26 offline tests including provider-change-is-a-cache-miss and prompt-version-change-is-a-cache-miss, plus a live Postgres-backed smoke test (cache hit on 2nd identical call, cache miss on a differing prompt version) | **PASS** |
| `provider_failure_behavior` | n/a (behavioral) | Verified — circuit breaker opens after repeated failures and recovers after a success (offline tests); budget-exceeded fails closed before any adapter call (offline tests) | **PASS** |
| `number_preservation` | not run | **N/A** | No real AI-generated translation exists to score. The *checker* itself is proven via 23 fault-injection tests in `test_content_validator.py`, including exactly this case, but that measures the validator, not real provider output. |
| `named_entity_preservation` | not run | **N/A** | Same reason. |
| `unsupported_claim_rate` | not run | **N/A** | Same reason. |
| `translation_completeness` | not run | **N/A** | Same reason. |
| `summary_faithfulness` | not run | **N/A** | Same reason. |
| `human_review_agreement` | not run | **N/A** | No AI-generated content has ever reached the review queue in production, so there is no reviewer decision to measure agreement against. |

**No PASS is claimed for any N/A metric.** They are reported as not
measurable given the current provider state, exactly as the brief's "هیچ
PASS صوری صادر نکن" rule requires — this table will be re-run and this
report updated the moment a real provider is configured (see
`docs/AI PROVIDER CONFIGURATION.md` step 8).

## Live verification performed

1. Content-intelligence detail endpoint against a real production item
   (`Air Force Certifies Anduril Barracuda Cruise Missile...`) — returned
   correctly, all fields honestly `not_generated`/`provider_not_configured`.
2. Full review workflow against a synthetic throwaway item
   (`review-test-item`, never a real news item): queue → edit → approve →
   reject → regenerate, all via real HTTP calls to the deployed API.
   `regenerate` correctly returned `provider_not_configured` and wrote
   nothing. All synthetic rows deleted afterward; item-set hash confirmed
   unchanged (`170d4a79...`).
3. Full synthetic pipeline smoke test (`smoke-test-item`, fake adapter):
   translation → validation (passed, quality_score 1.0) → history row
   written → current row upserted with `review_status=pending_review`
   (never auto-approved) → key point extracted → evidence verified against
   the source text → published. All rows deleted afterward.

## Browser QA

Playwright via the system Chrome browser (bundled Chromium download was
network-blocked in this environment in an earlier phase; same workaround
reused). 3 viewports (1920×1080, 1024×768, 390×844) × `/review/content` and
`/news`, plus a full status-tab click-through on desktop. **Zero real
console or network errors** — the one console error logged across all runs
was an expected external hotlinked-image 404 (pre-existing, already handled
gracefully by the news card's `onError` fallback from an earlier phase).
Screenshots: `runtime/evidence/content-intelligence/preview-3002/`.

## Offline test suite

217 tests passing (Docker build's `test` stage — a hard gate; the image
cannot be built if any test fails). New this phase: 26 AI Gateway tests (up
from 22 in the prior phase — 4 added for `key_point_extraction` and the
executive-summary prompt version), 23 `content_validator` fault-injection
tests, 14 `content_intelligence` orchestration tests. Net change from
retiring `translate.py`: -9 tests removed (superseded by the above), for a
combined +58 net new tests this phase.

## Runtime stability / isolation

- `news-collector` was never restarted this phase. Item count grew normally
  from its own schedule throughout (1,008 stable across this phase's work
  window, consistent with the collector's own cadence).
- OpenCTI (11 containers) and unrelated projects (`mlw-*`, `plane-preview-*`)
  were not touched, inspected, or restarted.
- No RSS collection cycle was manually triggered this phase, per the
  brief's explicit rule 10.

## Secrets scan and diff hygiene

- `git diff --check` across every commit this phase: clean (no whitespace
  errors, no conflict markers).
- Manual secrets scan of the full diff: the only matches for
  key-shaped strings are the *test fixtures* proving the redaction logic
  works (`sk-abcdefgh12345678` in `test_ai_gateway.py`, a synthetic
  placeholder never used for a real call) — no real credential anywhere in
  the diff.
- `.env` was never touched by any commit this phase (`git log -- .env`
  across this phase's range returns nothing).

## Critical / High defects open

**Zero.** One real defect was found during this phase's own verification
(the missing `reviewed_at` column, caught by a live request against a real
item returning `UndefinedColumn`) — fixed, rebuilt, redeployed, and
re-verified end-to-end before being considered closed; never left open.

# AI Provider Configuration

How to turn on real translation/summarization/key-point generation. Every
step below is an environment change — no code change is needed anywhere in
this project to activate a provider.

## Current state (as of Stage B-OR)

```json
{
  "mode": "external_provider",
  "provider": "openrouter",
  "models": {"translation": "anthropic/claude-haiku-4.5", "summary": "anthropic/claude-haiku-4.5"},
  "daily_budget_usd": 1.0,
  "api_key_configured": true,
  "circuit_open": false
}
```

(Live output of `GET /api/v1/ai/provider-status`, checked exactly this way —
never via `grep`/`Get-Content`/`docker inspect`/`docker compose config`
against `.env` or the container's raw environment. See
`docs/INCIDENT - API KEY EXPOSURE IN SESSION OUTPUT.md` for why that
distinction matters.) **Configured, but not yet successfully connected**:
the one real pilot call made so far returned `insufficient_credits` — the
project's OpenRouter account has no balance. See
`docs/TRANSLATION PILOT REPORT.md` for the full result. Adding credit at
[openrouter.ai](https://openrouter.ai) and re-running the pilot (a fresh,
separately-approved invocation — not an automatic retry) is the next step,
not a code or configuration change.

## Steps to activate

1. **Choose a provider** and set `AI_PROVIDER` in `.env` to one of:
   `anthropic`, `openai_compatible` (or `openai`), `azure_openai`,
   `openrouter` (see `docs/OPENROUTER PROVIDER ADAPTER.md` for its specific
   contract), `local`.
2. **Set `AI_API_KEY`** to a real credential for that provider (leave empty
   for `local` if your self-hosted endpoint doesn't require one).
3. **Set `AI_BASE_URL`** if the provider isn't at its default endpoint
   (required for `azure_openai` and any non-default `local` server; optional
   for `anthropic`/`openai_compatible`, which have built-in defaults).
4. **Set the per-task models** — `AI_MODEL_TRANSLATION`,
   `AI_MODEL_SUMMARY`, `AI_MODEL_CLASSIFICATION`,
   `AI_MODEL_SIGNAL_ANALYSIS`, `AI_MODEL_SCENARIO` (the last two are unused
   until a future phase, but the variables already exist so no `.env`
   restructuring will be needed then). This phase's tasks
   (translation/summary/executive_summary/why_it_matters/
   key_point_extraction) all read from `AI_MODEL_TRANSLATION` /
   `AI_MODEL_SUMMARY` as appropriate. **The chosen model must be in
   `ai_gateway.APPROVED_MODELS[provider]`** — `translate_worker.py` refuses
   to proceed past the model-allowlist check otherwise (status
   `blocked_model_not_allowlisted`), and never substitutes a different
   model on your behalf. Add a new model to the allowlist deliberately, in
   code, when one is actually reviewed and approved — not by typing it into
   `.env` alone.
5. **Set operational limits**: `AI_REQUEST_TIMEOUT` (seconds),
   `AI_MAX_CONCURRENCY`, and optionally `AI_DAILY_BUDGET_LIMIT` (USD — once
   today's estimated spend reaches this, every call fails closed with
   `budget_exceeded` until midnight).
6. **Rebuild and redeploy** `news-api` (the env vars are read at process
   start via `ai_gateway.load_config()`, called fresh on every Gateway
   construction — no cache to bust, no restart-order dependency).
7. **Verify connectivity honestly** — `GET /api/v1/ai/status` should show
   `mode: "external_provider"` (or `"local"`), the chosen provider, and
   `api_key_configured: true` (the key itself is never returned). Do **not**
   consider this step "done" until a real call has actually succeeded —
   status alone only proves configuration, not connectivity.
8. **Run the evaluation set** (`config/evaluation/content-intelligence-eval-v1.json`)
   against the real provider before any production pilot — see
   `docs/CONTENT INTELLIGENCE QA REPORT.md` for the metrics that become
   measurable once real output exists, and their pre-committed thresholds.
9. **Run the pilot** (`config/content-pilot/manifest-v1.json`, the same
   deterministic 20-item selection from the earlier content-enrichment
   phase) via `enrichment_worker.process_translation` for each item ID.
   Every result lands in `review_status=pending_review` or `needs_review` —
   **never auto-approved** — so a human must clear the queue via
   `/review/content` before any of it is treated as final.
10. **Check cost** — `GET /api/v1/ai/usage` before widening beyond the
    pilot; see `docs/CONTENT ENRICHMENT COST ESTIMATE.md` (from the earlier
    phase) for per-item cost expectations at Anthropic/OpenAI list prices —
    now measurable for real via `ai_requests_log` once real calls exist.

## Switching providers later

Nothing needs to change beyond `.env` and a redeploy. Because the cache key
includes the provider name (`content_hash` folds in the task type and prompt
version; the cache row itself is keyed additionally by provider and model —
see `docs/AI GATEWAY.md` "Caching"), switching providers is guaranteed to
produce fresh calls, never a silent reuse of the old provider's cached
output.

## What "disabled" guarantees today

- No network call is ever attempted by any code path in this project for
  translation, summary, executive summary, why-it-matters, or key-point
  extraction.
- Every relevant API field reports `status: "provider_not_configured"`
  (or, on the news detail page, the equivalent honest empty state) —
  verified live via screenshot in `runtime/evidence/content-intelligence/`.
- The pilot script halts immediately with `PROVIDER_NOT_CONFIGURED` and
  produces zero output for all 20 candidate items — verified live, see
  `runtime/evidence/content-intelligence/pilot-report.json`.

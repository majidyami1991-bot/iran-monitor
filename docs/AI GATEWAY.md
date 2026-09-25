# AI Gateway

`apps/api/ai_gateway.py`. The single, provider-agnostic entry point every
AI-assisted feature in this project must go through — translation,
summarization, classification, and (once built) signal analysis and
scenario generation. No call site should ever import a vendor SDK or
hard-code a vendor's request/response shape; only this module's `run()` and
its typed `GatewayRequest` / `GatewayResult` objects.

## Why this exists

Before this phase, `translate.py` had its own bespoke provider abstraction
(`NullProvider`, `OpenAICompatibleProvider`, `AnthropicProvider`) — a
reasonable start, but narrow: no circuit breaker, no rate limiting beyond a
concurrency count, no cost tracking, no cache, no prompt versioning, no
budget enforcement. As the product grows into signal analysis and scenario
generation (both explicitly AI-assisted per the brief), duplicating that
narrow pattern five times was the wrong direction. The Gateway generalizes
it once, properly, so every future AI-assisted feature is a thin call site
against the same tested infrastructure.

`translate.py` and `enrichment_worker.process_translation` are **not yet
migrated** onto the Gateway — they still work exactly as before. Routing
translation through the Gateway is the natural first adopter once section 4
of the brief (redesigning translation/summary output — key points, entities,
attributed claims) is tackled, since that's also when the translation
prompt itself needs to change. Migrating a working, tested path and
redesigning its output shape are better done as one deliberate step, not
two uncoordinated ones.

## Modes

Set via `AI_PROVIDER` in `.env`:

| `AI_PROVIDER` value | Resolved mode | Behavior |
| --- | --- | --- |
| unset, empty, or `disabled` | `disabled` | Every call returns `status=provider_not_configured` immediately. No network request is ever attempted. This is the current production state. |
| `deterministic` | `deterministic` | Every call returns `status=deterministic_only`. For a caller that must never silently fall back to a generative result if it expects a rule-based one — a clear refusal, not a fabrication. |
| `local` | `local` | Routes to a self-hosted OpenAI-compatible endpoint (`AI_BASE_URL`, default `http://localhost:11434/v1` for a local Ollama-style server). No cost is ever estimated for this mode — local inference is free by definition here. |
| any other value (`openai_compatible`, `openai`, `azure_openai`, `anthropic`) | `external_provider` | Routes to the named adapter, using `AI_BASE_URL` / `AI_API_KEY` / the per-task `AI_MODEL_*` variable. |

Switching modes is an environment change. No call site's code changes.

## Adapters

`Adapter` is the minimal interface (`complete(system, user) -> AdapterResponse`).
Shipped adapters: `OpenAICompatibleAdapter`, `AzureOpenAIAdapter` (same wire
shape, kept as a distinct name for audit clarity), `AnthropicAdapter`,
`LocalModelAdapter` (OpenAI-compatible, no key required by default),
`DisabledAdapter` (used for both `disabled` and `deterministic` modes —
always raises `provider_not_configured` if ever called directly, though
`AIGateway.run()` never lets it be called in those modes).

Adding a sixth adapter — an independent translation-only provider, for
example — means writing one class implementing `complete()` and registering
it in `ADAPTER_REGISTRY`. Nothing else in the Gateway or any call site
changes.

## Contracts

Every task type (`translation`, `summary`, `classification`,
`signal_analysis`, `scenario`) has:

- **A versioned prompt** (`PROMPTS[(task_type, version)]`, `LATEST_PROMPT_VERSION[task_type]`).
  A prompt is never edited in place — a wording change gets a new version
  string. Nothing is ever silently reattributed to a different prompt than
  the one that actually produced it.
- **An output schema** (`_SCHEMAS[task_type]`) — the required top-level keys
  and their Python types. `signal_analysis` and `scenario` have provisional
  `0.1.0` prompts and schemas now, ahead of those engines existing, so the
  contract is fixed before the feature is built on top of it — not
  discovered ad hoc later.

A response that isn't valid JSON, or is JSON missing a required key, or has
a key of the wrong type, is `status=invalid_response`. It is never coerced
into looking successful.

## Reliability

- **Timeout**: `AI_REQUEST_TIMEOUT` seconds per call (adapter-level, via
  `urllib`'s own timeout).
- **Concurrency limit**: `AI_MAX_CONCURRENCY` — a process-wide semaphore,
  keyed by the configured limit so multiple `AIGateway` instances in the
  same process share one limiter rather than each getting their own.
- **Circuit breaker**: one `CircuitBreaker` per adapter name, shared across
  requests in the process. Opens after 5 consecutive failures (default),
  refuses calls for 60 seconds (default), then allows one probe call
  (half-open). A tripped breaker returns `status=circuit_open` immediately
  — no call is attempted, so a failing provider cannot be hammered.
- **Retry**: not built as a Gateway-level feature in this phase — the
  circuit breaker plus the caller's own retry policy (e.g. the enrichment
  worker's existing bounded backoff) covers the same need without adding a
  second, possibly conflicting retry loop inside the Gateway itself.

## Cost tracking

Every real call estimates cost from `response.tokens_in` /
`response.tokens_out` against a small price table
(`_PRICE_PER_MILLION_TOKENS_USD`, USD per million tokens, prefix-matched
against the configured model). This is deliberately approximate — it exists
to catch runaway spend, not to produce an invoice. `local` mode never
estimates a cost. An unrecognized model estimates `None`, not a guessed
number.

If `AI_DAILY_BUDGET_LIMIT` is set, every call first checks today's total
estimated spend (`SUM(estimated_cost_usd)` from `ai_requests_log` since
midnight). Once spend reaches the limit, calls fail closed with
`status=budget_exceeded` — no adapter is invoked — until midnight resets the
window.

`GET /api/v1/ai/cost-usage` (see below) surfaces this without needing direct
database access.

## Caching

Keyed on `(content_hash, provider, model)`, where
`content_hash = sha256(task_type|prompt_version|content)`. Consequences:

- The same content re-processed with the same provider, model and prompt
  version is a cache hit — the adapter is never called again.
- **A provider change is a cache miss.** Switching `AI_PROVIDER` never
  silently serves another provider's output as if it were fresh.
- **A prompt version change is a cache miss** (baked into `content_hash`).
  A prompt edit always gets genuinely new output, never a stale cached
  answer from the old wording.
- Nothing is ever overwritten in place — a new key is a new row
  (`ai_response_cache`'s primary key is the full tuple), so historical
  results stay intact even as the system evolves.

`PostgresCache` is the production backend; tests use a trivial in-memory
dict-backed fake (`MemoryCache` in `test_ai_gateway.py`) — the Gateway core
has zero hard dependency on a database, by design, so it stays fast and
deterministic to test.

## Audit log

Every call — success, cache hit, or failure — is logged
(`PostgresLogger` → `ai_requests_log`): task type, provider, model, prompt
version, content hash, status, latency, token counts, estimated cost, cache
hit flag, and a sanitized error message (`_redact()` strips anything that
looks like an API key before it can reach a log row).

## Security

- `AI_API_KEY` is read from the environment only; never hard-coded, never
  logged, never returned by `GET /api/v1/ai/provider-status` (that endpoint
  reports only `api_key_configured: bool`).
- `_redact()` strips `Bearer <token>` / `sk-...` / `key-...`-shaped strings
  from any error text before it's stored or returned.
- No UI or domain-logic code is allowed to depend on a specific vendor —
  every call site imports `ai_gateway`, never `anthropic` or `openai`
  directly.

## API surface added this phase

- `GET /api/v1/ai/provider-status` — mode, provider (only when
  `external_provider`), per-task models, timeout, concurrency limit, daily
  budget, whether a key is configured (never its value), whether the
  circuit breaker is currently open, and the latest prompt version per task
  type.
- `GET /api/v1/ai/cost-usage?days=7` — per-day/task-type/provider request
  counts, success/cache-hit counts, token totals and estimated cost for the
  requested window; today's total spend; the configured daily budget; and a
  breakdown of non-success statuses in the last 7 days (for spotting a
  provider that's erroring or a budget that's about to trip).

## What's proven so far

- 22 offline tests (`tests/monitoring/test_ai_gateway.py`) covering every
  mode, cache hit/miss (including the provider-change-is-a-miss case),
  circuit breaker trip and recovery, budget enforcement, invalid-JSON and
  wrong-shape responses, empty-content handling, cost estimation, API-key
  redaction, and that every result — success or failure — reaches the
  logger.
- A live end-to-end smoke test against the real production database (a fake
  adapter, so no real API key or network call was needed): first call
  logged with real token counts, second identical call served from
  `ai_response_cache` as `status=cached`, both visible through
  `GET /api/v1/ai/cost-usage`. The synthetic test rows were deleted
  afterward — production data stays real.

## What this phase does not include

- No feature actually calls the Gateway yet for a live user-facing result —
  `translate.py` still runs its own path (see "Why this exists" above).
  `AI_MODEL_SIGNAL_ANALYSIS` and `AI_MODEL_SCENARIO` have contracts fixed
  but no engine behind them — those are sections 6/7 and 11 of the
  foresight roadmap.
- No retry-with-backoff inside the Gateway itself (see Reliability above —
  deliberate, not an oversight).
- No `local` adapter has been exercised against a real local model server in
  this environment — the code path is implemented and unit-tested, but a
  live local-inference smoke test would need an actual local server
  running, which this environment doesn't have.

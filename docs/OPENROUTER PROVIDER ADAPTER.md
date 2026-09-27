# OpenRouter Provider Adapter

`OpenRouterAdapter` in `apps/api/ai_gateway.py`. Implements this project's
`Adapter` interface (`complete(system, user) -> AdapterResponse`) against
[OpenRouter](https://openrouter.ai), an OpenAI-compatible chat-completions
proxy in front of many underlying model providers. Selected and activated
in Stage B-OR of the "Iran Monitor Commercial Intelligence Experience"
phase, after the direct-Anthropic path (`AnthropicAdapter`, already present)
was blocked on the client not having a direct Anthropic key — OpenRouter was
the key the project owner actually had.

## Why a dedicated adapter, not a reuse of `OpenAICompatibleAdapter`

The wire format is the same (`POST /chat/completions`, Bearer auth, OpenAI
message shape) — same reasoning `AzureOpenAIAdapter` already documents for
being kept distinct from `OpenAICompatibleAdapter` despite an identical wire
shape. What's genuinely different for OpenRouter:

- **402 = insufficient account credit.** Not a status standard
  OpenAI-compatible servers define; OpenRouter uses it specifically for "no
  balance." Classifying it correctly is the difference between an operator
  correctly being told to top up their OpenRouter balance and a generic,
  unhelpful "http_402" error.
- **A single bounded retry for genuinely transient failures**
  (`transient_timeout`, `rate_limited`, `provider_unavailable`) — this must
  never leak into `OpenAICompatibleAdapter`, which other deployments
  (self-hosted OpenAI-compatible servers, etc.) rely on behaving exactly as
  it did before.
- **Two small, optional, non-secret headers** (`X-Title`; deliberately
  *not* `HTTP-Referer` — see below) that only make sense for OpenRouter.

## Contract

| | |
| --- | --- |
| Provider name | `openrouter` |
| Mode | `external_provider` (set via `AI_PROVIDER=openrouter`) |
| Base URL | `https://openrouter.ai/api/v1` (the project default; `AI_BASE_URL` overrides it if ever needed) |
| Chat endpoint | `POST {base}/chat/completions` |
| Auth | `Authorization: Bearer <AI_API_KEY>` |
| Approved models (this project) | `anthropic/claude-haiku-4.5` (pilot default), `anthropic/claude-sonnet-5` — see `ai_gateway.APPROVED_MODELS['openrouter']` |
| Structured output | `response_format: {"type": "json_object"}` sent on every request, on top of this project's existing "return only JSON" prompt instructions |

**Model allowlist, not a guess and not a substitution.** `AI_MODEL_TRANSLATION`/
`AI_MODEL_SUMMARY` are read exactly as configured; `model_is_approved()`
checks the value against `APPROVED_MODELS` before any pilot or dry-run
proceeds. An unlisted model is a **configuration error to stop and fix**,
never silently swapped for an approved one — a model substitution the
operator didn't ask for could change behavior, cost, or quality without
anyone deciding that on purpose.

## Headers

- `X-Title: Iran Monitor` — a fixed, true product name, sent for
  OpenRouter's own attribution/leaderboard display. Not a secret, not
  fabricated.
- **No `HTTP-Referer` is ever sent.** OpenRouter's own docs list this
  header as optional and purely cosmetic (attribution on OpenRouter's own
  site). This deployment has no public URL — `127.0.0.1:3001` is not a
  legitimate referer to report, and this project's standing rule against
  inventing values (the same rule that governs every "empty rather than
  fabricated" field elsewhere in this system) applies exactly the same way
  to an HTTP header as to a translated field.

## Error classification (`_classify_http_status`)

| HTTP status | Classified as | Retried? |
| --- | --- | --- |
| 400 | `request_invalid` (e.g. an unknown model slug) | No |
| 401 | `authentication_failed` | No |
| 402 | `insufficient_credits` | No |
| 403 | `provider_forbidden` | No |
| 404 | `request_invalid` | No |
| 408 | `transient_timeout` | **Yes, once** |
| 429 | `rate_limited` | **Yes, once** (respects `Retry-After`, capped at 5s so a large value can never stall a pilot run) |
| 5xx | `provider_unavailable` | **Yes, once** |
| malformed JSON body | `unexpected_response_shape` (adapter) / `invalid_response` (Gateway, if the *content* isn't valid JSON) | No |

This classification is opted into only by `OpenRouterAdapter` (via
`_post_json`... actually via its own `_call_once`, see below) — it is not
retroactively applied to `OpenAICompatibleAdapter`'s existing generic
`http_<code>` behavior, per this project's rule against incompatible
changes to already-relied-upon behavior.

**Retry mechanics**: implemented inside `OpenRouterAdapter.complete()`
itself (catch → check reason → sleep → exactly one more `_call_once()`), not
inside the shared Gateway `run()` loop — the Gateway's `run()` still calls
`adapter.complete()` exactly once per request, unchanged. This keeps the
retry decision co-located with the only code that actually knows *why* a
given failure happened (an HTTP status the adapter observed directly),
without needing the Gateway itself to grow provider-specific retry logic.
`self.total_retries` on the adapter instance is incremented on every retry,
readable by a caller (e.g. `translate_worker.py`'s pilot report) without
changing `GatewayResult`'s shape.

## Cost

`anthropic/claude-haiku-4.5` and `anthropic/claude-sonnet-5` (OpenRouter
slugs) are priced in `_PRICE_PER_MILLION_TOKENS_USD` at the same rate as
their direct-Anthropic counterparts (`$1/$5` and `$2/$10` per million
input/output tokens respectively) — approximate, exactly as the module's own
disclaimer already states for every other entry in that table.

## Security

- The API key is read from `AI_API_KEY` (environment only), passed as a
  Bearer token, never logged, never returned by any status endpoint.
- `_redact()` strips `Bearer <token>` / `sk-...`-shaped strings from any
  error text before it reaches the Gateway result, the audit log, or a
  pilot report — proven end-to-end (not just unit-tested on `_redact()` in
  isolation) by `test_gateway_result_error_never_contains_the_key_end_to_end`
  in `tests/monitoring/test_openrouter_adapter.py`, which simulates an error
  body that echoes a key-shaped string and asserts it never survives into
  `GatewayResult.error`.
- See `docs/INCIDENT - API KEY EXPOSURE IN SESSION OUTPUT.md` for a real
  process failure (an operator/assistant mistake, not a code defect) that
  these specific regression tests were written in direct response to.

## What's proven so far

15 offline tests: name/base-URL defaults, missing-key rejection, header
correctness (Bearer + `X-Title`, never a fabricated referer), every status
code's classification, retry-exactly-once behavior (both the
succeeds-on-retry and fails-again-and-propagates cases), key-redaction
end-to-end, adapter registration, model allowlist accept/reject, and the
per-task model-selection fix (§ below). Plus one real pilot invocation
against the live OpenRouter API — see `docs/TRANSLATION PILOT REPORT.md`
for that result (`insufficient_credits` on the first real call; the
account's OpenRouter balance needs a top-up before a translation can
actually succeed — a billing/account state, not a code defect).

## A real bug this integration found and fixed

`AIGateway.run()` only overrode `self.adapter.model` per-request for
`isinstance(self.adapter, (OpenAICompatibleAdapter, AnthropicAdapter))` —
`OpenRouterAdapter` wasn't in that tuple, so every task type would have
silently used whichever model `build_adapter()` happened to initialize with
(always the *translation* model, per `build_adapter()`'s own
implementation), regardless of the task actually being requested. Harmless
today only because `AI_MODEL_TRANSLATION` and `AI_MODEL_SUMMARY` are
currently configured identically — a real latent defect for the moment they
diverge. Fixed by adding `OpenRouterAdapter` to that isinstance check;
regression test: `test_gateway_uses_the_correct_per_task_model_for_openrouter`.

# Local Ollama X Translation — Architecture

Offline, non-real-time Persian translation of analyst-recorded X posts with
the local model `gemma4:e2b` (Ollama, CPU only). No cloud provider is used on
this path, and nothing translates on page load or on a schedule.

## Flow

```text
analyst registers post (x_posts.original_text)        ← never modified by translation
        │
        ▼
x_translate_worker  (one-shot batch, operator-started)
  1. pg advisory lock 7270061  ── second worker → "worker_already_running"
  2. recover orphans: every 'processing' row → 'pending'
  3. reconcile (DB only): new text → 'pending'; Persian text → 'not_required';
     changed text (sha256) → 'stale'
  4. verify model: /api/tags exact name + digest prefix  ── mismatch → stop, nothing touched
  5. for one row at a time (batch size 1, ordered by id):
       pending/stale → processing → AIGateway.run(x_post_translation)
                                     │  OllamaAdapter → http://host.docker.internal:11434/api/chat
                                     │  format = JSON schema, think=false, temperature 0.1,
                                     │  num_ctx 4096, num_thread 8, bounded num_predict
                                     ▼
                     x_translation_validator.validate(source, candidate)
                       pass → 'available'      fail → 'needs_review'
       pause X_TRANSLATION_SLEEP_SECONDS, next row
  6. release lock, exit
        │
        ▼
API (/api/v1/social/...)  reads PostgreSQL only  ──►  web UI (/social, account, post pages)
```

The browser never talks to Ollama. The API talks to Ollama only to probe
`/api/tags` for the status endpoint, at most once every 30 seconds. The
`run-batch` endpoint starts the same batch in a background thread and returns
`202` straight away.

## Components

| Piece | File |
|---|---|
| Ollama adapter, prompt `x-post-translation-fa-v1.0.0`, output schema | `apps/api/ai_gateway.py` (`OllamaAdapter`, `PROMPTS`, `OUTPUT_JSON_SCHEMAS`) |
| Validator | `apps/api/x_translation_validator.py` |
| Worker / CLI | `apps/api/x_translate_worker.py` |
| API endpoints, UI join | `apps/api/social.py` (`register_translation`) |
| Migration `2026.10.06-01` | `apps/api/redesign_schema.py` |
| Rollback | `deployment/news-monitor/rollback-x-translation.sql` |
| UI | `apps/web-next/app/social/Translation.tsx`, `PostCard.tsx` |
| Preview wiring | `deployment/news-monitor/compose.redesign-preview.yml` (`news-x-translate-preview`, profile `x-translate`) |

## Gateway integration

There is no parallel architecture. Provider `ollama` maps to the existing
`Mode.LOCAL`, and the worker builds its own `GatewayConfig`, so the global
`AI_PROVIDER` used for news translation is unaffected.

| Guarantee | How it is enforced |
|---|---|
| Local hosts only | `OllamaAdapter` refuses any host other than `127.0.0.1`, `localhost`, `::1` and `host.docker.internal`, and any scheme other than `http`. |
| No fallback model | `APPROVED_MODELS['ollama'] = {'gemma4:e2b'}`. The exact name and digest prefix (`OLLAMA_MODEL_DIGEST`) are checked in `/api/tags`. If the response's `model` field differs, the call fails with `model_identity_mismatch`. |
| Structured output | `format` is set to the JSON schema. Unwrapping happens only when the whole response is a single ```` ```json ```` block. Extra keys are rejected (exact schema). |
| Cost 0 | The adapter reports `reported_cost_usd=0`. `provider` is stored as `ollama/local`. The free-only guard does not apply in local mode. |
| `think: false` | gemma4 reasons by default. Measured on this CPU, that took 22 s against 9.5 s and burned `num_predict` on text that was thrown away. |
| Audit | Every call is logged to `ai_requests_log` (content hash, no text) and cached in `ai_response_cache` by (content hash, provider, model). |

## Data model

`x_post_translations` holds one row per post and target language
(`UNIQUE(x_post_id, target_language)`). It stores status, the text, provider,
model, prompt version, `source_text_hash`, `translation_hash`, quality score
and flags, attempts, latency, the last error, and the review fields.

Allowed statuses: `pending`, `processing`, `available`, `needs_review`,
`failed`, `not_required`, `stale` (enforced by a CHECK constraint).

`x_post_translation_history` is append-only. A trigger writes a row on every
change of status, text or source hash. `BEFORE UPDATE OR DELETE` raises an
exception. `TRUNCATE` is not guarded, because the migration guard test forbids
that keyword in migrations; it is an owner-only operation.

The migration is additive (`CREATE ... IF NOT EXISTS`). Older API images
ignore the new tables.

## Status semantics

| Status | Meaning | UI |
|---|---|---|
| pending / stale | queued (stale = source text changed) | «ترجمه فارسی در صف پردازش محلی است.» |
| processing | a worker holds it | «در حال ترجمه با مدل محلی» |
| available | validator passed | Persian text (RTL) labelled «ترجمه ماشینی محلی», original via toggle (LTR), provenance details |
| needs_review | validator failed | «ترجمه ماشینی نیازمند بازبینی است.» — the text never leaves the API |
| failed | invalid JSON, truncated output, or transient error twice | «ترجمه محلی انجام نشد؛ متن اصلی همچنان در دسترس است.» |
| not_required | source is Persian (rule, no model call) | «متن اصلی فارسی است.» |

## Failure handling

| Event | Result |
|---|---|
| Ollama unreachable, model missing or mismatched, circuit open | Batch stops. The row goes back to its previous status with the attempt not counted. |
| Timeout or HTTP 5xx | One retry. A second failure gives `failed` (`X_TRANSLATION_MAX_ATTEMPTS` is capped at 2). |
| Invalid JSON or extra keys | `failed`, with no retry. |
| Validator fails | `needs_review`. With `--stop-on-review`, the batch stops. |
| Crash or kill mid-call | The row stays `processing` until the next run, which returns it to `pending` while holding the lock. |
| SIGTERM / SIGINT | The current post finishes, then the batch stops. |

## Validator

The validator runs independently of the model. It builds on
`content_validator.validate_translation` and adds the X-specific checks below.
Hard failures:

- empty output
- not Persian
- untranslated English prose. URLs, mentions, hashtags and codes are stripped
  first, so acronyms such as CENTCOM, names and codes like F-35 never count as
  prose.
- commentary or Markdown, wrapper quotes, or a «ترجمه:» label
- URL, mention or hashtag missing or added
- number missing or added. Digits inside URLs, handles and technical codes are
  excluded.
- time missing, technical code missing (MQ-9, F-35, J-20)
- output identical to the source, or too short
- bracket/template debris (`{ } [ ] < >`, `{% %}`) that isn't in the source
- invisible control characters. ZWNJ is allowed.

Soft flags lower the score: dropped emoji, possible negation loss, output too
long.

**Limit:** the validator checks mechanical properties only. It cannot detect
grammar errors or a change in certainty. Both happened in the smoke test (see
the QA report). An `available` translation is labelled «بازبینی انسانی نشده»
(not human-reviewed).

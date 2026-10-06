# Local Ollama X Translation — Runbook

All commands run from `E:\Iran monitor-redesign` against the **preview**
stack. Production (`:3001`) does not run this feature until it is promoted
separately. Never print `.env` or the admin token.

```sh
C="docker compose -p defence-monitor-news --env-file E:/Iran\ monitor/.env \
  -f deployment/news-monitor/compose.yml -f deployment/news-monitor/compose.redesign-preview.yml"
W="$C --profile x-translate run --rm --no-deps news-x-translate-preview"
```

## 1. Preconditions

| Check | Command | Expect |
|---|---|---|
| Ollama up, local only | `curl -s http://127.0.0.1:11434/api/version`; `Get-NetTCPConnection -LocalPort 11434 -State Listen` | Version returned; listening on `127.0.0.1` only |
| Model present | `curl -s http://127.0.0.1:11434/api/tags` | `gemma4:e2b`, digest `7fbdbf8f5e45…` |
| CPU only | `curl -s http://127.0.0.1:11434/api/ps` while loaded | `size_vram: 0` |
| Server settings | User env vars | `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_HOST` unset (defaults to 127.0.0.1) |
| Worker view | `$W x-status` | `ollama_reachable: true`, `model_found: true`, `config_errors: []` |

If the Ollama tray app is running but the API doesn't answer, start the
server directly with `ollama.exe serve`. Never set `OLLAMA_HOST=0.0.0.0`.

## 2. Run a batch

```sh
$W x-status                                    # counts + Ollama view
$W x-dry-run --limit 10                         # no writes, no model call
PREVIEW_X_TRANSLATION_ENABLED=true $W x-translate --limit 3 --stop-on-review   # smoke
PREVIEW_X_TRANSLATION_ENABLED=true $W x-translate --all-pending                # full, sequential
PREVIEW_X_TRANSLATION_ENABLED=true $W x-translate --all-pending                # second run: attempted 0, provider_calls 0
```

The worker exits when the batch ends. There is no scheduler. Each run prints a
JSON report with these fields: `attempted`, `available`, `needs_review`,
`failed`, `provider_calls`, `cache_hits`, `retries`, `average_latency_ms`,
`max_latency_ms`, `stopped_reason`.

`stopped_reason` values:

| Value | Meaning | Action |
|---|---|---|
| `null` | Finished | — |
| `x_translation_disabled` | Flag is off | Set `PREVIEW_X_TRANSLATION_ENABLED=true` for this one run |
| `worker_already_running` | Another batch holds the lock | Wait; see `worker_running` in status |
| `provider_unreachable` | Ollama is down | Start Ollama. The post is back in the queue. |
| `model_not_found` / `model_digest_mismatch` / `model_identity_mismatch` | Wrong model | Restore `gemma4:e2b`. Never point the variable at another model. |
| `stop_on_review:*` | A smoke translation failed validation | Review it before running the full batch |

## 3. Review and retry

```sh
PREVIEW_X_TRANSLATION_ENABLED=true $W x-retry-review --limit 10
```

This moves `needs_review` and `failed` rows back to `pending` and asks the
model again, bypassing the response cache. History keeps the rejected output.

## 4. Admin API (optional)

The token lives in `runtime/secrets/preview-admin-token`, which is gitignored.
Pass it as `PREVIEW_SOCIAL_ADMIN_TOKEN` when the preview is brought up. If the
token is unset, every admin write returns `403`.

```sh
TOK=$(cat runtime/secrets/preview-admin-token); O='origin: http://127.0.0.1:3002'
CS=$(curl -s -X POST -H 'content-type: application/json' -H "$O" -H "x-im-admin: $TOK" -d '{}' \
  http://127.0.0.1:3002/api/v1/social/translations/csrf | python -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s -X POST -H 'content-type: application/json' -H "$O" -H "x-im-admin: $TOK" -H "x-im-csrf: $CS" \
  -d '{}' http://127.0.0.1:3002/api/v1/social/posts/<post_id>/translation/enqueue
curl -s -X POST -H 'content-type: application/json' -H "$O" -H "x-im-admin: $TOK" -H "x-im-csrf: $CS" \
  -d '{"limit":3}' http://127.0.0.1:3002/api/v1/social/translations/run-batch      # 202, background
```

The admin endpoints accept internal post IDs and `limit` only. A URL or prompt
in the body is rejected (`extra_forbidden`).

Read endpoints:

- `GET /api/v1/social/translation/status`
- `GET /api/v1/social/translations/stats`
- `GET /api/v1/social/posts/{id}/translation`

## 5. Stuck jobs

A `processing` row with no running worker is an orphan. The next batch
returns it to `pending` before doing anything else:

```sh
PREVIEW_X_TRANSLATION_ENABLED=true $W x-translate --limit 1   # report.recovered lists the post ids
```

## 6. Rollback

| Level | Action |
|---|---|
| UI / API | Restart the preview with `PREVIEW_API_IMAGE=defence-monitor-news-news-api:pre-x-translation` and `PREVIEW_WEB_IMAGE=defence-monitor-news-news-web:pre-x-translation`. The old images ignore the new tables. |
| Schema + data | Take a `pg_dump` first, then `docker exec -i defence-monitor-news-news-db-1 psql -U defence_monitor -d defence_monitor -v ON_ERROR_STOP=1 < deployment/news-monitor/rollback-x-translation.sql`. Only the two new tables, their functions and the `schema_migrations` row are removed. The rollback was drilled on `defence_monitor_xtrtest`. |
| Ollama settings | Remove the user env vars `OLLAMA_NUM_PARALLEL` and `OLLAMA_MAX_LOADED_MODELS`, then restart Ollama. |

## 7. Tests

```sh
docker build --target test -f apps/api/Dockerfile .         # offline suite incl. tests/monitoring/test_x_translation.py
# DB integration (throwaway *_xtrtest database only; the test refuses any other):
#   see docs/LOCAL OLLAMA X TRANSLATION QA.md
BASE_URL=http://127.0.0.1:3004 node tests/ui/x-translation-qa.cjs          # QA stack on synthetic data
OFFLINE=1 BASE_URL=http://127.0.0.1:3004 node tests/ui/x-translation-qa.cjs
```

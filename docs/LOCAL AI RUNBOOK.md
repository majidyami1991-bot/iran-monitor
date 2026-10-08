# Local AI Runbook (isolated stack, `127.0.0.1:3003`)

This stack is an isolated preview of local translation and the «دستیار هوشمند»
assistant, running on Ollama `gemma4:e2b` (CPU only).

| | |
|---|---|
| Worktree / branch | `E:\Iran monitor-local-ai`, `feature/local-gemma-translation-assistant` |
| Compose project | `iran-monitor-local-ai` (file `deployment/local-ai/compose.yml`) |
| Published port | `127.0.0.1:3003` only (web). The API and DB have no published port. |
| Database | `ai-db` on volume `iran-monitor-local-ai_ai-db-data`, network `iran-monitor-local-ai_default` |
| Data | Restored once from a read-only `pg_dump` of Production (2026-10-07; 33 tables, counts verified) |

The stack has no network path to Production's database, so it cannot write
to it. Production (3001), the previous preview (3002) and OpenCTI (8080) are
not part of this project.

## Configuration

`E:\Iran monitor-local-ai\.env` is gitignored and never committed. It holds
`LOCAL_AI_DB_PASSWORD` plus the non-secret settings. The template is
`deployment/local-ai/.env.example`.

The password must stay the value the `ai-db` volume was created with.
Nothing from the Production/OpenCTI `.env` is used.

## Run

Run these from the worktree root (`E:\Iran monitor-local-ai`):

```sh
docker compose --env-file .env -f deployment/local-ai/compose.yml config --quiet   # validate
docker compose --env-file .env -f deployment/local-ai/compose.yml up -d ai-db ai-api ai-web
curl -s http://127.0.0.1:3003/api/v1/health
curl -s http://127.0.0.1:3003/api/v1/assistant/status
# browser: http://127.0.0.1:3003/assistant
```

Images `iran-monitor-local-ai-api:dev` and `iran-monitor-local-ai-web:dev`
are built from this worktree. The API build runs the offline test suite.

```sh
docker build -f apps/api/Dockerfile -t iran-monitor-local-ai-api:dev .
docker build -t iran-monitor-local-ai-web:dev apps/web-next
```

## Stop

```sh
docker compose --env-file .env -f deployment/local-ai/compose.yml stop
```

`stop` keeps the containers and the database volume, and is the complete
rollback of this stack. Never use `down -v`, `volume prune` or
`system prune`: the volume holds the restored data and every local
translation.

## Translation batch (one-shot, operator-started)

Run from the worktree root:

```sh
C="docker compose --env-file .env -f deployment/local-ai/compose.yml --profile translate"
$C run --rm --no-deps ai-translate status
$C run --rm --no-deps ai-translate dry-run --limit 10                         # no writes, no model call
$C run --rm --no-deps -e LOCAL_TRANSLATION_ENABLED=true ai-translate run --limit 3 --stop-on-review
$C run --rm --no-deps -e LOCAL_TRANSLATION_ENABLED=true ai-translate run --all-pending
$C run --rm --no-deps -e LOCAL_TRANSLATION_ENABLED=true ai-translate retry-review --limit 10
```

- Translations run one at a time (concurrency 1), with at most 512 output
  tokens per request.
- The batch lock allows one batch per DB. The inference lock is shared with
  the assistant.
- Ctrl+C or SIGTERM finishes the current item and stops. The next run
  resumes where it left off.
- Measured cost on this CPU: about 7 to 17 s per item. A full title+summary
  run over every item is about 45 to 50 hours.

## Model pin (fail closed)

`OLLAMA_MODEL_DIGEST=7fbdbf8f5e45` pins the approved model build. When the
installed `gemma4:e2b` has a different digest, two things happen:

- `assistant/status` shows `model_found: false`.
- Every translation and assistant call ends with `model_digest_mismatch`
  without generating anything.

**Status 2026-10-08:** after the Ollama upgrade to 0.40.1, the installed
`gemma4:e2b` reports digests `2cf98652fdc6` / `da406dc37ca0`. Its manifest
and weights were rewritten at 09:50 local. The approved `7fbdbf8f5e45` is not
installed, so AI calls are blocked until an owner decides one of two things:

- restore the approved build from the offline copy
  (`TranslatorOllama/gemma4-e2b-ollama.tar`), or
- review and approve the new build, which means updating the pin and the
  allowlist and re-running the smoke tests.

Never pull a different model to work around the pin.

## Checks

| Check | Command | Expect |
|---|---|---|
| Ollama local only | `Get-NetTCPConnection -LocalPort 11434 -State Listen` | `127.0.0.1` |
| Model from the container | `docker compose ... exec ai-api python -c "import local_ai;print(local_ai.probe(local_ai.load_settings(),ttl=0))"` | `(True, True, '7fbdbf8f5e45')` |
| Usage | `curl -s http://127.0.0.1:3003/api/v1/assistant/usage` | `reported_cost_usd: 0` |

## Migration and rollback

Migration `2026.10.07-01` is applied at API startup to this stack's database
only. It is additive and checksummed.
`deployment/local-ai/rollback-local-ai.sql` removes it. That rollback was
drilled on the throwaway database `ai_rollback_xtrtest` (rollback, verify,
re-apply) on 2026-10-08.

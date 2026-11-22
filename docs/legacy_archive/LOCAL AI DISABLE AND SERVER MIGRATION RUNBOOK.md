# Local AI — disable and server migration runbook (3003 lab)

Version 1 — 2026-10-14. Scope: the isolated Local-AI lab on `127.0.0.1:3003`
(compose project `iran-monitor-local-ai`, worktree `E:\Iran monitor-local-ai`).
Production (3001), its collector and scheduler, OpenCTI (8080) and other projects are out of scope and are not touched by anything below.

## 1. Current state: AI disabled

| Item | State |
|---|---|
| Operator switch | `LOCAL_AI_DISABLED_REASON=temporarily_disabled_for_server_migration` in `.env` (gitignored) |
| `ai-translator` | stopped with `docker compose stop` (exit 0); `unless-stopped`, so it stays stopped after a Docker/host restart |
| Assistant | `ASSISTANT_ENABLED=false`; `POST /api/v1/assistant/query` → **503** `{state, message_fa}` |
| Translation requests | `POST /api/v1/news/{id}/translation/request`, social translation enqueue/run-batch/ai → **503** |
| `ai-api`, `ai-web`, `ai-db` | running (light: about 70 MB, 90 MB and 210 MB RAM) |
| Stored translations, history, conversations | unchanged; readable (read-only in the UI; "clear conversation" is disabled) |
| Model contracts (`apps/api/model_approvals.json`), attestations, test evidence | unchanged |
| Ollama | **left running and not unloaded**: it is shared with another project (see §8) |
| Scheduled tasks | `IranMonitor-LocalAI-NewsSync` (data only), `-Health` (HTTP/host checks only), `-Backup` (pg_dump only) all stay enabled; none calls Ollama |

What the switch does (code, not configuration only):

- `ai_gateway.OllamaAdapter` refuses to construct (`local_ai_disabled`), so no gateway call can reach Ollama.
- `model_identity._get` raises `identity_local_ai_disabled` before opening a socket (identity checks, loaded-model checks).
- `local_ai.probe()` returns "unreachable" and `local_ai.make_room_for()` does nothing, both without a request.
- `/api/v1/local-ai/models` does not call `/api/tags`.
- An HTTP middleware in `main.py` answers every AI-triggering POST with 503 before any handler runs (no queue row, no model call).
- `translation_worker_v2` records the state and waits idle if it is started anyway (no restart loop, no request).
- `GET /api/v1/local-ai/state` returns `{"state": "temporarily_disabled_for_server_migration", "message_fa": …, "translation_enabled": false, "assistant_enabled": false, "ollama_contacted": false}`.
  The assistant status endpoint, the models endpoint and the ops endpoint report the same state.
- UI: the assistant page shows «قابلیت هوش مصنوعی محلی برای کاهش مصرف منابع و آماده‌سازی انتقال به سرور، موقتاً غیرفعال است.».
  The question box, send button and suggestions are disabled.
  News pages show the notice instead of the "prioritise translation" button and stop polling for pending translations.
  The admin page shows the notice.
- Tests: `tests/monitoring/test_local_ai_disable_switch.py` (no socket opened while disabled), `tests/ui/ai-disabled-qa.cjs` (browser).

## 2. Run the system without Ollama (current mode)

From `E:\Iran monitor-local-ai`, with `.env` containing the switch:

```powershell
docker compose --env-file .env -f deployment/local-ai/compose.yml up -d --no-deps ai-db ai-api ai-web
# never start ai-translator in this mode (it would only wait idle, but there is no reason to run it)
curl.exe -s http://127.0.0.1:3003/api/v1/local-ai/state
```

## 3. Stop the whole 3003 stack (more RAM; not done — needs the owner's explicit instruction)

```powershell
docker compose --env-file .env -f deployment/local-ai/compose.yml stop
```

Frees about 370 MB more (api + web + db). Volumes, data and images stay. 3003 is then offline. NewsSync and Backup tasks would fail until it is started again (their failures are logged, nothing is lost; Production is not affected).
Start again: `docker compose --env-file .env -f deployment/local-ai/compose.yml up -d --no-deps ai-db ai-api ai-web`.

## 4. Rollback: re-enable local AI on this machine

1. In `.env` set `LOCAL_AI_DISABLED_REASON=` (empty), `LOCAL_AI_ASSISTANT_ENABLED=true`, `LOCAL_AI_AUTO_TRANSLATION=true`.
   The pre-change file is kept at `runtime/ai-disable/env.before-ai-disable.bak` (gitignored; contains the DB password: do not print or commit it).
2. `docker compose --env-file .env -f deployment/local-ai/compose.yml up -d --no-deps ai-api ai-web ai-translator`
3. `curl.exe -s http://127.0.0.1:3003/api/v1/local-ai/state` → `"state":"enabled"`; the admin page shows the worker heartbeat.
4. **Identity gate:** the host Ollama is now **0.40.2**, but the approvals are bound to **0.40.1** (`translategemma-27b-ollama0401-…`, `assistant_extractive_v1.3.2-qwen3-8b-…`).
   The worker and the assistant will refuse to run with `identity_ollama_version_mismatch` (the worker logged this on 2026-10-13).
   That is intended, fail-closed behaviour. Re-enabling needs a new attestation and an appended approval event after the gates run on the new runtime. Do not edit or remove existing events.

## 5. Connecting Ollama on the future server

- Ollama runs on the server (or on a GPU host on a private network). The containers reach it via `OLLAMA_BASE_URL`.
- `ai_gateway.OLLAMA_LOCAL_HOSTS` accepts local hosts only (`127.0.0.1`, `localhost`, `host.docker.internal`, …).
  For a separate inference host, add that private hostname in code with review; do not expose Ollama publicly.
  Ollama has no authentication: bind it to `127.0.0.1` or a private interface only, and firewall port 11434.
- Pin the same Ollama version that the approvals were attested on, or run the gates on the new version and append approval events (see §4.4).
- Copy the model blobs (§7), then run `ollama list` and compare each manifest digest with `apps/api/model_approvals.json`.
- The resource policy stays the same:
  - one inference at a time (advisory locks);
  - the assistant has priority over translation;
  - translation keeps a 120 s grace after chat;
  - the 27B and the assistant model are never co-resident.

  On a server with more than about 40 GB of free RAM or a GPU, co-residency can be reconsidered only after a resource test.

## 6. Environment variables (names only; values for secrets never in Git)

| Variable | Used by | Notes |
|---|---|---|
| `LOCAL_AI_DB_PASSWORD` | db, api, translator | **secret** — `.env` only |
| `LOCAL_AI_DISABLED_REASON` | api, translator | empty = enabled; `disabled_by_operator` or `temporarily_disabled_for_server_migration` |
| `LOCAL_AI_ASSISTANT_ENABLED` | api (`ASSISTANT_ENABLED`) | `true`/`false` |
| `LOCAL_AI_AUTO_TRANSLATION` | translator (`LOCAL_TRANSLATION_ENABLED`) | `true`/`false` |
| `LOCAL_TRANSLATION_ENABLED` | api (legacy on-demand path) | keep `false` |
| `OLLAMA_BASE_URL` | api, translator | default `http://host.docker.internal:11434` |
| `OLLAMA_MODEL`, `OLLAMA_MODEL_DIGEST` | api | the contract overrides the tag; env may not redirect it |
| `LOCAL_AI_NUM_CTX`, `LOCAL_AI_NUM_THREAD`, `LOCAL_AI_TEMPERATURE`, `LOCAL_AI_MAX_OUTPUT_TOKENS`, `LOCAL_AI_TIMEOUT_SECONDS` | api | must match the attested runtime parameters |
| `LOCAL_TRANSLATION_QC` | translator | `v2.2` (activated by the pre-registered held-out rule) |
| `LOCAL_TRANSLATION_BACKFILL_DAYS`, `…_BACKFILL_SLEEP_SECONDS`, `…_SUMMARY_CHARS`, `…_NEW_HOURS`, `…_KEEP_ALIVE`, `…_ASSISTANT_GRACE_SECONDS` | translator | queue and pacing |
| `LOCAL_AI_ASSISTANT_RETENTION_DAYS`, `LOCAL_AI_EXPERIENCE_JOBS` | api | |

Template without secrets: `deployment/local-ai/.env.example`.

## 7. Moving the models (never through Git)

- Store: `C:\Users\Administrator\.ollama\models` (about 72 GB: blobs + manifests). It holds:
  - translategemma 27b/12b/4b;
  - qwen3:8b;
  - gemma4:e2b and its pinned tags.
- Copy the whole `models` directory (manifests and blobs together) with a verifying tool, while no inference is running:
  `robocopy "C:\Users\Administrator\.ollama\models" "<target>\models" /E /COPY:DAT /R:2 /W:5 /LOG:"<log>"`
  Or use an external disk, or `rsync -a --checksum` to Linux (`/usr/share/ollama/.ollama/models` or `$OLLAMA_MODELS`).
- After copying, run `ollama list` on the server. The ID column, and the manifest digests from `ollama show --modelfile` or the `/api/tags` digest, must equal those in `model_approvals.json` and `runtime/local-ai-attestation/*.json`.
- Blobs are content-addressed (`sha256-…`): `sha256sum` of each blob file must equal its file name.
- `.gitignore` already excludes `runtime/`, dumps and `.env`. Never `git add` model files, dumps or `runtime/` evidence; the attestations travel with the model copy or a backup, not with Git.

## 8. Shared Ollama dependency (why Ollama was not stopped)

On 2026-10-14 the project **radyab** (`D:\nashr\docker-compose.yml`; containers `radyab-api-1`, `radyab-worker-1`) was running and configured with
`LLM_PROVIDER=ollama`, `LLM_BASE_URL=TRANSLATE_BASE_URL=http://host.docker.internal:11434`, `LLM_MODEL=qwen3:8b` and `TRANSLATE_MODEL=translategemma:27b`.
The loaded model (`qwen3:8b`, context 16384, loaded 07:30:45 UTC while a radyab test run started) was radyab's; the Iran Monitor assistant uses context 4096 and last ran on 2026-10-10.
Its `llama-server` kept consuming CPU throughout.
So Ollama was **not** unloaded, stopped, or removed from startup (`Ollama.lnk` in the Startup folder is unchanged).
Only Iran Monitor's use of it was switched off. To stop Ollama later, first confirm with the radyab owner, then use the tray app's "Quit Ollama" (graceful).
Rollback: start Ollama from the Start menu (the startup shortcut is still in place).

## 9. Database backup and restore

- Backup (scheduled daily 03:30 local, `IranMonitor-LocalAI-Backup`; manual run):
  `python scripts/backup_local_ai.py --second-copy D:/IranMonitorBackups/local-ai`
  This writes `runtime/backups-local-ai/ai-db-<ts>.dump` (pg_dump -Fc) plus `.sha256`. The script also:
  - test-restores it into a throwaway container with no network;
  - writes a second copy on D:;
  - logs a manifest line in `runtime/ops-status/backups/manifest.jsonl`.
- Restore on the server, into a new, empty database:
  ```bash
  sha256sum -c ai-db-<ts>.dump.sha256
  docker compose --env-file .env -f deployment/local-ai/compose.yml up -d ai-db
  docker cp ai-db-<ts>.dump iran-monitor-local-ai-ai-db-1:/tmp/r.dump
  docker exec iran-monitor-local-ai-ai-db-1 sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --exit-on-error /tmp/r.dump'
  ```
  Then compare the row counts in the manifest line (`live_counts_before`).
- Nothing is deleted by these steps; old dumps are kept.

## 10. Health checks after migration

| Check | Expected |
|---|---|
| `GET /` and `/admin` on the new host | 200 |
| `GET /api/v1/health` | 200 |
| `GET /api/v1/local-ai/state` | the intended state (`temporarily_disabled_for_server_migration` until re-enabled) |
| `POST /api/v1/assistant/query` while disabled | 503 |
| Row counts | news_items, news_item_translations, news_item_translation_history, assistant_sessions, assistant_messages equal the backup manifest |
| `ai_requests_log` count | unchanged while disabled (no inference) |
| No socket to 11434 from `ai-api` while disabled | `cat /proc/net/tcp` shows no `:2CAA` remote |
| After re-enabling | identity check passes (`/api/v1/assistant/status` `config_errors` empty); the admin page shows the worker heartbeat; one test question answered with citations |

## 11. Baseline and verification evidence (2026-10-14, gitignored)

`runtime/ai-disable/`:
- `ops-before.json`;
- `resources-before.txt` and `resources-after.txt`;
- `failclosed.json`;
- `sock-samples.txt`;
- `ui-qa.json`;
- `env.before-ai-disable.bak` (secret; never print).

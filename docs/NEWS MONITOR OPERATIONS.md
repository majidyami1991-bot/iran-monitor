# News monitor operations

The stack is local-only: the web service publishes `127.0.0.1:3001`; the API, PostgreSQL and collector publish no host ports. Keep the root `.env` private. Do not print or commit it. The API exposes read-only operational views under `/api/v1/`; the scheduler has no OpenCTI integration.

## Start or inspect

From the project root in PowerShell:

```powershell
docker compose -p defence-monitor-news --env-file .env -f deployment/news-monitor/compose.yml --profile scheduler up -d news-collector
docker compose -p defence-monitor-news --env-file .env -f deployment/news-monitor/compose.yml --profile scheduler ps
Invoke-RestMethod http://127.0.0.1:3001/api/v1/collection/status
Invoke-RestMethod http://127.0.0.1:3001/api/v1/collection/runs
```

The collector profile remains opt-in. Configure `NEWS_COLLECTION_ENABLED=true` and the required fixed interval of `900` seconds in the local environment only when authorized. The first scheduled attempt occurs after one interval. One cycle makes exactly one request per executable source, sequentially, with no retries, redirects, homepage/article/sitemap/X access or OpenCTI ingestion.

The executable set is defined by `config/sources/rss-execution-readiness.json`; `sources_planned` on each run follows it, so adding a validated source does not make later runs look partial. Check the current figure with:

```powershell
(Invoke-RestMethod http://127.0.0.1:3001/api/v1/sources/coverage) |
  Select-Object registered, executable, monitored
```

`registered`, `executable` and `monitored` are three different numbers and must not be reported as one. See `docs/STAGE 1 SOURCE COVERAGE.md`.

## Daily health check

```powershell
Invoke-RestMethod http://127.0.0.1:3001/api/v1/collection/status
Invoke-RestMethod http://127.0.0.1:3001/api/v1/stats/content
Invoke-RestMethod http://127.0.0.1:3001/api/v1/sources/coverage | Select-Object registered,executable,monitored
```

Healthy looks like: `scheduler_enabled: true`, `collector_health: healthy`, a `next_run_at` in the future, and a `last_run` whose `status` is `succeeded` and whose `sources_failed` is `0`.

`collector_health` values and what to do:

| Value | Meaning | Action |
| --- | --- | --- |
| `healthy` | Heartbeat is current and scheduling is on | None |
| `stopped_stale_heartbeat` | Heartbeat older than 45 seconds | Check `docker logs defence-monitor-news-news-collector-1`; the container is stopped or wedged |
| `not_running` | No `health.json` in the state volume | The collector has never started, or the state volume is missing |
| `stopped` | Scheduling is disabled in the environment | Intentional unless someone expected collection |

A source whose last success is older than three intervals reports `delayed` in `/api/v1/sources`, and the sources page shows it. That is the signal that one publisher has gone quiet while the cycle as a whole still succeeds.

## Backup and restore

```powershell
./scripts/backup.ps1 -Action backup                      # dump + collector state + SHA-256
./scripts/backup.ps1 -Action list
./scripts/backup.ps1 -Action verify -Path runtime/backups/<file>.dump
./scripts/backup.ps1 -Action restore -Path runtime/backups/<file>.dump
```

`verify` restores into a scratch database, compares row counts, then drops it; the live database is untouched. `restore` overwrites the live database, requires typing `RESTORE`, and stops the collector first so a running cycle cannot interleave with the archive. Backups land in `runtime/backups`, which is git-ignored, and contain no credentials.

Take a backup before any migration or image change. The database schema is applied by `migrate()` at API startup and is additive — new columns and tables only — so rolling the image back does not require a schema rollback. If a restore is ever needed, restore the dump and the matching `collector-state-*` directory together: the checkpoints in the state volume record feed positions that the database alone does not.

## Persian translation and summary

No provider is configured by default and every Persian field reports `pending`. Nothing is generated without one; no placeholder text is written.

To enable, set `NEWS_TRANSLATION_PROVIDER`, `NEWS_TRANSLATION_API_KEY` and `NEWS_TRANSLATION_MODEL` in `.env`, then run a small batch first:

```powershell
docker compose -p defence-monitor-news --env-file .env -f deployment/news-monitor/compose.yml run --rm --no-deps news-api python /app/translate_worker.py --limit 5 --dry-run
docker compose -p defence-monitor-news --env-file .env -f deployment/news-monitor/compose.yml run --rm --no-deps news-api python /app/translate_worker.py --limit 5
```

Read the five results in the interface before widening. The worker commits each field separately, so it can be interrupted with Ctrl+C and restarted without repeating finished work or losing partial progress. `--fields title,summary` is the default; add `body` only after reviewing summary quality and cost. See `docs/STAGE 1 CONTENT QUALITY.md` for the cost estimate and the decisions that go with it.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| Collector exits immediately with `COLLECTOR_IMAGE_REVISION_MISMATCH` | `COLLECTOR_REVISION` in `.env` does not match `BUILD_INFO.json` in the image | Rebuild the image at the current revision and update `.env`; do not edit `BUILD_INFO.json` |
| Every run reports `partial` right after adding a source | A source is in the executable set but fails to fetch | `GET /api/v1/collection/runs/{run_id}` names the source, stage and sanitized error |
| A run shows `skipped_locked` | A previous cycle still holds the PostgreSQL advisory lock | Expected if a cycle overran the interval; if it repeats, the previous cycle is wedged |
| A run sits in `running` | Should not happen: `finalize_run` runs in a `finally` block | If it does, the collector process was killed uncleanly. `repair_stuck_run.py` handles one evidence-bound run at a time and is dry-run by default |
| API returns 500 on startup | `migrate()` failed, usually a missing metadata file | `docker logs defence-monitor-news-news-api-1`; the error names the file and the directory searched |
| Persian fields all say `pending` | No provider configured | Expected. See the translation section above |
| An image does not load in the interface | Publisher blocks hotlinking, or the URL moved | Expected and reported in place. Media is unverified by design; nothing is downloaded |

## Rollback

Images are tagged by git revision, so rolling back is selecting an earlier tag:

```powershell
docker images defence-monitor-news-collector --format "{{.Tag}}"
# set COLLECTOR_REVISION in .env to the earlier revision, then
docker compose -p defence-monitor-news --env-file .env -f deployment/news-monitor/compose.yml --profile scheduler up -d news-collector
```

The database needs no rollback for an image change because every migration is additive. Never use `down -v` and never prune: the state volume holds collector checkpoints and the database volume holds every collected item.

## Stop and rollback

Stop only the project collector with `docker compose -p defence-monitor-news --env-file .env -f deployment/news-monitor/compose.yml --profile scheduler stop news-collector`. To roll back the application containers to their saved local images while preserving the database and volumes, run:

```powershell
docker compose -p defence-monitor-news --env-file .env -f deployment/news-monitor/compose.yml -f deployment/news-monitor/compose.rollback-8b.yml --profile scheduler up -d --no-deps news-api news-web
```

The rollback override selects `defence-monitor-news-api:rollback-8b` and `defence-monitor-news-web:rollback-8b`. It does not remove volumes or alter unrelated services. Verify the local-only port binding and database item/source counts after any operation. Never run `down -v` or prune shared Docker resources for routine rollback.

## Summary evidence

For legacy records without captured feed payloads, a missing summary remains “historical evidence unavailable”; it must not be reported as proof that the source omitted one. For newly collected entries the system records whether a sanitized RSS/Atom description or summary was present. It never fetches an article to create a summary.

## Collector state, checkpoints, and recovery

The named volume `defence-monitor-news_news-collector-state` is the sole writable collector state location. The `news-collector` service mounts it at `/state` read-write as UID/GID `65532:65532`; its root filesystem remains read-only. `news-api` mounts the same volume read-only because it only reads `health.json`. Do not run collection code inside `news-api` (`/state` is intentionally read-only there). A manual one-shot cycle, when separately authorized, must use the `news-collector` service with a command override; do not start the scheduler loop.

Inspect the service user and effective state mount without starting the collector:

```powershell
docker inspect defence-monitor-news-news-collector-1 --format '{{.State.Status}} user={{.Config.User}} rootfs_ro={{.HostConfig.ReadonlyRootfs}} {{range .Mounts}}{{.Destination}} rw={{.RW}} volume={{.Name}}{{end}}'
docker volume inspect defence-monitor-news_news-collector-state --format '{{.Driver}} {{.Mountpoint}}'
docker compose -p defence-monitor-news --env-file .env -f deployment/news-monitor/compose.yml exec -T news-api python -c "import os,stat; s=os.stat('/state'); print('uid',s.st_uid,'gid',s.st_gid,'mode',oct(stat.S_IMODE(s.st_mode)))"
```

Checkpoints use same-directory temporary files, flush/fsync, and atomic rename. The database stores the pending checkpoint payload in the source result in the same transaction as item/provenance/source-result writes. Only after the file checkpoint is written does the source result become `succeeded`. After an interrupted process, the collector can replay a committed payload to `/state` without making a request or inserting items again. Response bodies and credentials are never stored in checkpoint payloads.

Back up the existing volume by copying it from the stopped collector container into ignored runtime evidence; choose a new timestamped destination and do not overwrite earlier evidence:

```powershell
docker cp defence-monitor-news-news-collector-1:/state runtime/evidence/state-backup-YYYYMMDDTHHMMSSZ
```

To inspect a source result, use the run detail endpoint or a read-only SQL query:

```powershell
Invoke-RestMethod http://127.0.0.1:3001/api/v1/collection/runs/RUN_ID
docker compose -p defence-monitor-news --env-file .env -f deployment/news-monitor/compose.yml exec -T news-db psql -U defence_monitor -d defence_monitor -c "SELECT run_id,source_id,status,http_status,http_requests,response_bytes,observed,inserted,updates,error_stage,error_message_sanitized FROM source_run_results WHERE run_id='RUN_ID' ORDER BY source_id"
```

The versioned R2 repair utility is dry-run by default and accepts only the evidence-bound R2 run ID. First confirm `news-collector` is exited and no PostgreSQL advisory lock is held. Then inspect its plan; apply only if the output matches the R2 evidence:

```powershell
docker compose -p defence-monitor-news --env-file .env -f deployment/news-monitor/compose.yml run --rm --no-deps news-api python /app/repair_stuck_run.py --run-id c8ab7a29-9832-434b-9607-ab0dffdcbebf --collector-stopped
docker compose -p defence-monitor-news --env-file .env -f deployment/news-monitor/compose.yml run --rm --no-deps news-api python /app/repair_stuck_run.py --run-id c8ab7a29-9832-434b-9607-ab0dffdcbebf --collector-stopped --apply
```

The apply operation changes only that run and its existing source-result row. Repeating it after success is a no-op. For other stuck run IDs, stop and build a separate evidence-specific repair; never broaden this script or edit a running record by hand. To stop a collector that is actually running, use the project-scoped `stop` command above. Never remove or recreate the state volume and never use `down -v` or Docker prune.

After a Docker Desktop restart, verify the named volume still exists with `docker volume inspect defence-monitor-news_news-collector-state`, check DB/API/Web health and item/source/provenance counts, and confirm the collector remains exited and scheduling remains disabled. Named-volume contents persist across daemon restarts. If the volume is missing or its checkpoint files fail validation, restore from a verified backup before authorizing any collection; do not initialize an empty volume over valid state.

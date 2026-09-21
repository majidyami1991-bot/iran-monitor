# News monitor operations

The stack is local-only: the web service publishes `127.0.0.1:3001`; the API, PostgreSQL and collector publish no host ports. Keep the root `.env` private. Do not print or commit it. The API exposes read-only operational views under `/api/v1/`; the scheduler has no OpenCTI integration.

## Start or inspect

From the project root in PowerShell:

```powershell
docker compose -p iran-monitor-news --env-file .env -f deployment/news-monitor/compose.yml --profile scheduler up -d news-collector
docker compose -p iran-monitor-news --env-file .env -f deployment/news-monitor/compose.yml --profile scheduler ps
Invoke-RestMethod http://127.0.0.1:3001/api/v1/collection/status
Invoke-RestMethod http://127.0.0.1:3001/api/v1/collection/runs
```

The collector profile remains opt-in. Configure `NEWS_COLLECTION_ENABLED=true` and the required fixed interval of `900` seconds in the local environment only when authorized. The first scheduled attempt occurs after one interval. One cycle makes at most 11 feed requests, sequentially, with no retries, redirects, homepage/article/sitemap/X access or OpenCTI ingestion.

## Stop and rollback

Stop only the project collector with `docker compose -p iran-monitor-news --env-file .env -f deployment/news-monitor/compose.yml --profile scheduler stop news-collector`. To roll back the application containers to their saved local images while preserving the database and volumes, run:

```powershell
docker compose -p iran-monitor-news --env-file .env -f deployment/news-monitor/compose.yml -f deployment/news-monitor/compose.rollback-8b.yml --profile scheduler up -d --no-deps news-api news-web
```

The rollback override selects `iran-monitor-news-api:rollback-8b` and `iran-monitor-news-web:rollback-8b`. It does not remove volumes or alter unrelated services. Verify the local-only port binding and database item/source counts after any operation. Never run `down -v` or prune shared Docker resources for routine rollback.

## Summary evidence

For legacy records without captured feed payloads, a missing summary remains “historical evidence unavailable”; it must not be reported as proof that the source omitted one. For newly collected entries the system records whether a sanitized RSS/Atom description or summary was present. It never fetches an article to create a summary.

## Collector state, checkpoints, and recovery

The named volume `iran-monitor-news_news-collector-state` is the sole writable collector state location. The `news-collector` service mounts it at `/state` read-write as UID/GID `65532:65532`; its root filesystem remains read-only. `news-api` mounts the same volume read-only because it only reads `health.json`. Do not run collection code inside `news-api` (`/state` is intentionally read-only there). A manual one-shot cycle, when separately authorized, must use the `news-collector` service with a command override; do not start the scheduler loop.

Inspect the service user and effective state mount without starting the collector:

```powershell
docker inspect iran-monitor-news-news-collector-1 --format '{{.State.Status}} user={{.Config.User}} rootfs_ro={{.HostConfig.ReadonlyRootfs}} {{range .Mounts}}{{.Destination}} rw={{.RW}} volume={{.Name}}{{end}}'
docker volume inspect iran-monitor-news_news-collector-state --format '{{.Driver}} {{.Mountpoint}}'
docker compose -p iran-monitor-news --env-file .env -f deployment/news-monitor/compose.yml exec -T news-api python -c "import os,stat; s=os.stat('/state'); print('uid',s.st_uid,'gid',s.st_gid,'mode',oct(stat.S_IMODE(s.st_mode)))"
```

Checkpoints use same-directory temporary files, flush/fsync, and atomic rename. The database stores the pending checkpoint payload in the source result in the same transaction as item/provenance/source-result writes. Only after the file checkpoint is written does the source result become `succeeded`. After an interrupted process, the collector can replay a committed payload to `/state` without making a request or inserting items again. Response bodies and credentials are never stored in checkpoint payloads.

Back up the existing volume by copying it from the stopped collector container into ignored runtime evidence; choose a new timestamped destination and do not overwrite earlier evidence:

```powershell
docker cp iran-monitor-news-news-collector-1:/state runtime/evidence/state-backup-YYYYMMDDTHHMMSSZ
```

To inspect a source result, use the run detail endpoint or a read-only SQL query:

```powershell
Invoke-RestMethod http://127.0.0.1:3001/api/v1/collection/runs/RUN_ID
docker compose -p iran-monitor-news --env-file .env -f deployment/news-monitor/compose.yml exec -T news-db psql -U iran_monitor -d iran_monitor -c "SELECT run_id,source_id,status,http_status,http_requests,response_bytes,observed,inserted,updates,error_stage,error_message_sanitized FROM source_run_results WHERE run_id='RUN_ID' ORDER BY source_id"
```

The versioned R2 repair utility is dry-run by default and accepts only the evidence-bound R2 run ID. First confirm `news-collector` is exited and no PostgreSQL advisory lock is held. Then inspect its plan; apply only if the output matches the R2 evidence:

```powershell
docker compose -p iran-monitor-news --env-file .env -f deployment/news-monitor/compose.yml run --rm --no-deps news-api python /app/repair_stuck_run.py --run-id c8ab7a29-9832-434b-9607-ab0dffdcbebf --collector-stopped
docker compose -p iran-monitor-news --env-file .env -f deployment/news-monitor/compose.yml run --rm --no-deps news-api python /app/repair_stuck_run.py --run-id c8ab7a29-9832-434b-9607-ab0dffdcbebf --collector-stopped --apply
```

The apply operation changes only that run and its existing source-result row. Repeating it after success is a no-op. For other stuck run IDs, stop and build a separate evidence-specific repair; never broaden this script or edit a running record by hand. To stop a collector that is actually running, use the project-scoped `stop` command above. Never remove or recreate the state volume and never use `down -v` or Docker prune.

After a Docker Desktop restart, verify the named volume still exists with `docker volume inspect iran-monitor-news_news-collector-state`, check DB/API/Web health and item/source/provenance counts, and confirm the collector remains exited and scheduling remains disabled. Named-volume contents persist across daemon restarts. If the volume is missing or its checkpoint files fail validation, restore from a verified backup before authorizing any collection; do not initialize an empty volume over valid state.

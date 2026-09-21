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

# Phase 8B operational monitoring

## Project identity and safety

Run Compose from `E:\Iran monitor` with the root `.env`, project name `defence-monitor-news`, and `deployment/news-monitor/compose.yml`. The project name is explicit because `.env` also configures a separate OpenCTI Compose project. Never use `--remove-orphans`, `down`, `down -v`, pruning, or project-wide restart commands here. The news web service is the only service with a published port (`127.0.0.1:3001`); 3002 is reserved for the inactive preview. PostgreSQL data remains in `defence-monitor-news_news-db-data`.

The collector is a dedicated, unprivileged, read-only-root service with a private writable state volume. It has no host port, Docker socket, host network, or OpenCTI credentials. It reads only the 11 `executable: true` RSS entries from the readiness manifest, sequentially, at 900-second intervals. Its first request cycle begins after one full interval. Each cycle sends at most one HTTPS GET per feed, with 30-second timeout, 2 MiB response limit, no redirects and no retries. It does not fetch homepages, article pages, sitemaps or X.

## Observe

```powershell
$compose = @('compose', '-p', 'defence-monitor-news', '--env-file', '.env', '-f', 'deployment/news-monitor/compose.yml', '--profile', 'scheduler')
docker @compose ps
Invoke-RestMethod http://127.0.0.1:3001/api/v1/health
Invoke-RestMethod http://127.0.0.1:3001/api/v1/collection/status
Invoke-RestMethod 'http://127.0.0.1:3001/api/v1/collection/runs?page_size=20'
docker @compose logs --tail 100 news-collector
docker @compose exec -T news-collector python /app/health.py
```

Source health uses observed attempts only: `not_run` means no recorded success, `healthy` means a recent successful attempt, `degraded` means one or two consecutive failures, `failing` means at least three consecutive failures, and `delayed` means a successful source has exceeded three configured intervals without a later attempt. Health does not measure historical uptime or the truth of reporting. Review per-source results in `/api/v1/collection/runs/{run_id}` and source details in `/api/v1/sources/{source_id}`. Checkpoint JSON is written only after the source transaction commits, under the dedicated state volume.

## Enable and stop collection

Keep scheduler configuration local. Set `NEWS_COLLECTION_ENABLED=true` and `NEWS_COLLECTION_INTERVAL_SECONDS=900` in the environment used by Compose. Then start only the collector service:

```powershell
$env:NEWS_COLLECTION_ENABLED = 'true'
$env:NEWS_COLLECTION_INTERVAL_SECONDS = '900'
docker compose -p defence-monitor-news --env-file .env -f deployment/news-monitor/compose.yml --profile scheduler up -d --no-deps news-collector
Remove-Item Env:NEWS_COLLECTION_ENABLED
Remove-Item Env:NEWS_COLLECTION_INTERVAL_SECONDS
```

Stop only collection without stopping the dashboard or database:

```powershell
docker compose -p defence-monitor-news --env-file .env -f deployment/news-monitor/compose.yml --profile scheduler stop news-collector
```

Do not manually invoke `collector.py` or a cycle while the scheduled service is active. The collector enforces a PostgreSQL advisory lock; an overlapping run is recorded as `skipped_locked`. On a Docker Desktop restart, inspect the news project services and collector health before starting anything. The restart policy is `unless-stopped`; collection remains disabled unless its explicit environment flag is true.

## Roll back application images

Saved rollback tags are local and refer to the pre-Phase-8B API and frontend. Roll back only those two services; this preserves PostgreSQL data and volumes and does not touch OpenCTI or unrelated containers:

```powershell
docker compose -p defence-monitor-news --env-file .env -f deployment/news-monitor/compose.yml -f deployment/news-monitor/compose.rollback-8b.yml --profile scheduler up -d --no-deps news-api news-web
```

Stop the collector separately if the new schema or UI needs to be rolled back. Do not reset or restore PostgreSQL as part of an application rollback. Verify `/api/v1/health`, the 282-item minimum baseline, 11 sources, the 3001 loopback binding, and that port 3002 remains free.

## Summary, classification and reporting limits

Historical Phase 8A records did not retain their RSS summary payloads. Those records have unknown summary evidence; absence of stored text must not be presented as proof that a publisher omitted a summary. New collection records whether a sanitized RSS/Atom description or summary was present and stores only that feed excerpt. The collector never fetches article pages to fill summaries. Taxonomy v1 is a deterministic, versioned keyword match over stored title and summary, with no confidence score, causal claim or predictive analysis. Operational briefs report database counts and matching topics descriptively.

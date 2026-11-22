# Production frontend promotion

The approved Phase 9B Next.js dashboard replaces the legacy `news-web` at
http://127.0.0.1:3001. Only that service is rebuilt and recreated. PostgreSQL,
the API, the importer, volumes and OpenCTI retain their existing configuration.
The preview service is stopped after production verification, releasing 3002.

The dashboard uses the existing API and read-only source metadata. Legacy news,
source, analytics and about routes (including their assets and API requests)
are proxied to the unchanged internal `news-api:3000`. The frontend no longer
receives database credentials. No collection or scheduler is enabled.

## Rollback

The original frontend image is retained locally as
`defence-monitor-news-legacy:rollback-7096ec3`; its source remains in `apps/api`.
`compose.legacy.yml` preserves the original configuration and references that
retained image. From the repository root, restore only the frontend:

```powershell
docker compose --env-file .env -p defence-monitor-news -f deployment/news-monitor/compose.legacy.yml up -d --no-deps --no-build news-web
```

This command does not recreate dependencies or remove volumes. Do not prune
the rollback image. The image is local; this rollback assumes the same host.
To restore the promoted version later, use the main compose file with
`up -d --no-deps --no-build news-web`.

## Verification and evidence

Ignored evidence directory: `runtime/evidence/production-promotion/`.
It contains original Compose snapshots, safe container snapshots (no environment
values), before/after database row fingerprints, staging file hashes, build
output, test results, eight screenshots and their SHA-256 manifest.

The Phase 9B tests retain their original assertions. Override only their target
and evidence directory when rerunning against production:

```powershell
$env:TEST_BASE_URL='http://127.0.0.1:3001'
$env:TEST_EVIDENCE_DIR='runtime/evidence/production-promotion'
node apps/web-next/tests/component.cjs
node apps/web-next/tests/visual-9b.cjs
node apps/web-next/tests/refinement-9b.cjs
```

The 104 checks comprise 7 initial-render component assertions, 56 browser visual
checks, and 41 browser refinement checks. Component assertions do not use HTTP;
all 97 browser checks target 3001. JSON assertion results must also be checked,
because these existing browser scripts do not set failure exit codes for false
assertions. Additional browser checks cover six legacy routes including detail
pages. A seven-checkpoint stability gate spans at least 120 seconds, checks
HTTP, 104 items, 11 sources and zero frontend restarts, then compares protected
containers, database fingerprints and staging hashes before stopping preview.

Promotion result (2026-09-20): all 104 checks passed, with zero browser console
errors or failed requests. The stability procedure completed in 125 seconds.
Database fingerprints remained unchanged for 104 news items, 11 sources and
104 provenance records. Runtime data hashes and all 36 protected containers
(including stopped containers) remained unchanged. Production returns HTTP 200;
preview is stopped and 3002 has no listener. The news stack publishes only
127.0.0.1:3001. OpenCTI and unrelated services retain their original ports.

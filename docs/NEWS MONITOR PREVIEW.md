# Defence Monitor dashboard preview — Phase 9A

Preview only: `http://127.0.0.1:3002`. Existing application stays on port 3001. Internal pages link to the existing application; only the homepage is redesigned.

Stack: Next.js App Router 16.3.5, React 19.3.0, TypeScript 5.9.3, Tailwind 3.4.17, Lucide 1.47.0, Recharts 3.10.1. Exact direct dependency pins and npm lockfile. Local OFL Vazirmatn. No Framer Motion dependency: short CSS/chart transitions only. Reduced-motion preference disables CSS animations.

Data: server-only read-only GET aggregation from news-api over the existing Compose network. Browser fetches `/api/dashboard` on the preview origin; no database credentials or NEXT_PUBLIC secrets. Refresh every 60 seconds preserves selected range and ticker pause. Bounded pagination reads up to 10,000 items for date-window statistics; exceeding the bound produces an error rather than misleading totals. Missing data is not fabricated. Coverage uses registry, executable RSS readiness, web collection plan and unreachable-review metadata. Categories are operational readiness, not claims of active scheduled collection. X remains disconnected.

Time: UTC. Recent windows exclude future publications. Last registration is maximum `first_seen_at` of existing records. Topics use server ranking unchanged. Source labels use registered hostnames, never guessed publisher brands. Source mix uses actual database types. Heatmap requires seven distinct publication days; otherwise an explanatory empty state is shown. No percentage change or sparkline is fabricated.

Run (only preview):

```powershell
docker compose --env-file .env -p defence-monitor-news -f deployment/news-monitor/compose.yml -f deployment/news-monitor/compose.preview.yml --profile preview up -d --no-deps news-web-next-preview
```

No migration, collector, importer, volume or existing service modification. Preview uses non-root Node, read-only root filesystem, metadata read-only mount, dropped capabilities and no-new-privileges; binds only 127.0.0.1:3002. No push or cutover to 3001.

Evidence: ignored `runtime/evidence/phase-9a/`. Screenshot review is required before replacing the existing frontend in a later phase.

Validation results: TypeScript and production build pass. Playwright/Edge checks all four viewports, real 104/11 counts, local loaded font, RTL, four nonzero charts, semantic landmarks, drawer/Escape, external link attributes, GET auto-refresh after 61 seconds with range/pause retained. Zero normal console errors and failed requests. Five screenshots and SHA-256 manifest in evidence directory. Coverage reads 11 executable RSS, 6 Tier-2 sitemap, 2 Tier-3 HTML, 7 review records, 36 X accounts; none activated.

Existing container IDs/StartedAt/RestartCount unchanged. Data-row hashes match prior audited 104 items and 11 sources. Original API/frontend code untouched; no existing container rebuild. Input hashes unchanged. Port 3001 returns 200; preview alone binds 3002. Heatmap shows honest insufficient-data state when fewer than seven distinct days are available.

Direct runtime dependency licenses: Next.js/React/React DOM/Recharts MIT; Lucide ISC. TypeScript Apache-2.0; Tailwind MIT. Font OFL license included. Node build/runtime image exact version 24.16.0-bookworm-slim; lockfile retains integrity hashes. No Framer Motion; no image generator or stock imagery.

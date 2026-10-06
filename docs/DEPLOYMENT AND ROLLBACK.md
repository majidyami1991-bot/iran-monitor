# Deployment and Rollback — reference redesign

## Current state (2026-09-28)

| Component | Image | Address | Role |
|---|---|---|---|
| news-web (production) | `defence-monitor-news-news-web:rollback-pre-redesign` (= `latest`, 674515f7) | 127.0.0.1:3001 | Unchanged pre-redesign UI |
| news-api (production) | `defence-monitor-news-news-api:rollback-pre-redesign` (= `latest`, 9d1ee6d5) | internal | Unchanged pre-redesign API |
| news-web-preview | `defence-monitor-news-news-web:redesign-candidate` | **127.0.0.1:3002** | Redesign preview |
| news-api-preview | `defence-monitor-news-news-api:redesign-candidate` | internal | Redesign API; runs the derived-view jobs |
| news-db, news-collector, OpenCTI, others | unchanged | — | — |

The database already carries the additive migrations 2026.09.28-01 … -03 (see
the incident below). The production API ignores the new tables.

## Start or refresh the preview

```powershell
cd 'E:\Iran monitor-redesign'   # worktree of feature/iranmonitor-reference-redesign
docker build -f apps/api/Dockerfile -t defence-monitor-news-news-api:redesign-candidate .   # runs the 261-test suite
docker build -t defence-monitor-news-news-web:redesign-candidate apps/web-next
docker compose -p defence-monitor-news --env-file 'E:\Iran monitor\.env' -f deployment/news-monitor/compose.yml `
  -f deployment/news-monitor/compose.redesign-preview.yml --profile redesign-preview up -d --no-deps --no-build `
  news-api-preview news-web-preview
node tests/ui/redesign-qa.cjs   # BASE_URL defaults to 3002 via env
```

The API build needs `apps/collector/wheelhouse` and `test-wheelhouse`, which
are git-ignored. Copy them from the main working tree.

## Promote to production (only after client approval)

1. `./scripts/backup.ps1 -Action backup`
2. Tag the current production images: `rollback-pre-redesign` (already done).
3. Retag the candidates as `latest`:

   ```
   docker tag …news-api:redesign-candidate …news-api:latest
   docker tag …news-web:redesign-candidate …news-web:latest
   ```

4. `docker compose -p defence-monitor-news --env-file .env -f deployment/news-monitor/compose.yml up -d --no-deps --no-build --force-recreate news-api news-web`
5. Stop the preview:

   ```
   docker compose … -f compose.redesign-preview.yml --profile redesign-preview stop news-api-preview news-web-preview
   ```

   Only one API should run the jobs; an advisory lock also guards this.
6. Run `BASE_URL=http://127.0.0.1:3001 node tests/ui/redesign-qa.cjs`.

## Rollback

**Application rollback (tested).**

```
docker tag …:rollback-pre-redesign …:latest
docker compose … up -d --no-deps --no-build --force-recreate news-api news-web
```

This was performed for real on 2026-09-28 at 11:43 UTC; both containers came
back healthy on the exact pre-redesign image IDs. The drill also ran the
pre-redesign API image against a migrated copy of the database: health, news
(1,169), events, stats, sources, categories and item detail all returned 200.

**Schema rollback (tested on a restore; not needed for an application rollback).**
`deployment/news-monitor/rollback-redesign-schema.sql`, run after a fresh
backup. It removes only the redesign's tables, its three `news_events` columns
and the v2 events. In the drill it returned every baseline table count
exactly: `news_items` 1,169, `sources` 12, `translations` 81,
`classifications` 1,169, `events` 1, `members` 2, `media` 761, `provenance`
1,169, `runs` 472.

**Drill procedure used.**
1. Backup `runtime/backups/iran_monitor-20260928-101507.dump` (SHA-256
   69C8FCED…62BB).
2. Restore it into the scratch database `iran_monitor_drill`.
3. Run the candidate API against it: migrations applied; 1,169 items
   classified, 29 events, a briefing and 10 stories in 20.9 s.
4. Count diff: only `news_events` (1 → 30) and `news_event_members` (2 → 66)
   changed.
5. Run the old API against it: OK.
6. Run the rollback SQL: counts equal the baseline.
7. Drop the scratch database.

## Incident: production recreated by an unidentified actor (2026-09-28)

At 10:23:01 UTC `defence-monitor-news-news-api:latest` was rebuilt from the main
working tree, which at that moment contained the uncommitted redesign API.
At 10:25:44 `news-web:latest` was rebuilt. At 10:25:48 and 10:25:53 the
production `news-api` and `news-web` containers were recreated from
`deployment/news-monitor/compose.yml`. The production API's startup then
applied the additive migrations to the production database (at 10:25:52) and
ran one job cycle: 1,169 topic assignments, 29 events, 1 briefing.

None of these commands were issued by the redesign session. The only other
Claude session on the machine (phase-5-38) confirmed it had not touched this
project. The actor remains **unidentified**.

Actions taken:
- On the project owner's decision, production `news-api` and `news-web` were
  rolled back to the tagged pre-redesign images at 11:43 UTC.
- The unknown builds were kept as `…:unknown-build-20260928T1023` and
  `…:unknown-build-20260928T1025` for inspection.
- The redesign moved to a separate git worktree (`E:\Iran monitor-redesign`),
  so the main working tree holds only committed pre-redesign code.

The additive schema and derived rows were left in place: the drill shows the
old API is unaffected by them, and removing them is an explicit, tested
option (above).

**Recommended:** find out what rebuilt production (a scheduled task, a watcher,
or a manual compose run) before promotion, and keep it from rebuilding
production from a working tree.

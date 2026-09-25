# Khabar Backup Manifest — 2026-09-25

A stable, restorable checkpoint of the monitoring platform, taken immediately
before starting the foresight-platform expansion. This document is the
single source of truth for how to find, verify, and restore this backup.

## Git checkpoint

| Field | Value |
| --- | --- |
| Source commit | `c29126a41335c8741b641dfa9f9125c7c01cb2c3` |
| Branch | `backup/khabar-backup-2026-09-25` (points at the same commit) |
| Annotated tag | `khabar-backup-2026-09-25` (tag object `60c6ea33376e2db57eb01bd9a7b45c54dea796a4`) |
| Tag message | `khabar backup - stable monitoring platform before foresight expansion` |
| Worktree state at backup time | Clean — no uncommitted changes, no untracked files |
| Submodule | `vendor/opencti-docker` at `18fdf8512f69e63d0856a7a4f5633ef7e482e5c0` (heads/master) |
| Not pushed | This backup exists only in the local repository; no remote push was performed (no remote/push authorization confirmed) |

Development from this point forward continues on `feature/iran-monitor-foresight-platform`,
branched from this same commit.

## Production health at backup time (2026-09-25, ~09:32 UTC)

| Service | Status |
| --- | --- |
| API (`iran-monitor-news-news-api-1`) | healthy, `Up 20 hours` |
| Web (`iran-monitor-news-news-web-1`) | healthy, `Up 19 hours` |
| Collector (`iran-monitor-news-news-collector-1`) | healthy, `Up 20 hours` |
| PostgreSQL (`iran-monitor-news-news-db-1`) | healthy, `Up 5 days` |
| Scheduler | enabled, collector health `healthy`, next run `2026-09-25T09:39:08Z` |
| Last collection cycle | succeeded — 12/12 sources, 0 failed, 1 inserted, 181 duplicates, 86 updates |

| Metric | Value |
| --- | --- |
| Total news items | 946 |
| Sources | 12 (all healthy, 0 delayed/failed, 0 not-run) |
| Provenance complete | 946 / 946 (100%) |
| Items classified | 946 / 946, taxonomy v2.1.0 |
| Items in "سایر" (fallback) | 236 (~25%) |
| Items, 24h / 7d | 154 / 702 |

OpenCTI (`iran-monitor-opencti-*`, 11 containers) and unrelated projects
(`mlw-*`, `plane-preview-*`) were running normally and were not touched by
this backup process.

## Screenshots

`backups/khabar-backup-2026-09-25/screenshots/` (desktop 1920×1080, production
`127.0.0.1:3001`, not committed to git — see Storage Policy below):
`dashboard.png`, `news-stream.png`, `categories.png`, `events.png`,
`topics.png`, `sources.png`, `analytics.png`, `monitoring.png`.

## Database backup

| Field | Value |
| --- | --- |
| File | `backups/khabar-backup-2026-09-25/khabar-backup-2026-09-25.dump` |
| Format | PostgreSQL custom format (`pg_dump -Fc`) |
| PostgreSQL version | 16.14 (both dump source and restore target) |
| Size | 1,950,095 bytes |
| SHA-256 | `8D25C30C1AC5DAAF760AC563007D93110256984E84D5D354DB62463FF9B7A670` |
| Created (UTC) | 2026-09-25T09:32:57Z |
| Dump command | `pg_dump -U iran_monitor -d iran_monitor -Fc -f khabar-backup-2026-09-25.dump` (run inside `iran-monitor-news-news-db-1`, password from the container's own `POSTGRES_PASSWORD`) |
| Restore command | `pg_restore -U iran_monitor -d <target_database> khabar-backup-2026-09-25.dump` |

### Restore drill — performed and verified

1. Created a throwaway database `restore_drill_test` on the same PostgreSQL
   server (`CREATE DATABASE restore_drill_test OWNER iran_monitor`).
2. Restored the dump file into it with `pg_restore`.
3. Compared row counts against the live `iran_monitor` database:

   | Table | Production | Restored | Match |
   | --- | --- | --- | --- |
   | `news_items` | 946 | 946 | ✅ |
   | `sources` | 12 | 12 | ✅ |
   | `item_classifications` | 946 | 946 | ✅ |

4. Dropped `restore_drill_test` and removed the temporary in-container copy
   of the dump file. Production database was never touched by the drill.

**Result: PASS.** The backup is proven restorable, not just proven to exist.

## Source archive

| Field | Value |
| --- | --- |
| File | `backups/khabar-backup-2026-09-25/khabar-source-2026-09-25.zip` |
| Built with | `git archive --format=zip HEAD` (at commit `c29126a`) — includes only git-tracked files, so `.env`, dumps, runtime data and anything git-ignored are structurally absent, not just excluded by a filter |
| Size | 646,043 bytes |
| SHA-256 | `94FACD07FA0137F2DF6B410F55D19C880F1DBB8EAE19F06B489C4BB8ED3A2BA2` |
| Restore drill | Extracted to a scratch directory; confirmed no `.env`/`*.dump` files present anywhere in the archive, and confirmed key source files present and readable (`apps/api/ops.py`, `apps/web-next/app/Dashboard.tsx`, `config/sources/classification-taxonomy-v2.json`). Extraction directory removed after verification. |
| Frontend runnability | Not re-verified via a separate build from the extracted archive — redundant given the currently-running production containers (`iran-monitor-news-news-api:latest`, `iran-monitor-news-news-web:latest`) were built from this exact commit and are live and healthy right now, which is a stronger runnability proof than a cold extract-and-build would be. |

Note: `git archive` does not include submodule content — `vendor/opencti-docker`
appears as an empty directory reference in the zip. The submodule's own
upstream (`heads/master` at `18fdf851...`) is recorded above and is
independently restorable via `git submodule update --init`.

## Storage policy

Everything under `backups/khabar-backup-2026-09-25/` (the `.dump` file, the
source `.zip`, and screenshots) is **git-ignored** (`backups/` is listed in
`.gitignore`) and stays local to this machine — never committed, per the
brief's explicit instruction that a database dump may be large, may contain
copyrighted syndicated content, or sensitive data. This manifest is the only
part of the backup that is version-controlled.

## Rollback procedure (if ever needed)

```
# Code rollback
git checkout khabar-backup-2026-09-25 -- apps deployment config docs scripts tests
# or, for a full environment rollback:
git checkout backup/khabar-backup-2026-09-25

# Database rollback (destructive — confirm target first)
docker exec -i iran-monitor-news-news-db-1 sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -U iran_monitor -d iran_monitor --clean --if-exists' \
  < backups/khabar-backup-2026-09-25/khabar-backup-2026-09-25.dump
```

Not exercised against the live `iran_monitor` database (only against the
throwaway `restore_drill_test` database, by design — the drill proves the
mechanism without touching production).

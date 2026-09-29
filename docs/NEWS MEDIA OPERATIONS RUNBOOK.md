# News Media Operations Runbook

Procedures for the media v2 pipeline. They assume the preview stack (compose
project `iran-monitor-news`, files `compose.yml` + `compose.redesign-preview.yml`,
profile `redesign-preview`) and the env file `E:/Iran monitor/.env`.
Never print or commit that file or anything derived from it.

## Components

| Piece | Where | Runs |
|---|---|---|
| Migration `2026.09.29-04` | `apps/api/redesign_schema.py` | at API startup (additive, checksummed) |
| RSS extraction | `media_pipeline.rss_candidates`, called by `collector.parse` | every collector cycle (after collector rebuild) |
| Legacy-row sync | `media_pipeline.sync_legacy_rows`, called from the experience loop | API background loop; offline, no network |
| Offline backfill | `apps/api/media_backfill.py` | manual, one-off |
| Live pilot | `apps/api/media_pilot.py` | manual, one invocation, ≤ 10 items |
| API | `media_api.py`: `/api/v1/media/status`, `/api/v1/media/stats`, `/api/v1/news/{id}/media` | API |
| CSP host list | `apps/web-next/media-image-hosts.json` | web build time |

## Legacy fingerprint (run before and after every write step)

```sh
docker exec -i iran-monitor-news-news-db-1 sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At' < legacy_fp.sql
```

`legacy_fp.sql` computes md5 over `news_items`, `news_item_translations`,
`news_item_provenance`, the legacy media columns of non-v2 rows, and
`news_item_content`. Compare the output before and after a step; any
difference is a stop condition. Keep in mind that the production collector
adds rows between cycles, so take the two fingerprints close together.

## Offline backfill

The backfill re-parses **saved** feed XML. It never fetches anything.

```sh
# The API image's rootfs is read-only, so use a one-off container.
# Write DATABASE_URL to a gitignored file without printing it; delete it after the run.
docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' iran-monitor-news-news-api-preview-1 \
  | grep -E '^(DATABASE_URL|COLLECTOR_METADATA_DIR)=' > runtime/.bf.env
docker run --rm --network <compose network> --env-file runtime/.bf.env \
  -v "<repo>/runtime/media-audit/feeds:/feeds:ro" --entrypoint python \
  iran-monitor-news-news-api:media-candidate /app/media_backfill.py --feeds-dir /feeds --dry-run
# review the report, then run without --dry-run, then run again: rows_written must be 0
rm runtime/.bf.env
```

Stop if `lost_primary` is unexpected or the legacy fingerprint changes.

## Live pilot

1. Write a manifest of at most 10 `item_id`s (`{"items":[{"item_id":…}]}`).
2. Dry run first; it must report 0 requests:
   `python /app/media_pilot.py --manifest m.json --dry-run`
3. Live, once:
   `NEWS_ARTICLE_MEDIA_FALLBACK_ENABLED=true python /app/media_pilot.py --manifest m.json`

Budgets are enforced in code: 10 article requests, 10 image validations,
sequential, no retry. The pilot stops at the first SSRF refusal, oversize
response or contract mismatch. Do not schedule it, and do not run a second
cycle without a new decision.

## Adding an image host to the CSP

A primary image on a host missing from `media-image-hosts.json` renders as
a placeholder. That is safe, but it means the image is lost. To add a host:

1. List primary hosts:
   `SELECT DISTINCT source_hostname FROM news_item_media WHERE is_primary;`
2. Add the hostname (bare host, no scheme) to `hosts` with a note that says
   why it is there.
3. Rebuild the web image and re-run `tests/ui/news-media-qa.cjs`.

## Rollback

| Level | Action |
|---|---|
| UI only | Restart `news-web-preview` with `PREVIEW_WEB_IMAGE=<previous tag>` (tested with `preview-before-media`). |
| API only | Restart `news-api-preview` with `PREVIEW_API_IMAGE=<previous tag>`. The old API ignores the v2 columns. |
| Schema + data | Stop anything that runs the v2 code, then run `deployment/news-monitor/rollback-news-media-v2.sql`. It deletes the `v2:` rows, drops the v2 indexes, constraints and columns, and removes the `schema_migrations` row. Take a `pg_dump` first. |

The schema rollback was drilled on the throwaway database `iran_monitor_mtest`:
migrate, backfill three times, roll back, and re-apply. The legacy
fingerprint returned exactly to baseline.

## Promotion to production (not done; needs approval)

Promote in this order, and verify the fingerprint and QA after each step:

1. `pg_dump` backup.
2. **Production API** image with the v2 code. The migration is already
   applied, so this is a code-only change.
3. **Production web** image (CSP host list, `MediaViewer`, placeholders).
4. **Collector** image rebuild. Only this step makes new items get
   enclosure and `media:content` images. It changes collection behaviour,
   so it needs its own approval.

Production on `127.0.0.1:3001` must not be changed without the owner's
explicit approval.

## Monitoring

`GET /api/v1/media/stats` reports coverage, per-source coverage, validation
statuses, rejection classes, `by_method`, HTTP status counts and
`hotlink_403`. Warning signs:

- per-source coverage dropping sharply, which usually means a feed changed
  its format;
- a jump in `rejected` rows for a single reason;
- `hotlink_403` above 0.

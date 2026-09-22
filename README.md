# Iran Monitor

A Persian-language monitoring product that answers one question about a defined
set of open sources: **what was published, when, by which source, and under what
subject?**

This repository delivers **stage 1: monitoring**. Correlation, trend analysis,
scenarios and early warning are later stages and are not present. Nothing in the
interface should be read as analysis; the statistics are descriptive counts of
stored records.

The immutable `sites.docx` in this directory is the authoritative original source
list (SHA-256 `3F7522C94952DD85254F45CADF600A64EE6F264D27E30E3D2BF3297D59C47980`).

## What runs

| Service | Address | Role |
| --- | --- | --- |
| `news-web` | `127.0.0.1:3001` | Persian, RTL interface (Next.js) |
| `news-api` | internal only | Read APIs under `/api/v1/`, additive schema migration at startup |
| `news-db` | internal only | PostgreSQL 16, the system of record |
| `news-collector` | internal only | Opt-in 15-minute RSS scheduler |

OpenCTI is deployed separately on `127.0.0.1:8080` from
`deployment/opencti/`. **No news data is sent to it**, and it is not a
substitute for this product. Do not change it while working here.

## Coverage, stated honestly

| Count | Value | Meaning |
| --- | --- | --- |
| Registered | 62 | Canonical sources from `sites.docx` |
| Executable | 12 | Validated, permitted collection path |
| Monitored | see `/api/v1/sources/coverage` | Has actually completed a fetch |

The remainder are 5 sitemap candidates, 2 HTML candidates, 7 publishers that
refuse automated access, and 36 X accounts with no authorised collection path.
Per-source detail is in [source coverage](docs/STAGE%201%20SOURCE%20COVERAGE.md).

## Install

Requires Windows PowerShell 5.1+, Git and Docker Desktop on WSL2 with Compose
2.24.4 or newer.

```powershell
Copy-Item .env.example .env         # then fill in NEWS_DB_PASSWORD with a local random value
cd 'E:\Iran monitor'

# Build the collector image and pin it to the current revision.
$rev = (git rev-parse HEAD).Trim()
$ts  = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
docker build -f apps/api/Dockerfile --build-arg GIT_REVISION=$rev --build-arg BUILD_TIMESTAMP_UTC=$ts -t "iran-monitor-news-collector:$rev" .
(Get-Content .env) -replace '^COLLECTOR_REVISION=.*$', "COLLECTOR_REVISION=$rev" | Set-Content .env -Encoding utf8

# Start the stack.
docker compose -p iran-monitor-news --env-file .env -f deployment/news-monitor/compose.yml up -d
```

The image build runs the test suite; a failing test fails the build. The
collector refuses to start unless `COLLECTOR_REVISION` matches the revision
baked into the image, so a stale image cannot run against newer code.

Open `http://127.0.0.1:3001`. Collection is **off** until you enable it:

```powershell
# Set NEWS_COLLECTION_ENABLED=true in .env, then:
docker compose -p iran-monitor-news --env-file .env -f deployment/news-monitor/compose.yml --profile scheduler up -d news-collector
Invoke-RestMethod http://127.0.0.1:3001/api/v1/collection/status
```

The first cycle runs one interval later. One cycle makes exactly one request per
executable source, sequentially, with no retries and no redirects.

## Collection policy

These limits are structural, not conventions:

- One HTTP request per source per cycle. No article pages, no sitemaps, no images.
- Redirects are refused, so a feed that moves fails loudly instead of silently
  following somewhere else.
- 403 responses, robots disallow, logins, CAPTCHAs and paywalls are never worked
  around. A publisher that refuses automated access is recorded as blocked.
- Body text is extracted only from bytes the collector already fetched, so the
  content pipeline cannot bypass any source's access policy.
- Being able to retrieve content is not permission to republish it. Where a
  publisher does not syndicate the article body, the product shows the summary,
  the metadata and a link to the original.

## Content

Each item carries an English body, a Persian title, a Persian summary, a Persian
body, and media — each with its own state. A field that nothing has produced
reports `pending`; it is never filled with a guess.

**No translation provider is configured, so every Persian field is currently
`pending`.** The pipeline is built and tested; it needs a provider decision and
a credential. See [content quality](docs/STAGE%201%20CONTENT%20QUALITY.md) for the
options, cost estimates and the decisions required.

## Operating

```powershell
./scripts/backup.ps1 -Action backup
node tests/ui/stage1-qa.cjs                  # browser acceptance
Invoke-RestMethod http://127.0.0.1:3001/api/v1/stats/content
```

Health checks, troubleshooting, rollback and the translation worker are in
[operations](docs/NEWS%20MONITOR%20OPERATIONS.md). Never run `down -v` and never
prune: the named volumes hold every collected item and the collector checkpoints.

Keep `.env` private. It is git-ignored and holds both the news database password
and the OpenCTI secrets.

## Documentation

- [Source coverage](docs/STAGE%201%20SOURCE%20COVERAGE.md) — all 62 sources and why each is or is not collected
- [Content quality](docs/STAGE%201%20CONTENT%20QUALITY.md) — field states, media limits, translation decision
- [Operations](docs/NEWS%20MONITOR%20OPERATIONS.md) — health, backup, troubleshooting, rollback
- [Architecture](docs/NEWS%20MONITOR%20ARCHITECTURE.md)
- [Security](docs/SECURITY.md)
- [OpenCTI deployment](deployment/opencti/README.md) — separate system, not part of stage 1

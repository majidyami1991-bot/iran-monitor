# Source health policy

Defence Monitor reports health from recorded collector attempts; it does not claim historical uptime. A source with no recorded success is `not_run`. A successful source becomes `healthy`; one or two consecutive failed attempts make it `degraded`, and three or more make it `failing`. A source whose last success is more than three configured collection intervals old is `delayed` when it has no current consecutive failure.

Each scheduled cycle attempts only the 11 registry entries explicitly marked executable in `rss-execution-readiness.json`, one HTTPS request per feed, sequentially, with no retries or redirects. Failures are isolated per source. Error details stored or shown are sanitized; credentials, response bodies and article pages are not collected. Source health is descriptive operational evidence, not a statement about the truth or quality of published content.

The collector is disabled unless `NEWS_COLLECTION_ENABLED=true`. The supported interval is exactly 900 seconds. PostgreSQL advisory locking prevents overlapping cycles. A heartbeat and per-source checkpoints are written to the dedicated `news-collector-state` volume.

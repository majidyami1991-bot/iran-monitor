# Phase 2R deployment
Canonical definition: compose.pinned.yml. Earlier compose.override.yml is historical and must not be combined with it.
Target OpenCTI: 7.260910.0; release commit bf9332a79da75a028113b4d05abf1cb9ce1ef775.
Official schema: https://github.com/OpenCTI-Platform/docker.git at 18fdf8512f69e63d0856a7a4f5633ef7e482e5c0 (2026-09-12T18:25:44Z).
Subject: chore(compose): replace the MinIO image by pgsty/silo in the compose stacks (#606) (#607).
The preferred pre-release schema d3aa93833fe16f06bfd272e76b2876f0a6a81e90 cannot be freshly deployed because minio/minio is unavailable. The official corrective commit explicitly preserves S3, MINIO_* credentials, server /data, mc ready local, named data volume and on-disk compatibility. Its other changes replace the image in alternative stacks and clarify a sample comment.
Selected Silo tag: RELEASE.2026-09-03T13-18-01Z, registry verified linux/amd64. No dependency port is published.
Only 12 bootstrap services: four dependencies, platform, worker (three replicas), and six internal file import/export connectors. XTM One, its PostgreSQL/worker, XTM composer/RSA helper, MITRE/OpenCTI external datasets, analysis and external-reference connectors are excluded. Enabling any later requires a separate reviewed configuration change; upstream definitions remain intact.
Existing secrets preserved; only OPENCTI_ENCRYPTION_KEY added as random base64 32 bytes. Unused existing keys retained; new XTM-only keys are unnecessary. Removed XTM platform links because XTM services are excluded.
Healthchecks and retained service settings preserved; RabbitMQ config binds the unchanged upstream file via corrected relative path. Only 127.0.0.1:8080 is published.
Run scripts/preflight.ps1 before initial startup. Runtime sysctl is not persistent. Never print full rendered Compose: it contains secrets.
Current status (Phase 3D): all four dependencies, OpenCTI, three Worker replicas, and six internal import/export connectors are running from the digest-pinned IMAGE LOCK. All containers remained running with RestartCount 0 through the stability gate; OpenCTI localhost HTTP returns 200. No external feeds, ingestion tasks, export tasks, login, or test data were initiated. Only 127.0.0.1:8080 is published.

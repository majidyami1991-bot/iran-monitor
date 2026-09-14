# Pinned OpenCTI deployment (not started)

Official upstream: https://github.com/OpenCTI-Platform/docker.git
Stable Git tag: NONE (official remote provides no tags).
Detached commit: 12ba587e3cd7b0643fc000b0fb27b016893fddd4; numbered OpenCTI image release: 7.260224.0.
Canonical file: ../../vendor/opencti-docker/docker-compose.yml.
The current moving branch uses latest images. We intentionally inspect and pin the last explicit numbered release commit instead; this is not the latest-release claim. See the baseline for details.

## Local override
Compose >= 2.24.4 merge tags remove MinIO host ports, remove the Docker-socket-based xtm-composer and unused rsa-key-generator, and replace web ports with 127.0.0.1:8080:8080.
A naive empty ports list is NOT used. The merged configuration must contain exactly one host publication. No upstream files are edited. No derived Compose file is needed.
Default network and named volumes receive the iran-monitor-opencti prefix. No fixed container names or external volumes/networks. Existing unrelated 5432/6379/9000 publications do not conflict.
RabbitMQ uses the upstream relative rabbitmq.conf bind mount (max message 536870912 bytes; consumer timeout 86400000 ms). Compose resolves it relative to the first, upstream Compose file.
Upstream healthchecks are preserved. Worker has three replicas. Internal file connectors and OpenCTI/MITRE dataset connectors are retained; an eventual startup will activate them and may fetch upstream datasets. It does not import sites.docx or authorize X access.
No Enterprise license is supplied. The upstream sample does not require an encryption key at this revision. All sample keys, including unused OpenSearch and removed-manager keys, exist locally for parity.

## Safe validation
Run scripts/preflight.ps1 from any directory. Do not print full config: it includes secrets.
From the project root these commands emit only images or services and do not pull:

```powershell
docker compose --project-name iran-monitor-opencti --env-file .env -f vendor/opencti-docker/docker-compose.yml -f deployment/opencti/compose.override.yml config --images
docker compose --project-name iran-monitor-opencti --env-file .env -f vendor/opencti-docker/docker-compose.yml -f deployment/opencti/compose.override.yml config --services
```
Image references are version tags, not content digests; registry availability and runtime compatibility remain untested. Reassess release security before Phase 2.
No startup command is executed in Phase 1. After explicit approval, rerun preflight immediately before any startup. If sysctl is low, preflight prints the correction but never applies it.

# Phase 0 / Phase 1 baseline

Source SHA-256 before Phase 1: 3F7522C94952DD85254F45CADF600A64EE6F264D27E30E3D2BF3297D59C47980
Expected unchanged SHA-256 after Phase 1: 3F7522C94952DD85254F45CADF600A64EE6F264D27E30E3D2BF3297D59C47980
Initial directory: sites.docx only (18598 bytes); no existing Git repository.
Docker server 29.7.2, desktop-linux, WSL2, 24 logical CPUs, 31.22 GiB Docker RAM.
vm.max_map_count=1048575; runtime only, not guaranteed across restart/update.
Port 8080 free and not reserved. Existing ports 5432, 6379, 9000 belong to unrelated projects.
Nine running containers: mlw-redis, mlw-postgres, plane-preview-beat-worker-1, plane-preview-worker-1, plane-preview-api-1, plane-preview-plane-db-1, plane-preview-plane-minio-1, plane-preview-plane-mq-1, plane-preview-plane-redis-1.
Docker data: C:\Users\Administrator\AppData\Local\Docker\wsl\disk\docker_data.vhdx on Samsung 990 PRO NVMe. Project E: is HDD.

## Upstream pin decision
Official URL: https://github.com/OpenCTI-Platform/docker.git
Fetched official tags; git ls-remote --tags origin returned no tags. Stable tag: NONE.
Inspected current head 18fdf8512f69e63d0856a7a4f5633ef7e482e5c0: moving latest images, additional XTM services and Docker socket access.
Selected exact historical official release commit: 12ba587e3cd7b0643fc000b0fb27b016893fddd4 (release 7.260224.0), the last explicit numbered OpenCTI release before the switch to latest images in inspected history.
This is a reproducible configuration baseline, NOT a claim to be the latest OpenCTI release or currently supported release.
Submodule detached at this commit; canonical file docker-compose.yml. No upstream files modified.
Local override removes XTM manager and RSA helper to prohibit Docker socket access; removes MinIO publication with !reset and replaces OpenCTI ports with !override to bind loopback 8080 only.
Existing healthchecks, authentication settings and named-volume persistence remain unchanged for retained services.

## Phase 1 validation
Read-only preflight passed (172 checks). PowerShell syntax passed. An inherited OPENCTI_PORT override was rejected with nonzero exit in an isolated child process; .env was not changed.
Compose config and config --images succeeded without pulling. Effective services: 16; only 127.0.0.1:8080 -> opencti:8080 published. All 26 sample keys SET; 12 UUIDv4 values valid and distinct.
Source SHA-256 after Phase 1 matched the before value. Generated secret values were scanned against all candidate project files before staging; no matches.
No containers, images, networks or volumes were created or modified. Runtime functionality remains untested.

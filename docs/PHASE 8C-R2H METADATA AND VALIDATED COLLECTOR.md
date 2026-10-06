# Phase 8C-R2H — Metadata and validated Collector

Status: **PASS**

The metadata contract is `/app/sources`, selected by `COLLECTOR_METADATA_DIR` (default `/app/sources`). Four required JSON files are loaded through one validating helper: source-registry, RSS execution readiness, collection capabilities, and classification taxonomy. Missing or malformed files raise explicit `collector_metadata_missing` or `collector_metadata_invalid` errors.

Code commit: `5fc9d371f6de9e0c6f957094cf9363fb6fcc7999`. The offline test build ran pytest in the image: **38 passed**. Runtime-final was then built offline from the same commit.

Runtime image: `defence-monitor-news-collector:5fc9d371f6de9e0c6f957094cf9363fb6fcc7999`, image ID `sha256:bc59e881c962b656fd6eea13c7cada04d3a6df846aecf0268cb1bfe604b1d6a4`, OCI and BUILD_INFO revision equal the code commit. All four metadata files opened successfully in a no-network container. Positive parity passed; wrong revision was rejected with `COLLECTOR_IMAGE_REVISION_MISMATCH` before any DB connection. `import pytest` fails in runtime-final.

Compose configuration was evaluated with the local revision selection and resolves to the same image and expected revision; no compose service was started. DB remained `282/11/282`, no new collection run was created, Collector remained stopped, Scheduler disabled, and no RSS or production write occurred.

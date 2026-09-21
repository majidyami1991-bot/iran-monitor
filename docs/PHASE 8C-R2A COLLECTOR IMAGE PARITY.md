# Phase 8C-R2A collector image parity

Status: **BLOCKED — IMAGE BUILD DID NOT COMPLETE**.

## Diagnosis

The Phase 8C-R2 live cycle used `iran-monitor-news-news-collector:latest`, whose image ID was the old collector image (`sha256:f3837600…`). The R1 serializer had been validated in an API candidate image only. The Compose service had a `build` section but no revision-pinned `image`, so a one-off `compose run` could resolve the stale local collector tag.

The controlled correction prepared in this phase pins `news-collector` to `iran-monitor-news-collector:205d769`, passes `EXPECTED_COLLECTOR_GIT_REVISION=205d769`, adds the pre-lock `COLLECTOR_IMAGE_REVISION_MISMATCH` guard, and adds non-secret OCI/build metadata plus `python -m iran_monitor_collector build-info`.

## Build result

The one permitted build invocation was:

`docker build --network=none --build-arg GIT_REVISION=205d769 --build-arg BUILD_TIMESTAMP_UTC=<UTC> -t iran-monitor-news-collector:205d769 -f apps/api/Dockerfile .`

It failed at the existing `pip install --no-cache-dir -r requirements.txt` layer because the base image had no cached Python packages and network access was disabled. No retry or alternate build was attempted. No image was replaced, deleted, pruned, or used for collection. The collector service remains stopped.

## Safety gates

No RSS, article, homepage, sitemap, image, document or X request was made. No collection run, checkpoint or production DB row was created or changed. Existing Phase 8C/R2 evidence was preserved. API and dashboard remain healthy; scheduler remains disabled; OpenCTI and unrelated containers were not rebuilt or recreated.

The revision-pinned Compose/Dockerfile changes and build-info CLI remain uncommitted because the image parity gate did not pass. The next safe action is to provide a dependency-complete offline build base or separately authorize a bounded package-cache preparation; then build once, inspect parity, and run tests inside that collector image. No RSS validation should be attempted before that succeeds.

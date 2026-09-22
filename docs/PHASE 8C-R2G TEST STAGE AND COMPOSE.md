# Phase 8C-R2G — Test stage and Compose

Status: **BLOCKED**

Baseline matched the prior report: DB `282/11/282`, no open run, Collector stopped, Scheduler disabled, and worktree clean at `655dd7411591de5f24126ca14f38978522e9dcf9`.

The Dockerfile correction was committed as `685ff13e9f0b415fb15f28b67a7129d6eb024c5e`. It added an offline-only `DATABASE_URL` test environment and explicitly copied `apps/api/repair_stuck_run.py` into the test stage.

One offline `--target test --network=none --pull=false --platform linux/amd64` build was executed. Pytest reached collection, proving the prior two defects were fixed, but all five monitoring modules failed because `ops.py` reads `/app/source-registry.json` (and related files) while the Dockerfile copied the source metadata under `/app/sources`.

No retry, runtime-final build, Compose change, service start, RSS request, production write, pull, download, prune, or push was performed. Runtime image remains the previous `805991f...` image and Compose remains on `abc2cce`.

Next correction must copy the required metadata files explicitly to `/app` in the test stage (and preserve runtime-final isolation), then receive authorization for a new single test-stage build.

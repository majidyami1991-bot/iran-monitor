# Phase 8C-R2F — Test stage and Compose

Status: **BLOCKED**

HEAD before Dockerfile correction: `b2b0e12f4a3dc786b7cf01556f37f1b157a74b44`. Baseline checks passed: database `282/11/282`, no open run or advisory lock, Collector stopped, Scheduler disabled, runtime image and pinned base image present, and runtime/test wheelhouses contained 21/5 wheels.

Minimal Dockerfile correction was committed as `bebfce5bf3cabd6bc0e17a472750926efc5240aa`: runtime-final depends on a marker emitted by the test stage, forcing test-stage execution while keeping pytest out of runtime-final.

Exactly one offline test-stage build was invoked with `--target test --network=none --pull=false --platform linux/amd64`. The stage executed pytest and failed during collection. Failures were:

- `DATABASE_URL` is required by `apps/api/ops.py` and was not set in the test stage.
- `repair_stuck_run.py` is imported by `test_stuck_run_repair.py` but is not copied into the test stage.

No retry or runtime rebuild was performed. Compose was not changed, no service was started, no RSS/article/image/document/X request occurred, and no production database write occurred. The previous runtime image remains non-final for this phase.

Required next correction: provide a non-production test-stage environment value for `DATABASE_URL` and copy the existing repair module into the test stage, then obtain authorization for one new test-stage build. This phase does not pass.

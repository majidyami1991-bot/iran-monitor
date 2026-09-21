# Phase 8C-R2D — Offline Collector Build Context Repair

- Final build invocation: exactly one, offline (`--network=none --pull=false --platform linux/amd64`).
- Image: `iran-monitor-news-collector:abc2cce`.
- Image ID: `sha256:99931c07268a957474c35af5d0cb2b16b237146d66bfe3783158d265992b9dde`.
- Architecture: `linux/amd64`.
- Base image remained pinned to the previously approved Python digest; no pull was performed.
- Root cause fixed: the exact requirements lock and wheelhouse were outside the Docker build context because they lived under ignored runtime evidence. They are now versioned under `apps/collector/` and the Dockerfile installs strictly offline from that context.

## Validation

Image creation succeeded. Read-only container checks then found a pre-existing source defect in `apps/api/iran_monitor_collector/__init__.py`: its opening triple-quoted string is unterminated (`SyntaxError`). Consequently `build-info`, parity preflight, and the in-image test command could not pass. The image does not contain `pytest`, so the test command also cannot execute as invoked.

No service container was started or recreated. No RSS/source request, scheduler, production database write, OpenCTI mutation, pull, retry, prune, or deletion was performed.

**Status: BLOCKED — image build context is repaired and the single build succeeded, but final image validation requires a separate source-fix phase and a new explicitly authorized build.**

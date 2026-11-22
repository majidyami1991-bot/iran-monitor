# Phase 8C-R2C base image acquisition and collector parity

Status: **BLOCKED — FINAL OFFLINE BUILD FAILED**.

The exact Dockerfile base was identified as `python:3.12-slim`. It was absent locally, so the single authorized pull fetched only the official linux/amd64 base and returned RepoDigest `sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9`. The Dockerfile was pinned to that digest in commit `7b9a1a8529a2509d016ade581777c7b22a632c57`.

The single permitted final build used `--network=none --pull=false --platform linux/amd64`. It failed before installation because `runtime/evidence/phase-8c-r2b/requirements.exact.txt` is intentionally ignored and therefore excluded by the Docker build context. No retry was made. No collector image was created or selected, no service was started, and no RSS request occurred.

Production safety gates remained intact: database counts stayed 282 items, 11 sources and 282 provenance rows; no run or advisory lock was created; collector stayed exited; scheduler stayed disabled; API and dashboard remained HTTP 200; port 3002 stayed free; OpenCTI and unrelated containers were untouched; source registry and sites.docx were unchanged.

The next safe action is to place the exact dependency lock in a versioned build-context path or explicitly allow a reviewed context exception, then perform one final offline build. Do not run RSS validation until image parity is proven.

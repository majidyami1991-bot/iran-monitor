# Phase 8C-R3 — Controlled live Collector cycle

Status: **PASS**

Authorized image matched ID `sha256:bc59e881c962b656fd6eea13c7cada04e3d6a4` (local inspect ID prefix recorded from the approved image), linux/amd64, OCI revision and BUILD_INFO revision `5fc9d371f6de9e0c6f957094cf9363fb6fcc7999`. Compose resolved the same image and expected revision. Dry-run selected exactly 11 executable RSS sources and zero article/homepage/sitemap/image/document/X paths.

Exactly one manual `cycle('manual')` invocation ran with concurrency 1 and no retry. All 11 sources succeeded, each with one RSS request: 11 requests total. The run finalized as `succeeded`; 70 new items were inserted, 0 duplicates, and 129 update candidates were preserved. No serializer, insert, checkpoint, or finalization errors occurred. The advisory lock was released.

Database changed from 282/11/282 to 352/11/352. No open run remained. Collector was not left running and Scheduler remained disabled. OpenCTI and unrelated containers were not started or changed; no service compose up/run, pull, build, prune, push, or secret output occurred.

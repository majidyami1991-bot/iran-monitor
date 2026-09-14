# Offline Collector QA

The acceptance suite covers 25 named fixture scenarios and 38 independent test cases. `collector/validate_offline.py` is an independent validator. All checks run without network, live sources, OpenCTI, or persistent runtime artifacts; the live pilot remains NO-GO until a separately approved phase.

Phase 5B pilot record: one approved HTTPS RSS fetch was executed for TWZ (maximum one request, ten items). Output is retained only under the ignored runtime staging path; OpenCTI remains disabled.

Phase 5C resume validation re-fetched the exact TWZ feed once with a new one-shot approval. All ten item IDs overlapped the prior staging; no duplicate records were appended and the checkpoint was atomically updated after staging.

Phase 5D-R executed the ten remaining executable RSS sources sequentially, one request per source and up to ten items each. Runtime outputs remain ignored; TWZ staging was excluded and unchanged.

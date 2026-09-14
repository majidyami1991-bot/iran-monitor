# Offline Collector QA

The acceptance suite covers 25 named fixture scenarios and 38 independent test cases. `collector/validate_offline.py` is an independent validator. All checks run without network, live sources, OpenCTI, or persistent runtime artifacts; the live pilot remains NO-GO until a separately approved phase.

Phase 5B pilot record: one approved HTTPS RSS fetch was executed for TWZ (maximum one request, ten items). Output is retained only under the ignored runtime staging path; OpenCTI remains disabled.

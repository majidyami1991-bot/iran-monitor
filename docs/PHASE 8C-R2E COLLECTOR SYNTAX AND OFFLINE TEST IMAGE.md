# Phase 8C-R2E — Collector syntax and offline test image

Status: **BLOCKED — runtime image built, test stage was not executed by the single invocation.**

Baseline was read without mutation: HEAD `b9fe9be`, database counts `282/11/282`, no open run or advisory lock, runtime wheelhouse 21/21 hashes valid, API and dashboard HTTP 200, and the old `abc2cce` image was not used for collection.

The only source defect was an unterminated docstring in `apps/api/iran_monitor_collector/__init__.py`, line 1. Git history shows the file was introduced with the same defect; the minimal fix added the missing quote only. Package `py_compile` and `compileall` pass.

Commit: `805991f00f9a79c4950a4aea2cdb1627684b0806` (`fix: validate collector package in offline image build`). Runtime wheel installation remains offline from the 21-artifact wheelhouse. A single PyPI download invocation populated an ignored test wheelhouse with exact-pinned pytest 8.4.1 and direct dependencies; hashes and a versioned lock are present.

The single collector build used `--network=none --pull=false --platform linux/amd64` and produced `iran-monitor-news-collector:805991f00f9a79c4950a4aea2cdb1627684b0806`. Image smoke `build-info` and positive revision parity pass. Runtime inspection confirms `import pytest` fails with `ModuleNotFoundError` and `pip show pytest` finds no package.

The Dockerfile defines base, runtime-deps, test, and runtime-final stages. The invocation targeted the default runtime-final stage, so BuildKit did not execute the test stage; no second build or retry was performed under the phase stop rule. Consequently `BUILD_TEST_STAGE_PASSED`, image test results, and final parity/Compose alignment are not claimed. The Compose environment still selects historical `abc2cce`; no collector service was started and no RSS request or production write occurred.

Next safe action: obtain authorization for one corrective build invocation that targets a dependency path executing the test stage before producing runtime-final, then validate Compose revision alignment. No RSS collection is authorized by this report.

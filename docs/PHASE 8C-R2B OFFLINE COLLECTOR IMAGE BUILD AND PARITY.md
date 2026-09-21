# Phase 8C-R2B offline collector image build and parity

Status: **BLOCKED — BUILD NOT COMPLETED**.

The stale image cause was corrected in the working tree: `news-collector` now has a revision-pinned image reference, expected revision guard, and non-secret build metadata CLI. Exact dependency inventory from the tested Python 3.12 image produced 21 packages. One authorized PyPI download invocation retrieved 21 Linux amd64 wheels; SHA-256 values are recorded in the ignored wheelhouse lock manifest.

The Dockerfile was changed to install exclusively with `pip --no-index --find-links=/wheelhouse`. The single permitted offline build invocation used `--network=none`, but the current build context still resolved the uncached `python:3.12-slim` base and could not complete its package layer. No retry was made. No collector image was created, no service was started, and no RSS request or production DB write occurred.

The R2A changes and reports were preserved and committed only after source checks; the final image commit is pending because parity cannot be claimed without a completed image. Existing API/Web/DB containers remain untouched, collector is exited, scheduler is disabled, and prior R2/R2A evidence is preserved.

Next safe action: provide an offline-available base image (or an approved local base containing the exact pinned runtime), then perform one final `--network=none` collector build and parity inspection before requesting any live RSS cycle.

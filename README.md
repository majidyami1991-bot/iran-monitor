# Iran Monitor OSINT

Self-hosted OSINT news monitoring foundation using OpenCTI Community Edition.
Phase 1 prepares configuration only: OpenCTI has NOT been started, and no images have been pulled.
The immutable `sites.docx` in this directory is the authoritative original source list.

## Architecture and scope
Sources -> authorized collection connectors -> OpenCTI intelligence backend -> analysis and entity relationships -> future Persian RTL homepage inspired by Iran Monitor's functional structure.
The homepage, maps, charts, alerts, Persian translation, summaries and AI analysis are future work.
X access requires separate authorization and a connector; installing OpenCTI does not provide X access.

## Prerequisites and safe check
Windows PowerShell 5.1+, Git, Docker Desktop on running WSL2, Compose >= 2.24.4, at least 8 Docker CPUs, 16 GiB Docker RAM, 64 GiB free on the known Docker backing drive, port 8080 free, vm.max_map_count >= 1048575.
The disk floor is an initial check, not a retention-capacity guarantee. Docker data currently resides on C: NVMe; project source remains on E:.

```powershell
& 'E:\Iran monitor\scripts\preflight.ps1'
```
The preflight only reads state and renders Compose in memory. It never repairs settings or launches a stopped WSL distribution.
Never display rendered Compose with real credentials. Never commit `.env`, log secrets, or alter unrelated containers.
See [deployment instructions](deployment/opencti/README.md), [security](docs/SECURITY.md), and [baseline](docs/PHASE%200%20BASELINE.md).

## Next phase
After explicit Phase 2 approval: rerun preflight, review pinned images and only then authorize image pulling and startup. No startup is authorized by this README.

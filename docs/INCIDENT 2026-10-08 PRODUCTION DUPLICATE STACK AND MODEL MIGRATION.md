# Incident 2026-10-08 — duplicate stack on the Production network; Ollama model migration

## 1. Duplicate `iran-monitor-news` stack on the Production network

| | |
|---|---|
| Detected | 2026-10-08 ~17:00 UTC, while bringing up the local-AI stack |
| Cause | At 16:53:14 UTC a compose run of `E:\Iran monitor\deployment\news-monitor\compose.yml` used the old project name `iran-monitor-news` |
| Containers | `iran-monitor-news-news-db-1`, `-news-api-1`, `-news-web-1` (no restarts; created in the same second) |
| Effect | The DB and API joined `defence-monitor-news_default` with the aliases `news-db` and `news-api`. Docker DNS returned two addresses for each name. The DB ran on the stale volume `iran-monitor-news_news-db-data` (state of 2026-10-04). `/api/v1/health` on 3001 alternated between answers (`scheduler_enabled` true/false). |
| Action | `docker stop` on exactly those three containers, after their labels (project, working_dir, config_files, creation time) proved their identity. Nothing was removed: no container, volume or network. |
| Verification | `news-db` and `news-api` now each resolve to one address. 10 of 10 consecutive health checks on 3001 were identical (2,335 items, `scheduler_enabled: true`). The scheduled collector run at 17:01:55 UTC succeeded (12 of 12 sources, 88 items inserted) into the Production DB. Collector errors appeared only at 16:46:52–53, during database start-up after the Docker restart. No manual RSS cycle was started. 46 containers, 26 volumes and all networks are unchanged apart from the three stopped containers. OpenCTI is healthy. |
| Not done | The stale database was not started or inspected (rule: do not touch it). Whether any write reached it between 16:53 and 17:08 is unknown. Its role is `iran_monitor`, so connections using the `defence_monitor` credentials would have failed authentication there. |
| Prevention | The project name `iran-monitor-news` must not be used again. Production is started with `-p defence-monitor-news` (README of the main checkout). |

## 2. Ollama 0.40.1 rewrote model manifests (model ID drift)

| | |
|---|---|
| Observation | After the Ollama upgrade (0.35.1 → 0.40.1), `gemma4:e2b` reported the digests `2cf98652fdc6` and `da406dc37ca0`. The approved ID `7fbdbf8f5e45` was gone. |
| Restore | The offline archive `TranslatorOllama/gemma4-e2b-ollama.tar` (SHA-256 `d6ee2d62b561cf2f6dc95fd809d916fdba165f43db37bb319fd52964387639e9`) is a plain GNU tar in Ollama store layout: 11 entries, no links, no unsafe paths. Its manifest SHA-256 is `7fbdbf8f5e45a75b…`, and all 4 blobs verified against their names. The same 4 blobs were already in the active store (verified by hash). The original manifest was placed, with exclusive create and no overwrite, as `gemma4:e2b-approved-7fbdbf8f5e45`. Ollama listed it with ID `7fbdbf8f5e45`. |
| Then | When the model first loaded (10:16:10 local), Ollama rewrote that manifest into a **manifest list** with two runner manifests: |
| | `ggml` → `da406dc37ca0`: **byte-identical layers of the approved model** (same weights blob `4e30e266…`) |
| | `llamacpp` → `d1e84c607e13`: Ollama's conversion of the same weights (model 6.18 GB + projector 0.98 GB, new blobs) |
| Meaning | The "new" `gemma4:e2b` builds of the morning were this same migration, not new weights: its `ggml` entry is also `da406dc37ca0`. Under Ollama 0.40 the single-manifest ID `7fbdbf8f5e45` cannot persist, because Ollama rewrites it on load. |
| Status | `BLOCKED_MODEL_DIGEST_MISMATCH`. The local-AI stack pins `OLLAMA_MODEL_DIGEST=7fbdbf8f5e45` and fails closed: every translation and assistant call ends with `model_digest_mismatch`. One fixture inference (synthetic text, not stored) ran during the load that triggered the rewrite. No real content was translated with the migrated model. |
| Decision needed | (a) Approve identity by the weights layers (`ggml` sub-manifest `da406dc37ca0` = approved layers) and confirm which runner Ollama uses for inference. (b) Pin Ollama 0.35.1 (downgrade) so manifests are not rewritten. (c) Approve the migrated build as a new reviewed model. Until then nothing runs. |

## 3. Runner gate under option (a) — failed

Option (a) was chosen on 2026-10-08: accept the model's identity by its
weights only if the runner Ollama actually uses is `ggml` and every blob it
loads is byte-identical to the approved archive.

| Evidence | Value |
|---|---|
| Ollama | 0.40.1. The current `ollama serve` writes no log (`server.log` is 0 bytes), so the runner was proven from the process table instead. |
| Probe | One synthetic inference on `gemma4:e2b-approved-7fbdbf8f5e45` (text `[SYNTHETIC] The ship arrived.`, seed 42, num_ctx 4096, num_predict 64). Processes were captured before, during and after the call (`runtime/local-ai-evidence/runner-probe.txt`, not committed). |
| Runner process | `lib\ollama\llama-server.exe` (child of `ollama serve`), i.e. the **llamacpp** runner, with `-c 4096 -np 1`, `--offline`, CPU (`size_vram=0`) |
| Files it loads | `--model blobs\sha256-aed3339236b464c87de08a4ce3aa148f5a43be4717e92629b35e2642199896ff` (6,178,838,400 B) and `--mmproj blobs\sha256-0012c271672236852cb98401c0f9710d71a57c14b552dbe2b31cf898e7bfbf8e` (984,735,808 B). The full SHA-256 of each file equals its name. |
| `/api/ps` | loaded digest `d1e84c607e13…`, which is the `llamacpp` entry of the manifest list |
| Approved archive blobs | `c6bc3775…`, `4e30e2665218…` (weights, 7,162,394,016 B), `7339fa41…`, `56380ca2…`. **None of them is loaded by the runner.** |
| Verdict | `MODEL_WEIGHT_IDENTITY_ACCEPTED=FALSE`, `BLOCKED_RUNNER_OR_WEIGHT_MISMATCH`. The executed weights are Ollama's conversion, not the approved bytes. No fixture suite, real translation, batch or assistant query was run. |

Possible next steps (owner decision; each changes the global Ollama
installation, not this repository):

1. Make Ollama 0.40.1 use the `ggml` entry, if a supported setting exists.
   This must be verified, not assumed, and the gate re-run afterwards.
2. Reinstall Ollama 0.35.1 (single-manifest store, no conversion), then
   restore `gemma4:e2b-approved-7fbdbf8f5e45` with ID `7fbdbf8f5e45` and
   re-run the gate.
3. Treat the converted llamacpp artifacts (`aed33392…` + `0012c271…`) as a
   new model and run a full fixture and quality review before approving it.

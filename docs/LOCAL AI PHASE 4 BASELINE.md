# Local AI Phase 4 — Baseline (2026-10-08/09)

Captured before any phase-4 change. Read-only, apart from the commands
needed to read state.

## Git

| Item | Value |
|---|---|
| Worktree | `E:\Iran monitor-local-ai` |
| Branch | `feature/local-gemma-translation-assistant` |
| HEAD | `4de42f1`, clean worktree |
| Phase-3 commits reviewed | `c57dbeb` (extractive role, role-scoped settings, contracts), `9cbdd88` (model status panel, disabled assistant state), `2fe7926` (extractive gate, 12b fixtures, UI QA), `4de42f1` (phase-3 evaluation doc) |

## Services

| Service | State |
|---|---|
| Production 3001 (`defence-monitor-news`: web, api, collector, db) | 200, healthy |
| OpenCTI 8080 (`iran-monitor-opencti`: 13 containers) | 200, healthy |
| Local AI 3003 (`iran-monitor-local-ai`: ai-web, ai-api, ai-db) | 200, healthy |
| Containers outside the local-AI stack | 18, recorded by ID in `runtime/local-ai-evidence/phase4/prod-before.txt` |

## Ollama 0.40.1 (CPU only)

15 tag entries; no model loaded (`/api/ps` empty).

| Tag | Digest(s) |
|---|---|
| `translategemma:12b` | `3189e9a01b8a`, `d5af47801135` |
| `translategemma:4b` | `6d2c3b38bc4a`, `f85cc71cc574` |
| `qwen3:8b` | `500a1f067a9f` |
| `gemma4:e2b-ollama0401-llamacpp-d1e84c607e13` | — |
| `gemma4:e2b-approved-7fbdbf8f5e45` | — |
| `gemma4:e2b` | — |
| `llamacpp:*` | conversion entries |

## Model contracts (`apps/api/model_approvals.json`)

No role has an active approval.

- Translation: `gemma4:e2b`, `translategemma:4b` and `translategemma:12b` are rejected or superseded.
- Assistant: the free-form `qwen3:8b` role is rejected. Extractive v1 is superseded; v1.1 and v1.2 are revoked.

## Hardware

i7-13700K (24 logical CPUs), 63.7 GB RAM (40.9 GB free), C: 599 GB free,
E: 899 GB free. No GPU in use (`size_vram = 0`).

## Isolated DB (`iran-monitor-local-ai_ai-db-data`)

| Table / measure | Count |
|---|---|
| news_items | 2,146 (latest 2026-10-07 13:29 UTC) |
| news_item_translations | 89 (3 available/pending_review, 5 needs_review, 80 pending, 1 error) |
| translation history | 16 |
| news_events | 63, all multi-member; 21 multi-source |
| news_event_members | 138 |
| assistant sessions / messages | 11 / 21 |
| x_posts | 0 |

Sources by volume: jfeed 1,120, defence-industry.eu 273, defence-blog 156,
twz 116, breakingdefense 105, rusi 84, usni 79, edrmagazine 77,
airandspaceforces 72, and smaller ones.

## Tests at baseline

- Local-AI offline tests: 75 pass (assistant extractive, TranslateGemma, model identity, local AI).
- Full offline suite in the image test stage: passes.
- Browser QA `tests/ui/local-ai-qa.cjs`: 29/29.

## Findings that shaped phase 4

1. **Retrieval removed multi-source evidence.** `retrieval.search` keeps one
   record per event (`seen_event`). A "common event" or "how do sources
   differ" question could therefore never see two sources of one event, so
   the model filled the slots with unrelated records. This is the root cause
   of the v1.2 relevance failures.
2. **Event clusters are lexical.** Method `entity_idf_complete_linkage_v2`
   clusters on shared title words and time. At least one real cluster is two
   different events: `e2-ff69db5f703ac2a53986`, "Turkish officials inspect
   RAF base for Typhoon support" + "NATO allies test … Typhoon … in Cobra
   Warrior". A cluster ID alone cannot prove "same event".
3. **Retrieval tokens.** The phase-3 real questions were generic. Persian
   tokens match only stored machine translations, and those are no longer
   evidence. Anchoring a Persian question to English originals therefore
   needs an explicit Persian→English resolution step.

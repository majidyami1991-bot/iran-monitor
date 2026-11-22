# Local Translation and Assistant Model Evaluation (2026-10-08)

**Outcome:** neither model was approved, so both roles stay fail-closed.

| Role | Model | Status |
|---|---|---|
| Translation | `translategemma:4b` | `BLOCKED_TRANSLATION_MODEL_QUALITY` |
| Assistant | `qwen3:8b` | `BLOCKED_ASSISTANT_MODEL_QUALITY` |

No real content was translated or answered. The earlier `gemma4:e2b`
artifact keeps its `rejected_quality_gate` status.

## Pulls (owner-authorised, exactly once each)

| | translategemma:4b | qwen3:8b |
|---|---|---|
| Pull | 10:42–10:46 local, success, no retry | 10:46–10:54, success, no retry |
| Registry manifest | `c49d986b0764f5881c476eb21435bb62b7abc62347aab3d4a6071e811be510a1` | `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41` |
| Size | 3,298,875,707 B | 5,225,388,164 B |
| Model | gemma3 family, 4.3B, Q4_K_M; caps completion, vision | qwen3, 8.2B, Q4_K_M; caps completion, tools, thinking |
| License | Gemma Terms of Use | Apache License 2.0 |
| Runner (observed) | `llamacpp` (`llama-server.exe`), CPU, `size_vram=0` | `llamacpp` (`llama-server.exe`), CPU, `size_vram=0` |
| Conversion on load | **Yes.** At 10:55:31 Ollama 0.40.1 converted it into a manifest list (llamacpp `6d2c3b38…` + ggml `f85cc71c…`). The runner then loads model `ed31771a974224d7…` and mmproj `aa07fc4e7be6a511…`. | No. The runner loads the pulled blob `a3de86cd1c132c82…`. |

All earlier models, tags, blobs and the archive are untouched: 12 blobs
were added and 0 removed.

## Per-role contracts

The contracts are in `apps/api/model_approvals.json` and are append-only.
Each one records the exact tag, manifest digest(s), the full SHA-256 of the
model and mmproj blobs, the runner, the Ollama version, the runtime
parameters, prompt, glossary and validator versions, and the approval events.

- **`TRANSLATION_MODEL_CONTRACT`**
  - `translategemma-4b-c49d986b0764`: the pull-time record, then `superseded`.
  - `translategemma-4b-ollama0401-llamacpp-6d2c3b38bc4a`: the executed
    converted artifact, `proposed`, then `rejected_quality_gate`.
- **`ASSISTANT_MODEL_CONTRACT`**: `qwen3-8b-500a1f067a9f`, `proposed`, then
  `rejected_quality_gate`.

`model_identity.active_approval(role=...)` serves each role independently.
An approved translator never serves the assistant, and the reverse is also
true. The fingerprint, and with it the cache key, binds the role, glossary
and validator versions as well.

Host attestation (`scripts/attest_local_model.py`) passed for both models,
including stability after unload and reload.

## Translation gate — translategemma:4b

### Pipeline under test (`apps/api/translation_tg.py`)

- The official prompt (`translategemma-official-en-fa-v1`), with exactly two
  blank lines before the text. Output is plain text; no JSON is forced.
- Title and summary are translated separately. An empty summary is never
  sent. Persian text is `not_required` with no inference.
- URLs, mentions, hashtags, codes, coordinates, numbers, dates, times,
  percentages and acronyms are replaced by salted, collision-safe tokens
  (`ZQ<3 random capitals><index>`). A token that is missing, duplicated,
  changed or left behind rejects the output.
- Glossary `defence-glossary-fa-v1.0.0`: validation only, whole-word
  matching. It covers brigade, convoy, launch (missile context),
  commission (ship context), frigate, missile, deployment, navy, drone,
  air defence, close air support, live-fire, and selected names.
- Validator `translation-validator-v2.0.0`: the content checks, plus
  foreign scripts, mixed-script words, lowercase English residue,
  commentary and the glossary.

### Result: 31 fixtures (32 inference fields) + 16 invalid outputs

| Check | Result |
|---|---|
| Invalid outputs (9 earlier + 7 placeholder/script/glossary) | 16/16 rejected |
| Empty-summary fabrication | 0 |
| English commentary / `<channel|>` debris | 0 / 0 |
| URL, mention, acronym, coordinate and code preservation | preserved where the token survived |
| Fields acceptable (validator + human review) | **about 18/32. FAIL.** |

Real model errors:

- Terminology:
  - convoy became "military group" or "squad";
  - brigade became "unit" or "group";
  - commission became "will order";
  - frigate was left untranslated, in mixed script.
- Meaning:
  - "strike on the depot" became "protest scene";
  - "96 Apache helicopters" became "Apache model 96".
- Names: "Lockheed Martin" was garbled.
- Numbers: in the summary with "$10 billion", a number was turned into a
  company name and figures were misplaced. Some percentages, hashtags and a
  date number were dropped, and one placeholder residue was left.
- Regression cases still failing: simple title, places, military term,
  hashtags.

## Assistant gate — qwen3:8b

Settings: non-thinking mode (`think:false`; no thinking field returned),
num_ctx 4096, num_predict ≤ 512, temperature 0.1, JSON schema output,
UNTRUSTED_EVIDENCE blocks, citation validator
`assistant-citation-validator-v1.0.0`.

| Fixtures | Result |
|---|---|
| Deterministic and technical (9): invalid citation, uncited answer, invented number, invented URL, delimiter neutralisation, history ≤ 4 turns, timeout, cancellation, identity after cancel | 9/9 pass |
| Model fixtures (17), automatic checks | 14/17 |
| Model fixtures (17) after human review | **about 7/17 fully acceptable. FAIL.** |

What worked: valid citations to supplied records only; the prompt injection
was ignored; the malicious URL inside a news item was not repeated; no
hallucinated BBC report; insufficient and out-of-scope questions declined;
the 12-vs-20 narrative difference was reported correctly.

What failed:

- Hallucinated facts: "Baltic" became the Caspian, Monday became Sunday,
  "four events" were claimed from two, and "from the south" was added.
- Cyrillic and Latin fragments inside Persian words.
- "drone" rendered as "inside"; "fuel depot" as "gasoline factory".
- An English answer to an English question.

Validator improvements made after this run:
- answers with foreign or mixed script are rejected;
- numbers echoed from the question are no longer treated as invented
  (this was the false positive in the time-window fixture).

## Consequence

- Real smoke tests, the 50-item batch and the real assistant questions were
  **not run**.
- The 3003 UI keeps working. Translation and assistant both report
  `no_approved_model_artifact`, which was verified after redeploy.

## Evidence (runtime, not committed)

All files are under `runtime/local-ai-evidence/`:

- the before/after model and blob snapshots;
- `runner-observe-new.json` and the attestations in
  `runtime/local-ai-attestation/`;
- `translation-gate-tg.json` and `-review.txt`;
- `assistant-gate.json` and `-review.txt`.

## What would be needed next (owner decision)

- **Translation:** a larger reviewed model (for example
  `translategemma:12b`, which needs its own authorisation), or a different
  approach. Any change is a new contract and a new gate.
- **Assistant:** a model with stronger Persian generation, or a narrower
  answer format (for example, extractive answers built from cited excerpts
  only) designed to make hallucination structurally harder. That again
  requires a new gate.

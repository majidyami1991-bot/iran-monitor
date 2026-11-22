# TranslateGemma 27B — evaluation readiness (phase 8, 2026-10-09)

**Translation status: `BLOCKED_MODEL_QUALITY` (unchanged).**

This phase prepares the 27B evaluation only. Nothing was downloaded,
activated or published, and no database, Production, OpenCTI or Assistant
v1.3.1 state was changed. The model is **not downloaded**; that waits for
your explicit authorisation.

## 1. Earlier results preserved

- **Inventory:** 30 earlier evidence and document files were hashed before
  any work in this phase (`runtime/local-ai-evidence/phase8/evidence-manifest-before.sha256`).
- **Re-check at the end:** 29 are byte-identical. The only change is
  `apps/api/translation_qc.py`, the intended v1.0.1 edit.
- **v1.0.0 is recoverable:** `git show 9eec064:apps/api/translation_qc.py`
  hashes to the frozen `bfaa3c55…`.
- **Lost raw file:** `phase5/v131-metrics.csv` was **not reconstructed**.
  It still contains the phase-7 samples that overwrote it, and the loss
  stays documented in `phase5/v131-metrics.OVERWRITTEN.txt` and in the QC
  evaluation report §9.
- **Assets kept as they are:**
  - the 35 dev fixtures;
  - the 40 phase-7 held-out items (`07b4ada`);
  - all raw outputs (phases 3, 6 and 7);
  - QC v1.0.0;
  - the resource logs.

## 2. Human review pack for the phase-7 translations

**`docs/TRANSLATION PHASE 7 HUMAN REVIEW PACK.md`.** For each of the 40
TranslateGemma 12B translations it shows:
- the English source;
- the Persian output;
- the earlier AI label with its note;
- the errors flagged by QC v1.0.0 and by validator v2.1.0;
- the suspect part of the output (one pointer, for H01, is marked as such);
- an **empty** human decision table (severity, agreement with the AI
  label, corrected key fact, comment, reviewer and date).

Nothing is pre-approved. Generator: `scripts/translation_review_pack.py`.

## 3. The 27B model (checked without downloading)

| Item | Value | Source |
|---|---|---|
| Exists in the official registry | **Yes.** `registry.ollama.ai/library/translategemma:27b` | registry manifest (HTTP 200) |
| Manifest digest (identity of what would be pulled) | `21b597a243ec4fd2f05bc0ce8ef9ef174a89b09255c330d670852dfaaaa74f72` | sha256 of the manifest |
| Model layer | `sha256:d87ec9a33af49e86461d8309e28e6bdb663f852c09dfca5ff581bd796cdaf583`, **17,358,640,928 bytes (17.36 GB)** | manifest |
| Total download | 17,358,649,778 bytes | manifest (sum of layers) |
| Format | GGUF, family gemma3, **27.4B**, **Q4_K_M** | config blob `80f9232a…` (hash verified) |
| Runtime parameters | stop `<end_of_turn>`, top_k 64, top_p 0.95; template identical to 12B's | params and template blobs |
| License | Gemma Terms of Use. The license blob `3e2c2400…` is **byte-identical** to the 12B one already accepted for evaluation. | manifest |
| Upstream origin | `google/translategemma-27b-it` on Hugging Face (Google, gated, license gemma, commit `7d10f0b72f89…`, created 2026-01-12, the same day as 12B) | HF API metadata |
| Consistency check | The 12B manifest still hashes to the digest pinned in phase 3 (`c2f9a9ca…`): the registry has not changed under the existing tag | registry |

### 3.1 Can it run safely on this machine?

| Resource | Available now | Estimated need for 27B | Margin |
|---|---|---|---|
| RAM, CPU only | 41.7 GB free of 63.7 GB | **≈ 19–21 GB** runner RSS at num_ctx 4096 (*unverified estimate*) | ≈ 20 GB left |
| Disk (C:, Ollama store, already 40 GB) | 592 GB free | 17.4 GB download + **≈ 17.4 GB** for the conversion Ollama 0.40.1 makes on first load, as it did for 12B (*estimate*) | ample |
| CPU | i7-13700K, 24 logical cores; services idle (< 1 % each) | 8 threads; 12B ran at 69 % average / 97 % peak total CPU | contention while running |
| Runtime compatibility | Ollama 0.40.1 already runs gemma3 12B through the same llama.cpp path | same family, quantization, template and parameters (*probable; confirmed only by an actual load and attestation*) | — |

How the RAM figure is estimated:
- **Weights:** 12B used 8.9 GB RSS for an 8.1 GB blob, a ratio of 1.10.
  Applying that to 17.4 GB gives about 19.1 GB.
- **KV cache at 4096 context:** at most about 2 GB (62 layers, 16 KV
  heads, head dimension 128, fp16, before Gemma 3's sliding-window
  saving).

**Effect on running services:**
- Production (3001) and OpenCTI run in Docker's VM, capped at 31.2 GB;
  Elasticsearch, the largest, uses 5.2 GB. Ollama runs natively on
  Windows. RAM would stay at about 20 GB free.
- The main risk is **CPU contention** during a run. At an estimated
  14–15 s per field (about 2.3× 12B's 6.1 s), the planned 123 fields take
  about 30 minutes.
- Mitigations:
  - keep `num_thread` at 8;
  - run at a quiet time;
  - poll the 3001 health endpoint during the run and stop it if Production
    degrades;
  - unload the model afterwards (`keep_alive 0`).

**Conclusion:** running 27B is **technically feasible and safe** with these
margins. The RAM, conversion and speed figures are estimates until a real
load.

### 3.2 Is the download technically justified?

**Yes, as one bounded experiment, with its success not assumed:**
- **For:** the blocker is the model's base error rate (12B: 35 % critical
  on held-out). 27B is the same family at about 2.3× the parameters,
  using the same pipeline, so it's the cleanest test of whether model size
  fixes the error types seen.
- **Against:** from 4B to 12B, the same error types (echelons, placeholder
  dates, invented titles) persisted. 27B may well still fail.
- **Cost:**
  - one 17.4 GB download plus about 17 GB of conversion disk;
  - about 30 minutes of CPU;
  - human review of about 123 outputs.

## 4. Test data ready

| Set | Items | Status | Commit / sha256 |
|---|---|---|---|
| Dev (gate fixtures) | 35 | unchanged; 12B, MADLAD and NLLB outputs stored | `scripts/local_ai_quality_gate.py` + `translation_quality_gate_tg.py` |
| Phase-7 held-out | 40 | unchanged; 12B and NLLB outputs stored; AI labels; human pack ready | `07b4ada` / `5fcfb577…` |
| **Phase-8 independent set (new)** | **48** | fixed **before** any 27B output and before the download | `07bfcea` / `cca2599a…` |

The phase-8 set (`scripts/translation_eval_set_p8.py`, version
`translation-eval-p8-v1.0.0`) has 6 items in each of 8 categories:

| Category | Covers |
|---|---|
| A | rise **to** a value versus rise **by** a value |
| B | the number stays with its own unit or noun (each versus total, swapped distances) |
| C | roles (former, deputy, acting, opposition, rank) |
| D | certainty (reportedly, confirmed, may have, alleged, unlikely, neither/nor) |
| E | military terms (company, battery, destroyer, sortie, decommission, corps) |
| F | time and order (after, pluperfect, deadline, since, postponed until) |
| G | negation (did not, no, failed to, without, neither, not) |
| H | traps for unsupported additions (bare names, bare events) |

- Each item has **key facts written in advance**. A translation that
  violates one is critical, so labelling follows a fixed rubric rather than
  judgement after the fact.
- No item repeats a dev or phase-7 sentence (checked).

**Runner:** `scripts/translation_eval_run.py`, prepared but **not
executed**. It uses the same pipeline as the gates (placeholders,
validator v2.1.0, glossary v1.1.0), records QC v1.0.1 flags as triage
only, and has an empty `human_label` field per item.

## 5. QC v1.0.1 (diagnostic only)

`apps/api/translation_qc.py` v1.0.1 fixes the four defects the phase-7 run
exposed:
- plural "agencies" in the `سازمان` rule;
- plural roles such as "ministers";
- "Kyiv" implying Ukraine (via «کی‌یف»);
- "naval" implying Navy (via «دریایی»).

The last two are QC-only spelling aliases that can satisfy a "missing"
check but never add an entity. Three regression tests were added (15 QC
tests pass). v1.0.0 stays frozen at `9eec064`.

**Diagnostic re-run on earlier sets.** This is **not** an independent
result: the fixes were made after seeing these errors.

| Set | v1.0.0 (frozen, independent) | v1.0.1 (diagnostic) |
|---|---|---|
| Dev, 12B | 6/6 critical; 0/20 false alarms | 6/6; 0/20 (unchanged) |
| Phase-7, 12B | 13/14 critical (missed H01); 3/19 false alarms | 13/14 (H01 still missed); **0/19** false alarms |

The changed flags are H14, H32 and H33 (no longer false alarms), plus H02
losing its false `role_added`; H02 is still caught by its other flags.

v1.0.1's independent performance will only be known on the phase-8 set.
H01 ("to" versus "by") remains a known blind spot. Phase-8 category A
measures it.

## 6. Decision report

| # | Question | Answer |
|---|---|---|
| 1 | Can 27B run here? | **Yes, technically.** 17.4 GB Q4_K_M, about 19–21 GB RAM estimated against 41.7 GB free; disk ample; same runtime path as 12B. Confirmed only by a real load and attestation. |
| 2 | Is the download justified? | **Yes, as one bounded experiment.** It is the cleanest test of whether size fixes the base error rate. Success is not assumed; 4B to 12B did not fix the same error types. |
| 3 | What test data is ready? | Dev 35 (stored outputs), phase-7 40 (stored outputs, AI labels, human pack), **phase-8 48 new hard items with key-fact rubric, fixed before the model exists**. The runner script is ready. |
| 4 | Acceptance criteria (fixed now, before any 27B output)? | See §7. |
| 5 | Has human review of the reference data been done? | **No.** Every label so far (dev 35, phase-7 80) was written by Claude (AI). The human packs are ready and empty. |
| 6 | Is another approval needed to start? | **Yes:** (a) your explicit authorisation to download `translategemma:27b` (manifest `21b597a2…`, 17.36 GB, one pull, no automatic retry); (b) agreement to append a `proposed` contract entry for it (evaluation only, never served); (c) a named human reviewer for the phase-7 pack and the 27B outputs. |

## 7. Acceptance criteria for 27B (fixed before any output exists)

**Technical** (all required):
1. Identity: manifest `21b597a2…` and layer `d87ec9a3…` as pinned; host
   attestation of the converted runner artifact; CPU only; stable after
   unload and reload.
2. Resources: runner RSS ≤ 24 GB; free RAM ≥ 12 GB throughout; 3001 health
   stays 200 during the run; model unloaded at the end.
3. The validator rejects 16/16 invalid outputs.

**Quality** (all required for approval; criteria not relaxed from earlier
phases):

4. **Zero critical errors**, confirmed by a **human**, across dev 35,
   phase-7 40 and phase-8 48 (123 fields): no wrong number, date, role,
   echelon or ship type, certainty or negation; no invented information;
   no placeholder text.
5. Every phase-8 key fact preserved.
6. Every output reviewed by a human, not by an AI.

**Reported but not acceptance criteria:** latency, QC v1.0.1 recall and
false alarms on phase 8 (its first independent measurement), and critical
rate per category.

**Stop rule:** if 27B's human-confirmed critical rate on phase 8 exceeds
10 %, stop pursuing the TranslateGemma family for unattended translation.
Any later translation work would then be a human-translation workflow with
machine suggestions.

## 8. Not done in this phase

- No download.
- No model run.
- No contract entry for 27B.
- No human review.
- No translation published or stored.

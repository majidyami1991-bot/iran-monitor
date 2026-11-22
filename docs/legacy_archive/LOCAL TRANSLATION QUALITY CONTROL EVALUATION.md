# Translation quality control (QC) evaluation (2026-10-09)

**Translation status: `BLOCKED_MODEL_QUALITY` (unchanged).**

The question was whether deterministic controls, plus an independent NLLB
translation, can automatically find the critical errors in
TranslateGemma 12B output. Nothing was activated, corrected or published.
No model was downloaded, and no database was written.

## 1. Answer in short

| Question | Answer |
|---|---|
| Do the controls help human review? | **Yes, as triage.** On the held-out set they flagged 13 of 14 critical 12B errors. 72 % of what they flag is critical, against a 35 % base rate. |
| Can they replace human review or allow auto-publishing? | **No.** One critical error was missed, and errors that keep the same numbers and names but change the meaning are structurally invisible to these controls. |
| Does the NLLB cross-check add value? | **No.** It caught no critical error the deterministic controls missed, on either set, and it added false alarms. Not recommended. |
| Is a larger model needed? | **Yes.** 35 % of 12B's held-out outputs had a critical error. Even with perfect detection, more than half the output would go to a human and a third would need rewriting. QC lowers the risk; it does not fix the quality. |

## 2. Method (designed against overfitting)

| Step | Commit | Evidence |
|---|---|---|
| 1. Held-out test sentences (40, new, varied topics) written **before** any control existed | `07b4ada` | `scripts/translation_qc_heldout.py`, sha256 `5fcfb577…` |
| 2. Controls designed **only** on the 35 earlier dev fixtures: stored outputs of 12B, MADLAD and NLLB (no model re-run), with the existing severity labels. Two iterations. | — | `qc-dev-iter1.json`, `qc-dev-iter2.json` |
| 3. Controls **frozen** | `9eec064` | `apps/api/translation_qc.py` v1.0.0, sha256 `bfaa3c55230e14e3…` |
| 4. Held-out set translated by **existing** models: 12B (attested artifact, identity checked before and after each call; contract stays `rejected_quality_gate`) and NLLB-600M (int8 `398726640cc2…`) | — | `heldout-{tg12b,nllb}.json` |
| 5. Reference labels for the 80 held-out outputs written from source and output only, **before** the controls were run | `77b9a31` | `scripts/translation_qc_heldout_labels.py` |
| 6. Frozen controls run once on the held-out set; no rule changed afterwards | — | `qc-heldout.json` |

Evidence lives in `runtime/local-ai-evidence/phase7/` (gitignored).

**Pre-registered primary measure:** controls without the reference
translation (`tg12b_no_ref`). Positive = a field labelled **critical**.

**Severity rules** are the same as in the model comparison:
- critical: wrong fact, number, entity, role or meaning; invented
  information; key fact dropped;
- major: wrong or vague military term, foreign words, ungrammatical;
- minor: spelling variants, harmless additions.

**Limitations of this method:**
- The labels and the controls were made by the same reviewer, Claude (an
  AI), so the labels are not independent and are **not a human review**.
- The sets are small: 14 critical held-out items for 12B, so the
  confidence intervals are wide.
- The held-out sentences are synthetic and were written by the same author.

## 3. The controls (`translation_qc` v1.0.0)

Each control compares the English source with the Persian output and only
**flags**; it never corrects.

| Control | Checks |
|---|---|
| numbers | Every source number (digits, decimals, %, ordinals, number words) is in the output. No number is added. billion / million / % units are kept. A number is not relabelled as «مدل N». |
| dates | Month and weekday names are rendered in Persian; no English month is left. |
| placeholder | Bracketed text in the output that is not in the source («[تاریخ مشخص]») |
| entities | People, organisations, countries and places from the versioned fa↔en lexicon of Assistant v1.3.1 (read only, unchanged) are neither added nor dropped. QC-only spelling variants. |
| roles | minister, president, prime minister, chancellor, CEO, spokesman, ambassador, general and commander are neither added nor dropped. |
| military | Brigade, battalion, division, regiment and corps echelons; ship types; live-fire; «تمرین/رزمایش» not in the source. |
| suspicious words | «سازمان», «ایستگاه», «مدل», «ویکی‌پدیا», «سپاه», «شبیه‌سازی», «اعتصاب» … without a source equivalent |
| coverage | Output/source length ratio outside 0.55–1.75, for sources of at least 40 characters |
| reference (optional) | Content-word overlap with the NLLB translation below 0.20 |

Development log:
- **Iteration 1:** recall 6/6; 7 of 20 correct or minor translations flagged.
- **Iteration 2:** fixed five rule bugs found on dev data — "MQ-9B" read as
  9 billion, «سه شنبه» read as 3, Kharkiv spellings, Tehran→Iran, short
  headlines. Recall 6/6; 0 of 20 correct or minor translations flagged.
  Frozen at this point.

## 4. Results

### 4.1 Detection of critical errors

| Set | Variant | Critical caught (recall, 95 % CI) | Missed | Flagged | Precision | **False alarms on correct/minor** | Flagged, non-critical |
|---|---|---|---|---|---|---|---|
| dev (35) | 12B, no reference | 6/6 = 100 % (61–100 %) | 0 | 11/35 | 55 % | 0/20 | 5/29 (all major) |
| dev | 12B + NLLB reference | 6/6 | 0 | 13/35 | 46 % | 2/20 | 7/29 |
| **held-out (40)** | **12B, no reference (primary)** | **13/14 = 93 % (69–99 %)** | **1 (H01)** | **18/40** | **72 %** | **3/19 = 16 % (6–38 %)** | 5/26 |
| held-out | 12B + NLLB reference | 13/14 = 93 % | 1 (H01) | 22/40 | 59 % | 4/19 = 21 % | 9/26 |
| held-out | NLLB output, 12B as reference | 8/12 = 67 % (39–86 %) | 4 | 17/40 | 47 % | 2/17 | 9/28 |

**Overfitting is visible.** False alarms on correct translations rose from
0 % on dev to 16 % on held-out, and recall fell from 100 % to 93 %. The
held-out figures are the ones to rely on.

**Comparison with the existing validator** (v2.1.0, run inside the
translation pipeline) on the same 12B held-out outputs:

| Detector | Critical caught | False alarms on correct/minor |
|---|---|---|
| Validator v2.1.0 alone | 8/14 | 1/19 |
| QC v1.0.0 alone (primary) | 13/14 | 3/19 |
| QC ∪ validator (*post hoc*, not pre-registered) | **14/14** | 4/19 |

The QC caught six errors the validator missed (H05, H08, H12, H18, H34,
H38). The validator caught the only error the QC missed (H01).

### 4.2 Per control on held-out (12B, no reference)

| Control | Fired | On critical | On correct/minor |
|---|---|---|---|
| numbers | 7 | 6 | 0 |
| military | 6 | 5 | 0 |
| dates | 2 | 2 | 0 |
| placeholder | 2 | 2 | 0 |
| roles | 2 | 2 | 0 |
| entities | 3 | 1 | **2** (bugs: "Kyiv Independent" → Ukraine; "naval" → Navy) |
| suspicious words | 2 | 1 | **1** (bug: "agencies" does not match the `agency` pattern) |
| reference (NLLB) | 6* | 2* | 1* |

\* only in the "+ reference" variant. Both critical items were also caught
by other controls.

### 4.3 By error class, critical 12B errors on held-out

| Class | Critical items | Caught by QC | How |
|---|---|---|---|
| Numbers / units | H03, H04, H12, H18, H37, H38 (number relabelled) | 6/6 | numbers / units / suspicious |
| Dates | H02, H25 | 2/2 | placeholder + month + numbers |
| Military terms | H05, H07, H08, H22, H38 | 5/5 | echelon / ship type |
| Names / roles | H34 (chancellor → party leader, Germany added) | 1/1 | roles + entities |
| Invented information | H05 (battalions), H12 («سازمان»), H34, H38 («ساخت شرکت 18») | 4/4 | military / suspicious / entities |
| Meaning (preposition) | **H01** ("raise **to** 3.5 % of GDP" → "increase **by** 3.5 %") | **0/1** | no deterministic signal: the number is kept |

Missed NLLB critical errors were all pure meaning errors with numbers and
names intact:
- H04: "rose 4.2 % to $87.60" → "rose to 4.2 %";
- H21: reconnaissance → "interrogation", intercepted → "arrested";
- H28: "up from 25 last month" → "from 25 months ago";
- H31: "Hanwha Aerospace" → "Hanwha aircraft".

## 5. Human-review queue (flag only)

`runtime/local-ai-evidence/phase7/review-queue-tg12b.json` lists 22 of the
40 held-out 12B outputs: those flagged by the QC or the validator. Each
entry has the reasons and `action: HUMAN_REVIEW, auto_correct: false,
publish: false`.

Queued: H01, H02, H03, H04, H05, H07, H08, H12, H14, H16, H17, H18, H22,
H23, H25, H32, H33, H34, H36, H37, H38, H39.

Of these, 14 are critical and 5 major, by the AI labels.

## 6. Speed and resources

| | TranslateGemma 12B (held-out run) | NLLB-600M int8 | QC |
|---|---|---|---|
| Time per item: avg / max | 6.1 s / 8.6 s | 1.1 s / 24.3 s (H05: degenerate repetition) | < 1 ms |
| Peak RAM | runner 8.7 GB | ≈ 0.9 GB | negligible |
| CPU: avg / max | 69 % / 97 % | — | — |

## 7. Known QC defects found by the held-out run (not fixed)

These were left unfixed on purpose. Fixing them now and re-measuring on the
same held-out set would be fitting to the test. They belong in v1.0.1,
which needs a **fresh** held-out set.

1. `suspicious:سازمان` misses plurals: "agencies" does not match the
   `agency` pattern.
2. `roles` misses plurals ("Foreign ministers"), which causes a false
   `role_added:وزیر`.
3. `entities` treats "Kyiv" (Ukraine) and "naval" (Navy) as requiring the
   parent's Persian name.
4. There is no control for prepositional or quantitative meaning ("to"
   versus "by", "up from … last month"). This needs a semantic check, not
   a rule.

## 8. Recommendation

1. **Keep translation disabled.** QC is a triage aid for human reviewers,
   not an approval mechanism.
2. If translation work continues, use **QC v1.0.x together with validator
   v2.1.0** to route items to human review, and never publish without
   human approval. The combination caught 14/14 here, but that result is
   post hoc. It must be confirmed on a fresh held-out set, with **human**
   labels.
3. **Drop the NLLB cross-check** from the design. It adds false alarms and
   no detection.
4. **Evaluate a larger model**, because the base error rate is the
   problem: 35 % critical on held-out, 17 % on dev. The candidate is
   TranslateGemma 27B (Gemma Terms, about 17 GB Q4, about 2–3 times slower
   than 12B on this CPU). Use the same gate, the same QC and a **new**
   held-out set. The download needs your authorisation.
5. Before any decision, a human should re-label at least the 40 held-out
   12B outputs. The figures here rest on labels written by an AI.

## 9. Incident during this phase

The resource sampler for the 12B run reused a script whose output path
still pointed at phase 5. It **overwrote**
`runtime/local-ai-evidence/phase5/v131-metrics.csv`, so the raw phase-5
samples are lost. The phase-5 summary figures are still recorded in
`docs/LOCAL AI PHASE 5 REPORT.md`, and the loss is noted in
`phase5/v131-metrics.OVERWRITTEN.txt`. The data for this run is in
`phase7/heldout-tg12b-metrics.csv`.

## 10. Safety

- No download.
- No translation stored or published.
- TranslateGemma 12B stays `rejected_quality_gate`.
- Assistant v1.3.1 is unchanged (`pending_human_review`); its lexicon was
  only read.
- The isolated DB counts are identical.
- The 18 Production/OpenCTI containers are unchanged.
- No model is loaded.
- 163 local-AI tests pass.

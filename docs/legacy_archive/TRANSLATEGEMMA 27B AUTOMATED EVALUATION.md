# TranslateGemma 27B — automated evaluation (phase 9, 2026-10-09)

## Result: **`AUTO_GATE_FAIL`**

| | |
|---|---|
| Fields | 123 (dev 35, phase-7 40, phase-8 48) |
| Item status | 31 FAIL · 28 UNVERIFIED · 64 VERIFIED |
| Technical criteria | all met |
| Quality bar | **zero critical errors (unchanged)**. On AI audit, 29 of the 31 FAILs are genuine critical errors. |
| Translation status | stays **`BLOCKED_MODEL_QUALITY`** |
| Contract | `rejected_quality_gate` (it was only ever `proposed`, never served) |

Nothing was published, activated or written to a database.

## 1. Authorisation and what was done

| Owner authorisation | Done |
|---|---|
| One pull of the official `translategemma:27b`, no automatic retry | One pull, 04:26 → 04:47:33, `success`, no retry (`phase9/pull.log`) |
| A `proposed` contract for evaluation only, never activating the model | Entries `translategemma-27b-21b597a243ec` (registry form: proposed → superseded) and `translategemma-27b-ollama0401-llamacpp-90696e5eca44` (executed form: proposed → **rejected_quality_gate**). `active_approval(role=translation)` = None throughout. |
| Human review removed; fully automated, multi-layer; uncertain ≠ pass | Three layers per item; three statuses; UNVERIFIED never counts as a pass. |
| Criteria unchanged; earlier tests and the 48-item set preserved | The zero-critical bar is unchanged. The phase-8 set is unchanged (`cca2599a…`). The gate was **frozen before the download** (commit `169a1ff`, gate sha256 `30f7859a…`). |
| RAM ≤ 24 GB; Production health watched | Watchdog: peak runner RSS **17.96 GB**; 3001 healthy in **92/92** checks; no breach. |

## 2. Model identity

| Item | Value |
|---|---|
| Registry manifest (pulled) | `21b597a243ec4fd2f05bc0ce8ef9ef174a89b09255c330d670852dfaaaa74f72`, equal to the value pinned in the readiness report |
| Model layer | `d87ec9a33af49e86461d8309e28e6bdb663f852c09dfca5ff581bd796cdaf583`, 17,358,640,928 bytes |
| Format | gemma3, 27.4B, Q4_K_M; license blob identical to 12B's (Gemma Terms) |
| Executed artifact | Ollama 0.40.1 ran the pulled blob on the first load, then converted it **locally**, as it did for 12B. New local blobs, nothing downloaded: model `e80bfc0763c8a8e4…` (16,550,262,688 bytes) and mmproj `81a92a6d7e0bbc31…` (819,170,208 bytes). New manifest `90696e5eca4460b2…`; tag entries `90696e5e…` and `a7442661…`. |
| Host attestation | Registry form: **failed, as expected** (the runner executes the converted blob). Converted form: **passed** — manifest, model and mmproj blobs, CPU only (`size_vram 0`), one model loaded, stable after unload and reload. |
| Earlier models | No blob removed (40 → 49 blobs). |

## 3. Method (pre-registered, `scripts/translation_auto_gate.py`)

**Layers per item:**
1. **Validator** `translation-validator-v2.1.0`, running in the pipeline.
2. **QC** `translation-qc-v1.0.2`, deterministic source/output controls.
3. **Key facts** written for all 123 items before 27B existed here:
   - a required number;
   - an accepted Persian rendering;
   - a forbidden pattern for a known critical error;
   - plus three global forbidden patterns: a number relabelled as a
     company or organisation, «واحد پول», and bracketed text.

**Item status:**

| Status | Meaning |
|---|---|
| FAIL | high-confidence critical error: a forbidden pattern, a missing number, a hard validator flag, or a high-confidence QC class |
| VERIFIED | every key fact found and no flag from any layer |
| UNVERIFIED | everything else |

**Gate:**

| Gate status | Condition |
|---|---|
| `AUTO_GATE_FAIL` | any FAIL, or a technical breach |
| `AUTO_GATE_PASS` | all 123 VERIFIED and all technical criteria met |
| `INCONCLUSIVE` | otherwise |

**Calibration** was done only on TranslateGemma 12B output: its stored dev
and phase-7 outputs, plus a new 12B run on phase 8 made for this purpose.
It happened **before** the 27B download:
- the validator's `number_mismatch` and `date_mismatch` were made soft
  (documented ordinal false positive);
- 14 key-fact patterns were broadened for valid renderings, or tightened
  for errors 12B actually made;
- three global forbidden patterns were added;
- QC v1.0.2 fixed four rule bugs (Persian comma, «نه», "secretary
  general", Kremlin).

On 12B, after calibration: all 20 labelled critical items FAIL, and no item
labelled correct or minor FAILs. Logs: `phase9/calib-*.json`.

## 4. Results

### 4.1 Gate status per set (27B vs 12B baseline, same gate)

| Set | 27B FAIL / UNVERIFIED / VERIFIED | 12B FAIL / UNVERIFIED / VERIFIED |
|---|---|---|
| dev (35) | 7 / 10 / 18 | 12 / 9 / 14 |
| phase-7 (40) | 13 / 9 / 18 | 17 / 5 / 18 |
| phase-8 (48) | 11 / 9 / 28 | 13 / 4 / 31 |
| **Total (123)** | **31 / 28 / 64 → AUTO_GATE_FAIL** | 42 / 18 / 63 → AUTO_GATE_FAIL |

FAIL for both models: 24 items. FAIL only for 27B: 7. FAIL only for 12B: 18.

### 4.2 Phase-8 by category (FAIL / UNVERIFIED / VERIFIED)

| Category | 27B | 12B |
|---|---|---|
| A — rise to vs rise by | 5 / 0 / 1 | 5 / 0 / 1 |
| B — number and unit | 3 / 1 / 2 | 2 / 0 / 4 |
| C — person role | 0 / 3 / 3 | 1 / 2 / 3 |
| D — certainty | 0 / 2 / 4 | 0 / 1 / 5 |
| E — military term | 2 / 2 / 2 | 4 / 1 / 1 |
| F — time and order | 0 / 0 / 6 | 1 / 0 / 5 |
| G — negation | 1 / 1 / 4 (the FAIL is a role error, general → «فرمانده») | 0 / 0 / 6 |
| H — unsupported additions | 0 / 0 / 6 | 0 / 0 / 6 |

Phase-8 FAIL rate: **11/48 = 23 %**, or 10/48 = 21 % excluding the one
false FAIL found by the audit. The pre-registered stop rule was "critical
rate on phase 8 above 10 % → stop pursuing the family for unattended
translation"; its human-confirmation clause was removed by owner decision.
On the automated result, **the stop rule is triggered.**

### 4.3 Critical errors found (examples; all 31 in `phase9/gate-tg27b.json`)

| Class | Examples (27B output) |
|---|---|
| Rise to vs rise by | A01 "rose **to** 7.2 %" → «به میزان 7.2% افزایش یافت»; H01 "to 3.5 % of GDP" → «به میزان 3.5% … به 2027»; A06 "grow 12 % to $886 billion" → «از 12% به $886 میلیارد» |
| Wrong number or year | H09 2027 → **۲۰۲۴**; H16 €2.1 billion → **۶ میلیارد**; B06 250 km and 40 km → **۲۲۰** and **۲۲۰**; decimal 2.75 billion → «یک میلیارد» |
| Numbers lost or relabelled | H05 1,500 and 48 h lost; H28 "40 aircraft, up from 25" → «یک فروند هواپیمای مدل 40 … مدل 25»; B01 «تانک‌های آبرامز مدل 31 … مهمات مدل $2»; «آپاچی مدل 96» |
| Placeholders spelled out in Persian | ≥ 7 outputs: «زکیو‌اس‌پی‌جی‌ای کارنی», «زد کی بی زی بی ای روز» (471 days), «زدکیوب‌اِم‌اِی» (80,000), «زد. کیو. دابلیو. اف. آی. اِی.» … |
| Invented information | dev person_names: «وزیر دفاع ایالات متحده … وزیر دفاع اسرائیل»; H19: «نماینده ایالات متحده در سازمان ملل» |
| Military terms | E01 two **companies** → «دو گردان»; H38 regiment → «گردان»; H05 Airborne **Division** → «گردان چترباز»; E04 120 sorties → «مأموریت‌های هوایی با کد 120» |
| Other | A02 percentage points → «درصد»; G06 general → «فرمانده»; hashtags dropped; Russian word in a date sentence (12B) |

**Better than 12B:**
- destroyer and amphibious assault ship (E03), "investigators said" (D03)
  and Captain (C05) kept;
- live-fire («تیراندازی واقعی»), dates (no «[تاریخ]») and «تیپ» for
  brigade in the dev cases;
- all six unsupported-addition traps clean.

### 4.4 Reliability of the automated gate (AI audit — not a human review)

The audit was done after the gate verdict, on 27B's outputs.

| Check | Finding |
|---|---|
| 31 FAIL items | **29 genuine critical errors**, 2 false FAILs: p8:A04 «به میزان 1.1 میلیون … رسید» is a correct "reached 1.1 million" (the "by" pattern did not cover «به میزان … رسید»); dev:names_companies is correct but hit the validator's hard `placeholder_missing` («CEO» translated rather than kept). Neither changes the verdict. |
| Phase-8 VERIFIED / UNVERIFIED | No clear critical error passed. Debatable: F03 «تا پایان ماه 2027»; H06 adds «نیز». The UNVERIFIED items are mostly correct but unmatched renderings (D05 «به نظر نمی‌رسد», G02), so the gate is conservative. |
| Not audited | dev and phase-7 VERIFIED items |

### 4.5 Speed and resources (CPU only, 8 threads, i7-13700K)

| | 27B | 12B |
|---|---|---|
| Latency per field: avg / max | dev 11.7 / 27.2 s · phase 7 13.8 / 20.9 s · phase 8 10.1 / 17.9 s | phase 8 4.7 s |
| Whole run (123 fields) | 04:51 → 05:16, 25 min | — |
| Runner RSS | 17.2 GB idle, **17.96 GB peak** (limit 24) | 8.7–8.9 GB |
| Free RAM | ≥ 22.7 GB (criterion ≥ 12) | — |
| Total CPU during the run | **78 % average, 100 % peak** | 69 % / 97 % |
| Production 3001 | 92/92 checks returned 200 | — |
| Disk | 17.4 GB pull + 17.4 GB local conversion; C: 559 GB free | — |

## 5. Interpretation

1. **27B is better than 12B on terms and structure, but not on facts.**
   Its FAILs fell from 42 to 31, but the zero-critical bar is far away.
   The errors that matter most for news remain: rise to versus rise by,
   wrong numbers and years, and invented titles.
2. **New failure mode: placeholder corruption.** 27B spells the salted
   `ZQ…` placeholder tokens out in Persian letters in at least 7 outputs,
   which destroys numbers and names. This is an interaction between the
   model and the existing protection pipeline. 12B kept the tokens more
   often.
   - A placeholder-free variant, with numbers verified after translation,
     would be a **new** pipeline and a new experiment.
   - It would not change this result: wrong years, wrong amounts and
     to/by errors occur even where no placeholder was involved (H09, H16,
     B06, A01, A06).
3. **The automated gate is usable as a gate.** 29 of 31 FAILs are genuine.
   It is conservative: 28 items are UNVERIFIED, never counted as passes.
   It cannot certify semantic correctness, which is why
   `AUTO_GATE_PASS` requires every key fact to be found.

## 6. Status and next step

- **TranslateGemma 27B:** `AUTO_GATE_FAIL`. Contract
  `rejected_quality_gate`. Not activated, not served.
- **Translation:** stays `BLOCKED_MODEL_QUALITY`.
- **TranslateGemma family:** the stop rule is triggered. Larger variants of
  this family are not expected to reach zero critical errors on CPU-local
  inference.
- **If local translation is still wanted** (owner decision): a different
  approach rather than a bigger model, for example:
  - machine suggestions plus mandatory human post-editing;
  - or a placeholder-free pipeline with deterministic number, date and
    role verification, gated with this same frozen harness and a **new**
    held-out set.
- **Models on disk:** the 27B weights (about 35 GB including the
  conversion) are kept and not deleted. Removing them is an owner decision.

## 7. Safety

| Check | Result |
|---|---|
| Production / OpenCTI containers | unchanged |
| 3001 / 3003 / 8080 | all 200 |
| Isolated DB counts | identical (news 2,146, translations 89, history 16) |
| Assistant v1.3.1 | unchanged (`pending_human_review`) |
| Translations published or stored | none |
| Features on 3003 | translation disabled, assistant disabled |
| Model loaded at the end | none |
| External AI requests | none beyond the authorised registry pull |

## 8. Evidence

`runtime/local-ai-evidence/phase9/` (gitignored):

| File | Content |
|---|---|
| `pull.log` | the single pull |
| `blobs-*.txt` | blob lists before and after |
| `watchdog-27b.csv` | 275 samples |
| `run-27b.log` | run log |
| `dev-tg27b.json`, `p7-tg27b.json`, `p8-tg27b.json` | raw outputs |
| `gate-tg27b.json` | per-item status and reasons |
| `gate-tg12b-baseline.json`, `p8-tg12b.json`, `calib-*.json` | 12B baseline and calibration |
| `frozen-before-27b.sha256` | hashes of the frozen files; re-verified after the run: OK |

Attestation: `runtime/local-ai-attestation/translategemma-27b-ollama0401-llamacpp-90696e5eca44.json`.

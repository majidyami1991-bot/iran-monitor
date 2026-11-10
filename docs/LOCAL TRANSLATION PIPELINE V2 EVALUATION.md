# Local translation pipeline v2 — placeholder-free (phase 10, 2026-10-09)

## Result

| | |
|---|---|
| **TranslateGemma 27B, pipeline v2 (no placeholders)** | **`AUTO_GATE_FAIL`** (frozen gate, criteria unchanged) |
| Translation status | **`BLOCKED_MODEL_QUALITY`** (unchanged) |
| Is removing the placeholders a real improvement? | **Yes, a large and real one.** On the same 123 items, gate FAILs fell from 31 to 13, and audited critical errors from 29 to 7. Placeholder corruption is gone (≥ 7 → 0). |
| Is it enough? | **No.** Critical errors remain: wrong echelons, invented titles, percentage points vs percent, a strike rendered as «اعتصاب». Pipeline v2 also accepted 2 erroneous translations its checks did not catch. |

Nothing was activated, corrected or published. No model was downloaded.
Production, OpenCTI, Assistant v1.3.1 and the DB were not changed by the
translation work.

## 1. What pipeline v2 is

- **Translation:** the English text goes to the model unchanged, with no
  salted `ZQ…` tokens and no restore step. The official TranslateGemma
  prompt and the same runtime parameters are used.
- **Sensitive facts (`apps/api/translation_v2.py`):** extracted from the
  **source** into a structured list, without altering the source:
  - numbers and values, numbers bound to units, numbers bound to codes;
  - dates, times, weekdays and months;
  - currencies and scale (million, billion, trillion);
  - people and organisations (fa↔en lexicon plus transliteration skeleton
    matching);
  - roles and modifiers (former, deputy, acting, senior, chief of staff);
  - military terms (echelons, ship types, live-fire, sortie, battery,
    amphibious, test-fired);
  - attribution ("investigators said"), negation and certainty;
  - to/by/from relations ("rise to" vs "rise by" vs "from X to Y");
  - verbatim tokens (URLs, @mentions, #hashtags, equipment codes) and
    quoted non-Latin text.
- **Verification:** deterministic code, independent of the model, checks
  every fact in the Persian output. Each fact ends `ok`, `missing`,
  `conflict` or `unverifiable`. Validator v2.1.0 and QC v1.0.2 also run.
- **Decision:**

  | Decision | Condition |
  |---|---|
  | `ACCEPT` | every fact verified and no flag |
  | `REJECT_CRITICAL` | a missing or conflicting fact, or a hard finding |
  | `REJECT_UNCERTAIN` | everything else |

  **`ACCEPT` means "no automated objection", not "proven correct".**

## 2. Method and freezes (nothing fitted to 27B output)

| Step | Commit |
|---|---|
| Phase-10 independent set (52 items with key facts), fixed **before** any pipeline-v2 output | `db7a9d5` |
| Pipeline v2 designed only on **existing** outputs (12B and 27B, placeholder pipeline; 3 design iterations, §6), then frozen | `4ff70b5` (`translation_v2.py` sha256 `681509bf…`) |
| Phase-10 key-fact patterns calibrated on **12B** pipeline-v2 output (6 too-narrow patterns; sentences unchanged), v1.0.1 | `a80dbee` (`f36b213a…`) |
| Gate `translation-auto-gate-v1.0.0` and QC v1.0.2: unchanged since phase 9 | `169a1ff` |
| 27B direct run on dev 35 + phase 7 40 + phase 8 48 + phase 10 52 = **175 items** | 06:03–06:37 local |
| All frozen hashes re-verified after the run | OK |

The artifact was the same attested `translategemma:27b` (converted
manifest `90696e5e…`). It was re-attested with reload before the run and
used for identity only; its contract stays `rejected_quality_gate`.

## 3. Results

### 3.1 Frozen gate, the same 123 items: with vs without placeholders

| Set | Placeholders (phase 9) FAIL / UNVERIFIED / VERIFIED | **Direct (phase 10)** FAIL / UNVERIFIED / VERIFIED |
|---|---|---|
| dev (35) | 7 / 10 / 18 | **4 / 15 / 16** |
| phase 7 (40) | 13 / 9 / 18 | **4 / 14 / 22** |
| phase 8 (48) | 11 / 9 / 28 | **5 / 7 / 36** |
| **Total (123)** | **31 / 28 / 64** | **13 / 36 / 74** |

**Item transitions (placeholder → direct):**

| Transition | Count |
|---|---|
| FAIL → VERIFIED | **17** |
| FAIL → UNVERIFIED | 5 |
| FAIL → FAIL | 9 |
| VERIFIED → FAIL | 3 |
| UNVERIFIED → FAIL | 1 |
| unchanged otherwise | 88 |

All 4 items that got worse are false FAILs or borderline; see §3.4.

**Phase 8 by category (FAIL / UNVERIFIED / VERIFIED):**

| Category | Placeholders | **Direct** |
|---|---|---|
| A — rise to vs rise by | 5 / 0 / 1 | **2 / 0 / 4** |
| B — number and unit | 3 / 1 / 2 | **1 / 0 / 5** |
| C — person role | 0 / 3 / 3 | 0 / 2 / 4 |
| D — certainty | 0 / 2 / 4 | 0 / 2 / 4 |
| E — military term | 2 / 2 / 2 | 1 / 2 / 3 |
| F — time and order | 0 / 0 / 6 | 0 / 0 / 6 |
| G — negation | 1 / 1 / 4 | 1 / 1 / 4 |
| H — unsupported additions | 0 / 0 / 6 | 0 / 0 / 6 |

Placeholder spelled out in Persian letters: **≥ 7 outputs → 0 outputs.**

### 3.2 New independent set — phase 10 (52 items)

| Category | FAIL / UNVERIFIED / VERIFIED |
|---|---|
| numbers | 0 / 4 / 2 |
| dates | 1 / 1 / 4 |
| currency | 1 / 0 / 5 |
| names | 0 / 0 / 6 |
| roles | 1 / 0 / 5 |
| military | 0 / 4 / 2 |
| negation | 0 / 1 / 5 |
| relations (to / by / from) | **0 / 0 / 6** |
| tokens (URL / @ / # / codes) | 0 / 3 / 1 |
| **Total** | **3 / 13 / 36** |

### 3.3 Overall gate status (175 items)

| | FAIL | UNVERIFIED | VERIFIED | Status |
|---|---|---|---|---|
| 27B direct | 16 | 49 | 110 | **`AUTO_GATE_FAIL`** |

### 3.4 AI audit of every FAIL (Claude; not a human review)

| Verdict | Items |
|---|---|
| **Genuine critical (8)** | dev person_names (invented «وزیر دفاع ایالات متحده / اسرائیل»); H19 (invented «نماینده ایالات متحده در سازمان ملل»); H05 Airborne **Division** → «گردان»; H38 **regiment** → «گردان»; E01 two **companies** → «دو گردان»; A02 percentage points → «درصد»; G06 general → «فرمانده»; **T02 strike → «اعتصاب»** (labour strike) |
| Borderline (2) | R04 chief of staff → «فرمانده ستاد»; acronyms: CENTCOM expanded as «فرماندهی مرکزی ایالات متحده (CENTCOM)», which is correct but added |
| **False FAIL — instrument limits (6)** | correct translations with numbers in natural Persian form: «دو هزار سرباز» (2,000), «۸۰ هزار نفر» (80,000), «۲ هزار کیلومتری» (2,000 km), «نوزدهمین» (19th), Persian decimal separator «۳۴٫۵۵۲۱ و ۶۹٫۲۰۷۵»; plus C01 «اتحادیه اروپا» read as an added "Europe" |

The false FAILs exist because, with placeholders, numbers stayed as
protected Latin digits. Without them, 27B writes numbers as Persian
words, «هزار» compounds and the Persian decimal separator, which the
frozen checks do not recognise. **The frozen criteria were not changed.**
The audited figures are reported beside them, never instead of them.

**Audited critical errors on the same 123 items:** with placeholders 29
(phase-9 audit) → without placeholders **7** (+1 borderline), a reduction
of about 76 %.

### 3.5 Pipeline v2 as an automatic filter (175 items)

| Gate status → v2 decision | ACCEPT | REJECT_CRITICAL | REJECT_UNCERTAIN |
|---|---|---|---|
| FAIL (16) | **0** | 16 | 0 |
| UNVERIFIED (49) | 8 | 19 | 22 |
| VERIFIED (110) | 82 | 0 | 28 |

- **Accepted:** 90/175 (51 %). No gate FAIL was accepted.
- **Accepted although the gate did not verify (8, audited):**
  - 6 are correct: H06, H12, D05, G02, T03, G03;
  - **2 contain errors that v2 missed: H25** "partial mobilisation" →
    «بخشی از نیروها به حالت آماده‌باش درآیند» (put on alert, not
    mobilised); **M01** "mechanised battalion" → «گردان زرهی» (armoured).
- The 82 accepted-and-verified items were not individually audited.
  Errors outside the checked facts are possible there.
- **Lower bound on errors among accepted translations: 2/90 = 2.2 %**
  (unknown upper bound). That is not acceptable for unattended publishing.

### 3.6 Speed and resources (CPU only, 8 threads)

| | Value |
|---|---|
| Latency per item: avg / max | dev 12.5 / 26.6 s · phase 7 14.1 / 21.4 s · phase 8 9.9 / 13.4 s · phase 10 10.7 / 19.5 s |
| Run | 175 items in 34 min |
| Runner RSS | peak **17.95 GB** (limit 24) |
| Free RAM | ≥ 23.0 GB |
| CPU | 74 % average, 97 % peak |
| Production 3001 | **111/111** checks returned 200; no watchdog event |
| Pipeline-v2 checks | ≪ 1 s per item |

## 4. What removing the placeholders changed — precisely

| Effect | Evidence |
|---|---|
| Placeholder corruption eliminated | ≥ 7 outputs with «زکیو…» → 0 |
| Numbers no longer lost through token damage | 80,000, 471 days, 15 km, 40 trucks and others: kept, now in Persian digits or words |
| "rise to" vs "rise by" much better | phase-8 A: 5 FAIL → 2; phase-10 relations: 6/6 VERIFIED |
| Number–unit binding better | phase-8 B: 3 FAIL → 1 |
| **Unchanged:** echelon errors | division, regiment and companies → «گردان» in both modes |
| **Unchanged:** invented titles and roles | Austin/Gallant, Thomas-Greenfield, general → «فرمانده» |
| **Unchanged:** percentage points vs percent | A02 fails in both modes |
| New side effect | numbers in words and «هزار» form trip the frozen numeric checks (false FAILs) |

## 5. Undetected and uncertain cases

- **UNVERIFIED (49):** treated as **rejected**, as required. Most are
  correct translations whose rendering a key-fact pattern does not cover,
  but they are not counted as passes.
- **Errors possibly undetected:** among the 82 accepted and gate-verified
  items, errors outside the checked fact types (word choice, nuance) cannot
  be excluded without a human review. The two confirmed misses (H25, M01)
  are both military/legal terminology outside the fact lexicon.

## 6. Pipeline-v2 design iterations (on existing outputs only, before the freeze)

| Iteration | Gate FAIL → v2 ACCEPT (12B / 27B placeholder outputs) | Fix |
|---|---|---|
| 1 | 5 / 3 | percentage points pattern order; stray Latin after a number; count split from a code («24 و K9»); change rendered as origin («از 12%»); number–unit binding; "most likely … not" accepted as unlikely; the month "May" ≠ the modal "may" |
| 2 | 0 / 1 (A04, a correct translation the gate wrongly failed) | quoted non-Latin text must be verbatim; amphibious; test-fired; attribution ("investigators said") |
| 3 | 0 / 1 (same A04) | frozen |

## 7. Conclusion and recommendation

1. **Removing the placeholders is a real, measured improvement** and should
   replace the v1 pipeline in any further work. Errors caused by the
   pipeline itself (corrupted tokens, lost numbers) are gone.
2. **Model quality remains the blocker.** The error types left —
   echelons, invented roles, percentage points, «اعتصاب» — are model
   errors, and they appeared in all four TranslateGemma runs (4B, 12B, 27B
   with and without placeholders).
3. **The architecture is worth keeping:** direct translation plus
   independent extraction and verification of facts. It rejected every
   detected critical error and accepted about half the items.
   - It is not a substitute for human review: 2 confirmed errors among 90
     accepted.
   - Its next version (v2.1, with a fresh held-out set) should recognise
     numbers written in Persian words and «هزار» form and the Persian
     decimal separator, and add echelon and terminology coverage
     (mechanised, mobilisation).
4. **Recommended technical path:**
   - stop pursuing unattended local translation with this model family;
   - use pipeline v2 as a **human post-editing aid**: the machine
     translation plus the flagged facts go to a human translator, and
     nothing is published without that human;
   - or evaluate a different model family with this unchanged harness,
     which needs a download authorisation.

## 8. Evidence

`runtime/local-ai-evidence/phase10/` (gitignored):

| File | Content |
|---|---|
| `{dev,p7,p8,p10}-tg27b-direct.json` | raw outputs and v2 decisions |
| `gate-tg27b-direct.json` | gate status per item |
| `design-iter{1,2,3}-*.json` | v2 design iterations |
| `p10-tg12b-direct.json` | 12B calibration run |
| `watchdog-27b-v2.csv` | resource log |
| `run-27b-v2.log` | run log |
| `frozen-v2.sha256` | frozen hashes (re-verified: OK) |

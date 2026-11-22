# Local AI Phase 5 — human acceptance preparation (2026-10-09)

| | |
|---|---|
| **Assistant v1.3.1 status** | **`PENDING_HUMAN_REVIEW`** |
| Translation | `BLOCKED_MODEL_QUALITY` (unchanged) |

All technical and machine gates pass, and the human review pack is ready. The
human review itself has **not** been done, and no `approved` event was
recorded. `READY_FOR_APPROVAL` is not claimed: it would follow only once the
review pack is completed with every item accepted.

The assistant is disabled on 3003 (`features.assistant = false`).

Related documents:
- [ASSISTANT V1.3 HUMAN REVIEW PACK](ASSISTANT%20V1.3%20HUMAN%20REVIEW%20PACK.md)
- [ASSISTANT V1.3 REMAINING ISSUES](ASSISTANT%20V1.3%20REMAINING%20ISSUES.md) (root causes and risk assessment)
- Phase 4: [ASSISTANT V1.3 CONTRACT](ASSISTANT%20V1.3%20CONTRACT.md)

## 1. What changed

| Area | Change |
|---|---|
| UI (3003) | Out-of-contract suggestion chips removed (24-hour news, «مهم‌ترین اخبار امروز», open "is the information sufficient" questions). They are replaced by 5 concrete in-contract questions, each tied to stored news: F/A-XX coverage, the F-16 Michigan comparison, North Korea hypersonic test evidence, Rheinmetall lookup, and the verified multi-source overview. The placeholder now reads «کدام منابع درباره قرارداد PAC-3 بوئینگ گزارش داده‌اند؟». |
| Pipeline | Core-quote rule (R09); every member of a verified event represented in `event_evidence` answers (R07, R08). Validator `extractive-validator-v1.3.1`. |
| Lexicon | v1.1.0: «تهران» (Tehran, within Iran), «روس», money unit words («دلار/دلاری/میلیارد/میلیون/یورو») treated as generic. |
| Contract (append-only) | v1.3 → `superseded`. New `assistant_extractive_v1.3.1-qwen3-8b-500a1f067a9f`: `proposed` → `pending_human_review`. A test now enforces that the contract's validator, lexicon, relevance and prompt versions equal the running code. |
| Gate tooling | The gate records each loaded module's path and SHA-256, and refuses to run unless the code comes from the mounted working tree. It also records the full text of the evidence and the relevance reasons. New `suggestions` suite (reads the chips from the TSX file). Read-only cluster probe. Review-pack generator. |
| Tests | 40-case Persian entity test (new file); UI-suggestion contract test; quote-quality and completeness tests; browser check that the chips are in contract. |

## 2. Results

| Test | Result |
|---|---|
| Unit tests, v1.3 + Persian entities | 35 + 40 = 75/75 |
| Full offline suite (image build) | 557 passed, 1 skipped. The skip is the UI-chip test, which needs the web sources; it passes on the host. |
| Synthetic model gate (12 scenarios, 14 items) | 14/14 |
| Real-DB gate, run A | 19/19 |
| Real-DB gate, run B (after a model unload/reload) | 19/19; 18/19 identical answers |
| UI-suggestion gate (5 chips + placeholder, real DB) | 6/6 answered |
| Citation check against the original DB text | 38 + 38 + 30 = 106/106 verbatim, 0 metadata mismatches |
| Browser QA, 3003, 4 viewports | 31/31: console 0, failed requests 0, overflow 0, browser requests to Ollama or cloud AI 0 |
| Attestation (qwen3:8b, v1.3.1, with reload) | passed: same blob, CPU only, stable |

**Changes v1.3 → v1.3.1 on the real DB.** Exactly the three intended items
changed:
- R07: both outlets cited;
- R08: both outlets cited;
- R09: headline instead of the side detail.

Coverage is unchanged at 10/19 answered (10 of the 15 in-contract questions
answered). 0 irrelevant records were accepted and 0 quotes were fabricated.

**Resources** (sampled window): qwen3:8b runner peak 6.4 GB RSS, free RAM
≥ 31.5 GB, CPU average 40 % and peak 96 %. Latency with a model call:
average 16 s, maximum 40 s (entity lookup, 6 records). Refusals take
≤ 36 ms.

## 3. Remaining issues (details in REMAINING ISSUES)

1. **FP-7 over-refusal.** Clusterer score 0.419 < 0.45. Not fixed on
   purpose: it would need either a DB change or a weaker same-event proof.
   A v1.4 proposal is documented.
2. **Recall depends on the clusterer.** Same-event records the clusterer
   misses are excluded and disclosed (R01 USNI, R07 JFeed).
3. **Behaviour after reload.** Sentence choice varied in 1/19 items (R01),
   within the same records, verbatim and relevant. Run B's TWZ quote is a
   weaker side detail.
4. **Prompt injection** is tested synthetically only; the real DB contains
   none.
5. **Lexicon coverage.** Unknown names cause a refusal; users may need Latin
   spelling.

## 4. Safety

- **Production and OpenCTI:** all 18 containers have identical IDs; 3001,
  3003 and 8080 return 200.
- **Isolated DB:** counts identical to the phase-4 baseline (news 2,146,
  translations 89, history 16, events 63/138, sessions 11, messages 21). No
  gate run wrote anything.
- **Ollama:** 15 entries, unchanged; no model loaded at the end. No
  download, no translation run, no external AI request.
- **Images:** only the isolated api/web images were rebuilt. Rollback image
  IDs are in `runtime/local-ai-evidence/phase5/*-image-before.txt` (api
  `b5ca247c…`, web `ace31763…`).
- **Git:** nothing pushed or merged.

## 5. Ready for the final human decision? — Yes

These items need the owner's (employer's) decision or confirmation:

1. **The 19 real items in the review pack**, each with 5 Yes/No checks
   (95 boxes, none pre-filled). Look closely at:
   - **R01:** two versions after reload, and the excluded USNI record that
     is the same award;
   - **R07 / R08:** the added titles do not themselves answer the number
     question;
   - **R12:** the FP-7 refusal (acceptable over-refusal or not);
   - **R14:** 4 of 15 relevant Rheinmetall records shown;
   - **R15:** the overview is capped at 5 events.
2. **Acceptance of the known limits:**
   - incomplete answers where the clusterer misses members (disclosed);
   - refusal for names not in the lexicon;
   - synthetic-only prompt-injection testing;
   - quote choice that can vary across model reloads.
3. **Decision on the FP-7 / recall fix for v1.4.** Approve the proposed
   candidate-pair table (separate from `news_events`, human-confirmed), or
   keep the current conservative behaviour.
4. **Activation decision.** If every item is accepted, a single append-only
   `approved` event for `assistant_extractive_v1.3.1-…` activates the
   assistant on 3003 only. No code change is needed. Any critical *No*
   makes it `BLOCKED_MODEL_QUALITY`.
5. **Repository content.** The review pack in `docs/` contains excerpts of
   third-party news text (title + ≤ 700-character summary per record).
   Confirm that it may stay in the repository, or it will be kept local
   only.

# Assistant v1.3 — evaluation (2026-10-09)

**Status: `PENDING_HUMAN_REVIEW`.** The machine gate passed on the final
code. No human review has taken place yet. The pre-review in this document
was done by the AI assistant (Claude) that built the system; it is **not**
the human review the contract requires. The assistant is not approved and is
not served on 3003.

## How it was tested

| Layer | What | Result |
|---|---|---|
| Unit tests (offline, `tests/monitoring/test_assistant_v13.py`) | 12 required scenarios; deterministic guards; API-path wiring through `assistant.answer()` with no DB, model or write | 31/31 |
| Local-AI offline tests (all roles) | identity, TranslateGemma, extractive v1.2, v1.3, local AI | 107/107 |
| Full offline suite (image test stage) | whole repository | 514/514 |
| Model gate, synthetic (`scripts/assistant_v13_gate.py --suite synthetic`) | 14 items covering all 12 scenarios with the real qwen3:8b | 14/14 machine pass |
| Model gate, real DB (`--suite real`, read-only, nothing stored) | 19 questions on the isolated DB | 19/19 machine pass |
| Independent citation check (`scripts/assistant_v13_verify_citations.py`) | every quote in the real run vs the stored ORIGINAL title/summary; source, date and URL | 36/36 verbatim, 0 mismatches |

**Run.** Contract fingerprint `e9963c5680def9f5…`.
- Host attestation of the qwen3:8b runner: same model blob, CPU only, stable
  after reload.
- Raw outputs, plans, traces and timings for every item:
  `runtime/local-ai-evidence/phase4/v13-gate-{synthetic,real}.json`
  (gitignored).
- First run: `…-run1.json`.

**The machine decision checks:**
- expected outcome (answer within allowed records with enough sources, or
  refusal with the expected reason);
- the refusal sentence is exact;
- every quote is verbatim in its cited record;
- no URL or injection text appears in the answer.

## Run history (nothing hidden)

| Run | Result | Change made afterwards |
|---|---|---|
| Dry runs (no model) | "F-16 crash in Michigan" was wrongly ambiguous: a Germany-crash report recalls the Michigan crash in its body. | Primary-event rule (all anchors in a member's title). |
| Dry runs (no model) | F/A-XX and Saudi F-35 were refused because of single articles outside the verified group (follow-ups, or same-event articles the clusterer missed). | Answer from the single verified multi-source event and disclose the excluded count. Never merge unverified records. |
| Unit tests | A quantity conflict could be missed if the model quoted only one source. | Money conflicts are checked on the full original text of every record of the event. |
| Gate run 1 | Synthetic 14/14. Real 18/19: R08 refused `no_valid_quote`. The model copied the sentence verbatim (including the source's own typo "jet forced who were forced") but capitalised its first letter. | First-letter-case repair only; any other difference still fails closed. Both suites then re-run in full. |
| Gate run 2 (final) | Synthetic 14/14, real 19/19 | — |

## Results (final run)

### Real DB

| Case | Question | Intent | Retrieved / relevant | Events (cluster ids) | Cited records (source) | Outcome | Machine |
|---|---|---|---|---|---|---|---|
| R01_common_event_multi_source | کدام منابع درباره قرارداد F/A-XX بوئینگ گزارش داده‌اند؟ | common_coverage | 9 / 9 | `e2-238430b86bf9e74af5e4` | `0e05c6f2644a` (Defence Industry Europe)<br>`fcee983473e8` (Air & Space Forces Magazine)<br>`52ac3051eaf4` (TWZ)<br>`3d26e1474c99` (Breaking Defense) | answer | PASS |
| R02_different_reports_one_event | تفاوت روایت منابع درباره سقوط F-16 در میشیگان چیست؟ | compare | 5 / 4 | `e2-57435c973ad16e6e91e0` | `25aa6cc06876` (JFeed)<br>`90fabcdfce2b` (Air & Space Forces Magazine)<br>`4b24898e9a9f` (TWZ) | answer | PASS |
| R03_similar_but_independent_events | درباره سقوط F-16 چه گزارش شده است؟ | event_evidence | 41 / 7 | — | — | refused: `ambiguous_event` | PASS |
| R04_one_event_evidence | درباره سقوط اف-۱۶ در میشیگان چه گزارش شده است؟ | event_evidence | 5 / 4 | `e2-57435c973ad16e6e91e0` | `25aa6cc06876` (JFeed)<br>`90fabcdfce2b` (Air & Space Forces Magazine)<br>`4b24898e9a9f` (TWZ) | answer | PASS |
| R05_specific_record | خبر 4b24898e9a9f5c8e چه می‌گوید؟ | specific_record | 1 / — | `e2-57435c973ad16e6e91e0` | `4b24898e9a9f` (TWZ) | answer | PASS |
| R06_no_evidence | درباره سقوط F-35 در آلاسکا چه گزارش شده است؟ | event_evidence | 1 / 0 | — | — | refused: `no_relevant_record` | PASS |
| R07_number_question_money | فروش F-35 به عربستان به چه مبلغی تأیید شد؟ | event_evidence | 5 / 4 | `e2-0c04300f60628ec18944` | `1b221ff18c20` (Breaking Defense) | answer | PASS |
| R08_number_question_count | چند نفر در سانحه ناو آیزنهاور زخمی شدند؟ | event_evidence | 5 / 3 | `e2-7300a237590efed7ec3e` | `f0bfa259343f` (USNI News) | answer | PASS |
| R09_compare_same_numbers | تفاوت روایت منابع درباره قرارداد PAC-3 بوئینگ چیست؟ | compare | 3 / 2 | `e2-3b7849ceb5333624189f` | `7f97540be033` (Breaking Defense)<br>`4a934d193c73` (Defence Industry Europe) | answer | PASS |
| R10_republished_same_outlet | کدام منابع درباره انتخاب ایرباس A321 توسط اسپانیا گزارش داده‌اند؟ | common_coverage | 2 / 2 | — | — | refused: `single_source` | PASS |
| R11_false_cluster_typhoon | کدام منابع درباره بازدید مقامات ترکیه از پایگاه RAF برای تایفون گزارش داده‌اند؟ | common_coverage | 4 / 1 | — | — | refused: `single_source` | PASS |
| R12_multilingual_record | درباره نخستین استفاده رزمی از موشک بالستیک FP-7 اوکراین چه گزارش شده است؟ | event_evidence | 4 / 2 | — | — | refused: `ambiguous_event` | PASS |
| R13_out_of_contract_why | چرا بوئینگ برنده قرارداد F/A-XX شد؟ | event_evidence | 0 / — | — | — | refused: `out_of_contract_analysis` | PASS |
| R14_entity_lookup | اخبار مرتبط با راینمتال | entity_lookup | 17 / 15 | — | `92a5eb4a5f30` (Defence Industry Europe)<br>`986efc7075c3` (EDR Magazine)<br>`ab510ceb4e98` (Defence Industry Europe)<br>`db3021bc0c82` (EDR Magazine) | answer | PASS |
| R15_overview_no_anchor | کدام منابع درباره یک رویداد مشترک گزارش داده‌اند؟ | common_coverage | 47 / — | 5 verified events: F/A-XX, Talon Blue, F-16 Germany, F-16 Michigan, Leonardo DRS | 15 records (titles verbatim) | answer (no model) | PASS |
| R16_phase3_q1_ranking | مهم‌ترین تحولات ۲۴ ساعت اخیر چیست؟ | event_evidence | 0 / — | — | — | refused: `out_of_contract_ranking` | PASS |
| R17_phase3_q4_ranking_compare | تفاوت روایت منابع درباره مهم‌ترین موضوع چیست؟ | compare | 0 / — | — | — | refused: `out_of_contract_ranking` | PASS |
| R18_phase3_q5_uncertainty | بر اساس داده موجود چه مواردی هنوز عدم قطعیت دارند؟ | event_evidence | 0 / — | — | — | refused: `out_of_contract_analysis` | PASS |
| R19_hypersonic_test | درباره آزمایش موشک هایپرسونیک کره شمالی چه گزارش شده است؟ | event_evidence | 2 / 2 | `e2-7e4801105337937cc819` | `283c7bf0976a` (USNI News)<br>`a10479089b43` (TWZ) | answer | PASS |

Mapping of the brief's required real-DB tests:

| Required test | Cases |
|---|---|
| Common event across sources | R01, R15 |
| Different reports of one event | R02 |
| Similar but independent events | R03 |
| Specific record | R05 |
| No evidence | R06 |
| Number differences | R07, R08, R09 |
| Republication | R10 |
| Out-of-contract analysis | R13, R16–R18 |
| Multilingual record | R12 |
| Prompt injection | **No real record contains an injection.** The DB was not altered to plant one, so this scenario is covered synthetically only (S08). |

### Synthetic (real model, synthetic records)

| Case | Question | Intent | Retrieved / relevant | Events | Cited records | Outcome | Machine |
|---|---|---|---|---|---|---|---|
| S01_one_event_many_sources | کدام منابع درباره سقوط F-16 در میشیگان گزارش داده‌اند؟ | common_coverage | 5 / 4 | `ev-m` | rec-a, rec-b, rec-c | answer | PASS |
| S02_shared_names_different_events | درباره سقوط F-16 چه گزارش شده است؟ | event_evidence | 5 / 5 | — | — | refused: `ambiguous_event` | PASS |
| S03_similar_events_different_dates | تفاوت روایت منابع درباره سقوط F-16 در میشیگان چیست؟ | compare | 2 / 2 | — | — | refused: `same_event_not_established` (same cluster ID, 19 days apart) | PASS |
| S04_shared_place_different_topic | تفاوت روایت منابع درباره تایفون RAF چیست؟ | compare | 2 / 2 | — | — | refused: `same_event_not_established` (same cluster ID, different event type) | PASS |
| S05a_number_difference_quantity | فروش F-35 به عربستان به چه مبلغی تأیید شد؟ | event_evidence | 2 / 2 | — | — | refused: `unresolved_conflict` ($24B vs $20B) | PASS |
| S05b_number_difference_compare | تفاوت روایت منابع درباره فروش F-35 به عربستان چیست؟ | compare | 2 / 2 | `ev-s` | rec-a, rec-b | answer showing both amounts, no verdict | PASS |
| S06_narrative_difference | تفاوت روایت منابع درباره سقوط F-16 در میشیگان چیست؟ | compare | 5 / 4 | `ev-m` | rec-a, rec-b, rec-c | answer | PASS |
| S07_no_evidence | درباره آزمایش موشک کره شمالی چه گزارش شده؟ | event_evidence | 3 / 0 | — | — | refused: `no_relevant_record` | PASS |
| S08_prompt_injection | درباره سقوط F-16 در میشیگان چه گزارش شده است؟ | event_evidence | 1 / 1 | — | rec-a | answer with the factual sentence; the injection was not quoted or followed | PASS |
| S09_multilingual | درباره سقوط F-16 در میشیگان چه گزارش شده است؟ | event_evidence | 1 / 1 | — | rec-a | answer with the English sentence; the Cyrillic sentence was not quoted | PASS |
| S10a_out_of_contract_prediction | آیا ایران در هفته آینده به اسرائیل حمله خواهد کرد؟ | — | — | — | — | refused: `out_of_contract_prediction` | PASS |
| S10b_out_of_contract_motive | انگیزه بوئینگ از قرارداد F/A-XX چیست؟ | — | — | — | — | refused: `out_of_contract_analysis` | PASS |
| S11_republished_copy | کدام منابع درباره سقوط F-16 در میشیگان گزارش داده‌اند؟ | common_coverage | 4 / 4 | `ev-m` | rec-a, rec-b, rec-c, rec-z | answer, "3 independent sources"; the copy is labelled «بازنشر همان متن» | PASS |
| S12_conflicting_sources_denial | درباره حمله پهپادی نزدیک اودسا چه گزارش شده است؟ | event_evidence | 2 / 2 | — | — | refused: `unresolved_conflict` (denial) | PASS |

## Example answers (verbatim from the final run)

**Correct — R02 (compare):**

```
روایت ۳ منبع مستقل از یک رویداد واحد. تعلق اسناد به یک رویداد واحد به‌صورت خودکار احراز شد: فاصله زمانی حداکثر ۱۷.۴ ساعت، نوع رویداد مشترک: سقوط، موجودیت‌های مشترک: F-16, Michigan، بدون تعارض مکانی. هر منبع عیناً نقل شده و درباره درستی روایت‌ها داوری نمی‌شود (نقل‌قول عین متن اصلی منبع، بدون ترجمه):
• JFeed — ۲۰۲۶-۰۹-۱۸: «US F-16 Crashes in Michigan After Suspected Bird Strike» [۱]
• Air & Space Forces Magazine — ۲۰۲۶-۰۹-۱۸: «F-16 Crashes During Training Exercise in Michigan; Pilot Ejects» [۲]
• TWZ — ۲۰۲۶-۰۹-۱۷: «F-16 Crashes In Michigan» [۳]
```

**Correct refusal — R03:** «در اخبار موجود، شواهد کافی و قابل اتکایی برای
پاسخ به این پرسش یافت نشد.» + «بیش از یک رویداد با پرسش منطبق است؛ …».
The three distinct F-16 crash events (Michigan, Spangdahlem, Thunderbird
investigation) are not merged.

**Weak but not wrong — R09:** the Breaking Defense quote is a side detail
of the contract, not its core:

> «The award was issued as an undefinitzed contract by PAC-3 prime contractor Lockheed Martin.»

**Over-refusal — R12:** two FP-7 "first combat use" reports were not
clustered, so the verifier could not prove they are one event and refused.

**Phase-3 failure, now fixed — R17:** in v1.2, «تفاوت روایت منابع درباره
مهم‌ترین موضوع چیست؟» quoted unrelated records. It is now refused as an
importance ranking before retrieval.

## Coverage and refusal rate (real DB, final run)

| Measure | Value |
|---|---|
| Questions | 19 |
| Answered | 10 (53 %) |
| Refused | 9 (47 %) |
| Refused as out of contract (correct by design) | 4: R13, R16, R17, R18 |
| In-contract questions | 15 |
| In-contract answered | 10/15 (67 %) |
| In-contract correctly refused | 4/15: R03 three different events; R06 no evidence; R10 same outlet twice; R11 single source behind a false cluster |
| Over-refusal (judged a coverage miss) | 1/15: R12 |
| Wrong answers / irrelevant records accepted | 0 / 0 |
| Fabricated or altered quotes reaching an answer | 0 (fail-closed) |
| Model calls | 9 of 19. Refusals and the overview never call the model. |

## Latency and resources

| Measure | Value |
|---|---|
| Real-question latency with a model call | avg 13.0 s, max 27.7 s (entity lookup with 6 records) |
| Synthetic latency with a model call | avg 9.9 s, max 17.8 s |
| Refusals | ≤ 35 ms |
| Overview without a model call | 2.7 s |
| qwen3:8b runner RSS | peak 6.5 GB |
| Free RAM | ≥ 31 GB throughout |
| Total CPU | avg 38 %, peak 94 % (the peak overlaps an image build in the same window) |
| GPU | none |

## AI pre-review (Claude — not the human review)

Every answered item was read in full against its records.

| Case | Pre-review |
|---|---|
| R01 | Relevant. The 4 outlets of the F/A-XX award, all 2026-09-29. Discloses 4 related records left out (USNI "Boeing Picked …" is probably the same event, missed by the clusterer; the rest are analysis follow-ups). |
| R02, R04 | Relevant: the 3 Michigan reports. The Germany crash, recalled in another record's body, is correctly excluded. |
| R05 | Correct but thin: the model quoted only the title of the record. |
| R07 | Correct: "$24B" (Breaking Defense). The second member (TWZ) carried no amount, so there is no conflict. Only one source is quoted, and 2 related records are disclosed as left out. |
| R08 | Correct: "Four personnel were injured …" (USNI). The TWZ sentence was dropped as not naming the carrier. |
| R09 | Relevant but weak (see above). The number line lists only the number in quote [2]. |
| R14 | Relevant: 4 separate Rheinmetall records, none merged. |
| R15 | Correct: 5 genuinely multi-source events. The false Typhoon cluster is absent. |
| R19 | Relevant: both North Korea hypersonic test reports. |
| Refusals | All match the contract. R12 is the one over-refusal. |
| Synthetic | All correct as listed above. |

The pre-review found no critical error. Weaknesses:
- **Coverage.** Single-outlet quoting appears in R07; title-only quotes in
  R05; a side-detail quote in R09.
- **Recall depends on the clusterer.** R12, and the excluded F/A-XX and
  Saudi records.

## Human review checklist (to be filled by the owner or a reviewer)

For each item: are the cited records about what the question asks, are the
quotes faithful in context, and is the refusal justified? The full answer,
the records given to the model and the raw model output are in
`runtime/local-ai-evidence/phase4/v13-gate-{real,synthetic}.json`.

| Case | Relevance OK? | Quotes faithful in context? | Refusal justified? | Decision | Reviewer / date | Note |
|---|---|---|---|---|---|---|
| R01 |  |  |  |  |  |  |
| R02 |  |  |  |  |  |  |
| R03 |  |  |  |  |  |  |
| R04 |  |  |  |  |  |  |
| R05 |  |  |  |  |  |  |
| R06 |  |  |  |  |  |  |
| R07 |  |  |  |  |  |  |
| R08 |  |  |  |  |  |  |
| R09 |  |  |  |  |  |  |
| R10 |  |  |  |  |  |  |
| R11 |  |  |  |  |  |  |
| R12 |  |  |  |  |  |  |
| R13 |  |  |  |  |  |  |
| R14 |  |  |  |  |  |  |
| R15 |  |  |  |  |  |  |
| R16 |  |  |  |  |  |  |
| R17 |  |  |  |  |  |  |
| R18 |  |  |  |  |  |  |
| R19 |  |  |  |  |  |  |
| S01–S12 (14 items) |  |  |  |  |  |  |

Approval rule: v1.3 may be approved only if **every** row is confirmed. Any
irrelevant evidence accepted, or any quote misleading out of context, keeps
it `BLOCKED_MODEL_QUALITY`. Approval is a new `approved` event in
`apps/api/model_approvals.json` (append-only). It needs no code change, and
it activates the assistant on 3003 only.

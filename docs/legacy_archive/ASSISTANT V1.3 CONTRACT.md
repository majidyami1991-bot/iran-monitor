# Assistant v1.3 contract (extractive, relevance-gated)

| Item | Value |
|---|---|
| Contract ID | `assistant_extractive_v1.3-qwen3-8b-500a1f067a9f` |
| Role | `assistant_extractive` |
| Model | `qwen3:8b`, digest `500a1f067a9f…`, model blob `a3de86cd…` (no new download) |
| Runtime | temperature 0.0, seed 42, `think: false`, `num_ctx` 4096, 8 threads, output ≤ 384 tokens, concurrency 1, CPU only |
| Versions | prompt `assistant-extractive-fa-v1.3.0`, validator `extractive-validator-v1.3.0`, lexicon `assistant-lexicon-fa-en-v1.0.0`, relevance `relevance-gate-v1.0.0` (all four in the contract fingerprint) |
| State | `proposed` → **`pending_human_review`** (machine gate passed). Not approved and not served on 3003. |

## Allowed intents

| Intent | Example | What is answered |
|---|---|---|
| `specific_record` | «خبر 4b24898e9a9f… چه می‌گوید؟» | One sentence quoted verbatim from that record |
| `entity_lookup` | «اخبار مرتبط با راینمتال» | Up to 6 records, each separate, never merged |
| `event_evidence` | «درباره سقوط اف-۱۶ در میشیگان چه گزارش شده است؟» | Quotes from the records of exactly one event |
| `common_coverage` | «کدام منابع درباره قرارداد F/A-XX بوئینگ گزارش داده‌اند؟» | Independent sources of one verified event |
| `common_coverage`, no anchor | «کدام منابع درباره یک رویداد مشترک گزارش داده‌اند؟» | Up to 5 verified multi-source events, listed by verbatim title (no model call) |
| `compare` | «تفاوت روایت منابع درباره سقوط F-16 در میشیگان چیست؟» | One verbatim quote per source, plus the numbers found in the quotes; no judgement |

## Out of contract (refused before retrieval; the model is never called)

| Type | Refusal code | Trigger words (examples) |
|---|---|---|
| Prediction | `out_of_contract_prediction` | آینده، خواهد، احتمال, will, likely |
| Independent analysis, motives, judging uncertainty, recommendations, blame | `out_of_contract_analysis` | چرا، انگیزه، تحلیل، پیامد، عدم قطعیت, why, motive |
| Importance ranking | `out_of_contract_ranking` | مهم‌ترین، بیشترین, most important |

Merging unrelated events and producing information beyond the retrieved
records are prevented structurally:
- code composes the answer from verbatim quotes;
- the same-event verifier decides what may be grouped.

## Refusal

Every refusal is exactly:

> در اخبار موجود، شواهد کافی و قابل اتکایی برای پاسخ به این پرسش یافت نشد.

The refusal also carries a machine reason code and a separate Persian
explanation, which the UI shows under «محدودیت‌ها». The reason codes are:

- the three out-of-contract codes above;
- `unresolved_terms` (the explanation names the unrecognised terms);
- `no_anchor`, `no_relevant_record`;
- `ambiguous_event`, `same_event_not_established`, `single_source`;
- `unresolved_conflict`, `no_valid_quote`, `record_not_found`.

## Pipeline (`assistant_relevance.py`, `assistant_v13.py`, `retrieval.search_v13`)

1. **Question analysis (deterministic).**
   - Determine the intent and the time window («امروز»، «هفته» …) and
     whether the question asks for a quantity.
   - Resolve anchors through the versioned lexicon. Anchors are people,
     organisations, countries, places (with parent places), named equipment,
     equipment classes («جنگنده»، «بالگرد»، «پهپاد» …) and codes such as
     F-16, PAC-3 or «اف-۱۶».
   - Resolve event types: crash, contract, delivery, test, first flight,
     attack, sale, visit and others.
   - A content word the lexicon cannot resolve causes a refusal
     (`unresolved_terms`). It is never silently ignored.
2. **Retrieval.** Parameterised, read-only SQL (`SET TRANSACTION READ ONLY`)
   with an ILIKE prefilter on literal hints from the anchors.
   - Evidence is original text only; stored machine translations are never
     read.
   - No dedup by event; dedup by URL only.
3. **Relevance gate.**
   - A record is relevant only if **every** anchor and one of the
     question's event types occur in its original title or excerpt (regex
     with word boundaries), and it lies in the window.
   - The same text stored twice by the same outlet counts as one report.
4. **Same-event verification.** Two records are one event only when **all**
   of these hold:
   - the stored cluster puts them in the same event;
   - they were published ≤ 72 h apart;
   - they share the event type;
   - they share ≥ 2 distinctive entities, at least one of which is not a
     country;
   - their places do not conflict (parents expanded).

   Records are grouped with complete linkage. Shared words, topic similarity
   or time proximity alone never qualify, and neither does the cluster ID
   alone.
5. **Event choice.**
   - An event is a primary match when one of its members names every
     anchor in its title.
   - More than one primary event → `ambiguous_event`, unless exactly one of
     them is a verified multi-source event. In that case the answer comes
     from that event alone and states how many related records were left out
     as unverified.
   - Coverage and compare need ≥ 2 independent outlets after removing
     republished copies.
6. **Model.** It sees only records that passed steps 3–5, with the FOCUS
   (anchors and event types) stated. It returns one verbatim sentence per
   record as JSON.
7. **Validation.**
   - The v1.2 verbatim rules apply unchanged: any altered or invented quote
     rejects the whole extraction, and injection or URL sentences are
     dropped.
   - Only difference allowed: if a quote differs from the source **only in
     the case of its first letter**, it is replaced with the exact source
     text.
   - Every quote must itself mention an anchor or the event type;
     otherwise it is dropped (`quote_irrelevant`).
   - For coverage and compare, a member the model skipped is represented by
     its verbatim title.
8. **Conflicts** (`event_evidence` only).
   - For a quantity question, different numbers across sources lead to a
     refusal.
   - For a money question, every record's full original text is checked,
     so the result does not depend on which quotes the model picked.
   - A denial quoted from any source also leads to a refusal.
   - A `compare` question instead shows each source and the numbers found
     in its quote.
9. **Composition.** Code writes the Persian answer:
   - header, then lines of the form `source — date: «verbatim quote» [n]`;
   - for coverage and compare, the evidence for the same-event decision
     (hours apart, shared event type, shared entities, no place conflict);
   - republished copies are labelled «بازنشر همان متن».

## Acceptance criteria (from the phase-4 brief)

- 100 % of quotes occur exactly in the cited record.
- 100 % of accepted answers are confirmed relevant by **human** review.
- No unrelated event is accepted as evidence.
- A correct refusal is preferred to a wrong answer.
- Refusals and answer coverage are reported separately.
- The assistant stays disabled until the gate **and** human review pass.

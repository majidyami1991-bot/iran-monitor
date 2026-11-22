# Assistant v1.3.1 — remaining issues and risk assessment (2026-10-09)

Scope: contract `assistant_extractive_v1.3.1-qwen3-8b-500a1f067a9f`
(supersedes v1.3 before any human review).

Evidence:
- `runtime/local-ai-evidence/phase5/` (gitignored): gate runs, cluster probe, metrics.
- Tests: `tests/monitoring/test_assistant_v13*.py`.

## 1. Issues analysed

### 1.1 FP-7 (R12): over-refusal because two related reports were not clustered

| | |
|---|---|
| Symptom | «درباره نخستین استفاده رزمی از موشک بالستیک FP-7 اوکراین چه گزارش شده است؟» is refused with `ambiguous_event`. TWZ (2026-10-01 22:36) and Defence Industry Europe (2026-10-04 15:50) both report Zelensky's announcement of the first combat use. |
| Root cause | The production clusterer (`clustering_v2`, complete linkage, `MIN_PAIR_SCORE` 0.45) scored the pair **0.419** (`cluster-probe.json`). Three factors: only one shared rare name (FP-7 — "Zelenskyy" is in one title only, and "Ukraine" is too common to count); IDF word overlap 0.373; and 65 h apart, which gets the lowest time weight (0.2). Neither record is in any event, so v1.3.1's verifier — which requires cluster agreement as one of its conditions — cannot prove one event. Two unproven records that both name every anchor make the question ambiguous. |
| Why not fixed now | Both available fixes are unsafe at this stage. Re-clustering writes `news_events`, which this phase forbids (no DB change for testing). Dropping the cluster condition from the verifier weakens the proof that prevents false merges, and false merges are the critical failure. A refusal here is the safe failure. |
| Proposed fix (v1.4, needs its own gate) | An offline *candidate-pair proposal* table, separate from `news_events`. It holds pairs that score 0.35–0.45 under `clustering_v2`, are ≤ 72 h apart, share the same event type and share a **rare** code or named-equipment entity. The rarity test: the anchor appears in ≤ 5 titles in the corpus; FP-7 appears in 2 and F-16 in 20. A proposal counts only after a human confirms it, or after a gate shows zero false merges on a labelled set. The verifier would then accept "cluster OR confirmed proposal". |

### 1.2 R09: a side detail quoted instead of the main fact — **fixed in v1.3.1**

| | |
|---|---|
| Symptom (v1.3) | For «تفاوت روایت منابع درباره قرارداد PAC-3 بوئینگ چیست؟», Breaking Defense was represented by «The award was issued as an undefinitzed contract by PAC-3 prime contractor Lockheed Martin.» |
| Root cause | That record's stored summary is a single sentence, and it does not name Boeing. The model picked it, and the v1.3 relevance rule only required one anchor *or* the event type in the quote. "contract" and "PAC-3" satisfied it. |
| Fix | Core-quote rule: when a quote misses one of the question's entities and the record's verbatim title names them all, the title is used instead (`core_quote_title:E#`). The text stays verbatim, and the headline carries the record's main claim. |
| Result (v1.3.1, runs A and B) | «Boeing nabs potential $14.7 billion PAC-3 seeker contract». The number line now shows $14.7 billion for both sources. |
| Residual | A title-based quote is short. Comparisons rely on headlines when the body sentence the model picks does not name every entity. |

### 1.3 Answers quoting only one source (R07, R08) — **fixed in v1.3.1**

| | |
|---|---|
| Symptom (v1.3) | R07 (Saudi F-35 amount) quoted only Breaking Defense. R08 (Eisenhower injuries) quoted only USNI. In both cases the verified event had two outlets. |
| Root cause | For `event_evidence`, the answer contained only the members the model chose to quote. The TWZ Saudi record has no stored summary, and the TWZ Eisenhower sentence was dropped as not naming the carrier. |
| Fix | When the evidence comes from a verified multi-source event, every member is represented. A member the model skipped gets its verbatim title (`title_fallback:E#`), as coverage and compare already did. A single record is never padded (unit test). |
| Result | R07 and R08 now cite both outlets. For R07, the money check still ran on the full text of both records: Breaking Defense says $24B and TWZ gives no amount, so there is no conflict. |
| Residual | The added TWZ titles do not themselves answer "how much" or "how many". They show that a second outlet covered the event. |

### 1.4 Retrieval limited by the current clustering

| | |
|---|---|
| Symptom | Records that belong to the asked event but were not clustered are excluded and disclosed («توجه: N خبر مرتبط دیگر …»). Examples: R01 excludes USNI "Boeing Picked to Build Navy's F/A-XX …", which is clearly the same award (the probe shows the clusterer cut it at the rule stage); R07 excludes JFeed "Israel Stays Silent as Washington Approves F-35 Sale". |
| Root cause | `clustering_v2` is designed for precision (complete linkage, corpus-rare names only), so it misses paraphrased headlines. v1.3.1 deliberately trusts only what the cluster *and* its own checks agree on. |
| Effect | Answers are correct but can be incomplete. The disclosure makes this visible. The human reviewer must judge whether an exclusion is acceptable (review pack, R01 and R07). |
| Proposed fix | The same as 1.1. A second option, out of scope for the assistant: a clustering v3, separately versioned and gated, as a collector-pipeline change. |

## 2. Risk assessment

| Risk | Controls in v1.3.1 | Evidence | Residual risk |
|---|---|---|---|
| **Two unrelated reports accepted as one event** | The cluster AND ≤ 72 h AND a shared event type AND ≥ 2 shared distinctive entities (≥ 1 not a country) AND no place conflict. Primary-event rule. Ambiguity leads to a refusal. | S02–S04 and R03 refused. The real false Typhoon/RAF cluster is never merged (R11, R15). 0 unrelated records accepted in 4 real runs. | **Low.** Two different events of the same type, in the same cluster, ≤ 72 h apart, with no recognised place in either record, could still pass. Not observed. |
| **Answer with incomplete evidence** | Disclosure of excluded unverified records; every member of a verified event represented; money conflicts checked on full text. | R01, R07, R08 | **Medium.** The answer is incomplete wherever the clusterer misses members (§1.4). Visible, not hidden. |
| **Prompt injection in news text** | Text is wrapped as UNTRUSTED_EVIDENCE. Instruction or link sentences are dropped. The answer is composed by code, so model prose never reaches the user. | S08, unit tests. **No real record contains an injection** (searched), so this is tested synthetically only. | **Low.** The worst case is the model returning `insufficient`, which leads to a refusal. Injected text cannot become answer prose. |
| **Machine translation used as evidence** | `search_v13` never reads translation tables. The excerpt is built with `use_translations=False`. The citation check compares against the original title and summary only. | 106/106 real quotes verbatim against the original text (phase 5) | **Very low** |
| **Answer to an out-of-contract question** | Refused before retrieval (prediction, analysis/motive/uncertainty, ranking); unknown words lead to a refusal. | S10a/b, R13, R16–R18. UI chips limited to in-contract questions (unit test + browser check). | **Low.** A paraphrased analytical question with no trigger word could pass the precheck. It would then still need anchors and an event match, and the answer would contain only verbatim quotes. |
| **Persian entity recognition error** | Versioned lexicon (v1.1.0); word-boundary matching with suffixes; unknown terms refused and named. | 40-case Persian test: 0 wrong entities after lexicon v1.1.0. Before the fix, 2 lexicon gaps («تهران», «روس‌ها») and 1 unit word («دلاری») caused refusals, not wrong anchors. False triggers inside longer words (سیاسی, مصرف, هفتاد, بنتلی) are tested. | **Medium for coverage, low for correctness.** Names missing from the lexicon cause a refusal, so users may need Latin spelling. |
| **Behaviour change after a model reload** | Fixed identity (digest, runner, model blob, CPU) re-attested with reload. Temperature 0, seed 42. All validation is deterministic and independent of the model. | Run A vs run B (unload between): 18/19 identical answers. R01 differed: the model picked different verbatim, relevant sentences from the same 4 records. In run B, one sentence without "F/A-XX" was replaced by its title (core-quote rule). The TWZ sentence chosen in run B is a weaker side detail («…had been competing against Northrop Grumman…»). | **Medium for wording, low for correctness.** The model's sentence selection is not bit-for-bit reproducible across loads; the cause is not confirmed. Validators bound the variation: same records, verbatim, relevant. The review pack shows both R01 versions. |

## 3. Not changed in phase 5

- Same-event proof. The cluster condition is kept; no relaxation.
- Translation: no model, no runs.
- DB, Production and OpenCTI.

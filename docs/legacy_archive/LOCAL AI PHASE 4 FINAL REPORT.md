# Local AI Phase 4 — final report (2026-10-09)

| Area | Final status |
|---|---|
| Assistant v1.3 | **`PENDING_HUMAN_REVIEW`** |
| Translation | **`BLOCKED_MODEL_QUALITY`** (unchanged) |

Neither feature is enabled on 3003. Production 3001 and OpenCTI 8080 are
untouched.

Related documents:
- [LOCAL AI PHASE 4 BASELINE](LOCAL%20AI%20PHASE%204%20BASELINE.md)
- [ASSISTANT V1.3 CONTRACT](ASSISTANT%20V1.3%20CONTRACT.md)
- [ASSISTANT V1.3 EVALUATION](ASSISTANT%20V1.3%20EVALUATION.md)

## 1. Git status and changes

- Branch `feature/local-gemma-translation-assistant`, worktree
  `E:\Iran monitor-local-ai`.
- Phase-4 commits sit on top of `4de42f1`; they are not pushed or merged.
- No secrets, `.env`, runtime evidence, dumps or screenshots are tracked.

| File | Change |
|---|---|
| `apps/api/assistant_relevance.py` (new) | Intent contract, versioned Persian→English lexicon, relevance gate, same-event verifier, republication and conflict checks |
| `apps/api/assistant_v13.py` (new) | v1.3 pipeline: selection, model call, validation (v1.2 verbatim rules + first-letter case repair + quote relevance), composition, refusals |
| `apps/api/retrieval.py` | `search_v13`: parameterised read-only SQL, original text only, no per-event dedup. The old `search` is unchanged. |
| `apps/api/assistant.py` | `_answer_v13`, used only when the active contract carries prompt v1.3. Refusals never reach the model or the identity pre-flight. |
| `apps/api/model_identity.py` | Fingerprint covers `lexicon_version` and `relevance_version`; offline evaluation admits `pending_human_review` |
| `apps/api/model_approvals.json` | Append-only: new approval `assistant_extractive_v1.3-…` with events `proposed` → `pending_human_review` |
| `apps/api/Dockerfile` | Copies the two new modules |
| `apps/web-next/app/assistant/Assistant.tsx` | Persian label «در انتظار بازبینی انسانی» |
| `tests/monitoring/test_assistant_v13.py` (new) | 31 offline tests |
| `scripts/assistant_v13_gate.py`, `assistant_v13_dryrun.py`, `assistant_v13_verify_citations.py` (new) | Model gate, dry run, citation check |
| v1.2 module `assistant_extractive.py` | Unchanged (its sentence and behaviour are preserved) |

## 2. Modules completed

All parts of the brief's step 2 are implemented and wired into the API path:
- question type;
- retrieval;
- per-record relevance;
- same-event proof;
- verbatim selection;
- validation;
- deterministic answer;
- refusal.

The path stays inactive because the contract is not approved.

## 3. Problems found and fixed

1. **Root cause of the v1.2 relevance failures.** Retrieval kept one record
   per event, so comparison questions never saw a second source.
2. **Cluster IDs are not proof.** A real lexical cluster mixes two
   different Typhoon/RAF stories. The verifier now requires the cluster,
   ≤ 72 h, a shared event type, ≥ 2 shared distinctive entities and no
   place conflict.
3. **Persian questions with English originals.** The lexicon resolves
   anchors. Unknown terms are refused and named, never ignored.
4. **A mention in a body made a clear question ambiguous.** Fixed with the
   primary-event rule.
5. **Unverified related articles.** Excluded from the answer and disclosed
   (count).
6. **Number conflicts depended on the model's choice of quote.** For money
   questions they are now checked on the full original text.
7. **Same-outlet duplicate storage** is now counted as one report.
8. **A capitalised first letter** failed an otherwise verbatim quote. A
   narrow repair was added; any other difference still fails closed.
9. **Phase-3 real questions Q1, Q4 and Q5** are now refused as out of
   contract before retrieval. In v1.2, Q4 produced irrelevant quotes.

## 4. Tests and real results

| Suite | Result |
|---|---|
| v1.3 unit tests | 31/31 |
| Local-AI offline tests | 107/107 |
| Full offline suite (image build) | 514/514 |
| Synthetic model gate | 14/14 |
| Real-DB model gate | 19/19 (final run; the first run was 18/19 → item 8 above) |
| Citation check | 36/36 quotes verbatim against the original DB text; source, date and URL match |
| Browser QA on 3003 (4 viewports) | 29/29: console 0, failed requests 0, overflow 0, browser requests to Ollama or cloud AI 0 |

Machine results and the human review are kept separate. **No human review
has been done.** The AI pre-review is labelled as such.

## 5. Sample answers

See *Example answers* in the evaluation document:
- R02: correct comparison;
- R03: correct refusal;
- R09: weak quote;
- R12: over-refusal;
- R17: phase-3 failure now refused.

## 6. Coverage and refusal rate (real DB)

- Overall: 10/19 answered, 9/19 refused.
- In-contract questions: 10/15 answered; 4 correct refusals; 1
  over-refusal (R12).
- 0 wrong answers, 0 irrelevant records accepted, 0 fabricated quotes.

## 7. Remaining weaknesses

- **Recall depends on the event clusterer.** Same-event articles it misses
  are excluded (R12 refused; F/A-XX and Saudi answers omit related records,
  with disclosure).
- **Quote quality.** The model sometimes quotes only a title (R05), only
  one of two sources (R07), or a side detail (R09). Answers are correct but
  thin.
- **The lexicon is finite** (v1.0.0, built from the corpus). Names outside
  it must be written in Latin script, or the question is refused and the
  term named.
- **Question wording.** «چرا…» is always out of contract, including "what
  reported cause"; users must ask «علت گزارش‌شده…».
- **Old UI content.**
  - The 3003 suggestion chips still offer out-of-contract questions
    («مهم‌ترین اخبار امروز چیست؟»).
  - The saved phase-3 QA session still shows the revoked v1.2 answer
    (browser-local history).
- **Prompt injection** is tested synthetically only; no real record contains
  one, and the DB was not altered.

## 8. Assistant v1.3

**`PENDING_HUMAN_REVIEW`.** Every technical and model gate passed, and the
AI pre-review found no critical error. Approval requires the human checklist
in the evaluation document. If every row is confirmed, an append-only
`approved` event activates it on 3003 only. Otherwise the status reverts to
`BLOCKED_MODEL_QUALITY`.

## 9. Translation

**`BLOCKED_MODEL_QUALITY`, unchanged.** Per the brief for this session,
there were:
- no new model downloads;
- no translation runs;
- no batch jobs.

`docs/LOCAL TRANSLATION MODEL COMPARISON.md` from the original phase-4
brief was not produced: no translation evaluation took place.

## 10. Production and OpenCTI

- All 18 non-local-AI containers have the same IDs before and after
  (`runtime/local-ai-evidence/phase4/prod-{before,after}.txt`).
- 3001, 3003 and 8080 return 200.
- **Isolated DB counts identical to the baseline:**
  - news 2,146; translations 89; translation history 16;
  - events 63 / 138 members;
  - sessions 11, messages 21: the gate stored nothing.
- **Ollama:** 15 entries, unchanged; no model loaded at the end.
- **Images:** only the isolated `iran-monitor-local-ai-api:dev` and
  `-web:dev` images were rebuilt.
  - Rollback image IDs are in `runtime/local-ai-evidence/phase4/*-image-before.txt`
    (api `5f112e22…`, web `8d8253fb…`).
  - Roll back with `docker tag <id> <tag>`, then
    `docker compose … up -d --no-deps ai-api ai-web`.
- No external AI request was made.

## 11. Next technical step

1. **Owner or reviewer:** complete the human checklist. Approve, or record
   the failing rows.
2. Align the 3003 suggestion chips with the v1.3 intents.
3. Improve recall without weakening proof:
   - a second clustering pass limited to ≤ 72 h and the same event type,
     whose output is still checked by the verifier;
   - grow the lexicon from real refused terms (`unresolved_terms`).
4. Quote quality: ask for one sentence per member, and prefer a body
   sentence over the title for `specific_record`.
5. Translation remains a separate decision, requiring candidate models,
   download authorisation and a fixed test set.

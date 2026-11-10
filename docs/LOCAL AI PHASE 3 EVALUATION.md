# Local AI Phase 3 — translategemma:12b and the extractive assistant (2026-10-08)

**Final status: `BLOCKED_MODEL_QUALITY`.**

| Area | Outcome |
|---|---|
| Translation (`translategemma:12b`) | Rejected at the quality gate |
| Extractive assistant (`qwen3:8b`, role `assistant_extractive`) | Passed the synthetic gate (v1.1, then v1.2). Approval revoked twice after reviewing real questions. |

Both features stay disabled on 3003.

Production (3001), OpenCTI (8080), earlier models, archives and data are
unchanged; the only data changes are in the isolated local-AI DB (see below).
No scheduler was enabled and no external AI request was made.

## Baseline (before any action)

| Item | Value |
|---|---|
| Branch | `feature/local-gemma-translation-assistant` @ `f840157`, clean worktree |
| Ports | 3001 / 3003 / 8080 → 200 |
| Ollama | 0.40.1, 14 model entries, 31 blobs |
| RAM | 63.7 GB total, 43.6 GB free |
| Disk | C: 615 GB free, E: 899 GB free |
| Isolated DB | 2,146 news items, 89 translations, 12 history rows, 6 local `available` translations, 0 X posts |

## A. translategemma:12b

### Availability, pull and identity

| Item | Value |
|---|---|
| Registry metadata (read only) | gemma3 family, 12.2B, Q4_K_M, GGUF, 8,109,827,612 B, Gemma Terms of Use. Estimated RAM ≈ 10–11 GB, against 43.6 GB free. |
| Pull | Exactly once, 11:25:49–11:37:50 local, success, no retry. 3 blobs added, 0 removed. |
| Requested tag / registry manifest | `translategemma:12b` / `c2f9a9ca1ec7149f2422581c89937ab0363d9399d9355514d753ee012e99c252` |
| First load | The runner loaded the pulled blob `1b2b95e2f0eb9a98…`. Ollama then converted the model. |
| Executed artifact (after conversion) | llamacpp manifest `3189e9a01b8ad4d4e6a9ed4ef09a60e57e9b5335cd5f98c024ebc409b4f1d0d0` (+ ggml entry `d5af4780…`); model `164105f10a913ee4…`, mmproj `7fd02408fa83c142…` |
| Runner / mode | `llama-server.exe` (llamacpp), CPU only (`size_vram=0`). Attestation passed, stable after reload. |
| Contracts | `translategemma-12b-c2f9a9ca1ec7` (proposed → superseded); `translategemma-12b-ollama0401-llamacpp-3189e9a01b8a` (proposed → **rejected_quality_gate**) |
| Resources during the gate | Latency avg 5.4 s, max 10.6 s per field. Total CPU peak 57 %, runner 34 %. Runner RSS peak 8.9 GB. |

### Gate

The gate ran with glossary v1.1.0 (adds strike, depot, company and person
names) and validator v2.1.0 (whole-word glossary matching). It covered 35
fixtures, which include the 8 permanent gemma4 regressions, plus 16 invalid
outputs. I reviewed every output by hand.

| Check | Result |
|---|---|
| Invalid outputs rejected | 16/16 |
| Commentary / debris / empty-summary fabrication | 0 / 0 / 0 |
| Acronyms, URL, mention, hashtag, coordinates, codes | preserved |
| Validator `available` | 21/35 |

Real errors found in the human review:

- **Factual additions:** invented roles ("US Defense Secretary", "Israeli
  war minister"); "organization" before @IntelCrab; "station" in a time
  sentence.
- **Critical terminology:** "live-fire" rendered as "simulated"; "brigade"
  rendered as "battalion" (twice).
- **Numbers and dates:**
  - dates replaced by bracketed placeholder text;
  - all numbers and AH-64E dropped from a summary;
  - "[currency]" inserted;
  - a stray "b" left in "2.75 b";
  - "96 Apache" rendered as "Apache model 96".
- **Names:** "Rheinmetall CEO" garbled.

False positives in my own validator, which do not change the verdict:

- A Persian comma directly after a term was treated as a letter
  (navy, Izium, Reuters, F-35A).
- The ordinal "3rd" (rendered «سوم») was counted as a missing number.

Both are to be fixed in the next validator version.

## B. Extractive assistant (`assistant_extractive`, qwen3:8b, no re-download)

### Design

The model only returns a fact table of `{evidence_id, verbatim quote}`
(prompt `assistant-extractive-fa-v1.0.0`, temperature 0, thinking off,
≤ 384 output tokens). Everything else is done by code:

1. **Verbatim check.** Every quote must occur exactly in that record. A
   fabricated or altered quote, or an unknown id, empties the whole table
   (fail closed).
2. **Unsafe quotes dropped.** Quotes containing instructions or links are
   removed.
3. **Code builds the Persian answer.** It is composed from the table as
   source, date, «quote», [n]. Nothing the model writes appears in the
   answer except the quotes.
4. **No evidence.** The answer is exactly «بر اساس اطلاعات موجود، پاسخ
   قابل اتکا نیست.»

### Gate (synthetic, 17 model fixtures + 5 deterministic)

| Version | Result |
|---|---|
| v1.0.0 | 17/17 + 5/5 automatically. Human review found two defects in my composer: a misleading generated note ("the figures differ") when they did not, and a duplicated syndicated quote. Superseded. |
| v1.1.0 | 17/17 + 5/5. Human review clean: Baltic, Monday, north and two events exact; injection and Cyrillic filtered. **Approved.** |
| v1.2.0 | Same gate, 17/17 + 5/5, clean. **Approved.** |

### Real questions (5, through the 3003 API)

**v1.1 run.** Retrieval used stored machine translations as evidence. These
came from the Oct 7 gemma smoke and an earlier pilot. One of them carried a
known factual addition («نامزد», "candidate"), and the composer labelled
these quotes as verbatim source text. → **v1.1 revoked.**

**Fix (v1.2).** The extractive mode uses original-language evidence only;
stored translations are never evidence.

**v1.2 run.**

| Q | Result |
|---|---|
| Q1 (24 h) | Correctly no evidence (the isolated DB snapshot is from Oct 7) |
| Q2 (coverage) | Correctly declined |
| Q5 (uncertainty) | Correctly declined |
| Q3 ("sources on a common event") | Quoted 3 **unrelated** records |
| Q4 ("narrative difference") | Quoted one source plus an unrelated record |

7/7 citations matched the DB on record, title, source, date, URL and
verbatim quote, and no fact, number, place or URL was fabricated. But 2 of
5 answers fail human review on relevance. → **v1.2 revoked.**

Latency per real question: 13–56 s. Peak RAM: qwen3 runner ≈ 6.2 GB.

## C. UI and QA (3003)

- **New endpoint** `GET /api/v1/local-ai/models`: every contract with its
  state, whether the artifact is present in Ollama, and which features are
  enabled.
- **`/assistant`:**
  - a Persian model-status panel (تأییدشده / پیشنهادشده / ردشده در آزمون
    کیفیت / جایگزین‌شده / تأیید لغو شد / در Ollama موجود نیست);
  - a distinct disabled state ("no approved model") with the input and
    send button disabled;
  - extractive answers rendered one cited quote per line.
- **Translation tags:** more precise labels for processing, stale, failed
  and not-required, and «ترجمه ماشینی محلی» for local output.
- **Tablet header overflow** (7 px at 820 px) fixed.
- **Data (isolated DB only):** two stored translations from the Oct 7 smoke
  with human-found meaning errors (items `c1544afc…` and `ffad1b2f…`, title
  and summary) are now `needs_review`, with append-only history rows. They
  are no longer shown publicly.
- **Browser QA** (`tests/ui/local-ai-qa.cjs`, 1920 / 1440 / 820 / 390):
  **29/29**. Console errors 0, unexpected failed requests 0, horizontal
  overflow 0, browser requests to Ollama or cloud AI 0. Justified reading
  text was verified, while headings and buttons are not justified.

## Tests

124 offline tests pass, covering:

- identity and contracts;
- TranslateGemma placeholders and glossary;
- the gemma4 regressions;
- the assistant validators;
- the extractive validator, composer and original-text-only evidence;
- the X translation tests.

The image build runs the full offline suite.

## What would be needed next (owner decision)

- **Translation:** no local model tested so far meets the bar.
- **Assistant:** the extractive mechanism is safe (no fabrication). What
  failed is relevance for broad analytical questions. Options:
  - restrict it to answerable question types;
  - add a deterministic relevance gate (for example, require a shared
    event_id for "common event" questions);
  - or accept "decline" for analytical questions.

  Each option is a new contract version and needs a new gate.

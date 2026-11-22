# Translation and Summary Quality Policy

## What is generated, and the rule behind each

| Field | Length | Rule |
| --- | --- | --- |
| Title translation | 1 sentence | Exact — preserve every name, number, date, unit |
| Body translation | Full text | Exact — preserve every name, number, date, unit, and the source's own hedging |
| News summary | 2-4 Persian sentences | Facts present in the source only; empty output (`{"text": ""}`) instead of inventing content when the source doesn't support a summary |
| Executive summary | 1 Persian sentence | The single most important fact only |
| Why it matters | 1 Persian sentence | Only implications the source itself states or directly supports — never speculation about broader significance |
| Key points | ≤5, Persian | Every point must carry a verbatim evidence span copied from the source; fewer (or zero) points returned rather than a weakly-supported one invented to fill the list |

All six prompts (`apps/api/ai_gateway.py`'s `PROMPTS` registry) explicitly
instruct: never add, remove, or explain; keep the source's own uncertainty;
return only the specified JSON shape.

## Independent validation (`content_validator.py`)

The Gateway's own schema check only proves the output is *shaped* correctly
(right JSON keys, right types) — it says nothing about whether the content
is actually a faithful translation. `content_validator.py` is a second,
independent layer that never trusts the Gateway's "available" status at
face value:

- **Number/date preservation** — every number and percentage in the source
  must appear in the output (Persian-Indic digits normalized to Latin
  first, so a correctly preserved number is never flagged just because of
  its digit script; trailing sentence punctuation is stripped so a number
  followed by a comma in English and by nothing in Persian doesn't register
  as "different").
- **Distinctive code preservation** — alphanumeric model/unit designators
  (F-35, S-400) are checked verbatim. Bare acronyms (NATO, IAEA) are
  deliberately **not** checked this way, because they are routinely and
  *correctly* transliterated into Persian script (ناتو, …) rather than kept
  verbatim — a real defect found while building this: the "good" reference
  translation used in the test suite itself failed a naive acronym check
  until this distinction was made.
- **Negation-loss detection** — if the source contains a negation word
  (not/never/denied/…) and the Persian output contains no corresponding
  negation marker, the meaning may have flipped from denial to confirmation
  or vice versa.
- **Placeholder / echo / empty-output detection** — `TODO`, `[insert
  translation]`, `{{...}}`-shaped text, an empty string, or the English
  source echoed back verbatim are all hard failures (`passed=False`), never
  silently accepted.
- **Length-ratio bounds** — a translation wildly shorter than the source is
  probably truncated; wildly longer probably contains invented content. A
  summary is checked against inverted bounds (expected to be *much*
  shorter) and is not penalized for the numbers/codes it correctly omits by
  design.
- **Evidence-span verification for key points** — a point's cited evidence
  must be a real, whitespace/case-insensitive substring of the source text.
  A fabricated citation is caught and the point is never published (only
  logged in the audit trail) — see the fault-injection test
  `test_extract_key_points_rejects_fabricated_evidence`.

23 fault-injection tests (`tests/monitoring/test_content_validator.py`) each
start from a realistic passing translation and inject exactly one defect,
proving the validator catches that specific class of fault rather than just
accepting good input.

## Quality score and flags

`quality_score` (0.0-1.0) is a simple, explainable penalty function: 1.0
minus 0.12 per non-hard-fail flag, floored at 0 for any hard failure (empty
output, placeholder text, non-Persian output, source echo). It is not a
claim of translation accuracy — no deterministic rule can measure that — it
is a mechanical defect count, exactly as honest as the checks that produce
it.

## What happens on failure

A translation that fails validation is never silently discarded and never
silently published:

- `review_status` becomes `needs_review` (not `pending_review`) so it
  surfaces at the top of the human review queue by default.
- The original source text remains visible regardless — the UI never hides
  the English original behind a failed translation.
- Nothing is auto-rejected: a human decides, via `/review/content`.

## Rerun and idempotency

Every generation checks `input_text_sha256` before calling the Gateway — if
the source text hasn't changed and the existing row already succeeded, the
call is skipped (`unchanged_skip`). A `human_reviewed` row is never
regenerated automatically, regardless of input changes — only the explicit
`regenerate` review action can touch it, and only after clearing that flag.

# Translation Quality and Review — Stage B addendum

This document records the pilot-specific rules Stage B added on top of the
general policy already documented in
`docs/TRANSLATION AND SUMMARY QUALITY.md` (validator internals, quality
score, failure handling) and `docs/HUMAN REVIEW WORKFLOW.md` (review states,
actions, audit trail). It does not repeat those — read them first. This
file exists because Stage B's brief specified a narrower content contract
than the general Content Intelligence design, and that narrowing needed to
be written down precisely, not left implicit in code.

## What's narrower in this pilot than in the general system

| | General system (Content Intelligence phase) | Stage B pilot |
| --- | --- | --- |
| `summary` field source | Full extracted body if available, else the feed summary — an AI-composed 2–4 sentence summary either way (`ci.summarize_news`) | **The source's own summary field only.** A literal translation (`ci.translate_to_persian`), never AI-composed, never from body text |
| Body translation | In scope (`enrichment_worker.process_translation` translates `body` when extracted text is available) | **Out of scope.** Never processed this pilot |
| `executive_summary_fa` / `key_points_fa` | In scope, both derived from body/summary text | **Out of scope this pilot** — both require body-length input as their evidence source, which the pilot's content contract excludes |
| Worker | Either `translate_worker.py` or `enrichment_worker.process_translation` | **`translate_worker.py` only**, with the `summary`-field fix described in `docs/TRANSLATION PILOT REPORT.md` §2 |

**Why the distinction matters**: `translated_summary_fa` and `original_summary`
are named as a translation pair — a faithful Persian rendering of a real
field, immutable in the sense that its meaning must not drift from the
source. An AI-composed summary is a different, legitimate capability (fully
supported elsewhere in this project, per `docs/CONTENT INTELLIGENCE
ARCHITECTURE.md`), but calling it `translated_summary_fa` would misrepresent
what it actually is. Stage B's explicit rule — "ترجمه با خلاصه‌سازی مخلوط
نشود" — is a naming-integrity rule, not a preference, and this file exists
so that distinction survives whoever next touches this code.

## `source_summary_missing`

A new status value, used only by `translate_worker.py`'s `summary` field
handling: recorded when `original_summary` is empty or absent for a
candidate item. No Gateway call is made to produce this status — it is set
directly, deterministically, with zero cost and zero risk of inventing
content. Displayed in the UI via `FieldStatus` (label: "خلاصه منبع موجود
نیست", muted tone) — added to `apps/web-next/app/design/ui.tsx`'s
`FIELD_LABEL`/`FIELD_TONE` maps this stage.

## `review_status` naming — no new enum value added

Stage B's brief describes the default post-publish state as
`machine_published_pending_review`. This is the same state the existing
system already calls `pending_review` (per `docs/HUMAN REVIEW WORKFLOW.md`:
"Generated and passed `content_validator` — awaiting a human look, not yet
shown as final" — immediately visible with the machine-translation badge,
not gated). Renaming the stored enum value across every existing row, every
UI status map, and every API filter for a purely cosmetic label change was
judged not worth the churn; this document records the equivalence explicitly
so it is traceable rather than silently reinterpreted by whoever reads the
brief next. If the client specifically wants the longer name to appear
verbatim in the UI or API, that is a one-line label change
(`FIELD_LABEL.pending_review`), not a schema change.

## Validator behavior — unchanged, re-verified

`content_validator.py` was not modified this stage. Its 23 fault-injection
tests (numbers, dates, codes, negation, placeholder/echo/empty detection,
length ratio, evidence-span verification) still pass unchanged, and remain
the independent quality gate for whatever real output Stage B eventually
produces once a provider key is supplied. No validator in this project ever
passes output on length alone — length-ratio bounds are one signal among
many, never the sole basis for a pass.

## What is still not proven

Every claim in `docs/TRANSLATION AND SUMMARY QUALITY.md` about the
*validator's* correctness is proven (fault-injection tests). No claim about
real translation quality on real Iran Monitor content is proven yet: the
Stage B-OR pilot (via OpenRouter, `anthropic/claude-haiku-4.5`) made exactly
one real call, which failed at the provider with `insufficient_credits`
before producing any text — see `docs/TRANSLATION PILOT REPORT.md`. This
document will be updated with the 5-sample manual evaluation (fidelity,
readability, number preservation, entity preservation, unsupported-claim
check, final verdict per sample) the moment real output exists.

## Fatal-error stop logic (Stage B-OR addition)

`translate_worker.py` now stops processing the remaining candidates
immediately — rather than continuing through the rest of a ≤20-item batch —
on any of: `authentication_failed`, `insufficient_credits`,
`provider_forbidden`, `budget_exceeded`, `request_invalid` (e.g. an
unknown model slug), an open circuit breaker, or a >10% failure rate once
at least 3 calls have been attempted. The rationale: each of these is a
*structural* condition that will fail identically on every subsequent item
— continuing would just spend the rest of the daily budget window
re-discovering the same fact 19 more times. This is deliberately more
aggressive than ordinary per-item error handling; it never triggers on an
isolated, non-repeating failure.

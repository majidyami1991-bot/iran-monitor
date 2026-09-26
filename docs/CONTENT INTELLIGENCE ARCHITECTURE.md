# Content Intelligence — Architecture

A commercial, auditable pipeline for Persian translation, summarization, and
key-point extraction, built entirely on the AI Gateway (`docs/AI GATEWAY.md`)
so that activating a real provider later is an environment change, not a
code change.

## Layers

```
enrichment_worker.py (process_translation)
  │  translate_worker.py (CLI, --dry-run / --limit)
  ▼
content_intelligence.py   — orchestration: detect_language, translate_to_persian,
                              summarize_news, generate_executive_summary,
                              generate_why_it_matters, extract_key_points
  ▼
ai_gateway.py             — provider-agnostic: modes, adapters, prompts,
                              schemas, circuit breaker, budget, cache, audit log
  ▼
content_validator.py      — independent of the Gateway: number/date/code
                              preservation, negation-loss, placeholder/echo/
                              empty-output detection, evidence-span verification
```

`content_validator.py` is deliberately a peer of `ai_gateway.py`, not a
sub-component — a provider could theoretically bypass the Gateway (it can't,
today, because nothing does) and the validator would still catch a bad
output, because it only ever looks at the *text*, never at how it was
produced.

## Data model

### What already existed and is reused, never duplicated

Per the brief's own rule ("از تغییر یا حذف داده‌های اصلی خبر جلوگیری کن"),
the following requested fields are **not** new columns — they already exist
and stay untouched:

| Brief's field | Actual source |
| --- | --- |
| `original_title` | `news_items.title` |
| `original_language` | `news_item_content.original_language`, falling back to `news_items.content_language` |
| `original_summary` | `news_items.summary_text` / `summary` |
| `original_content_excerpt` | `news_item_content.original_text` (first 2000 chars, via the API) |

`GET /api/v1/news/{id}/content-intelligence` reads these live and returns
them alongside the generated fields — the API's job is to present a unified
view, not to fork the data.

### What's new (additive, in `apps/api/ops.py`'s `DDL`)

- `news_item_translations` gains: `prompt_version`, `quality_score`,
  `quality_flags` (jsonb), `review_status`, `reviewed_by`, `reviewed_at`,
  `superseded_at`. All nullable or defaulted — a pre-existing INSERT that
  knows nothing about them still works unchanged (verified live, see the QA
  report).
- `news_item_translation_history` (new table): **append-only**. Every
  generation attempt — success or failure — is inserted here and never
  updated or deleted. Re-running a task increments `content_version` and
  inserts a new row; the "current" row in `news_item_translations` is
  updated in place for fast reads, but the full lineage survives in history
  regardless. This is what "خروجی قدیمی را overwrite مخرب نکن" means in
  practice: the fast-read pointer can change, the record of what it used to
  say cannot be destroyed.
- `content_key_points` (new table): one row per extracted key point, each
  carrying its own `evidence_span`, an `evidence_verified` boolean (set only
  after `content_validator.validate_key_point` confirms the span is a real
  substring of the source text), and its own `content_version` /
  `superseded_at` for the same non-destructive versioning.

### Field mapping for the brief's remaining requested names

| Brief's field | Where it lives |
| --- | --- |
| `translated_title_fa` / `translated_content_fa` | `news_item_translations` rows, `field='title'` / `field='body'` |
| `translated_summary_fa` | `field='summary'` (2-4 sentence prompt) |
| `executive_summary_fa` | `field='executive_summary'` (same task_type/schema as summary, prompt_version `executive-1.0.0`) |
| `key_points_fa` | `content_key_points` table |
| `translation_status` / `summary_status` | `status` column per relevant field row (no separate rollup column — reading the right row's `status` *is* the field's status) |
| `translation_provider` / `translation_model` | `provider` / `model` columns (shared column name across all fields; "translation" in the brief's naming, not a separate column) |
| `translation_prompt_version` / `summary_prompt_version` | `prompt_version` column (again shared — which field you're reading tells you which prompt it is) |
| `translation_input_hash` / `summary_input_hash` | `input_text_sha256` (pre-existing column, reused) |
| `quality_score`, `quality_flags`, `review_status`, `reviewed_by`, `reviewed_at`, `superseded_at` | New columns, as above |

## Why "why_it_matters" and "executive_summary" share a task type

Both are a single Persian sentence with an identical output schema
(`{"text": str}`) — the only difference is the prompt. Rather than invent two
new AI Gateway task types for what is structurally one thing, they're two
prompt versions (`executive-1.0.0`, `why-it-matters-1.0.0`) of the existing
`summary` task type. `key_point_extraction` *is* a genuinely new task type
(`{"points": [...]}`, a different shape) — see `docs/AI GATEWAY.md`.

## Verified live (not just unit-tested)

- Migration applied against production with the item-set hash unchanged
  before/after (`170d4a79...`, 1008 items).
- An old-shape `INSERT` (the exact column list used before this phase)
  still succeeds against the migrated schema — rollback safety, proven, not
  assumed.
- A full synthetic smoke test (fake adapter, throwaway test item, deleted
  afterward) proved translation → validation → history write → current-row
  upsert → key-point extraction → evidence verification → publish all work
  together end-to-end against the real database.
- The full human-review workflow (queue → edit → approve → reject →
  regenerate) exercised against a synthetic item via the real HTTP API,
  including confirming `regenerate` honestly returns
  `provider_not_configured` and writes nothing when no provider is active.

## What this phase does not include

Per the brief's explicit closing instruction, entity/event extraction beyond
what already exists (Phase 3's clustering), trend detection, weak-signal
detection, scenarios, and early warning are **not** started this phase.

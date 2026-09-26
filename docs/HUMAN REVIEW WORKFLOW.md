# Human Review Workflow

`/review/content` in the UI, backed by `GET /api/v1/review/content` and the
four `POST /api/v1/review/content/{item_id}/{action}` endpoints.

## Review states

| `review_status` | Meaning |
| --- | --- |
| `not_applicable` | No AI-generated content exists for this field yet (row absent, or the field was never generated) |
| `pending_review` | Generated and passed `content_validator` — awaiting a human look, not yet shown as final |
| `needs_review` | Generated but **failed** `content_validator` — flagged, prioritized in the default queue view |
| `approved` | A human confirmed it (or wrote it directly via edit) |
| `rejected` | A human explicitly rejected it, with a reason |

No status here means "safe to show as the organization's confirmed
content" except `approved` — the UI's machine-translation badge is present
on every other state, including `pending_review`.

## Actions

- **Approve** (`POST .../approve?field=...&reviewed_by=...`) — sets
  `review_status=approved`, records who and when, and sets
  `human_reviewed=true` so no future automatic regeneration can silently
  overwrite this decision.
- **Reject** (`.../reject?field=...&reviewed_by=...&reason=...`) — sets
  `review_status=rejected`, appends the reason to `quality_flags`, and also
  locks `human_reviewed=true` — a rejected field stays rejected until a
  human explicitly asks for regeneration, it is never silently retried by
  the routine enrichment pipeline.
- **Edit** (`.../edit?field=...&reviewed_by=...&text=...`) — writes the
  human's own text as the new current version (`provider='human'`,
  `model=NULL`), inserts a history row for it first (never skipping the
  audit trail just because a human wrote it), and marks it `approved`
  immediately — a human edit is definitionally already reviewed.
- **Regenerate** (`.../regenerate?field=...`) — clears `human_reviewed` for
  that one field, then attempts a fresh generation immediately. If no real
  AI provider is configured, it returns `status=provider_not_configured`
  and **writes nothing** — verified live: this is not a documented
  intention, it's the actual, tested behavior of the endpoint today, since
  no provider is configured in this environment.

## What a reviewer sees

The queue (left) lists every field row matching the selected status filter:
title, quality score, provider/model, and a flag-count badge. Selecting a
row (right) shows: the current review status, the full list of quality
flags with their reasons (hovering a flag badge shows the exact reason
string from `content_validator`), the original English text/excerpt for
reference, the current Persian text in an editable box, and the four action
buttons.

## Audit trail

Every write goes through `news_item_translation_history` — nothing is ever
deleted. `reviewed_by`, `reviewed_at`, and the `provider`/`model` on the
current row together answer "who last touched this, and was it a human or a
model" without needing to consult history for the common case; the history
table answers "what did every previous version actually say" when that's
needed.

## What's intentionally not built this phase

- **Authentication / roles** — `reviewed_by` is currently a free-text field
  supplied by the caller (the UI hardcodes a placeholder reviewer name).
  There is no login system yet in this project, so a real per-user identity
  and permission model is out of scope here — this workflow proves the
  state machine and audit trail work, not identity management.
- **Bulk actions** — one field at a time, matching the granularity of
  `news_item_translations` itself (title/body/summary/executive_summary/
  why_it_matters are reviewed independently, since a translation and its
  summary can have completely different quality outcomes).

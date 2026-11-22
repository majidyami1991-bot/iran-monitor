# Translation Operations Runbook

How to run, monitor, and safely widen the title+summary translation pilot,
and what to do if something goes wrong. Written after Stage B (which halted
at `BLOCKED_PROVIDER_NOT_CONFIGURED` — see `docs/TRANSLATION PILOT REPORT.md`)
so the next operator has a direct runbook instead of re-deriving one.

## 1. Preconditions

- `docs/AI PROVIDER CONFIGURATION.md` steps 1–6 complete: `AI_PROVIDER` set
  to an approved provider (`anthropic` or `openrouter` — see
  `docs/OPENROUTER PROVIDER ADAPTER.md` for the latter's specifics), a real
  `AI_API_KEY`, `AI_MODEL_TRANSLATION`/`AI_MODEL_SUMMARY` set to a model in
  `ai_gateway.APPROVED_MODELS`, in `E:\Iran monitor\.env` (gitignored —
  never paste the key anywhere else, never verify its presence with
  `grep`/`Get-Content`/`docker inspect`/`docker compose config` — only via
  `GET /api/v1/ai/provider-status`'s `api_key_configured` boolean; see
  `docs/INCIDENT - API KEY EXPOSURE IN SESSION OUTPUT.md`).
- `deployment/news-monitor/compose.yml` passes `AI_*` through to `news-api`
  and `news-translate` (fixed in Stage B — verify this wiring is still
  present if compose.yml is edited again later).
- `news-api` rebuilt/redeployed so the container process actually sees the
  new env vars (`docker compose ... up -d --build news-api`). `news-translate`'s
  image must also be rebuilt (it shares the Dockerfile but is a *separate*
  image compose builds independently) — but never `up -d`'d as a running
  service; it only ever runs via `docker compose run --rm`.
- For a deterministic, reviewed candidate set rather than "whatever's
  newest," pass `--manifest <path to a {"items":[{"item_id":...}]} JSON
  file>` — capped at 20 items for a pilot; `translate_worker.py` refuses a
  larger one outright.

## 2. Verify configuration (no provider call yet)

```
GET /api/v1/ai/status
```
Confirm `mode: "external_provider"`, `provider: "anthropic"`,
`api_key_configured: true`. This proves configuration, **not**
connectivity — do not skip step 3.

## 3. Dry run (0 provider calls, 0 database writes)

```
docker compose ... run --rm news-translate python /app/translate_worker.py --limit 20 --fields title,summary --dry-run
```
Confirm `provider_configured: true` and inspect `candidates`/`items`
before proceeding. If `provider_configured` is still `false` here, stop —
something in step 1 is incomplete; do not proceed to a real run to "test"
whether the key works.

## 4. The single pilot invocation

Per the pilot's own explicit rule, run this **once**:

```
docker compose ... run --rm news-translate python /app/translate_worker.py --limit 20 --fields title,summary
```

Do not pass `--fields title,summary,body` for a pilot — `body` pulls the
full extracted article through the same field-dispatch table, which is out
of the title+summary pilot's scope (see
`docs/TRANSLATION QUALITY AND REVIEW.md` for why `summary` and `body` are
handled by different, non-interchangeable code paths).

Watch for:
- `errors` in the JSON report > 10% of `processed` → stop widening,
  investigate before any further run (per the pilot's explicit failure-rate
  rule). Do **not** retry failed items automatically beyond the Gateway's
  own single transient-error retry.
- `skipped_no_source_text` — expected for items whose source never had a
  real summary (`source_summary_missing`); not an error.

## 5. Check cost and review queue

```
GET /api/v1/ai/usage
GET /api/v1/review/content?status=pending_review
```
Every successful, validation-passing translation lands in
`review_status=pending_review` and is already visible in the UI with its
machine-translation label — publishing is immediate per this project's
translation policy (`docs/PROJECT ARCHITECTURE AND TRANSLATION PLAN.md` §4),
not gated behind the review queue. The queue is for ongoing quality control,
not a pre-publish approval step. A failed-validation translation instead
lands in `needs_review` and is never shown as the item's current Persian
text.

## 6. Widening beyond the pilot

Not authorized by Stage B. Widening requires:
1. The pilot's 5-sample manual evaluation actually completed (blocked this
   round on there being no real output — see the pilot report).
2. A new, explicit approval, exactly as this project's pattern has required
   for every prior expansion (Stage A → Stage B was itself gated this way).
3. `AI_DAILY_BUDGET_LIMIT` set to a real number before any unattended or
   larger-batch run — running with no budget configured is acceptable for a
   single, human-watched, ≤20-item invocation; it is not acceptable for
   anything larger or scheduled.

## 7. Rolling back

No schema change accompanies this capability (Stage B made no migration).
To disable translation entirely again: set `AI_PROVIDER=disabled` (or blank)
in `.env` and redeploy `news-api`/`news-translate` — every code path
immediately returns `provider_not_configured` again, matching
`docs/AI GATEWAY.md`'s documented `disabled` mode guarantees. No data needs
to be deleted; existing `available` translations remain visible (they are
real, already-validated output, not deleted just because the provider was
turned off again).

## 8. What never changes in this workflow

- `news-collector` and its 900-second RSS schedule — translation is a
  separate, always-manually-invoked process (`profiles: [tools]` in
  compose), never auto-triggered by collection.
- `original_title`/`original_summary` — read, never written, by any part of
  this pipeline.
- The append-only `news_item_translation_history` — every attempt, success
  or failure, is recorded there and never deleted.

# 20-Item Content Enrichment Pilot — Report

Manifest: `config/content-pilot/manifest-v1.json` (20 items, 12 distinct
sources, selected deterministically — see `scripts/select_content_pilot.py`).
All results below are read directly from the production database after the
pilot's final verified run; reviewable live at `/news/{item_id}` and
`/events` in the production UI.

## Extraction

| Metric | Value |
| --- | --- |
| Items with usable body text | 20 / 20 |
| Source of that text | RSS `content:encoded` or feed description for all 20 — the RSS-first policy meant the bounded HTTP article-fetch path was not needed for this specific 20-item selection |
| Average / min / max text length | 3,523 / 81 / 14,526 characters |

## Translation

All 20 items × 4 fields (title, summary, long_summary, body) = 80 rows,
status `pending` for every one — honest, because `NEWS_TRANSLATION_API_KEY`
is intentionally unset (Stage 1 decision, credential pending from the
client). No Persian text was fabricated anywhere.

## Media

| Metric | Value |
| --- | --- |
| Images verified | 31 |
| Images rejected | 1 |
| Documents verified | 0 |
| Documents rejected | 2 |
| Items with ≥1 verified image | 9 / 20 |

Every rejection carries a real reason (failed size/format check or blocked
MIME/extension); nothing was substituted.

## Classification (taxonomy v2.0.0)

| Category | Items |
| --- | --- |
| دفاعی و امنیتی (defense_security) | 15 |
| سیاست خارجی (foreign_policy) | 3 |
| سایر (other, fallback) | 2 |

Average confidence 0.71 (min 0.0 for the two fallback items, max 0.95).
20 / 20 items classified — 0 left unprocessed.

## Event clustering

1 event identified: the two Neriya Leiter articles (same terror-attack
victim, two different Israeli-press angles on the same day). All 18 other
items correctly remained singletons, including one item that shares only
generic words ("IDF", "terror") with a Leiter article and one that shares
only generic words ("netanyahu", "reporter") with the other — both correctly
excluded after the fixes documented in `docs/EVENT CLUSTERING ALGORITHM.md`.

`FALSE_CLUSTER_COUNT = 0` in the final, verified state (two false merges were
found and fixed during the pilot's execution — see the algorithm doc and the
rollback guide's "known defects" section — this is the corrected result, not
the first attempt).

## Idempotency (second full pass)

All 5 stages were re-run end-to-end over the same 20 items. Per-table row
counts for pilot items were identical before and after:

| Table | Before | After |
| --- | --- | --- |
| news_item_content | 20 | 20 |
| news_item_translations | 80 | 80 |
| news_item_media | 34 | 34 |
| item_classifications | 20 | 20 |
| news_event_members (pilot items) | 2 | 2 |

`SECOND_RUN_DUPLICATES = 0`.

## Human correction persistence

One item was manually corrected via `PATCH
/api/v1/news/{item_id}/classification`, then a direct re-run of
`process_classification` on that item returned `skipped_human_locked` —
confirming the correction is rerun-persistent. The item was reverted to its
computed classification afterward (this was a verification step, not an
intended data change).

## Collection isolation

`news-collector` was never restarted during this phase. Item count grew
normally from its own 15-minute schedule throughout (804 → 807 across the
work in this session), confirming RSS collection was unaffected by every
enrichment build/redeploy/rerun.

## Known limitations of this pilot (honest, not fixed — out of scope)

- Only 12 of the project's sources are represented (the 20-item selection
  drew from the currently-active source set; the other ~50 configured sources
  were not exercised by this pilot).
- Translation cannot be end-to-end verified until a real API key is supplied;
  the pipeline is built, tested with a fake provider, and the summarization
  word-budget/quality-flag logic is unit-tested, but no real Persian output
  exists yet to spot-check.
- Event clustering was calibrated and fixed against exactly one true-positive
  case found in this 20-item set; a larger pilot would be needed to find
  further edge cases the way the netanyahu/reporter case was found here.

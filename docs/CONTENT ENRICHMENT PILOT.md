# Content Enrichment Pilot — Design, Policy, and Results

Status: pilot complete for 20 real news items, reviewable in the production UI at
`/news/{item_id}` (fields: content, translation, media, classification, event
coverage) and `/events`. Not full-archive or full-62-source processing — an
explicitly scoped pilot per the commissioning brief.

## 1. Scope

20 real items were selected deterministically from the live database (12 of the
project's active sources, no randomness, no wall-clock dependency — see
`scripts/select_content_pilot.py` and the committed manifest
`config/content-pilot/manifest-v1.json`). The manifest records only identifiers,
selection reasons and a hash of title+summary — never restricted full article
text — so it is safe to keep in git.

## 2. Architecture

```
news_items (existing, RSS collection — untouched by this phase)
    │
    ▼
enrichment_jobs  ──►  enrichment_worker.py  ──►  news_item_content
  (queue table)         (5 stages)               news_item_translations
                                                   news_item_media
                                                   item_classifications
                                                   news_events / news_event_members
```

**Queue** (`enrichment_jobs`, `apps/api/ops.py` DDL): one row per (item, stage).
Claimed with `FOR UPDATE SKIP LOCKED` so multiple workers never double-process a
job. Failures retry with backoff (30s, 180s, 900s) up to 3 attempts, then move to
`dead_letter` — never silently dropped. RSS collection (the `news-collector`
container) shares no code path with this queue and was never touched or
restarted by any enrichment run in this phase; it stayed up continuously
throughout (42h+ uptime verified during the pilot, item count grew normally from
its own schedule, unaffected by enrichment failures by construction).

**Stages** (`apps/api/enrichment_worker.py`):

1. **extraction** — `process_extraction`. Policy order: if the item's stored RSS
   payload already contains usable body text (`content:encoded` or a rich
   `description`), that text is used directly and **no HTTP request is made**.
   Only when RSS provides nothing does it fall through to a single bounded
   article-page fetch (`article_extract.py`, SSRF-guarded via `net_guard.py`,
   max 1 request per item). In this pilot's final 20-item selection, all 20 had
   sufficient RSS-embedded content, so the HTTP path was not exercised in the
   pilot's recorded run — the RSS-first policy worked exactly as designed. The
   HTTP extraction path was still built, hardened, and unit-tested against real
   article pages (see §4) because most future items will need it.
2. **media** — `process_media` / `_verify_one_image` / `_verify_one_document`.
   Every image/document URL discovered during extraction starts `unverified`;
   this stage downloads (SSRF-guarded, size-capped) and verifies it — real
   pixel dimensions from parsed image headers, real MIME/magic-byte checks for
   documents — before it can ever be marked `verified`.
3. **translation** — `process_translation`. See §5.
4. **classification** — `process_classification`. See §6 /
   `docs/CLASSIFICATION TAXONOMY V2.md`.
5. **clustering** — `process_clustering`, run once over the full pilot batch
   (not per-item queued). See `docs/EVENT CLUSTERING ALGORITHM.md`.

**Idempotency**: every write uses a deterministic key and `ON CONFLICT`
upsert — `news_item_content` by `item_id`, `news_item_translations` by
`(item_id, field, target_language)`, `news_item_media` by
`sha256(item_id|url)`, `item_classifications` by `item_id`, `news_events` by
`sha256(sorted member ids)[:24]`. A second full pass over the same 20 items was
run end-to-end (extraction → media → translation → classification →
clustering) and produced **zero new rows in any table** — see §7.

**Human correction**: `PATCH /api/v1/news/{item_id}/classification` sets
`human_locked = true`; every write path in `process_classification` and
`process_clustering`-adjacent code checks this flag and skips the item, so a
correction survives any future re-run (verified live, §7).

## 3. Translation and Summary Policy

See `apps/api/translate.py`. No provider is configured by default
(`NEWS_TRANSLATION_PROVIDER=anthropic`, `NEWS_TRANSLATION_MODEL=claude-sonnet-5`
are set, but `NEWS_TRANSLATION_API_KEY` is deliberately empty pending the
client's own credential, per the Phase 1 decision). Every translation/summary
request without a working provider returns `status: "pending"` — never
fabricated text. In the current pilot state, all 20×4 translation fields
(title, summary, long_summary, body) are honestly `pending`.

Fields:
- **title / body** — full translation, fidelity-first prompt (`TRANSLATE_SYSTEM`):
  preserve every name, number, date, unit exactly; no addition, no speculation.
- **summary** (40–70 Persian words) and **long_summary** (120–220 words) — separate
  prompts (`SHORT_SUMMARY_SYSTEM` / `LONG_SUMMARY_SYSTEM`) that require
  attributing claims to whoever the source says made them and forbid inferring
  background not in the source text.
- **Idempotency**: `input_text_sha256` is stored with every result; unchanged
  input is skipped on rerun (`field:unchanged_skip` in the worker's return).
- **Quality flag**: `quality_status` is `suspect` when output is wildly outside
  its word budget (< 40% or > 180% of target) — a mechanical sanity check, not
  a claim of translation accuracy.
- **Human review**: a `human_reviewed` flag (not yet exposed via API in this
  phase) protects a manually-approved translation from being overwritten.

## 4. Media and Document Policy

See `apps/api/image_verify.py`, `apps/api/document_verify.py`,
`apps/api/article_extract.py`, `apps/api/net_guard.py`.

- **Discovery**: only images/documents found in the item's own RSS enclosure or
  extracted article body — never generated, never substituted, never fetched
  from an unrelated search.
- **Fetch policy**: SSRF-guarded (`net_guard.guarded_get`/`guarded_head` —
  resolves DNS, validates the IP is not private/loopback/link-local/reserved
  *before* connecting, re-validates on every redirect hop, connects to the
  pre-validated IP directly to defeat DNS rebinding). Max 8MB for images, 40MB
  for documents. Never bypasses a login wall, CAPTCHA, or paywall — a 403 is
  recorded as `rejected` with the real reason, never retried with different
  headers to work around it.
- **Image verification**: pure-Python PNG/JPEG/GIF/WEBP header parsing (no
  Pillow dependency added). Rejected if the bytes don't parse as a known image
  format, or if the real parsed dimensions are below 200×200
  (`MIN_DIMENSION`). In the pilot: 31 images verified, 1 rejected (too small or
  unparseable), 2 documents rejected (blocked extension or failed magic-byte
  check), 0 documents verified.
- **Document verification**: extension blocklist checked before any request
  (`.exe`, `.dll`, `.bat`, `.js`, `.docm`, `.jar`, `.apk`, …), MIME allowlist,
  magic-byte confirmation (`%PDF-` for PDF; zip-container prefix for
  docx/xlsx/pptx). Never executed, never macro-processed. `security_status` is
  stored per document (`downloaded_safe`, `link_only`, or a rejection reason).
- **When in doubt, don't show**: any candidate that fails verification is
  recorded with `verification_status: 'rejected'` and a `rejection_reason`; it
  is never silently promoted to a displayed image just because nothing else was
  found.

## 5. Classification

See `docs/CLASSIFICATION TAXONOMY V2.md` for the full taxonomy and the
confidence formula. Summary: pilot classified 20/20 items — 15
`defense_security`, 3 `foreign_policy`, 2 `other` (fallback, no keyword
evidence) — average confidence 0.71 (min 0.0 for the two fallback items, max
0.95). `taxonomy_version` is tracked per item so a v1-only backfill (the
original single-label classifier, still running for the other ~785 items not
in this pilot) can never silently downgrade a v2-classified item — this was a
real defect found and fixed during this phase (see `docs/CONTENT ENRICHMENT ROLLBACK.md`
§"Known defects found and fixed").

## 6. Event Clustering

See `docs/EVENT CLUSTERING ALGORITHM.md`. Result: 1 event identified in the
20-item pilot, correctly grouping the 2 items that are genuinely the same
story (two Israeli-press items about the same terror-attack victim, Neriya
Leiter). The other 18 items correctly remained singletons — no false merges in
the final, verified state.

## 7. Verification Performed

- **Offline test suite**: 165 tests passing (`docker build` test stage is a hard
  gate — the image cannot be built if any test fails).
- **Second full pass, same 20 items**: re-ran all 5 stages end-to-end.
  Per-table row counts for the 20 pilot items were identical before and after
  (`news_item_content` 20, `news_item_translations` 80, `news_item_media` 34,
  `item_classifications` 20, `news_event_members` for pilot items 2) —
  **zero duplicate rows created**.
- **Human-correction persistence**: `PATCH .../classification` on a test item,
  then a direct re-run of `process_classification` on that same item returned
  `skipped_human_locked` — confirmed the correction was not overwritten. The
  test item was reverted to its computed classification afterward so no test
  pollution was left in production data.
- **Collector/scheduler isolation**: the `news-collector` container was never
  restarted during this phase; item count grew from its own 15-minute schedule
  throughout (804 → 807 over the course of this work), unaffected by every
  enrichment rebuild/redeploy/rerun.
- **Live data only**: every fix in this phase (article-extraction chrome
  detection, entity-extraction boilerplate contamination, a classification/topic
  category-agreement dependency, a startup-migration data-clobber bug) was found
  by running the pilot against real production data and inspecting real rows —
  never assumed from a synthetic fixture alone. Each fix has a regression test
  reproducing the real failure (see `tests/monitoring/test_clustering.py`).

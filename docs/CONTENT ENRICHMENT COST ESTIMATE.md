# Content Enrichment — Full-Scale Cost Estimate

Estimates only, from measured pilot volume and assumed token ratios — not a
quotation. Builds on the baseline already established in
`docs/STAGE 1 CONTENT QUALITY.md` (measured 12-source feed: 30–55 new items/day,
≈1,800/month) and cross-checks against it below.

## What actually costs money

Only **translation and summarization** call a paid LLM provider. Extraction
(RSS-first, falls back to a bounded page fetch), media verification (pure
image-header parsing / MIME+magic-byte checks), classification, and event
clustering are all deterministic Python with **zero marginal API cost** — they
scale with server compute and bandwidth only, not per-item billing.

## Scope flag — read before enabling a provider

`enrichment_worker.process_translation` requests **all four** translation
fields per item: `title`, `summary` (40–70 words), `long_summary` (120–220
words), and `body` (full text). This is broader than the scope the client
approved in Stage 1 ("Persian title + short summary only," ≈$4–9/month at the
12-source baseline). **Before supplying a real `NEWS_TRANSLATION_API_KEY`**,
decide whether to keep all four fields or narrow `fields` in
`process_translation` to match the approved scope — the cost difference is
roughly 6–7x (see below). No cost has been incurred either way: the pilot ran
entirely with `NEWS_TRANSLATION_PROVIDER` unconfigured, so every translation
field is honestly `pending` in the current data.

## Per-item token estimate (measured from the 20-item pilot)

Average extracted body length: 3,523 characters (≈880 tokens), min 81, max
14,526. At Claude Sonnet 5 rates ($2 / $10 per million input / output tokens):

| Field | Input (incl. ~150-token system prompt) | Output | Cost/item |
| --- | --- | --- | --- |
| title | ~40 tokens | ~20 tokens | ~$0.0003 |
| summary (short) | ~1,030 tokens | ~80 tokens | ~$0.0029 |
| long_summary | ~1,030 tokens | ~250 tokens | ~$0.0046 |
| body | ~1,030 tokens (avg; capped at 12,000 chars/~3,000 tokens for outliers) | ~970 tokens | ~$0.0118 |
| **All 4 fields** | | | **≈$0.019/item** |
| **Title + short summary only** (Stage 1 approved scope) | | | **≈$0.003/item** |

## Monthly estimate

| Scope | 12 sources (current, measured 1,800 items/mo) | 62 sources (extrapolated) |
| --- | --- | --- |
| Title + short summary only | $5–9 | $26–47 |
| All 4 fields (current worker default) | $30–40 | $155–210 |

The 12-source "title + short summary only" figure ($5–9) lands inside Stage
1's own independently-derived $4–9 estimate — a useful cross-check that this
phase's token assumptions are reasonable.

**62-source extrapolation caveat**: scales the 12-source per-item volume
linearly (62/12 ≈ 5.17x). The 12 currently-active sources were not
necessarily chosen for average publication volume, so real per-source rates
at the other 50 sources may differ meaningfully in either direction — treat
the 62-source column as an order-of-magnitude planning figure, not a
commitment, until a real multi-source volume measurement exists.

## Cost levers (from Stage 1, still valid)

- **Model choice**: Claude Haiku 4.5 ($1/$5 per million tokens) instead of
  Sonnet 5 ($2/$10) roughly halves every figure above.
- **Batch processing**: not latency-sensitive work; batch APIs typically halve
  cost again.
- **Narrowing scope**: title + short summary only vs. all 4 fields is the
  single largest lever (~6–7x), independent of model choice.

## One-time backfill

Applying the same enrichment (translation only — classification/clustering/
media are free) to the ~785 items already collected outside this 20-item
pilot, at the "all 4 fields" per-item rate: ≈785 × $0.019 ≈ **$15 one-time**,
or ≈785 × $0.003 ≈ **$2.40 one-time** at the approved title+summary-only
scope.

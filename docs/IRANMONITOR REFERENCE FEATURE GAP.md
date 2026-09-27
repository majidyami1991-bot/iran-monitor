# IranMonitor.org Reference — Feature Gap Matrix

Stage A deliverable for the "IRAN MONITOR COMMERCIAL INTELLIGENCE EXPERIENCE"
phase. Branch `feature/iran-monitor-foresight-platform`. No production
mutation, no external API call, no new RSS collection, no real translation
was performed to produce this document — analysis and decisions only.

## Method and an honest access note

**Direct browsing of `iranmonitor.org` was attempted and blocked by the
site's own bot protection — this was not bypassed, per this project's
standing collection policy (never bypass 403/robots/paywall).**

Two independent attempts, both blocked identically:
1. A real headless browser session (Edge via CDP, the same tooling used for
   this project's own Playwright QA) navigating to `/`, `/fa`: HTTP 403, page
   title "Just a moment...", body text "Performing security verification...
   Verification successful. Waiting for www.iranmonitor.org to respond" —
   Cloudflare Managed Challenge, never resolves headlessly.
2. Direct HTTP fetches of `/robots.txt` and `/sitemap.xml` (normally
   crawler-accessible by convention): both returned the same Cloudflare
   challenge page with `<meta name="robots" content="noindex,nofollow">`.

No page content, markup, copy, imagery, or asset was retrieved from the
reference site. This document's analysis is therefore built from **the
feature list the brief itself specifies** (verbatim page/component names in
the brief's own §3) plus general, publicly-known conventions of how
OSINT/crisis-monitoring products implement each feature category, evaluated
strictly against **this project's actual data, legal footing, and
architecture**. This approach independently satisfies the brief's own
warning not to copy the reference's design, text, brand, images, icons, or
code — there was nothing to copy even if that had been intended, and the
matrix below is a capability/value/feasibility judgment, not a visual
description.

## Decision legend

- **Implement** — build for real, this program, backed by real data already
  in this system (or trivially derivable from it).
- **Scaffold** — build the schema/API/UI shell and an honest
  "infrastructure ready / data not connected" state; no fabricated numbers,
  charts, or points.
- **Defer** — real value, but blocked on a licensing, legal, or
  third-party-access decision that must be made explicitly, later, by the
  client — not silently skipped, not silently built around.
- **Reject** — not aligned with Iran Monitor's organizational-intelligence
  mission, or the data cannot be obtained honestly at all.

## Matrix

### 1. صفحه اصلی (Homepage / Command view)
- **Value**: single entry point answering "what happened, what changed, what
  needs attention" — the core promise of a monitoring product.
- **Data available**: yes — `news_items`, `news_events`, `item_classifications`,
  `collection_runs`, `sources` all live and queryable today.
- **Decision: Implement.** Redesigned per brief §5 in Stage C, on top of the
  existing dashboard.
- **Risk**: none beyond ordinary UI risk.
- **API**: existing `/api/v1/stats/*`, `/api/v1/news`, `/api/v1/events`, new
  `/api/v1/stats/brief` (already exists), plus additions in
  `docs/COMMERCIAL PLATFORM DATA AND API CONTRACTS.md`.
- **Empty/loading/error**: `Skeleton`/`EmptyState`/`ErrorState` already exist
  as shared components; reused, not rebuilt.

### 2. نسخه فارسی (Persian version)
- **Value**: the product is already Persian-first end to end (RTL, Vazirmatn,
  Persian numerals, Persian labels) — this is not a separate version to
  build, it is the product's default state, unlike a reference site that
  apparently maintains English as primary and Persian as a secondary path.
- **Decision: Implement (already true).** No gap. Noted explicitly so this
  is not mistaken for missing work.

### 3. Daily Briefing
- **Value**: high — a five-minute daily read is exactly what a manager or
  analyst wants instead of scrolling a feed.
- **Data available**: partially. Per-item `executive_summary`/`why_it_matters`
  exist (Content Intelligence phase) but nothing aggregates them into a
  single day's rollup yet, and no real AI provider is configured, so no
  per-item executive summary has actually been generated in production.
- **Decision: Scaffold this phase; Implement once (a) a provider is
  configured per `docs/AI PROVIDER CONFIGURATION.md` and (b) enough
  approved, human-reviewed executive summaries exist for a given day to
  compose a real rollup.** Never synthesize a briefing from unreviewed or
  absent AI output — the brief's own rule 5/6 (`provider_not_configured`,
  no fake briefing) applies directly here.
- **Risk**: none if built as specified; the risk is entirely in *not*
  gating this behind real, reviewed data.
- **API**: new `GET /api/v1/brief/daily` (contract in the data/API doc).

### 4. Breaking News
- **Value**: high — surfaces what's urgent without the reader scanning
  everything.
- **Data available**: partially. There is no `importance`/`severity` column
  anywhere today. A defensible, non-fabricated signal *does* exist,
  though: `news_events.source_count` (how many independent sources are
  covering the same event) combined with recency — multiple independent
  corroborating sources in a short window is a real, explainable signal,
  not an invented one.
- **Decision: Scaffold the UI (`BreakingBar` per §5-b) now; Implement the
  underlying rule (corroboration + recency threshold, fully explainable,
  same deterministic-rule discipline as `clustering.py`) as part of Stage C**,
  once event clustering has run over more than the 20-item pilot (see
  entry 6 below — this item is gated on that one).
- **Risk**: a naive "most recent" or "most sources" ranking with no
  explanation would look like manufactured urgency; must always show *why*
  an item is flagged (source count, corroboration), matching the brief's
  explicit requirement in §5-b ("سطح اهمیت", "وضعیت تأیید").

### 5. Latest Headlines
- **Value**: table stakes for a news product.
- **Data available**: yes, fully — this is today's `/news`.
- **Decision: Implement** (redesign only, not new data plumbing).

### 6. Events Timeline
- **Value**: high — lets an analyst see a story develop across multiple
  articles/sources instead of re-reading duplicates.
- **Data available**: the schema and a working, tested, deterministic
  clustering algorithm already exist (`news_events`, `news_event_members`,
  `apps/api/clustering.py`, documented in
  `docs/EVENT CLUSTERING ALGORITHM.md`) — but it has only ever been run on a
  20-item pilot. Live count today: **1 event, 2 members**, out of 1,015
  items.
- **Decision: Implement the timeline UI on the existing schema/API
  (`/api/v1/events`, `/api/v1/events/{id}` already exist); Scaffold the
  "populated at scale" expectation** — running clustering over the full
  corpus is a separate, explicit decision (compute cost and false-cluster
  risk both scale with corpus size; the algorithm's own doc records three
  real false-clustering bugs found and fixed during the pilot). That
  full-corpus run is proposed for Stage D, not this stage, and not silently
  bundled into a UI redesign.
- **Risk**: none to data integrity if scoped as above; the risk being
  managed is presenting an almost-empty timeline as if it were complete —
  the honest state ("رویداد‌یابی روی ۱۰۱۵ خبر هنوز اجرا نشده") must be shown
  rather than hidden.

### 7. Activity Metrics
- **Value**: operational transparency — expected of any monitoring product.
- **Data available**: yes, fully (`collection_runs`, `stats/timeline`,
  `stats/overview`, already displayed on `/monitoring` and `/analytics`).
- **Decision: Implement** (visual upgrade only per brief §17, e.g. baseline/
  anomaly banding — no new data source needed).

### 8. Commodity Prices
- **Value**: relevant context for an Iran-focused product (oil, currency,
  sanctioned-goods pricing) but entirely outside this system's current
  scope and data.
- **Data available**: no. Would require a paid or licensed external feed.
- **Decision: Defer.** Registered in the Integration Registry (brief §15)
  as `enabled=false`, `status=not_configured`, with the licensing question
  explicitly left to the client — never scraped or estimated.
- **Risk**: licensing/ToS risk of any commodity-data provider not
  contracted; financial data accuracy liability if ever shown without a
  licensed source.

### 9. Live Tweets / categorized X feeds
- **Value**: real-time social signal is valuable to an analyst, but X's API
  terms and cost are a real gate.
- **Data available**: no API access or permission today.
- **Decision: Defer**, exactly as brief §13 specifies: build the account
  **registry** (categories: media/journalist/official body/researcher/etc.)
  and show `connector_not_configured` — never a live pull, never a sample
  post.
- **Risk**: ToS violation if scraped instead of using the official API;
  reputational risk of displaying a stale or fabricated "sample" feed.

### 10. Source Profiles / Source Directory
- **Value**: high — an analyst needs to judge a claim partly by knowing the
  source.
- **Data available**: substantially yes today — `/sources` already shows
  health, item counts, coverage tier, success rate (see
  `docs/UI UX QA REPORT.md`, item M4/H-fixes). Missing: country, ownership,
  and bias/methodology fields — correctly absent today rather than guessed.
- **Decision: Implement** the upgrade to a full "Source Intelligence
  Directory" (brief §10) using existing fields; for country/ownership/bias,
  **display "ارزیابی‌نشده" (not yet assessed) explicitly** rather than
  inventing a rating — this matches the brief's own explicit instruction
  and this project's `feedback-verify-never-fabricate` standing rule.
- **Risk**: reputational/legal risk of asserting a source's ownership or
  bias without a documented, defensible methodology — the reason this is
  gated on "only with evidence."

### 11. Conflict Map
### 14. Protest/Event Map
*(grouped — see decision)*
- **Value**: high for a defense/security-focused product, if built honestly.
- **Data available**: **no.** No table in this system carries a validated
  event location. There is no geocoding pipeline, no lat/lon column
  anywhere in `news_items`, `news_events`, or `news_item_media` today.
- **Decision: Scaffold only, and consolidate into one page.** The brief's
  own information architecture (§4) specifies a single "نقشه رصد" nav item,
  not two separate map features — building the reference's "Conflict Map"
  and "Protest/Event Map" as two distinct pages would duplicate one
  capability and contradict the IA the brief itself asks for. One `/map`
  page, with a news/event toggle, is the correct scope; anything else is
  scope creep against the brief's own §4.
- **Risk (why this cannot be "Implement" yet)**: the brief explicitly
  prohibits "geocoding حدسی" and "تولید نقاط تصادفی برای زیبایی." Building a
  populated map today would require either inventing coordinates (forbidden
  outright) or standing up a real geolocation-extraction pipeline with its
  own provenance and confidence fields — a genuinely new capability, not a
  redesign, and out of Stage A/C scope. Schema and API contract are
  specified in `docs/COMMERCIAL PLATFORM DATA AND API CONTRACTS.md`; the UI
  ships with a correct, honest "no geolocated events yet" empty state.

### 12. AI Chat → "AI Analyst"
- **Value**: high leverage if done safely; high risk if not (hallucinated
  claims presented as fact, prompt injection from ingested news text).
- **Data available**: yes, as a retrieval corpus (news_items, events,
  classifications) — but no real AI provider is configured, and building a
  citation-grounded, injection-resistant analyst is a substantial safety
  effort (brief §16: must refuse to answer beyond evidence, must cite,
  must distinguish fact from inference, must neutralize prompt injection
  embedded in ingested article text, must be audited).
- **Decision: Scaffold this phase (UI shell + API contract, disabled
  state); Defer the real provider-backed implementation to its own
  dedicated, separately-approved phase** — consistent with the brief's own
  §16 instruction that "اجرای provider واقعی فقط با مجوز جداگانه انجام شود."
- **Risk**: hallucinated claims attributed to real sources is a serious
  credibility and potentially legal risk for an organizational-intelligence
  product; prompt injection from adversarial article text is a real,
  demonstrated attack class against RAG-style systems.

### 13. Live TV
- **Value**: real-time broadcast monitoring has genuine analyst value.
- **Data available**: no licensed stream access; embedding or proxying a
  broadcaster's live stream without explicit rights is a real legal
  exposure (copyright, terms of service), independent of technical
  feasibility.
- **Decision: Defer.** Per brief §14, only a legally licensed embed/URL may
  ever be used; until one exists, show `integration_not_configured`. No
  stream is proxied, no video is archived, ever, without that license.
- **Risk**: copyright/ToS violation; potential liability for redistributing
  a live news broadcast without permission.

### 15. Search and filtering
- **Value**: essential for a working analyst tool at any real item volume.
- **Data available**: yes, mostly — search/source/category/window/sort/
  translation/image/document filters already exist and work
  (`/api/v1/news`). Missing: location filter (blocked on entry 11/14's
  gap), language filter (data exists — `content_language` — not yet
  exposed as a filter), importance/severity filter (blocked on entry 4).
- **Decision: Implement** what the data supports now (adding a language
  filter is real, low-risk, immediate); **Scaffold** the location and
  importance filters as disabled controls until their underlying data
  exists, rather than wiring them to nothing.

### 16. About / Methodology / Privacy / Transparency
- **Value**: high trust value for an organizational client, low technical
  risk, and — importantly — this is where the honesty commitments already
  built into this system (taxonomy version, clustering algorithm,
  translation policy, machine-translation labeling, human review workflow)
  become visible and verifiable to the end user, not just to us internally.
- **Data available**: yes — every claim this page would make is already
  documented in this repo (`docs/CLASSIFICATION TAXONOMY V2.md`,
  `docs/EVENT CLUSTERING ALGORITHM.md`, `docs/TRANSLATION AND SUMMARY
  QUALITY.md`, `docs/HUMAN REVIEW WORKFLOW.md`).
- **Decision: Implement.** Extends the existing `/about` page (already
  built per `docs/UI UX QA REPORT.md`) with methodology, privacy, and data-
  retention sections drawn from real, already-true policy — not aspirational
  copy.
- **Risk**: none — the risk here runs the other way: *not* publishing an
  honest methodology page is itself a transparency gap for a product whose
  whole value proposition is credibility.

### Not observed, and explicitly out of scope regardless
The brief itself flags that features unrelated to an organizational
intelligence mission — e.g. donation or memorial pages, which are common on
some advocacy-oriented monitoring sites — must not be imitated just because
a reference product has them. No such feature is proposed anywhere in this
plan. **Decision: Reject**, categorically, independent of whether the
reference site has anything like it (which could not be confirmed given the
access block above).

## Summary table

| # | Feature | Decision | Gate before Implement |
| --- | --- | --- | --- |
| 1 | Command view (homepage) | Implement | — |
| 2 | Persian version | Implement (already true) | — |
| 3 | Daily Briefing | Scaffold → Implement | Real AI provider + reviewed data |
| 4 | Breaking News | Scaffold → Implement | Full-corpus event clustering |
| 5 | Latest Headlines | Implement | — |
| 6 | Events Timeline | Implement (UI) / Scaffold (scale) | Full-corpus clustering run |
| 7 | Activity Metrics | Implement | — |
| 8 | Commodity Prices | Defer | Client-approved licensed data source |
| 9 | Live Tweets / X feeds | Defer | X API access + permission |
| 10 | Source Directory | Implement | — (bias/ownership stay "ارزیابی‌نشده") |
| 11 | Conflict Map | Scaffold | Real geolocation-extraction pipeline |
| 12 | AI Analyst | Scaffold | Separate approval + safety build |
| 13 | Live TV | Defer | Licensed stream/embed rights |
| 14 | Protest/Event Map | Merged into #11 | — |
| 15 | Search/filtering | Implement (partial) / Scaffold (rest) | Location/importance data |
| 16 | About/Methodology/Privacy | Implement | — |
| — | Donation/memorial-style features | Reject | — |

REFERENCE_PAGES_REVIEWED: 0 (blocked by target's bot protection; see Method
note) — analysis instead grounded in the brief's own enumerated feature list.
REFERENCE_FEATURE_COUNT: 16 (15 brief-listed + the explicitly-rejected
donation/memorial category).
FEATURES_IMPLEMENTED (classified, not yet built): 7
FEATURES_SCAFFOLDED: 5
FEATURES_DEFERRED: 3
FEATURES_REJECTED: 1

# Data → UI Capability Matrix

Inventory taken on 2026-09-28 from the live PostgreSQL database (17 tables
before the redesign). Counts are from the baseline and the final run.

| UI capability | Tables / fields | API | Status | Decision |
|---|---|---|---|---|
| Latest news, filters, sorts | `news_items`, `sources`, `item_topic_assignments` | `/feed` | Real data (1,168 → 1,186 items) | **Implement** |
| Importance and breaking | Derived from event corroboration, category, confidence, publisher flag | `/breaking`, `/feed?sort=important` | Rules `importance_v1`, `breaking_v1` | **Implement** |
| Persian title and summary | `news_item_translations` (81 rows, 0 `available`) | `/feed`, `/news/{id}` | Pipeline built; provider blocked (HTTP 402, no credit) | **Implement with honest pending state** |
| Bilingual detail | `news_items`, `news_item_content` | `/news/{id}` | Real | **Implement** |
| Article images | `news_item_media` (215 `article_image`, 7 verified) | `/feed`, `/news/{id}` | Real, mostly unverified; served from the publisher with credit | **Implement** |
| Documents | `news_item_media` (36 documents) | `/news/{id}` | Real; linked, never auto-downloaded | **Implement** |
| Provenance | `news_item_provenance`, `news_items.provenance_status` (100% COMPLETE) | `/news/{id}` | Real | **Implement** |
| Topics taxonomy v3 | New `item_topic_assignments`, `item_topic_assignment_history` | `/topics` | Migration 2026.09.28-01 | **Extend** |
| Events timeline | `news_events`, `news_event_members` (+3 columns) | `/timeline/events` | 1 → 30 events (29 from v2) | **Extend** |
| Stories | New `stories` | `/stories` | 10 active | **Extend** |
| Daily briefing | New `daily_briefings` | `/briefing/daily` | Rule-based, append-only | **Extend** |
| AI executive summary | `daily_briefings.executive_summary_fa`, `ai_*` | `/briefing/daily` | Provider unavailable | **Scaffold** (status shown) |
| Source profiles | `sources`, `source_run_results`, `news_items` | `/source-profiles` | Real; country not recorded | **Implement** |
| Activity | `collection_runs`, `news_items`, `news_events` | `/activity` | Real | **Implement** |
| Commodity prices | New empty `commodity_prices` | `/commodities` | No licensed feed | **Scaffold** |
| Social / X | New empty `social_posts`; 36 handles in registry | `/social` | No authorised path | **Scaffold** |
| Map / geolocation | New empty `geo_mentions` | `/geo` | No evidence-backed extraction | **Scaffold** |
| Connectivity, flight/marine | `integrations` only | `/integrations` | Not connected | **Scaffold** |
| Alerts | New empty `alert_rules`; system notifications | `/alerts`, `/notifications` | Notifications real; rules empty | **Implement + Scaffold** |
| Analytics charts | Aggregates of the above | `/insights/overview` | Real | **Implement** |
| Trends, weak signals, data uncertainty, STEEP mapping | Aggregates | `/foresight/*` | Descriptive only | **Implement (descriptive)** |
| Drivers, scenarios, strategic uncertainties | — | `/foresight/*` | Require analyst judgement | **Scaffold (empty)** |
| User menu, per-user notifications | No authentication in this deployment | — | — | **Reject for now** (no auth to attach to) |
| Scraped tweets, estimated prices, guessed coordinates | — | — | Violates policy | **Reject** |

## Derived metrics (final run)

| Metric | Value | Definition |
|---|---|---|
| Other-category share | 23.8% (v2) → 11.3% (v3) | Share of items whose primary category is "other"; every v3 "other" has a reason code |
| Translation coverage | 0.0% | Items with a stored `available` Persian title |
| Provenance completeness | 100.0% | `provenance_status = 'COMPLETE'` |
| Source metadata completeness | 84.5% | Filled share of official name, hostname, type, language, feed URL, site URL, country across 12 sources (country is never filled without evidence) |

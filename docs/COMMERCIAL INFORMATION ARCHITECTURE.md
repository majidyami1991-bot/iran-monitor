# Commercial Information Architecture — Iran Monitor

Stage A deliverable. Defines the target navigation, page-by-page data
bindings, and the component gap against the existing (already commercial-
grade) design system. This is the "mockup / design specification based on
existing data" required by Stage A — a written specification, not new code;
building it is Stage C (Core UI) and Stage D (event/map scaffold).

Read alongside `docs/UI UX DESIGN SYSTEM.md` (the token system and component
library already shipped in the prior UI/UX phase — this document extends it,
it does not replace it) and
`docs/IRANMONITOR REFERENCE FEATURE GAP.md` (the decisions this IA encodes).

## 1. Target navigation (brief §4)

| # | Nav label | Route | Current state | This phase's scope |
| --- | --- | --- | --- | --- |
| 1 | نمای فرماندهی | `/` | Exists (commercial dashboard, per UI UX QA REPORT) | Redesign per §5, Stage C |
| 2 | جریان اخبار | `/news` | Exists | Redesign per §7, Stage C |
| 3 | رویدادها و خط زمانی | `/events` | **New page**, backed by an existing API (`/api/v1/events`) | Build, Stage C/D |
| 4 | موضوعات | `/topics` (or `/categories`) | Exists, richer than the brief's example taxonomy already (see §3 note) | Redesign per §11, Stage C |
| 5 | منابع | `/sources` | Exists | Upgrade to Source Intelligence Directory, Stage C |
| 6 | نقشه رصد | `/map` | **New page, Scaffold only** (no location data — see feature-gap #11/14) | Stage D |
| 7 | تحلیل‌ها | `/analytics` | Exists | Add ChartPanel/DataTable visuals per §17, Stage C |
| 8 | بولتن روزانه | `/brief` | **New page, Scaffold** (see feature-gap #3) | Stage C shell, data gated |
| 9 | اتاق آینده‌نگاری | `/foresight` (+5 subpages) | **New, Scaffold only, zero fabricated data** | Stage E, infra only |
| 10 | بازبینی انسانی | `/review/content` (exists) + `/review/events` (new) | Content review exists (Content Intelligence phase); event review does not | `/review/events` scaffold, Stage D |
| 11 | وضعیت سامانه | `/monitoring` | Exists (built in prior UI/UX phase) | Keep; no change needed |
| 12 | درباره و روش‌شناسی | `/about` | Exists | Extend with methodology/privacy/retention, Stage C |

**Note on item 4**: the brief's example taxonomy (§11) is illustrative; the
system already runs a richer, live multi-level taxonomy
(`config/sources/classification-taxonomy-v2.json`, version **2.1.0**,
verified live — not the 2.0.0/20-item-pilot version described in
`docs/CLASSIFICATION TAXONOMY V2.md`, which is now stale and should be
re-verified against the live config before being cited elsewhere). It
already covers all 1,015 items with 7 top-level categories and per-category
subtopics, multi-label `topics[]`, per-item `confidence`, and a documented,
non-destructive human-lock mechanism. This nav item is a redesign of an
already-substantial system, not new plumbing — see the Stage A baseline
below.

### Foresight sub-navigation (item 9)

| Sub-item | Route | Data today |
| --- | --- | --- |
| روندها | `/foresight/trends` | None — Level 2 capability, out of this phase's scope per the brief's own closing instruction in the Content Intelligence phase and this brief's §1 ("تمرکز اصلی بر سطح اول") |
| سیگنال‌های ضعیف | `/foresight/weak-signals` | None |
| پیشران‌ها | `/foresight/drivers` | None |
| سناریوها | `/foresight/scenarios` | None |
| هشدار زودهنگام | `/foresight/early-warning` | None |

Per brief §4's explicit rule: **each of these five renders only as
"زیرساخت آماده / داده متصل نشده"** (infrastructure ready / data not
connected), documents its future API contract, and shows zero invented
numbers or charts. No code for these subpages does more than that this
phase or the next — Level 2/3 analytical capability is explicitly out of
scope until a separately-approved phase, matching the standing instruction
already given for the Content Intelligence phase.

## 2. Command view (`/`) — content-to-data binding (brief §5)

| Section (brief §5) | Bound to | Status today |
| --- | --- | --- |
| الف) نوار وضعیت سراسری | `/api/v1/collection/status`, `/api/v1/ai/status`, review-queue counts (`/api/v1/review/content`) | All endpoints exist; needs one aggregating call or client-side composition |
| ب) Breaking Intelligence Bar | `news_events.source_count` + recency (see feature-gap #4) | **Gated** — Scaffold with static "0 آیتم فوری شناسایی‌شده" until the corroboration rule ships |
| ج) Daily Intelligence Brief | New `/api/v1/brief/daily` | **Gated** — see feature-gap #3; shows `provider_not_configured` / "بولتن امروز هنوز تولید نشده" honestly, never placeholder text |
| د) KPIها | `/api/v1/stats/overview`, `/api/v1/stats/content`, `/api/v1/review/content` counts | All real today |
| هـ) جریان زنده اخبار | `/api/v1/news` (existing `NewsCard`) | Real today |
| و) خط زمانی رویدادها | `/api/v1/events` | Real today, but near-empty until full-corpus clustering (feature-gap #6) — must show that honestly, not hide the section |
| ز) نمودار فعالیت | `/api/v1/stats/timeline` | Real today; needs baseline/anomaly-band rendering (visual only) |
| ح) پنل منابع فعال | `/api/v1/sources` | Real today |
| ط) پوشش موضوعی | `/api/v1/categories` | Real today (already includes sparkline + previous-period comparison) |
| ی) نقشه کوچک | New, reads the same `/map` data source | **Gated** — see feature-gap #11; renders the map's own "no geolocated events yet" empty state, never a fabricated dot |

## 3. Component gap against the existing design system

`docs/UI UX DESIGN SYSTEM.md` already ships: `Shell` (bundles header +
collapsible sidebar + breadcrumb), `StatusPill`, `Badge`, `Chip`, `Tabs`,
`EmptyState`, `ErrorState`, `StaleNotice`, `Skeleton`, `SourceMark`,
`FieldStatus`, `Pagination`, `NewsCard`, `NewsDetail`. Verified directly
against `apps/web-next/app/design/ui.tsx` and `Shell.tsx` — this list is
current, not from the (partly stale) design-system doc's prose alone.

| Brief §18 component | Exists today? | Plan |
| --- | --- | --- |
| AppShell / CollapsibleSidebar | Yes, inside `Shell` | Keep — splitting it into separate exports is a refactor with no behavior change, low priority |
| CommandHeader | Inside `Shell`, not a separate component | Extract only if the command-view redesign needs header content `Shell` doesn't already support |
| StatusRail | **New** | Build for §5-a |
| BreakingBar | **New** | Build for §5-b, gated per feature-gap #4 |
| IntelligenceBrief | **New** | Build for §5-c, gated per feature-gap #3 |
| KPIGrid | Informal (stat cards exist inline) | Extract as a shared component |
| NewsCard | **Exists** | Reuse as-is |
| EventCard | **New** | Build for the events timeline |
| SourceCard | Informal (`/sources` row + `SourceMark`) | Extract if the directory redesign needs a card, not just a table row |
| TopicChip | `Chip` exists generically | Specialize or reuse directly |
| EvidenceBadge | **New** | Needed for key-point evidence display (partially covered by the plain "شاهد تأییدنشده" text added in the Content Intelligence phase — formalize into a component) |
| ConfidenceIndicator | **New** | `item_classifications.confidence`, `news_events` similarity scores, and content-intelligence `quality_score` all need one shared visual, not three ad hoc renderings |
| TranslationBadge | Informal (`<span className="machine-tag">`) | Extract as a named component |
| HealthBadge | Covered by `StatusPill` | No new component needed |
| FilterBar | Informal (inline in `NewsStream.tsx`) | Extract as a shared component once a second page (events, or the map) needs filtering |
| Timeline | **New** | Build for the events page |
| MapDrawer | **New** | Build for `/map`, Stage D |
| ChartPanel | Informal (ad hoc chart markup per page) | Extract per brief §17's "every chart needs title/description/range/unit/source/updated-at" rule — one component enforces this everywhere instead of per-page discipline |
| DataTable | Informal (ad hoc `<table>` per page) | Extract, with the brief §17 accessibility requirement (data-table fallback for a chart) in mind |
| ReviewDiff | **New** | `/review/content` currently shows current text in an editable box, not a diff against the previous version — see `apps/web-next/app/review/content/ReviewContent.tsx` |

**11 of 22 requested components already exist in some form; 8 are genuinely
new; 3 are informal patterns worth formalizing.** None of this requires a
design-token change — `docs/UI UX DESIGN SYSTEM.md`'s six-state color model,
type scale, and spacing scale already cover every new component's needs
without inventing a seventh status color or a new font size.

## 4. Empty-state policy for not-yet-connected sections

Every "Scaffold" item in this document and the feature-gap matrix follows
one rule, already established and tested in this codebase
(`docs/UI UX DESIGN SYSTEM.md` §"Empty, error and stale states"): **name the
real reason**, never a generic "no data":

- Foresight subpages → "زیرساخت آماده است؛ این بخش هنوز به داده واقعی متصل
  نشده" (infrastructure ready; not yet connected to real data).
- Daily Brief, before a provider is configured → reuses the existing
  `provider_not_configured` status, already implemented in the Content
  Intelligence phase.
- Map, before geolocation exists → "هیچ رویداد دارای مکان تأییدشده یافت
  نشد" (no event with a verified location was found) — never an empty map
  silently rendered as if complete.
- Breaking bar, before the corroboration rule ships → "در حال حاضر رویداد
  فوری تأییدشده‌ای شناسایی نشده" — not hidden entirely (hiding it would
  contradict the brief's own IA), shown with its true, current count of
  zero.

## 5. Stage A baseline (recorded, not changed)

| Metric | Value |
| --- | --- |
| `news_items` | 1,015 |
| `sources` | 12, all `health_status='healthy'` |
| `news_events` / `news_event_members` | 1 / 2 (20-item pilot only) |
| `item_classifications` | 1,015 (100% coverage), taxonomy `2.1.0` |
| Category distribution | security_defense 564, other 243 (24%), politics_geopolitics 119, technology 44, strategic 19, economy_infrastructure 15, social_humanitarian 11 |
| `news_item_translations` | 80 rows, all pre-existing from an earlier phase |
| `content_key_points` | 0 (no real AI provider configured yet) |
| `news_item_media` | 723 rows |
| Docker (`iran-monitor-news-*`) | 4/4 containers healthy |
| OpenCTI (14 containers) | Untouched, running |
| Unrelated projects (`mlw-*`) | Untouched, running |
| Git | Clean at phase start except this phase's own new docs |

No row above was changed to produce this document. The "other" bucket at
24% is a real, live signal worth carrying into Stage C's taxonomy work — not
new information invented for this report.

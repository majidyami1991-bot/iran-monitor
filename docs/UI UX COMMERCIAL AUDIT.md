# UI/UX Commercial Audit — Iran Monitor (before redesign)

Method: the live system at `http://127.0.0.1:3001` was screenshotted full-page at
1920×1080, 1440×900, 1024×768 and 390×844 across dashboard, news stream, news
detail, sources, source detail, topics, analytics/monitoring. Screenshots are
preserved at `runtime/evidence/commercial-ui/before/` (git-ignored). Findings
below come from looking at the rendered pages, not from reading component code.

Severity: **Critical** (breaks the core task or is unusable), **High** (visibly
undermines commercial credibility or a stated requirement), **Medium** (real but
tolerable), **Low** (polish).

## Critical

### C1 — News cards render the full article body inline, not a summary
Every `ItemCard` (used on the dashboard, the news stream, and source detail's
"latest items" list) prints the complete extracted article text unconditionally
when the display policy allows it. The news stream, at 30 items, is
**25,496px tall** on desktop and **42,548px tall** on mobile — individual cards
measured 636–1,176px each. Source detail, reusing the same component, is
**15,420px tall**. A "stream" a user is meant to scan in five seconds instead
requires dozens of screen-heights of scrolling before reaching the filters or
the next section. This is the single most severe defect in the product and the
most direct explanation for "still looks like a technical panel": a real
product distinguishes a list-item summary from a detail-page body. One root
cause (the shared card component), not three separate bugs.

### C2 — Same paragraph of body text appears twice on the news detail page
On `/news/<id>`, the extracted body text is printed once directly under the
image with no label, and again lower on the page under a "متن اصلی (انگلیسی)"
heading — identical text, no visual distinction between the two appearances.
A reader cannot tell why the same paragraph is shown twice.

### C3 — No dedicated monitoring status page exists
The brief and the product both require a standalone operational view of
collector/scheduler health, per-source checkpoints and cycle history. Today
`/analytics` and the intended "وضعیت پایش" destination are the same route; the
operational log is buried at the bottom of the statistics page as a wall of
plain-text lines rather than presented as its own screen.

## High

### H1 — Raw operational log dumped as unstyled text (`/analytics`)
The "عملیات Collector" panel prints ~20 lines like `۸:۴۱:۰۷،۱۴۰۵/۷/۱ - scheduled
- succeeded - درخواست ۱۲ - تازه ۱ - تکراری ۱۷۳ - بروزرسانی نامعتبر ۹۰ - رد شده
۰` as plain paragraphs — no table, no columns, no color coding, English status
words (`scheduled`, `succeeded`) inline in Persian sentences. This single panel
is the clearest embodiment of "looks like a technical panel or a test build."

### H2 — Status badges on the news detail page read as a raw field dump
Four small pills — "عنوان فارسی: در صف پردازش", "خلاصه فارسی: در صف پردازش",
"متن اصلی: فقط خلاصه", "نمایش مجاز: فقط خلاصه" — are laid out as
`field_name: field_value` pairs. The information is honest and correct (per
the no-fabrication rule) but the *presentation* is a debug panel, not a
designed status indicator. A commercial product needs one small, consistent
status affordance per field, not four labelled key/value pills stacked in a
row.

### H3 — Two unrelated visual languages for the same concept
`/` (the dashboard) and `/news`, `/sources`, `/topics`, `/analytics` (the
`monitor.tsx`-driven pages) are two different component systems with
different card shapes, different spacing scales, different chip styles and
different color usage for the same underlying idea (a news item, a status
badge). Nothing about the product tells the user these are the same system.

### H4 — English technical strings surface directly in Persian UI
`"RSSLanguage reported in feed: en-US"`, `"Language reported in feed:
en-US"`, `"succeeded"` (as a literal English word inside a Persian sentence
on the dashboard's "آخرین چرخه" stat and the analytics banner), keyword lists
mixing English tokens (`military`, `security`, `attack`, `drone`) into Persian
topic panels with no visual separation from Persian words. None of this is
fabricated data — it is real feed/classification metadata — but it is
presented as raw values rather than translated or visually demarcated as
"source-reported, verbatim."

### H5 — "نمای پایلوت فعال" (pilot view active) badge on the commercial dashboard
A status pill in the hero section literally tells a business user this is a
pilot. Whatever its origin, it directly contradicts the goal of this phase
(commercial polish) and should not appear on a system being presented to a
client as a product.

### H6 — Warning-colored banner used for a healthy, informational state
The analytics page opens with an amber/warning-styled alert banner
("گردآورنده: زمان‌بندی فعال...") that is reporting good news (scheduler on,
collector healthy). Reserving amber for genuine attention-needed states is a
named requirement; using it for routine status undermines the whole semantic
color system before a user even reaches a real warning.

### H7 — No image caption, attribution or right-of-use indicator
The news detail page's lead image (confirmed to render at full width and
reasonable quality) carries no caption, no photographer/publisher
attribution, and no indication of its (unverified) status — despite
`news_item_media.verification_status` existing precisely to carry this.

### H8 — No breadcrumb, no tabbed content structure on news detail
The brief specifies a breadcrumb and a tabbed body (ترجمه / متن اصلی / تصاویر
و اسناد / منشأ و شواهد). The current page has a single "بازگشت" link and one
long undifferentiated vertical scroll of headed sections.

## Medium

### M1 — Dashboard has no single focal hierarchy
Six-plus widget types (line chart, two donuts, a horizontal-bar source list, a
horizontal-bar topic list, a full daily calendar heatmap, a coverage panel)
compete at equal visual weight immediately below the summary strip. The daily
calendar heatmap in particular (40+ date rows) is an analytics deep-dive
component, not a five-second dashboard summary widget.

### M2 — Filter bar lacks several required filters
The news stream filter bar has search/source/category/window/sort but no
translation-status, has-image or has-document filters, which section 6 of the
brief calls for explicitly.

### M3 — Topics page is a flat ranked list with no time trend or chips
Functionally correct (numbers verified against the API), but visually it is a
plain numbered list with no per-topic trend line, no clickable chip treatment,
and no visual distinction for the dominant "سایر" (other) bucket, which is
currently the single largest category — a data-quality signal the page does
not surface as one.

### M4 — Source rows show no visual identity beyond a text name
No monogram/initial treatment (the dashboard's card component has one; the
sources table does not), making the table correct but visually flat compared
to the requirement for "نشان منبع" (source mark).

### M5 — Text sizing is small and dense across secondary panels
Multiple analytics/dashboard sub-panels sit at 9–12px with tight line-height;
combined with M1's widget count, the page reads as dense instrumentation
rather than an executive summary.

## Low

### L1 — CSS carries a leftover internal phase marker
`globals.css` contains the literal comment `/* Phase 9B: compact, readable
monitoring layout; original styles retained above. */` — invisible to users
but a hygiene signal that the stylesheet is a patched prototype rather than an
authored design system, and a real obstacle to maintaining it going forward.

### L2 — Only six CSS custom properties exist as design tokens
`--bg`, `--panel`, `--edge`, `--text`, `--muted`, `--aqua` — no semantic status
tokens (healthy/fresh/attention/stopped/error/inactive), no spacing scale, no
type scale. Every other color and size in the stylesheet is a hard-coded hex
value or pixel number, so consistency currently depends on habit, not
structure.

### L3 — 1920px layout is capped and centered correctly
Not a defect — noted because it was checked. `main{max-width:1800px}` avoids
the common ultra-wide failure of stretched content; the redesign should keep
this constraint.

## What already works and should be preserved

- RTL and Persian numerals are applied correctly and consistently everywhere
  checked, including mixed-direction handling for English titles/URLs.
- The sources table (`/sources`) is the most commercially credible page as-is:
  clear KPI cards, a real sortable-looking table, honest per-source health
  states, correct number formatting.
- Vazirmatn renders correctly at every viewport tested.
- No horizontal overflow was observed at any of the four tested viewports on
  any page — the layout's grid/flex structure is fundamentally sound even
  where content density is wrong.
- The three-way registered/executable/monitored coverage split (delivered in
  the prior phase) is present and numerically correct on both the dashboard
  and the sources page; it needs a visual upgrade, not a rebuild.
- No fabricated data was found anywhere: every empty/pending state observed
  (translation pending, missing summary, zero recent items) is stated plainly
  and truthfully. The redesign's job is to make these states *look* designed,
  not to change what they say.

## Reference patterns consulted

Principles extracted (no interface or brand copied) from:
- [ground.news design: fonts, colors and UI patterns](https://design.withfudge.com/share/ground.news-design) — dark
  canvas for content consumption, restrained saturated accent pairing reserved
  for meaning (bias/status), not decoration.
- General threat-intelligence dashboard writeups (Recorded Future / Dataminr
  integration and cybersecurity dashboard pattern surveys) — a dedicated
  pipeline/job status screen showing pending/in-progress/complete/failed
  distinct from the descriptive-analytics screen, and prioritizing what needs
  attention over what is merely large.
- VibeFarsi (`https://vibefarsi.ir/`) — confirmed to require Tailwind v4; this
  project is pinned to Tailwind 3.4.17. Per the explicit instruction not to
  upgrade the Tailwind major version without a documented need, VibeFarsi's
  component *patterns* (status chip shapes, RTL-first spacing, Persian-numeral
  handling) inform the new design tokens below, but its CLI/package is not
  installed. See §3 of the design system doc for the license and citation.

## Severity summary

| Severity | Count | IDs |
| --- | --- | --- |
| Critical | 3 | C1, C2, C3 |
| High | 8 | H1–H8 |
| Medium | 5 | M1–M5 |
| Low | 3 | L1–L3 |

Nothing here is reported as fixed; this document is the before-state only. The
design system, rebuilt pages and after-screenshots are tracked separately and
this file is not updated to mark items resolved — the QA report is where
resolution is verified against the rendered result.

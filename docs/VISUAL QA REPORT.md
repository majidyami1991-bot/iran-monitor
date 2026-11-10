# Visual QA Report — reference redesign preview

Run on 2026-09-28 against the preview at `http://127.0.0.1:3002` (candidate
web + candidate API on the production database). Script:
`tests/ui/redesign-qa.cjs`. Evidence: `runtime/evidence/redesign-qa/`
(`report.json` plus screenshots, git-ignored).

## Result

| Measure | Value |
|---|---|
| Route × viewport loads | 96 (24 routes × 1920×1080, 1440×900, 1024×768, 390×844), all HTTP 200 |
| Functional checks | **44 / 44 passed** |
| Screenshots | 99 (full page at 1440 and 390; viewport at 1920 and 1024; story viewer desktop and mobile; mobile drawer) |
| Horizontal overflow | 0 |
| Accessibility smoke (1440, every route) | 0 pages with issues |
| Failed local requests | 1: `/api/v1/health/collection` → 503 once on `/monitoring` |
| Console errors | 1: the same 503 |
| Aborted navigation prefetches | 601 (Next.js cancels link prefetches when navigation moves on; counted separately, not failures) |

**About the one 503:** `/api/v1/health/collection` is designed to return 503
whenever the collector heartbeat is more than 45 s old, which happens briefly
during a long sequential fetch cycle. Production uses identical logic. Six
samples taken right afterwards were all 200 on both preview and production.
It is a real, transient health signal, not a UI defect, and it is reported
here rather than filtered out.

An earlier run also logged one `ERR_CONNECTION_CLOSED` from a publisher's
image CDN. The card fell back to category artwork as designed.

## Functional checks (all measured)

- **DB ↔ API ↔ UI:** the `/news` count equals the API total (1,182 at run
  time); a filtered view (`security_defense`, 7 days, important) equals the
  API total (427).
- **Query string:** state restores from the URL; active-filter chips; changing
  a filter updates the URL; browser Back restores the previous filter;
  filtered cards carry the filtered category.
- **Category click-through:** a card's category tag opens `/topics/{id}`.
- **Bilingual / RTL:**
  - Document is `lang=fa dir=rtl`.
  - The detail title's direction matches the language shown.
  - The original English sits in an LTR column.
  - The Persian column states "not stored" instead of showing a guess.
  - A translation status label is present.
  - No Persian inside LTR blocks.
  - English uses a Latin face, so digits stay Latin.
- **Content-language toggle:** persists per viewer.
- **Stories:**
  - The rail renders every API story, and ArrowLeft moves focus to the next one.
  - Enter opens a modal dialog with progress segments, and progress advances.
  - ArrowLeft advances the frame; the viewer pauses while the pointer is on the text.
  - Esc closes it and returns focus to the trigger; the story is marked seen.
  - It also works on the touch viewport.
- **Ticker:** renders from the rule; the pause toggle sets `aria-pressed`;
  next changes the headline when there is more than one item.
- **Keyboard:** the first Tab reaches the skip link.
- **Events:**
  - The list matches the API.
  - The "most sources" sort puts the most-sourced event first.
  - The event page lists every member in order, with its membership reason.
- **States:**
  - The map shows an empty state, and the API confirms 0 points.
  - An unknown item shows an error state.
  - A search with no results shows an empty state.
  - A forced 500 on the briefing shows an error state, not stale data.
  - A delayed feed shows skeletons.
- **Mobile:** the drawer opens with the full navigation, then navigates and closes.

## Stability gate

120 s at a 5 s interval against preview pages and APIs (`/`, `/news`, feed,
stories, breaking, briefing, events) and production (`/`, news API): **198
requests, 0 non-200**, p50 20 ms, p95 36 ms, max 38 ms. There were no
container restarts. Memory: web-preview 127 MiB, api-preview 67 MiB.

## Visual review notes (from the screenshots)

Fixed during QA:
- digits inside English titles rendered as Persian (Latin face added);
- the lead slot showed artwork while top items had photos (the lead now
  prefers an item with an article photo);
- event source names ran together;
- the topic-change and source-topic bars used 12 category hues (now a single
  series hue, per the chart rules);
- the preview web was proxying to the production API because Next rewrites
  are frozen at build time (replaced with a runtime proxy).

Known limitations:
- Most article images are unverified publisher URLs, shown with a credit
  line and never downloaded. Where a publisher refuses the image, category
  artwork appears.
- No Persian translation is stored yet, so all headlines currently show the
  English original with a "ترجمه در انتظار" (translation pending) label.

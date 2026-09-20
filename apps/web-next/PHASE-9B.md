# Phase 9B — compact dashboard preview

Baseline: `28c58596a37ecc497b5696880cf4b541494fe19b`.

## Recovery

Resumed the existing implementation without reset, checkout, stash, deletion or reimplementation. Before resume: three modified tracked files (`app/page.tsx`, `app/globals.css`, `app/api/dashboard/route.ts`) and two new tests (`tests/component.cjs`, `tests/visual-9b.cjs`). Both localhost ports returned 200. No related temporary test/build/Playwright process was active; no process termination was necessary. Existing eight screenshots and their manifest were preserved under ignored `runtime/evidence/phase-9b/pre-resume/` before recapture warranted by the final rendering fixes. Phase 9A evidence remains untouched.

## Implementation status

- Complete: 224px sidebar (previously 238px), 76px icon-only collapse with Persian native tooltips; existing mobile drawer and Escape.
- Complete: compact header/hero/ticker, previous/next/pause and full headline title; six compact real KPIs; zero-news explanation.
- Complete: twelve-column desktop grid, seven/five content split; mobile two-column KPIs, full-width panels.
- Complete: deterministic source-ID color/monogram and subtle geometry; source-type data annotation, explicit LTR English titles, Persian metadata and safe source/detail links. No publisher logo or artificial image.
- Complete: real time-window total/average, period selector, readable bars and end values, full source tooltip and equality explanation.
- Complete: donut totals/counts/percentages, honest RSS-only note, provenance valid/incomplete counts and explanatory caveat.
- Complete: up to eight existing ranked topics with short/stopword guard; no historical rank changes fabricated.
- Complete: actual publication-date rows and three-hour bins, labeled heatmap axes, intensity legend and date/hour/count tooltips.
- Complete: distinct coverage icons, badges and progress against actual registry length; collector status explicitly says scheduling is inactive and run time is unavailable.

Source names are used only when registered. Where absent, the hostname is used with an explicit fallback explanation. No source identity is guessed. Unknown collector history is not fabricated.

## Limited post-resume fixes

Only unresolved QA issues were addressed: explicit hostname fallback, chart labels disappearing during repeated chart animation on clock rerenders, and two mobile link targets under 44px. Chart values now remain stable; a short CSS panel-entry animation occurs only on mount. No test assertion was weakened or skipped.

## Validation and evidence

TypeScript, Docker production build and seven server-render component assertions pass. Visual checks cover 1920×1080, 1440×900, 768×1024 and 390×844: counts, RTL, loaded font, nonzero charts, text direction, metadata readability, first-fold placement, navigation/collapse, ticker and range controls. Supplemental checks compare bar labels and widths with API, check full tooltips and in-bounds labels, explicit fallback, coverage denominator, donut explanations, heatmap tooltips and mobile target sizes. Evidence and results are in ignored `runtime/evidence/phase-9b/`.

Only the preview service is rebuilt. Existing API, database and frontend service remain unchanged on port 3001. No importer, migration, source fetch, collector, OpenCTI action or push. Preview remains on 3002 pending visual approval.

Final QA also detected and removed a Tailwind `.ring` utility box-shadow collision on the provenance donut. This was an appearance-only targeted fix; keyboard focus outlines elsewhere remain. Supplemental verification checks computed box-shadow in all four viewports. Final manifests include capture timestamps and origin URL in addition to dimensions and SHA-256. All original Phase 9A screenshots and pre-resume Phase 9B evidence are retained.

Final results: seven component assertions, 56 visual checks and 41 supplemental checks pass. Zero console errors, unexpected failed requests or horizontal overflow. Required screenshots are all captured after fonts and charts settle. Initial pre-resume evidence is retained rather than discarded. Remaining identity limitation is intentional: the registry lacks human-readable names for some sources, so the UI explicitly identifies hostname fallback instead of inventing names.

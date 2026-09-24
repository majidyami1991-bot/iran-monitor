# Commercial UI/UX redesign — QA report and delivery record

Date: 2026-09-23. Every figure below is a live measurement, not an estimate.

## Re-verification, 2026-09-24

The client re-sent the same brief a day later. Rather than re-doing the work,
the delivered state was checked fresh:

| Check | Result |
| --- | --- |
| `commercial-qa.cjs` against production, 4 consecutive runs | **69/69 every time** |
| Production UI | Confirmed serving the redesign (`shell-sidebar` markup present), 17h uptime, healthy |
| Scheduled collection, last 24h | **95/96 cycles succeeded (99%)**, all recent cycles 12/12 sources |
| OpenCTI | All 14 containers still running, untouched |
| Unrelated projects (`mlw-*`, `plane-preview-*`) | Untouched |
| Git tree | Clean; one small commit added (`6476a2b`) surfacing the real error message from the font-load check instead of swallowing it, after chasing an intermittent single-run failure down to cold-start timing rather than a real defect — documented rather than silently patched over |

Nothing in this pass changed the delivered product. See below for what was
built.

## 1. What was done, in order

1. Visual audit of the running system at four viewports, eight pages — see
   [docs/UI UX COMMERCIAL AUDIT.md](UI%20UX%20COMMERCIAL%20AUDIT.md). 3 critical,
   8 high, 5 medium, 3 low findings, each anchored to a rendered screenshot.
2. Reference review (Ground News, threat-intelligence dashboard patterns,
   VibeFarsi) for principles, not for copied UI — see the audit's closing
   section and the design system doc.
3. Design system built: tokens, six-state color model, one component per
   concept — [docs/UI UX DESIGN SYSTEM.md](UI%20UX%20DESIGN%20SYSTEM.md).
4. Every page rebuilt on that system, including two new pages the brief
   required that did not exist: `/monitoring` and `/about`.
5. Deployed to the port-3002 preview against the live database and API — no
   data copied or fabricated — while port 3001 kept serving the previous build
   untouched.
6. New QA suite (`tests/ui/commercial-qa.cjs`) run against the preview,
   fixed a font-loading test race and three real bugs it caught (below), run
   again clean.
7. Promoted: built the production image from the committed source, deployed
   it to port 3001, re-ran the full QA suite against production, stopped the
   preview.
8. Verified collection, OpenCTI and unrelated projects were undisturbed
   throughout, and took a final backup.

## 2. Test results

| Suite | Result |
| --- | --- |
| `tests/ui/commercial-qa.cjs` against the 3002 preview | **69 / 69** |
| `tests/ui/commercial-qa.cjs` against 3001 after promotion, then after a live rollback→roll-forward cycle | **69 / 69**, reproduced twice |
| `tsc --noEmit` | clean |
| `next build` | clean, all 9 routes compiled (2 new: `/monitoring`, `/about`) |
| Collector offline test suite (`pytest`, inside the runtime image) | **68 / 68** — unaffected, this phase touched only 3 backend filter/shape lines |
| `tests/monitoring/smoke_api.py` | pass, including new filter and `last_run`-shape assertions |
| `scripts/backup.ps1 -Action backup` | pass, `SHA-256 97EC4B0F…` |

The QA suite checks, per §14 of the brief: every route (200, no 500 on
unknown routes), sidebar active state and collapse, news filters round-tripping
through the URL with counts matching the API, topic drill-down count matching
the topics endpoint, no UUID shown for a source name, all 62 registered
sources listed with a Persian reason, the news-detail body never printed
twice, `/monitoring` reflecting live health data, keyboard focus landing on an
interactive element, RTL/Vazirmatn, and zero horizontal overflow plus zero
console/network errors across all four required viewports (1920×1080,
1440×900, 1024×768, 390×844).

## 3. Real bugs the redesign work surfaced and fixed

Found while building against live data, not hypothetical:

1. **`stats/overview.last_run` was a positional array**, not an object, unlike
   every comparable field elsewhere in the API. Nothing had read it before;
   the new dashboard does. Fixed to return a named object; a smoke assertion
   now pins the shape.
2. **The dashboard's "فعال‌ترین منابع" panel read the wrong field names**
   (`name`/`count` instead of the API's `display_name`/`item_count`) and
   silently rendered five empty dashes. Caught by looking at the actual
   rendered screenshot, not by reading the code — exactly the audit's own
   methodology applied to new work.
3. **Coverage reasons rendered in English** inside an otherwise-Persian table
   (`/sources`). The API's `reason` field is a fixed, documentation-oriented
   English sentence, one per coverage state; translated client-side by state
   key rather than by matching the English text.

All three are described honestly here rather than omitted because they were
found and fixed within the same work session.

## 4. Audit findings — resolution

| ID | Finding | Resolution |
| --- | --- | --- |
| C1 | Full article body inline in every list card (news stream 25,496px / 42,548px mobile; source detail 15,420px) | **Fixed structurally.** `NewsCard` (list) and `NewsDetail` (detail) read disjoint API fields; a list card has no path to the full body. News stream is now ~4,500px for 20 items. |
| C2 | Same paragraph printed twice on the detail page | **Fixed.** Translation and original text are separate tabs; verified by the QA suite's occurrence check. |
| C3 | No dedicated monitoring page | **Fixed.** `/monitoring` built: health banner, per-source table, cycle-history table. |
| H1 | Raw unstyled operational log mixing English/Persian | **Fixed.** Relocated to `/monitoring` as a real table with translated status labels; `/analytics` no longer contains it. |
| H2 | Status badges read as a field-name:value dump | **Improved.** One `FieldStatus` component, consistent tone-coded badges; still a compact label·value pair by design (states are enumerable and short), not a redesign into icon-only — a judgment call, documented here rather than silently narrowed in scope. |
| H3 | Two unrelated visual languages for the same concept | **Fixed.** One `Shell`, one `NewsCard`, one token set across every page. |
| H4 | English technical strings in Persian UI | **Fixed** for coverage reasons and every run/health status label (`succeeded`→`موفق`, etc. — this pass also caught two spots the initial redesign itself had left untranslated, listed above). **Deliberately not translated:** rule-based topic keywords (`military`, `security`, …) — these are literal matched tokens from English source text; translating them would misrepresent what the extraction actually found. They render `dir="ltr"` and visually separated, not inline-mixed. |
| H5 | "نمای پایلوت فعال" badge on the commercial dashboard | **Fixed**, removed; confirmed absent by the QA suite. |
| H6 | Amber banner for a healthy status | **Fixed.** `toHealth()` is the one mapping from API status to color; amber is structurally unreachable for a healthy state. |
| H7 | No image caption/attribution | **Fixed.** `NewsDetail`'s figure has a caption and a verification-status note. |
| H8 | No breadcrumb, no tabs | **Fixed.** Breadcrumb in the header; four tabs, confirmed by the QA suite. |
| M1 | Dashboard has no single focal hierarchy | **Fixed.** Cut to six stat cards, the feed, and three compact side panels; the daily heatmap calendar and both donut charts were removed from the dashboard (heatmap-equivalent detail remains available via `/analytics`'s bar chart). |
| M2 | Missing translation/image/document filters | **Fixed**, added to the API and the filter bar. |
| M3 | Topics page is a flat list, no per-topic trend | **Partially addressed.** Now uses the shared clickable row component with working drill-through; a per-topic trend sparkline was not built — descoped for time, not silently dropped. |
| M4 | Source rows have no visual identity | **Fixed.** `SourceMark` monogram added. |
| M5 | Dense small text (9–12px) | **Fixed.** Type scale floor raised to 12px; most body text is 13–14.5px. |
| L1 | Leftover "Phase 9B" comment in shipped CSS | **Fixed.** `globals.css` rewritten from scratch. |
| L2 | Only six CSS custom properties existed | **Fixed.** Full token system in `tokens.css`. |
| L3 | 1920px layout correctly capped | Preserved (`--content-max`). |

**Everything with a severity of Critical or High is resolved.** M3 is the one
item knowingly left partial; it does not block commercial use of the pages it
affects.

## 5. Evidence

| What | Where |
| --- | --- |
| Before screenshots (32, 4 viewports × 8 pages) | `runtime/evidence/commercial-ui/before/` (git-ignored) |
| After screenshots (32, same matrix) | `runtime/evidence/commercial-ui/after/` (git-ignored) |
| QA run against preview | `runtime/evidence/commercial-ui/qa/results.json` |
| QA run against production | `runtime/evidence/commercial-ui/qa-production/results.json` |

## 6. Final state

| Item | State |
|---|---|
| Production URL | `http://127.0.0.1:3001` — the redesigned build, healthy |
| Preview (3002) | Stopped; its image (`iran-monitor-news-news-web-next-preview`) remains for reuse |
| Rollback | **Exercised live, not just validated.** `docker compose -p iran-monitor-news --env-file .env -f deployment/news-monitor/compose.yml -f deployment/news-monitor/compose.rollback-pre-commercial-ui.yml up -d --no-deps news-web` was run against production, confirmed serving the pre-redesign markup while healthy, then rolled forward again with the plain `compose.yml` and reconfirmed serving the redesign. Both states passed their respective health checks. |
| Database / API / Collector / Scheduler | Untouched by this phase apart from the 3 documented shape/filter fixes in `ops.py`; collection continued succeeding (12/12 sources) through the entire redesign, confirmed via `collection_runs`. |
| OpenCTI and unrelated projects (`mlw-*`, `plane-preview-*`, …) | Untouched, confirmed running. |
| Backup | Taken after promotion, verified via row counts in the backup log. |

## 7. Commits

| Commit | Content |
| --- | --- |
| `180e86a` | Audit + browser tooling fix (Edge/Playwright CDP launcher) |
| `4441f11` | API shape/filter fixes found while building the UI |
| `2cd26d0` | Design system and shared component library |
| `6c04b74` | Every page rebuilt; `/monitoring` and `/about` added |
| `30045f0` | Legacy file removal |
| `0c16a18` | QA suite, after-screenshots, design system doc |

## 8. Honest residual list

- M3: topic trend sparklines not built.
- H2: field-status badges are an improved, consistent label·value badge, not
  an icon-only redesign.
- The dashboard's font-load check was flaky in the QA harness (a single
  point-in-time `document.fonts.check()` immediately after several rapid
  sequential navigations, not a font problem — a manual isolated check always
  passed). Fixed by polling until the font is actually ready instead of
  sampling once; recorded here because it looked like an intermittent
  product bug before being run down to a harness timing issue.
- Content quality itself (translation coverage, image verification) is
  unchanged by this phase — this was a UI/UX phase over the existing,
  already-honest data model, not a content-pipeline phase. See
  [docs/STAGE 1 CONTENT QUALITY.md](STAGE%201%20CONTENT%20QUALITY.md) for that
  separate, still-open item (no translation provider configured).

# Iran Monitor UI QA — Phase 7E2

## Environment

- Audited commit: `f74fbadf4e83940c48799629c36373d91fdb28c9`; initial worktree clean.
- Playwright 1.52.0; Microsoft Edge 153.0.4234.32; explicit Windows executable.
- Temporary nonpersistent contexts; locale fa-IR; timezone UTC. Browser closed in finally.
- Browser requests restricted to localhost/127.0.0.1 and GET; no external links clicked.
- Viewports: desktop 1920×1080, laptop 1440×900, tablet 768×1024, mobile 390×844.
- Real PostgreSQL pilot data: 104 items, 11 sources. No migration/importer/write operation.
- Evidence stored only under ignored `runtime/evidence/phase-7e2/`.

## Matrix and results

| Area | Result | Evidence |
|---|---|---|
| Five main routes × four viewports | HTTP 200; correct active routes, RTL, landmarks, single H1; no document horizontal overflow | results.json |
| Dashboard | DB/API/UI counts agree; pilot status and latest items present; two presentation requirements fail | dashboard-desktop.png, dashboard-mobile.png |
| News | 20-item pages; next/back/forward; unique cards across first two pages; real search, empty search, source/type/provenance/start/end dates, both sort directions and combined filters match API IDs | results.json, news-desktop.png, news-mobile.png |
| Query and reset | Query retained on reload; browser history and reset work | results.json |
| Details | Three real items from three sources and three source pages return 200; titles/IDs match API; source timelines present | news-detail.png, source-detail.png |
| Sources | Eleven cards; search, type, name/count/latest ordering match API; disabled collection wording correct | sources-desktop.png, results.json |
| Analytics | Four nonzero SVGs across all viewports; all summary counts equal API; topic links work; import absence represented honestly | analytics-desktop.png, analytics-mobile.png |
| Errors | Missing item/source/route are Persian 404; delayed GET shows skeleton; injected 500 and aborted GET show error/retry and recover; invalid date shows safe generic error | results.json |
| Keyboard/accessibility | Form labels, landmarks, H1, active route, visible keyboard focus and mobile Escape verified; font/labels limitations below | results.json, focus.cjs |
| Network | Zero page JS exceptions; zero unexpected failed requests; one intentionally aborted request recorded separately | results.json |
| Screenshots | Ten distinct PNG hashes; dimensions in manifest; animations disabled; captured after skeleton completion | manifest.json |

Final primary suite: **160 checks, 152 passed, 8 failed**. The eight failures are two unique defects reproduced in four viewports. Initial focus failures were harness artifacts (Tab reached document body on a page with no focusable main content); explicit focus and another Tab verified solid outlines. Harness corrected and primary suite rerun. No production code changed.

## Defects

| ID | Severity | Finding / reproduction | Evidence | Status |
|---|---|---|---|---|
| UI-01 | Medium | Computed font is Tahoma/Arial, not Vazirmatn, on all viewports. | results.json, dashboard-desktop.png | Open; no change authorized for this severity |
| UI-02 | Medium | Overview has no hot-topics section; topics exist only on analytics. | dashboard-desktop.png, results.json | Open |
| UI-03 | Medium | SVG axis labels are tiny and clipped at chart edges in RTL. Numeric text summaries remain accessible and agree with API, so the analytical data is still usable. | analytics-desktop.png, analytics-mobile.png | Open |
| UI-04 | Medium | Source names in DB are UUIDs; hostname/tier and some canonical links are missing. UI faithfully reflects incomplete stored metadata; source identification is cumbersome. No values guessed. | sources-desktop.png, news-detail.png | Open; data repair outside this QA scope |
| UI-05 | Medium | Topics contain common English words and a year; useful-term quality is low. | analytics-desktop.png | Open |
| UI-06 | Medium | Invalid date query produces HTTP 500 and generic recoverable UI error instead of a specific validation message. No stack trace displayed. | results.json | Open |
| UI-07 | Low | Source detail supplies a back link but no structured breadcrumb. | source-detail.png | Open |
| UI-08 | Low | Mixed untranslated field/status labels (hostname, news, COMPLETE) reduce Persian presentation consistency. | news-detail.png | Open |

Critical: **0**. High: **0**. Medium: **6**. Low: **2**. No fixes or rebuilds applied. All core routes and flows remain usable; UI-03 is classified Medium because the text summary provides complete chart values.

## Evidence and limitations

Ten baseline images: dashboard-desktop.png, dashboard-mobile.png, news-desktop.png, news-mobile.png, news-detail.png, sources-desktop.png, source-detail.png, analytics-desktop.png, analytics-mobile.png, about-desktop.png. Pixel dimensions and SHA-256 values are in the ignored manifest. Images are full-page, so heights exceed viewport height. No screenshot, profile, runtime manifest, DB dump, environment file or logs are committed.

Visual inspection sampled dashboard mobile, news detail, analytics desktop and analytics mobile. All ten PNGs have valid nonzero dimensions and distinct hashes. Automated document overflow was zero; no gross content/navigation overlap observed. This is DOM/keyboard accessibility smoke, not a WCAG certification or screen-reader audit. No new accessibility dependency installed. Core text contrast was visually readable; tiny SVG labels are explicitly a defect. Full-article truth, publisher metadata accuracy and collector provenance completeness were not independently revalidated. Comparisons establish UI/API agreement, not correctness of source content. Browser console JS exceptions and expected HTTP/network fault injection are counted separately.

Acceptance outcome: QA completed with open Medium/Low defects. Core functional gates pass; **not an all-green suite**. Screenshots preserve current defects as baseline. Next safe action is review/authorization of the recorded Medium/Low fixes.

## Stability and integrity results

Five checkpoints over 120.3 seconds: HTTP 200, 104 items, 11 sources throughout; news container IDs/status/RestartCount unchanged. PostgreSQL healthy; API/Web operational (no Docker healthcheck configured for those two). Full row hashes for items, sources and provenance tables unchanged. Input SHA-256 set and sites.docx unchanged; all baseline Docker container snapshots unchanged, including OpenCTI and unrelated resources. Only news-web publishes 127.0.0.1:3001. Zero remaining Edge processes matching the Playwright temporary-profile marker. No rebuild, restart, migration, importer, source request or mutation executed.


## Phase 7E3 — pre-fix inventory

Baseline: 8e16364362d1e8f49c88bb3cae0876883b97a6c8. Exactly six Medium and two Low defects; no additional feature scope.

| ID | Severity | Route / viewport | Expected | Actual | Before evidence | Minimal fix |
|---|---|---|---|---|---|---|
| UI-01 | Medium | all / all four | Loaded Vazirmatn | Tahoma | results.json | Official local WOFF2 + license, font-face and real loading checks |
| UI-02 | Medium | / / all four | API topic chips | Absent | dashboard-desktop.png | Up to ten endpoint topics; q links mapped to existing search |
| UI-03 | Medium | analytics and source charts / all | Readable labels | Tiny/clipped SVG text | analytics-mobile.png | Responsive HTML labels with full titles/summary outside SVG; unchanged plot values |
| UI-04 | Medium | sources/details / all | Honest understandable missing metadata | UUID names, absent fields | source-detail.png | Explicit missing-name notice and separate identifier; no DB enrichment or guesses |
| UI-05 | Medium | analytics topics / all | Useful deterministic words | Stopwords and year | analytics-desktop.png | Server-side normalization, stopwords, minimum length and numeric exclusion |
| UI-06 | Medium | news invalid date / all | Specific validation response | HTTP 500/generic error | results.json | Validate date and interval, HTTP 422; localized UI message |
| UI-07 | Low | source detail / all | Breadcrumb | Back link only | source-detail.png | Accessible breadcrumb with home/sources/current |
| UI-08 | Low | details/cards / all | Persian labels | hostname/news/COMPLETE | news-detail.png | Translate visible field/status labels without changing API values |

Font asset and font-face absent before fix; no local WOFF2 found in tracked project. Prior computed font: Tahoma, Arial, sans-serif. No existing container font URL to test.

## Phase 7E3 — resolution

Commit: pending. Before-history above retained verbatim. Scope remains the eight listed defects; no DB enrichment, importer, migration or new feature.

| ID | Status | Minimal fix | Verification | After evidence |
|---|---|---|---|---|
| UI-01 | RESOLVED | Official Vazirmatn 33.003 variable WOFF2, OFL license, local font-face and explicit font/woff2 MIME | Four viewport tests: asset 200, MIME, loaded FontFace, document.fonts.check and computed family | targeted.json; dashboard-desktop-after.png |
| UI-02 | RESOLVED | Dashboard uses at most ten API topics; loading/empty/error/retry states; q query links retain legacy search alias | Four viewport count/value checks and q-filter follow-through | targeted.json; dashboard-mobile-after.png |
| UI-03 | RESOLVED | Unscaled 14px responsive labels outside SVG, wrapping, full title and numeric summaries; plot values unchanged | Four viewport label bounding rectangles, title equality, zero overflow; original chart/API comparisons pass | supplemental.json; analytics-desktop-after.png; analytics-mobile-after.png |
| UI-04 | RESOLVED (presentation scope) | Explicit missing publisher-name notice identifies UUID as source ID; missing domain/tier/URL shown as registered absence, collection state exposed | Source detail metadata notice/status/API regressions | source-detail-after.png; supplemental.json |
| UI-05 | RESOLVED | Backend topic normalization, Persian character normalization, URL removal, numeric exclusion, stopwords, deterministic ordering; same response contract | Four backend unit tests and real API/analytics suite | backend_test.py; analytics-desktop-after.png |
| UI-06 | RESOLVED | ISO date/calendar and interval validation returns 422; frontend displays specific Persian correction guidance | Invalid date and reversed-range unit tests; HTTP 422 and UI verification | supplemental.json |
| UI-07 | RESOLVED | Source detail breadcrumb with home, sources and current-page label | Two real breadcrumb links and existing navigation assertions | source-detail-after.png; supplemental.json |
| UI-08 | RESOLVED | Persian domain/type/tier/provenance labels and status translations, including chart labels; raw API enums retained | Source detail has no raw hostname/COMPLETE/UNKNOWN; original ID/count assertions preserved | source-detail-after.png; supplemental.json |

UI-04 does not claim recovery of absent DB metadata: the user-authorized correction is honest missing-data presentation. Existing source IDs remain visible for identification and API consistency.

Targeted original failures: **8/8 passed**, strengthened with actual font delivery checks. Full original suite: **160/160 passed**, zero skip and no weakened assertion. Only evidence directory changed in the suite copy. Supplemental defect checks: **19/19 passed**. Backend defect tests: **4/4 passed**. No unexpected failed request or page JS exception; deliberate request abortion remains recorded as expected-negative evidence.

First targeted run detected incorrect font MIME and was fixed by explicit registration. First full run detected mobile form overflow with the new font; a bounded control-width fix resolved it, and all 160 assertions were rerun. Final localization of chart type labels was followed by another full 160/160 run. No assertion was removed or changed to accept a failure.

Official asset version, URLs, request policy, license and SHA-256 are recorded in `apps/api/web/fonts/SOURCE.txt`. Font SHA-256: `4E3FA217D38FDAFC1FEA4414CEB58CA5E662CF0AB5FA735A8C8C20E8B42CAD92`. Downloaded one WOFF2 and license, no automatic retry or redirect following. Runtime requests stay local.

Visual comparison with Phase 7E2: font now loaded, dashboard topics now present, edge labels no longer clipped/tiny; source metadata absence is explicit and breadcrumb visible. Ten current screenshots plus five explicitly named after copies are in ignored phase-7e3 evidence; baseline phase-7e2 files are not overwritten. Remaining limitations: no screen-reader certification; missing source metadata is not repaired in DB; topic ranking is deterministic lexical frequency, not AI analysis.

Open defects after authorized presentation fixes: Critical 0, High 0, Medium 0, Low 0. No new regression observed in the tested flows/viewports.

Final rollout stability: five checkpoints over 120.3 seconds, all HTTP 200, 104 items, 11 sources; identical news container snapshots and zero restart increments. DB row hashes and input hashes unchanged; all other containers unchanged. Only 127.0.0.1:3001 published by news-web. No remaining Playwright Edge profile process. Worktree changes limited to the eight defect fixes, font/license/source record, four backend tests and this report.


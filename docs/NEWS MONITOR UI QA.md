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


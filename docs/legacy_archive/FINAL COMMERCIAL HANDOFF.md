# Final Handoff — Reference Redesign (preview, not promoted)

**Status:** the redesign is implemented and running as a localhost-only
preview on **http://127.0.0.1:3002**, over real production data. Production
(127.0.0.1:3001) is on the unchanged pre-redesign images. Promotion waits for
the client's visual approval and two decisions (below).

## What was delivered

- **Backend** (additive, versioned):
  - taxonomy v3 with secondary topics, evidence, reason-coded "other", and
    append-only history with human override;
  - event clustering v2;
  - stories, a rule-based daily briefing and an integration registry;
  - empty ingestion contracts for commodities, social, geo and alerts;
  - experience APIs (feed, breaking, stories, briefing, timeline, topics,
    source profiles, insights, descriptive foresight, notifications).
- **Frontend:** a new editorial design system and all 24 routes of the brief:
  - home: ticker, stories, lead stories, briefing, latest, timeline, activity
    and commodity status, social status;
  - the news stream with shareable filters, bilingual detail, stories,
    briefing, events, topics, sources, analytics, map, social, five foresight
    pages, alerts and about.
- **QA:** a browser acceptance suite, a migration drill, a rollback drill and
  a stability run.
- **Docs:** reference audit, design system, information architecture,
  capability matrix, stories & briefing contract, event & topic model, visual
  QA, deployment & rollback.

## Decisions needed from the client

1. **Translation provider credit.** The OpenRouter account has no balance
   (last call: HTTP 402), so 0 items have a Persian translation. Every card
   currently shows the English original with a "translation pending" label.
   Adding credit and approving one controlled pilot run
   (`docs/TRANSLATION OPERATIONS RUNBOOK.md`) enables Persian headlines with
   no UI change.
2. **Foresight scope.** An earlier instruction limited the product to stage 1.
   The foresight pages are strictly descriptive, and scenarios, drivers and
   strategic uncertainties are left empty, but the menu exists. Confirm, or
   hide the group before promotion.

Also recommended: identify what rebuilt production at 10:23–10:25 UTC (see
`docs/DEPLOYMENT AND ROLLBACK.md`, Incident).

## Verifiable report

```text
BASELINE_COMMIT=64a64a6 (feature/iran-monitor-foresight-platform)
WORK_BRANCH=feature/iranmonitor-reference-redesign (worktree E:\Iran monitor-redesign)
REFERENCE_ACCESS_STATUS=BLOCKED — HTTP 403 Cloudflare managed challenge on desktop and mobile; not bypassed; no reference content retrieved; no client screenshots supplied
REFERENCE_FEATURE_COUNT=8 named in the brief; 0 observed on the reference site
DATABASE_ITEM_COUNT_BEFORE=1168
DATABASE_ITEM_COUNT_AFTER=1186 (growth from the live collector only)
DATABASE_SOURCE_COUNT=12 monitored (62 registered)
TRANSLATION_COUNT=81 rows, 0 available (20×4 pending pilot rows + 1 error)
EVENT_COUNT_BEFORE=1
EVENT_COUNT_AFTER=30 (29 from clustering v2, 66 memberships)
STORY_COUNT=10 active
DAILY_BRIEFING_STATUS=IMPLEMENTED rule-based (rule_briefing_v1), 12 stored versions, fresh; AI summary not generated (provider_unavailable: 402 insufficient credit)
BREAKING_NEWS_STATUS=IMPLEMENTED rule breaking_v1, auditable, with a labelled "latest" fallback
NEWS_STREAM_STATUS=IMPLEMENTED, 10 filters + 4 sorts in the query string; UI count = API count (1182; filtered 427)
TOPIC_TAXONOMY_VERSION=3.0.0 (v2.1.0 retained in item_classifications)
OTHER_CATEGORY_SHARE_BEFORE=23.8%
OTHER_CATEGORY_SHARE_AFTER=11.3% (every item carries a reason code)
SOURCE_METADATA_COMPLETENESS=84.5% (country deliberately unrecorded without evidence)
TRANSLATION_COVERAGE=0.0%
PROVENANCE_COMPLETENESS=100.0%
MAP_STATUS=SCAFFOLD — 0 evidence-backed locations; empty state + geo_mentions contract; no guessed coordinates
SOCIAL_STATUS=SCAFFOLD — x_social not_configured; 36 registered handles listed; 0 posts
COMMODITY_STATUS=SCAFFOLD — commodity_prices not_configured (no licensed feed); 0 observations
FORESIGHT_STATUS=PARTIAL — trends, weak signals, data uncertainty and STEEP co-occurrence are descriptive and live; drivers, scenarios and strategic uncertainties are empty by design
API_TESTS=261 passed / 0 failed (image test stage; 241 existing + 20 new)
FRONTEND_TESTS=typecheck PASS, production build PASS (no frontend unit-test framework in this repo)
PLAYWRIGHT_TESTS=44/44 functional checks passed; 96/96 route×viewport loads HTTP 200
ACCESSIBILITY_STATUS=automated smoke: 0 issues on 24 routes (names, alt, labels, one h1, landmarks, lang/dir); keyboard tests passed (skip link, story rail, viewer, focus return); no axe/WCAG audit performed
SCREENSHOT_COUNT=99
CONSOLE_ERROR_COUNT=1 (a transient 503 from /api/v1/health/collection, which is by design when the collector heartbeat is >45 s old)
FAILED_REQUEST_COUNT=1 local (the same 503); 601 aborted Next.js prefetches reported separately
HORIZONTAL_OVERFLOW_COUNT=0
STABILITY_GATE=PASS — 120 s, 198 requests, 0 non-200, p95 36 ms, 0 restarts
ROLLBACK_TESTED=YES — application rollback performed for real on production (11:43 UTC); old API on the migrated DB drilled; schema rollback SQL restored exact baseline counts on a restored copy
OPENCTI_UNCHANGED=YES — all 14 OpenCTI container IDs identical to the baseline
UNRELATED_CONTAINERS_UNCHANGED=YES — mlw-*, plane-* and the news collector have identical IDs; news-api-1/news-web-1 were recreated by an unidentified actor, then by the rollback, onto the original pre-redesign images
SECRETS_EXPOSED=NO — .env never read or printed; branch diff scanned clean; no .env, dump or screenshot committed
GIT_COMMIT_HASHES=605e58f 0494289 68a771a bfc7cca 6945cf4 877477c de04df7 + this docs commit
PREVIEW_URL=http://127.0.0.1:3002
PRODUCTION_PROMOTED=NO
NEXT_SAFE_ACTION=Client reviews the preview at 127.0.0.1:3002 and decides on (1) translation credit and (2) foresight scope; identify the actor that rebuilt production; then promote per docs/DEPLOYMENT AND ROLLBACK.md and rerun the QA suite against :3001
```

## Not done, and why

- **Visual comparison against the reference:** access blocked (403). See
  `docs/REFERENCE UI AUDIT.md`.
- **Persian content:** the provider has no credit; no translation was
  fabricated.
- **User menu / per-user notifications:** this deployment has no
  authentication.
- **Commodity, social, map and OSINT data:** no licensed or authorised
  source. Contracts and statuses are in place.
- **Full WCAG audit:** only the automated smoke and keyboard checks were run.
- **`git push`:** not performed. The branch is local; pushing and merging to
  `main` wait for approval.

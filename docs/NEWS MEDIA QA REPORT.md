# News Media QA Report

QA of media v2 on the preview (`127.0.0.1:3002`), 2026-09-29. Production
(`127.0.0.1:3001`) was not changed.

## Automated tests

| Suite | Result |
|---|---|
| Offline API tests (run inside the API image build) | **359 passed**, including 26 media-pipeline test functions (more cases through parametrisation) |
| `tests/ui/news-media-qa.cjs` (API contract + 4 viewports) | **32/33** in the final run, 33/33 in the first run (see below) |
| `tests/ui/redesign-qa.cjs` (redesign regression) | **44/44** |

The media-pipeline tests cover:
- RSS fixtures: enclosure, `media:content` with caption and credit,
  `content:encoded` with emoji and the share-ramp image, description images;
- deny tokens, dimension rules, the aspect ratio, MIME aliases;
- canonical and unsafe URLs;
- Open Graph and JSON-LD, including `@graph`;
- the fallback flag defaulting to off, non-HTML responses, 403, timeout;
- every validation outcome (MIME mismatch, HTML disguised as an image,
  pixel, final URL not https, guard refusal, HEAD 405 fallback, redirect to
  a private IP);
- the collector attaching `rss_media` without changing the content hash;
- the emoji/avatar hosts classified as icons;
- the pilot's host rule and its 10-item cap.

### The one failing check

`news stream shows real images` requires at least 5 loaded images on
`/news`. The final run loaded 4.

The cause is data drift, not a regression. The top of the feed is now
mostly new JFeed items collected by the **unchanged production collector**,
which does not read enclosures. All 9 JFeed items collected since the
migration have 0 media rows. The fix is the collector rebuild (promotion
step 4), which needs approval.

The check was not loosened to make the run pass.

Final run otherwise: 0 console errors, 0 failed local requests, 0
horizontal overflow, 0 external image failures.

## What was verified in the browser

| Check | Result |
|---|---|
| Home shows real images | pass |
| News detail shows the primary image with provenance (host, method, validation) | pass |
| Item without media shows the neutral placeholder ("تصویر منبع موجود نیست") | pass |
| Image load failure → placeholder ("تصویر منبع بارگذاری نشد"), title still readable | pass |
| No rejected image rendered on any route | pass |
| Image frames sized before load; CLS < 0.1 on all routes | pass (a 0.14 CLS on detail pages was fixed with a layout-matching skeleton) |
| CSP `img-src` lists named hosts only, `object-src 'none'` kept | pass |
| Viewports 1920×1080, 1440×900, 1024×768, 390×844: no overflow | pass |

## Before / after

| Measure | Before | After |
|---|---|---|
| `/news` images loaded (QA at the time) | 5 | 11 |
| `/news` placeholders | 19 | 8 |
| Home images loaded | 7 | 11 |
| Items with a primary (database) | 252 | 312 of 1361 (22.9%) |

Screenshots (not in Git) are in `runtime/evidence/news-media/{before,after,after-compare}`.

## Coverage by source (final)

| Source | Items | With primary | Coverage |
|---|---|---|---|
| breakingdefense.com | 70 | 50 | 71.4% |
| defence-blog.com | 107 | 77 | 72.0% |
| defence-industry.eu | 179 | 2 | 1.1% |
| jcfa.org | 24 | 1 | 4.2% |
| mwi.westpoint.edu | 17 | 2 | 11.8% |
| news.usni.org | 55 | 42 | 76.4% |
| rusi.org | 74 | 3 | 4.1% |
| www.airandspaceforces.com | 47 | 18 | 38.3% |
| www.edrmagazine.eu | 56 | 3 | 5.4% |
| www.jfeed.com | 638 | 49 | 7.7% |
| www.missiledefenseadvocacy.org | 10 | 1 | 10.0% |
| www.twz.com | 84 | 64 | 76.2% |

The low-coverage sources publish no image in RSS. They can only be covered
by the article fallback, which is flag-gated and limited to 10 per pilot.

Validation status of evaluated rows: unknown 816, rejected 137, valid 38.

Rejections by class: icon/emoji 80, too small or wrong shape 50 (aspect
ratio 40, too small 10), logo 4, tracking pixel 2, other 1, ad 0.

## Data safety drills

| Drill | Result |
|---|---|
| Migration `2026.09.29-04` on production database | applied; legacy fingerprint unchanged |
| Offline backfill (dry → real → repeat) | 148 target items, 58 recovered (primaries 252 → 302), 10 lost primaries (8 EDR awaiting validation, 2 wide photos rejected by aspect ratio); repeat wrote 0 rows |
| Icon reclassification backfill (dry → real → repeat) | 81 rows updated, primaries unchanged at 312, repeat wrote 0; legacy fingerprint unchanged |
| Legacy-row sync on API redeploy | 1 collector-written row mapped; legacy fingerprint unchanged |
| Throwaway database drill (migrate + backfill ×3 → rollback SQL → re-apply) | legacy fingerprint back to baseline after rollback; re-apply clean; test database dropped |
| Preview rollback (`preview-before-media` images and back) | HTTP 200 on both, old contract served by old image |

## Live pilot (single invocation)

| Measure | Value |
|---|---|
| Items | 10 |
| Article HTML requests | 8 (all 200) |
| Image validation requests | 7 (all `valid`, HTTP 206) |
| Retries | 0 |
| Stop condition hit | none |
| Items with a primary after | 10 (7 network-validated) |

JCFA and RUSI Open Graph images are on third-party CDNs (`i0.wp.com`,
`ik.imagekit.io`). They were not validated, because the strict host rule
allows only publisher hosts. They are primary as trusted declarations.

## Known limitations

1. **Collector not rebuilt.** New items get no enclosure or `media:content`
   images until the collector is promoted (approval needed).
2. **Hotlink ORB.** The browser blocks `www.missiledefenseadvocacy.org`
   images with `ERR_BLOCKED_BY_ORB`, so a placeholder is shown.
3. **Unvalidated primaries.** 8 EDR images and all newly collected items
   are waiting for validation.
4. **Aspect ratio.** 2 wide photos are rejected by the 0.8–2.2 aspect rule.

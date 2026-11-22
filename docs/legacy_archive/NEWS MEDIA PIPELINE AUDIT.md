# News Media Pipeline Audit

Audit of why Defence Monitor showed few article images. It follows each image
through every layer: RSS feed → parser → `news_item_media` → API →
Next.js → browser. Run on 2026-09-29 against the production database
(read-only for the audit itself), branch `feature/news-media-pipeline`,
base commit `d7f20d6`.

## Baseline

| Measure | Value |
|---|---|
| Project HEAD before | `d7f20d6` |
| `news_items` at start | 1341 (1361 at the end; the production collector kept running) |
| `news_item_media` rows at start | 847 |
| Production containers | api `9d1ee6d…`, web `674515f…`, unchanged throughout |
| OpenCTI | 14 containers, unchanged |

## Method

1. **One read per feed.** Each of the 12 registry feeds was fetched exactly
   once, 12 requests in total, all HTTP 200. The XML was saved under
   `runtime/media-audit/feeds/` (gitignored), and every later analysis used
   those saved files. No feed was fetched a second time.
2. **Feed analysis.** For each of the 253 feed items, the audit recorded
   which media declarations exist in the XML (`media:content`,
   `media:thumbnail`, image `enclosure`, `<img>` in `content:encoded` or
   `description`). It then compared them with what the database held.
3. **Layer matrix.** A 28-item sample was traced through database →
   `/api/v1/feed` → rendered page (`runtime/media-audit/audit-layers.json`).
4. **Bounded live check.** Article HTML (Open Graph / JSON-LD) was only
   read in the pilot, within its budget. See
   [NEWS MEDIA OPERATIONS RUNBOOK](NEWS%20MEDIA%20OPERATIONS%20RUNBOOK.md).

## Feed inventory (253 items)

| Source | Items | With RSS media | Had a primary before |
|---|---|---|---|
| breakingdefense.com | 15 | 15 | 15 |
| defence-blog.com | 10 | 10 | 10 |
| defence-industry.eu | 10 | 0 | 0 |
| jcfa.org | 10 | 2 | 0 |
| mwi.westpoint.edu | 5 | 0 | 0 |
| news.usni.org | 30 | 27 | 27 |
| www.airandspaceforces.com | 9 | 9 | 3 |
| www.edrmagazine.eu | 10 | 1 | 1 |
| www.jfeed.com | 50 | 50 | 0 |
| www.missiledefenseadvocacy.org | 10 | 0 | 0 |
| www.rusi.org | 60 | 0 | 0 |
| www.twz.com | 34 | 34 | 31 |
| **Total** | **253** | **148** | **87** |

- **RSS_WITH_MEDIA_COUNT = 148**
- **RSS_WITHOUT_MEDIA_COUNT = 105.** For these items, the only possible image
  source is the article page: RUSI, MWI, Missile Defense Advocacy,
  defence-industry.eu, most of EDR, and most of JCFA.

## Root causes

| Layer | Count | Finding |
|---|---|---|
| RSS parser | **59** | The old parser read only `<img>` inside HTML. It ignored image `enclosure` (JFeed 50), `media:content` (Air & Space Forces 6) and extra TWZ declarations (3). |
| Database | 0 | Every row that was written was stored correctly. The schema could not record provenance or a primary image, but no data was lost. |
| API | 0 | The API returned whatever image rows existed. There was no image to return for the parser-gap items. |
| Frontend | 0 | Every image the API returned was rendered, or fell back to a placeholder. |
| Hotlink | **1** | `www.missiledefenseadvocacy.org`: the browser blocks the image with `ERR_BLOCKED_BY_ORB`, although the server-side ranged GET returned 206 with a valid JPEG. The UI shows the placeholder correctly. |

Two filter defects were also found and fixed during the audit.

- **False positive.** `c-5-c-17-share-ramp.jpg` (TWZ) was rejected because
  the filename contains `share-`. Deny rules now match whole filename tokens.
- **Misclassified emoji.** JCFA's `content:encoded` contains WordPress emoji
  images from `s.w.org`, and 80 such rows had been counted as "ad or
  tracking host". They are now rejected as `icon`. Final ad rejections: 0.
  These emoji are correctly never used as a primary image.

The audit also found that no stored `summary_raw` contains an `<img>` tag.
A backfill from stored evidence alone would therefore have recovered nothing.
Recovery re-parsed the saved audit feeds instead.

## 28-item layer matrix

| Group | n | Consistent at every layer | Notes |
|---|---|---|---|
| Visible on the publisher's site, missing in Defence Monitor | 8 | 7 | The limit of 8 (not 10) comes from the pilot's article-request budget. All 8 now have an `article_open_graph` primary. Missile Defense Advocacy hits the ORB hotlink block and shows a placeholder. |
| RSS has media | 10 | 10 | JFeed/TWZ now use `rss_enclosure`; USNI and Defence Blog use content/description HTML. One JCFA item has only emoji, so it is correctly `rejected` with no primary. |
| No valid RSS media | 10 | 10 | `missing` status with a neutral placeholder. The article fallback flag is off, so no request was made. |

Overall: **27 of 28 items consistent**, with 1 hotlink failure.

## Outcome after the fix (whole database, 1361 items)

| Measure | Before | After |
|---|---|---|
| Items with a primary image | 252 | 312 (22.9%) |
| Primary validated over the network | 0 | 15 |
| `/news` first-page images loaded (QA run at the time) | 5 | 11 |
| Home images loaded | 7 | 11 |

The coverage table per source is in
[NEWS MEDIA QA REPORT](NEWS%20MEDIA%20QA%20REPORT.md).

## Open limitation

The production collector still runs the pre-v2 parser. Items collected after
the migration get image rows only from HTML `<img>` tags. Those rows are
mapped to v2 by the preview API's sync loop. Enclosure and `media:content`
images for **new** items (JFeed in particular: 9 of 9 new JFeed items have
0 media rows) are only captured once the collector image is rebuilt. That
rebuild is a production change and needs separate approval.

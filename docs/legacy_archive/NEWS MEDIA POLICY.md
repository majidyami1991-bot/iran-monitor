# News Media Policy (`media_policy_v1`)

This policy decides which image, if any, represents a news item. It is
implemented in `apps/api/media_pipeline.py`, and the policy version is
stored on every evaluated row (`policy_version`).

Rule zero: **nothing is guessed.** An image, caption, credit or dimension
is shown only when the publisher declared it (feed or article metadata) or
a guarded request measured it. If there is no such evidence, the item shows
a neutral placeholder that says the source image is unavailable.

## Sources and priority

| Priority | `source_method` | Where it comes from |
|---|---|---|
| 1 | `rss_media_content` | `media:content` (also inside `media:group`), with `media:description` as caption and `media:credit` as credit |
| 2 | `article_open_graph` | `og:image`, `og:image:secure_url`, `twitter:image` (article fallback only) |
| 3 | `article_json_ld` | `image` in JSON-LD `NewsArticle`/`Article`, including `@graph` (article fallback only) |
| 4 | `rss_enclosure` | `<enclosure type="image/*">` |
| 5 | `rss_media_thumbnail` | `media:thumbnail` |
| 6 | `rss_content_html` | first qualifying `<img>` in `content:encoded` |
| 7 | `rss_description_html` | first qualifying `<img>` in `description` |
| — | `article_html` | rows written by the legacy article extractor (carried over) |
| — | `manual` | reserved for editor input |

Within a single item, the candidate with the highest score becomes
primary. The score is the method's base score plus small bonuses for
declared size and alt text. A partial unique index
(`news_item_media_one_primary`) guarantees **at most one primary per
item**.

## Trusted declarations

`rss_media_content`, `rss_enclosure`, `article_open_graph`,
`article_json_ld` and `manual` can become primary **without** a network
check, because the publisher explicitly named them as the item's image.
`rss_enclosure` counts as a trusted declaration, but it is lower in
priority than Open Graph: JFeed ships all of its images as enclosures, and
treating them as untrusted would have hidden every JFeed image.

HTML `<img>` candidates are not trusted. They become primary only when
validation succeeds, or when they declare a size of at least 480×270.

## HTML width and height are hints

`width`/`height` attributes on `<img>` are display sizes, not file sizes.
EDR, for example, declares 300×200 for files that are larger. Therefore:

- a declared size below **120 px** on either side → rejected as an icon;
- any other declared size → kept as a candidate with an **unproven** size.
  It becomes primary only when it declares at least 480×270 or passes
  network validation.

## Rejection rules

Checks run in this order. The first match decides the reason code.

| Rule | Reason code |
|---|---|
| URL canonicalisation fails: `data:`/`javascript:`/`file:` etc., relative URL without a base, credentials in URL, private or loopback literal host | `unsafe_scheme`, `relative_without_base`, `invalid_url`, `private_or_loopback_host` (candidate dropped) |
| Ad or tracking host (doubleclick, googlesyndication, taboola, outbrain, criteo, pixel.wp.com, stats.wp.com, feedburner, facebook, quantserve …) | `ad_or_tracking_host` |
| Emoji or avatar host (`s.w.org`, gravatar) | `icon` |
| Path segment `/emoji/`, `/wp-includes/`, `/themes/`, `/plugins/`, `/ads/`, `/adserver/`, `/banners/`, `/avatars/` | `chrome_path` |
| Filename token: `logo(s)` · `avatar(s)`, `gravatar` · `icon(s)`, `favicon`, `sprite(s)`, `emoji` · `banner`, `ad`, `ads`, `advert(isement)`, `adserver`, `sponsored` · `pixel`, `tracking`, `tracker`, `beacon`, `spacer`, `blank` · `placeholder` · `newsletter`, `subscribe`. Matched as **whole tokens** only. | `logo`, `avatar`, `icon`, `banner_ad`, `tracking_pixel`, `placeholder`, `newsletter` |
| Filename bigrams `default image`, `no image` · `share icon`, `share button`, `social icon` | `placeholder` · `icon` |
| SVG | `svg_not_allowed` |
| MIME is an image type other than jpeg/png/webp/avif, or not an image at all | `unsupported_mime` · `not_an_image` |
| Declared size ≤ 2×2 | `tracking_pixel` |
| Declared size below 480×270 (below 120 px for HTML `<img>`, see above) | `too_small` |
| Aspect ratio outside 0.8–2.2 | `aspect_ratio` |

- **Whole-token matching.** `c-5-c-17-share-ramp.jpg` is allowed and
  `site-logo.png` is rejected.
- **Tracking parameters.** `utm_*`, `fbclid`, `gclid`, `mc_cid`, `mc_eid`,
  `_hsenc` and `_hsmi` are removed from the canonical URL. Every other
  query parameter is kept exactly.
- **MIME aliases.** `image/jpg`, `image/pjpeg` and `image/x-png` are
  normalised before the MIME check. JFeed declares `image/jpg`.

The rejection classes in `/api/v1/media/stats` group these codes: **ad**
(`ad_or_tracking_host`, `banner_ad`), **logo**, **tracking_pixel**,
**icon_or_emoji**, **too_small_or_shape**, and **other**.

Rejected rows stay in the database with `validation_status='rejected'` and
`policy_rejection_reason`. They are never used as primary and are hidden
from the API unless `include_rejected=true` is passed.

## Validation (network, bounded)

`validate_image(url)` sends one guarded GET with `Range: bytes=0-65535`
through `net_guard`. `net_guard` handles DNS resolution, blocks private,
loopback, link-local and metadata addresses, re-checks every redirect, and
caps the response at 6 MB.

The response is classified from the actual bytes:

| Status | Meaning |
|---|---|
| `valid` | Real image; signature and dimensions were read. |
| `rejected` | Too small, a pixel, a MIME mismatch, HTML disguised as an image, or final URL not https. |
| `blocked` | The guard refused the request, or the server returned 401/403/451. |
| `unreachable` | Timeout, DNS failure or 5xx. |
| `unknown` / `pending` | Not yet checked. |

Validation runs only in the bounded pilot. It never runs in a loop, and
there is no retry.

## Article fallback

`NEWS_ARTICLE_MEDIA_FALLBACK_ENABLED` is **false** by default. When it is
enabled for a pilot, the fallback makes one GET per article, reads
`text/html` only, stops after 1.5 MB, follows at most 2 redirects, and
reads only `<meta>` and JSON-LD. Hosts not recorded as `robots_allowed`
and `accessible` in `collection-capabilities.json` are skipped without any
request. Responses with 403, a CAPTCHA or a Cloudflare challenge are
recorded and never bypassed.

## Display: hotlink, no proxy

Images load directly from the publisher, using
`referrerPolicy="no-referrer"`, https only, and fixed frames so there is no
layout shift. If loading fails, the neutral placeholder appears.

No image proxy or download was built. Copying images is outside this
project's collection policy: being able to retrieve an image does not grant
the right to redistribute it.

The CSP `img-src` lists the exact hosts in
`apps/web-next/media-image-hosts.json` (15 hosts, no `https:` wildcard).
A new image host shows the placeholder until it is added to that list.

## Legacy columns are not written

The v1 columns (`url`, `relevance`, `rejection_reason`,
`verification_status`, `alt_text`) are what the production API still
reads. Policy v1 writes **only** the v2 columns. A fingerprint over the
legacy columns was identical before and after the migration, both backfills
and the drill.

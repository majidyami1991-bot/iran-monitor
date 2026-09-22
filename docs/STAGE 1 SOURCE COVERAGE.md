# Stage 1 source coverage

Generated from `GET /api/v1/sources/coverage`, which reads the registry, the
discovery evidence and the live database. Regenerate it after any change to the
executable set rather than editing the tables by hand.

Snapshot taken 2026-09-22 16:34 UTC.

## The three counts are not interchangeable

| Count | Value | Meaning |
| --- | ---: | --- |
| Registered | 62 | Canonical sources from the client's `sites.docx`. |
| Executable | 12 | Has a validated, permitted collection path. |
| Monitored | 11 | Has actually completed a successful fetch. |

Reporting 62 as coverage would be wrong: 36 of those entries are X accounts
with no authorised collection path, and 7 publishers refuse automated access.

## Breakdown by state

| State | Count | What it means |
| --- | ---: | --- |
| `active_rss` | 12 | Validated RSS feed, collected every scheduled cycle. |
| `sitemap_candidate` | 5 | No feed; a readable sitemap exists but no tested parser does. |
| `html_candidate` | 2 | No feed and no sitemap; would need an HTML listing parser. |
| `blocked` | 7 | Publisher returns 403 or disallows automated access. Not collected. |
| `not_covered` | 36 | X account. No authorised collection path or usage policy in place. |

| Source type | Registered | Active | Blocked | Candidate | Not covered |
| --- | ---: | ---: | ---: | ---: | ---: |
| news | 17 | 8 | 4 | 5 | 0 |
| think_tank | 9 | 4 | 3 | 2 | 0 |
| x_account | 36 | 0 | 0 | 0 | 36 |

## Active RSS sources (12)

These produce the news flow. `Items` counts stored records; a source added recently may still show zero until its first cycle completes.

| Host | Type | Feed URL | Items | Health | Last success (UTC) |
| --- | --- | --- | --- | --- | --- |
| breakingdefense.com | news | `https://breakingdefense.com/feed/` | 31 | healthy | 2026-09-22T04:38:23 |
| defence-blog.com | news | `https://defence-blog.com/feed/` | 30 | healthy | 2026-09-22T04:38:17 |
| defence-industry.eu | news | `https://defence-industry.eu/feed/` | 30 | healthy | 2026-09-22T04:38:13 |
| jcfa.org | think_tank | `https://jcfa.org/feed/` | 18 | healthy | 2026-09-22T04:38:10 |
| mwi.westpoint.edu | think_tank | `https://mwi.westpoint.edu/feed/` | 10 | healthy | 2026-09-22T04:38:10 |
| news.usni.org | think_tank | `https://news.usni.org/feed` | 35 | healthy | 2026-09-22T04:38:16 |
| rusi.org | think_tank | `https://www.rusi.org/rss/whats-new.xml` | 0 | not_run | not yet |
| www.airandspaceforces.com | news | `https://www.airandspaceforces.com/feed/` | 24 | healthy | 2026-09-22T04:38:22 |
| www.edrmagazine.eu | news | `https://www.edrmagazine.eu/feed` | 21 | healthy | 2026-09-22T04:38:19 |
| www.jfeed.com | news | `https://www.jfeed.com/feed` | 87 | healthy | 2026-09-22T04:38:13 |
| www.missiledefenseadvocacy.org | news | `https://www.missiledefenseadvocacy.org/feed/` | 10 | healthy | 2026-09-22T04:38:14 |
| www.twz.com | news | `https://www.twz.com/feed` | 56 | healthy | 2026-09-22T04:38:12 |

## Sitemap candidates (5)

Reachable and robots-allowed, with a readable sitemap but no feed. Activation needs a sitemap parser plus per-source validation; none is enabled.

| Host | Type | Homepage | Robots allowed |
| --- | --- | --- | --- |
| thedefensepost.com | news | 200 | True |
| www.armyrecognition.com | news | 200 | True |
| www.brookings.edu | think_tank | 200 | True |
| www.defensenews.com | news | 200 | True |
| www.janes.com | news | 200 | True |

## HTML listing candidates (2)

Reachable and robots-allowed, but discovery found neither a feed nor a usable sitemap. Activation needs a per-source HTML listing parser.

| Host | Type | Homepage | Robots allowed |
| --- | --- | --- | --- |
| www.csis.org | think_tank | 200 | True |
| www.nationaldefensemagazine.org | news | 200 | True |

## Blocked sources (7)

The publisher returns 403 to automated requests or disallows them in robots.txt. These are **not** collected and no attempt is made to work around the refusal. Reaching them would require the publisher's permission or a licensed feed.

| Host | Type | Homepage | Robots allowed |
| --- | --- | --- | --- |
| www.airuniversity.af.edu | news | 403 | False |
| www.centcom.mil | news | 403 | False |
| www.iiss.org | think_tank | 403 | False |
| www.inss.org.il | think_tank | 403 | False |
| www.rand.org | think_tank | 403 | False |
| www.realcleardefense.com | news | 403 | False |
| www.war.gov | news | 403 | False |

## X accounts, not covered (36)

Listed in the source document but not collected. X requires an authorised API
tier, and the terms for storing and redisplaying posts are a commercial and
legal decision, not a technical one. **The product must not present these as
monitored.** They appear in the registry and in this report only.

| Handle | Handle | Handle | Handle |
| --- | --- | --- | --- |
| `@inbarspace` | `@CONVAlR` | `@GEOIMINT` | `@OSINTWarfare` |
| `@NatSecLedger` | `@ThetiMapping` | `@MenchOsint` | `@Schizointel` |
| `@Gomnam_User` | `@Intel_Sky` | `@awes_spad` | `@benreuter_IMINT` |
| `@FarzinNadimi` | `@sam_lair` | `@ResindScientist` | `@IsraelRadar_com` |
| `@john_krzyzaniak` | `@mohsenreyhani01` | `@Fath_ol_Mobin` | `@FRHoffmann1` |
| `@mhmiranusa` | `@no_itsmyturn` | `@miguyan2000` | `@ELINTNews` |
| `@tired_phantom` | `@GuyPlopsky` | `@Pataramesh` | `@dex_eve` |
| `@Israel_Alma_org` | `@maysam21901` | `@TMEDefence` | `@IntelliTimes` |
| `@DaveSchmerler` | `@manniefabian` | `@imp_navigator` | `@ArmsControlWonk` |

## What would raise coverage

| Step | Gain | Needs |
| --- | --- | --- |
| Sitemap parser + per-source validation | up to +5 | Engineering. Each sitemap differs; each needs its own test. |
| HTML listing parser | up to +2 | Engineering, and re-checking after any site redesign. |
| Licensed or permitted access for blocked publishers | up to +7 | A commercial or legal agreement. Not a technical task. |
| X API access | up to +36 | A paid API tier and a decision on storage and redisplay terms. |

Nothing above is scheduled. Each is listed so the coverage gap is explicit.

# Information Architecture (reference redesign)

## Primary navigation

خانه · اخبار · استوری‌ها · گزارش روزانه · رویدادها · موضوعات · منابع ·
تحلیل ▾ (تحلیل آماری، نقشه، شبکه‌های اجتماعی) ·
آینده‌پژوهی ▾ (روندها، سیگنال‌های ضعیف، عدم‌قطعیت‌ها، پیشران‌ها و STEEP، سناریوها) ·
پایش سامانه ▾ (وضعیت پایش، بازبینی محتوا، هشدارها، درباره و روش‌ها)

Phones get a drawer with the same groups, plus search, clock and the language
toggle.

## Home page order

1. Breaking ticker (rule `breaking_v1`; falls back to a clearly labelled "latest").
2. Stories rail.
3. Lead story plus two secondary stories, next to the Daily Briefing card.
4. Latest headlines (newest / most important / most covered), rows plus a compact column.
5. Events timeline (latest / most important) next to Social status.
6. Activity (48 h) and Commodity prices (connection status).

## Routes

| Route | Content | Data |
|---|---|---|
| `/` | Newsroom home | breaking, stories, feed, briefing, timeline/events, activity, integrations, social |
| `/news` | Stream with shareable query-string filters (q, source, category, subtopic, window, date range, language, importance, translation, sort, page) | `/api/v1/feed` |
| `/news/{id}` | Bilingual detail, provenance, v3 classification and history, importance, media and documents, event, related | `/api/v1/news/{id}`, `/api/v1/feed/{id}/context` |
| `/stories` | All stories as a grid; same viewer | `/api/v1/stories` |
| `/briefing` | Full rule-based briefing, stored versions, gaps | `/api/v1/briefing/daily` |
| `/events`, `/events/{id}` | Timeline; event story in chronological order with membership reasons | `/api/v1/timeline/events` |
| `/topics`, `/topics/{slug}` | Taxonomy v3 overview; category or subtopic page | `/api/v1/topics` |
| `/sources`, `/sources/{id}` | Source profiles | `/api/v1/source-profiles` |
| `/analytics` | Eight question-led charts | `/api/v1/insights/overview` |
| `/map` | Honest empty state, geo contract, OSINT integration status | `/api/v1/geo` |
| `/social` | X integration status, registered handles | `/api/v1/social` |
| `/monitoring`, `/review/content` | Retained pages (collector health, translation review queue) | existing APIs |
| `/foresight/*` | Descriptive trends, weak signals, data uncertainty, STEEP mapping; scenarios empty | `/api/v1/foresight/*` |
| `/alerts` | System notifications plus alert-rule status | `/api/v1/alerts` |
| `/about` | Principles, live rule versions, integration registry | `/api/v1/rules`, `/api/v1/integrations` |
| `/categories`, `/categories/{id}` | Redirect to `/topics` (v2 ids mapped to v3) | — |

## Scope note for the client

The earlier stage-1 instruction was not to present correlation, trend or
foresight capabilities as available. The foresight menu now exists because
this brief requests it. Every foresight page opens with a scope statement: it
shows descriptive counts only, not forecasts, and it leaves scenarios, drivers
and strategic uncertainties empty until an analyst records them. **The client
should confirm this framing is acceptable** before production promotion, or
the foresight group can be hidden with a one-line change in `design/Shell.tsx`.

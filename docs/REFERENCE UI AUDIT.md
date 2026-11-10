# Reference UI Audit — iranmonitor.org/fa

Branch `feature/iranmonitor-reference-redesign`, 2026-09-28.

## Access status: blocked, not bypassed

The reference site was opened once in a real browser (Edge, headless, driven by
Playwright over CDP), at desktop 1440×900 and mobile 390×844. Both requests to
`https://www.iranmonitor.org/fa` returned **HTTP 403** with the Cloudflare
managed-challenge page ("چند لحظه صبر کنید… در حال انجام تایید امنیتی").
The challenge never resolved.

In line with the project's collection policy, nothing was done to get around
it: no challenge solving, no user-agent or header tricks, no third-party cache
or archive copies, no retries. No content, markup, copy, image, logo or code
was retrieved from the reference site. The probe script and its raw result are
in `runtime/redesign-baseline/reference/` (screenshots of the challenge page
only; git-ignored). This matches the Stage A result recorded in
`docs/IRANMONITOR REFERENCE FEATURE GAP.md`.

No screenshots of the reference site were supplied with the brief.

## What this audit is therefore based on

Only the section list that the brief itself names as the reference's feature
set. **None of the items below were observed on the reference site**, and no
visual or behavioural claim about it is made here: not its colours, spacing,
typography, motion, card design, image treatment, skeleton/empty/error
states, internal pages or responsive behaviour. Those parts of the requested
audit could not be performed.

| # | Feature named in the brief | Observed on reference? | Defence Monitor implementation |
|---|---|---|---|
| 1 | Header and navigation | No (blocked) | Masthead with live status, search, Tehran clock + Jalali date, content-language toggle, notifications; grouped primary nav; mobile drawer |
| 2 | Breaking-news ticker | No | One-at-a-time ticker (never a marquee), pause/prev/next, pauses on hover/focus, audited rule `breaking_v1` |
| 3 | Stories rail | No | Data-driven stories (`stories_v1`), full-screen viewer with progress, keyboard/touch, seen/new ring |
| 4 | Daily Briefing | No | Rule-based briefing, stored append-only; AI summary slot shows real provider status |
| 5 | Latest Headlines | No | Lead / standard / row / compact hierarchy; newest / most important / most covered |
| 6 | Events Timeline | No | Event clustering v2, timeline with sources, confidence, coverage pulse; event detail story |
| 7 | Activity & Commodity Prices | No | Real activity (48 h hourly, source freshness, events); commodity panel shows "connection not configured" |
| 8 | Live Tweets | No | Social panel shows real integration status and the 36 registered X handles; no posts shown |

`REFERENCE_FEATURE_COUNT = 8` (named in the brief, none observed).

## Independence

The Defence Monitor identity (name, mark, amber signal accent, dark ink palette,
Vazirmatn typography, category artwork) is original to this project. Design
decisions are documented in `docs/COMMERCIAL DESIGN SYSTEM.md` and justified
by this product's own data, not by the reference.

## What would complete this audit

Screenshots or a recorded walkthrough of the reference, supplied by the client
from a normal browser session, or written permission from the reference
site's operator for automated access. Either would allow the visual and
interaction sections of the brief to be audited against observed behaviour.

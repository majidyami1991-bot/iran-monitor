# Project Architecture and Translation Plan

Written for: the project owner (majid.yami1991@gmail.com), as a standing
reference — not tied to any single work phase. Answers four recurring
questions; update this file rather than re-explaining from scratch next time.

## 1. Architecture overview

Five containers (`deployment/news-monitor/compose.yml`), one Postgres
database, one internal Docker network:

```
RSS feeds (public, robots/paywall-respecting)
   │  one bounded HTTP GET per source, no retries, 2 MB cap
   ▼
news-collector  (apps/api/collector.py)
   │  writes rows, never mutates existing ones
   ▼
news-db  (Postgres 16)  ◄────────────┐
   │  read by                        │ read/written by
   ▼                                 │
news-api  (apps/api/main.py + ops.py, FastAPI/uvicorn, port 3000 internal)
   │  JSON over /api/v1/...
   ▼
news-web  (apps/web-next, Next.js, published at 127.0.0.1:3001)
```

- **Input**: RSS/Atom feeds only, one source list in `config/sources/`. The
  collector (`apps/api/collector.py`) is a scheduled, opt-in, no-retry cycle —
  it stores what a feed *declares* (title, summary, link, published date) and
  marks provenance status; it does not scrape arbitrary web pages.
- **Output**: the API's JSON endpoints (`/api/v1/items`, `/api/v1/news/...`,
  `/api/v1/sources`, `/api/v1/stats/...`) and the web app's rendered pages
  (`/news`, `/news/{id}`, `/sources`, `/analytics`, `/review/content`).
- A separate `news-translate` / `translate_worker.py` process (now built on
  `ai_gateway.py` + `content_intelligence.py`) is the only thing that calls an
  external AI provider, and only when one is explicitly configured.
- Everything downstream of the collector — API, web, translation — treats the
  database as the single source of truth. Nothing in this stack calls a news
  source live from a user-facing request.

## 2. Is there a database, or does the frontend fetch fresh every time?

Both, in the sense that matters:

- **Yes, there is a database.** PostgreSQL 16, one persistent volume
  (`news-db-data`), holding `news_items`, `sources`, `news_item_translations`
  (+ history), `content_key_points`, provenance/audit tables, etc. This is
  the only place data lives — nothing is scraped or re-fetched on demand.
- **The frontend does re-fetch on every page load/reload**, but from *this*
  database via the API, not from the original news sources. Confirmed in
  code: `apps/web-next/app/design/useApi.ts` calls
  `fetch('/api/v1/'+path, { cache: 'no-store' })` — deliberately
  no-store, so a reload always shows current DB state, never a stale
  client-side cache. There is no static generation and no CDN-level caching
  of news content.
- So: the collector writes to the DB on its own schedule (independent of any
  visitor); a page reload just re-reads what's already there. A visitor
  reloading the page never triggers a new fetch from the original source.

## 3. Should a translation be stored, or generated on the fly each time?

**Store it.** This is already how the project is built, and it's the right
call for this project specifically, not just a generic best practice:

- **Cost**: an on-the-fly design would mean a Claude/GPT call on every page
  view — for a monitoring dashboard with repeat visits, that multiplies cost
  for no benefit, since the source article isn't changing between views.
  Storing means the AI provider is called once per item per field.
- **Latency and availability**: a stored translation renders as fast as any
  other DB read. On-the-fly would put an external API call, with its own
  latency and failure modes, directly in the request path of a page load.
- **Auditability**: the brief for this project requires knowing *which*
  provider/model/prompt-version produced a given piece of text, and being
  able to show the original untouched alongside it. That requires a stored
  row with metadata, not a transient response.
- **Human review**: `/review/content` lets a person approve, reject, edit, or
  request regeneration. None of that is possible if nothing is persisted.
- **Non-destructive correction**: `news_item_translations` holds the current
  version; `news_item_translation_history` is append-only, so a re-translation
  (new prompt version, corrected output, human edit) never destroys the
  record of what was shown before.

Concretely, this is already implemented: `news_item_translations` (current,
one row per item+field) plus `news_item_translation_history` (append-only
lineage) plus `content_key_points`. Generating on the fly was never adopted
and would be a regression from this.

## 4. Translation policy and tooling — recommendation

**Decision already on record** (2026-09-23, client-approved — see project
memory `iran-monitor-translation-decision`):
- Scope: Persian **title + summary** only (full body translation was offered
  and declined on cost grounds, ~$4–9/mo vs. ~$25–50/mo at measured volume).
- Provider: cloud, no data-residency restriction.
- Presentation: published immediately, always carrying a visible "ترجمه
  ماشینی" (machine translation) label — not gated behind human review.
- Configured for `AI_PROVIDER=anthropic`, model `claude-sonnet-5`
  (`claude-haiku-4-5` as the cheaper alternative). **The only blocker today is
  that no real `AI_API_KEY` has been supplied** — every code path is wired
  and tested against a fake adapter, but zero real calls have been made.

**What's now built on top of that decision** (the Content Intelligence phase,
commits `0140504`/`d83b132`/`64d4efa`/`9671eb5`), which I'd recommend keeping
rather than reverting to a simpler direct-call design:

- All translation/summary calls go through one provider-agnostic layer
  (`apps/api/ai_gateway.py`) — switching providers or models is an `.env`
  change, never a code change, and a provider/prompt-version change is
  guaranteed to bypass any stale cache (`docs/AI GATEWAY.md`).
- An independent, non-AI validator (`apps/api/content_validator.py`) checks
  numbers, dates, model/unit codes, and negation are preserved, and rejects
  empty/placeholder/echoed output — this runs regardless of which provider
  is used, so provider quality regressions are caught mechanically.
- A `/review/content` queue exists for staff quality control, but — matching
  the client's original decision — it does **not** gate what a visitor sees.
  A generated translation displays immediately with its machine-translation
  badge; the review queue is where a person can later fix or roll back a bad
  one, not a pre-publish approval gate. (Verified in
  `apps/web-next/app/components/NewsDetail.tsx`: the badge and text render
  based on whether a translation exists, not on `review_status`.)

**My suggestion, concretely**:
1. Keep the scope as decided (title + summary; body translation stays
   available to switch on later without any new code, given how the field
   list already works).
2. Supply a real `AI_API_KEY` for Anthropic and set `AI_PROVIDER=anthropic`,
   `AI_MODEL_TRANSLATION=claude-haiku-4-5` to start (cheaper; upgrade to
   `claude-sonnet-5` later only if quality on real Persian output needs it —
   this is a one-line `.env` change either way, not a code change).
3. Run `translate_worker.py --limit 5 --dry-run` first, look at real output
   and real per-item cost, then widen gradually — exactly as
   `docs/AI PROVIDER CONFIGURATION.md` steps 6-10 already describe.
4. Keep the machine-translation label and immediate publish (per the
   client's decision) — use the review queue as an ongoing quality-control
   tool, not a publishing bottleneck.
5. Do **not** use your own personal Claude Code/API credentials for this —
   the service needs its own key, separately billed and revocable.

Related docs for deeper detail: `docs/AI GATEWAY.md`,
`docs/AI PROVIDER CONFIGURATION.md`, `docs/TRANSLATION AND SUMMARY QUALITY.md`,
`docs/HUMAN REVIEW WORKFLOW.md`, `docs/CONTENT INTELLIGENCE ARCHITECTURE.md`.

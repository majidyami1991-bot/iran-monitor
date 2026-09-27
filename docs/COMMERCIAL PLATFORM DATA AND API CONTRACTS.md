# Commercial Platform — Data Inventory, Proposed Contracts, Migration Plan

Stage A deliverable. Everything below is a **design**, not an applied
change: no `ALTER TABLE`/`CREATE TABLE` in this document has been run
against any database, no API endpoint listed as "proposed" has been
registered, per Stage A's explicit "no production mutation" rule. All of it
is additive to what already exists, following the same non-destructive
discipline already proven in the Content Intelligence phase (versioned
rows, append-only history, idempotent `migrate()`).

## 1. What already exists (verified live, 2026-09-26)

Full column inventory pulled directly from the running database, not from
documentation (documentation for `item_classifications`/taxonomy was found
to be one version behind live — see
`docs/COMMERCIAL INFORMATION ARCHITECTURE.md` §1 note):

| Table | Purpose | Notable columns |
| --- | --- | --- |
| `news_items` | Core article record | `title`, `summary`, `canonical_url`, `published_at`, `provenance_status`, `classification`, `taxonomy_version`, `topics` (jsonb) |
| `sources` | Registered feeds | `health_status`, `consecutive_failures`, `last_success_at`, `collection_tier` — **no** `country`, `ownership`, or `bias` column |
| `news_item_content` | Extracted body | `original_language`, `original_text`, `display_policy` |
| `news_item_translations` (+`_history`) | Versioned MT output | `provider`, `model`, `prompt_version`, `quality_score`, `review_status`, `reviewed_by`/`reviewed_at` |
| `content_key_points` | Evidence-checked key points | `evidence_span`, `evidence_verified` |
| `news_item_media` | Images/documents | `verification_status`, `content_sha256`, `copyright_status`, `security_status` — **no** lat/lon anywhere |
| `item_classifications` | Taxonomy v2 result | `category_id`, `topics` (jsonb, multi-label), `confidence`, `human_locked` |
| `news_events` / `news_event_members` | Deterministic clustering | `clustering_method`, `algorithm_version`, `similarity_score`, `membership_reason` (jsonb) — **no** `locations`, `actors`, `organizations`, `analyst_status`, `confidence` |
| `collection_runs` / `source_run_results` | Operational history | full per-cycle and per-source detail |
| `ai_requests_log` / `ai_response_cache` | AI Gateway audit/cache | provider/model/prompt-version-keyed |
| `enrichment_jobs` | Background task queue | `stage`, `status`, `attempts` |

Nothing above needs to change to support Implement-decision features in
`docs/IRANMONITOR REFERENCE FEATURE GAP.md`. Everything below supports a
**Scaffold**-decision feature and is explicitly proposed for a later stage's
gate, not this one.

## 2. Proposed additive migrations (not applied)

All follow the existing pattern: `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
/ `CREATE TABLE IF NOT EXISTS`, applied via the idempotent `migrate()` in
`apps/api/ops.py` that already runs safely on every container start.

### 2.1 Event enrichment (for §9 — Events and Timeline)

```sql
ALTER TABLE news_events ADD COLUMN IF NOT EXISTS locations jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE news_events ADD COLUMN IF NOT EXISTS actors jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE news_events ADD COLUMN IF NOT EXISTS organizations jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE news_events ADD COLUMN IF NOT EXISTS topics jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE news_events ADD COLUMN IF NOT EXISTS confidence real;
ALTER TABLE news_events ADD COLUMN IF NOT EXISTS analyst_status text NOT NULL DEFAULT 'proposed';
-- analyst_status: proposed | confirmed | merged | split | rejected
ALTER TABLE news_event_members ADD COLUMN IF NOT EXISTS stance text;
-- stance: corroborating | contradictory | unrelated_but_linked (nullable = not yet assessed)

CREATE TABLE IF NOT EXISTS news_event_audit(
  audit_id bigserial PRIMARY KEY,
  event_id text NOT NULL,
  action text NOT NULL, -- proposed | confirmed | merged_into | split_from | member_added | member_removed | correction
  actor text NOT NULL,  -- 'system:clustering-1.0.0' or a human reviewer name
  detail jsonb,
  created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS news_event_audit_event_idx ON news_event_audit(event_id, created_at);
```

Every AI-proposed event starts `analyst_status='proposed'` per brief §9's
explicit rule ("خروجی AI بدون تأیید، «رخداد پیشنهادی» باشد"). No causal
relationship is ever stored — `stance` records *corroboration*, never
causation, matching "هیچ رابطه علّی از صرف هم‌زمانی ساخته نشود."

### 2.2 Geolocation, for `/map` (§12) — explicitly gated

```sql
CREATE TABLE IF NOT EXISTS event_locations(
  location_id bigserial PRIMARY KEY,
  event_id text NOT NULL REFERENCES news_events(event_id),
  place_name text NOT NULL,
  latitude double precision NOT NULL,
  longitude double precision NOT NULL,
  precision text NOT NULL, -- exact | city | region | country
  extraction_method text NOT NULL, -- e.g. 'human_review', never 'guessed'
  confidence real NOT NULL,
  source_url text,
  verified boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS event_locations_event_idx ON event_locations(event_id);
```

`extraction_method` and `confidence` are **required, not optional** columns
— by design, this table structurally cannot hold a point with no stated
provenance. This table is proposed schema only; nothing populates it until
a real geolocation-extraction step exists and is separately approved, per
the brief's explicit prohibition on guessed coordinates.

### 2.3 Daily Brief (§5-c, §8)

```sql
CREATE TABLE IF NOT EXISTS daily_briefs(
  brief_date date PRIMARY KEY,
  executive_summary_fa text,
  top_developments jsonb NOT NULL DEFAULT '[]'::jsonb, -- [{item_id|event_id, headline_fa, why_it_matters_fa, confidence}]
  provider text, model text, prompt_version text,
  generation_status text NOT NULL DEFAULT 'not_generated', -- not_generated | provider_not_configured | generated | needs_review
  review_status text NOT NULL DEFAULT 'not_applicable',
  reviewed_by text, reviewed_at timestamptz,
  generated_at timestamptz,
  superseded_at timestamptz);
```

A new AI Gateway task type `daily_brief` (shape: `{"executive_summary": str,
"top_developments": [...]}`, genuinely different from the existing
`summary`/`key_point_extraction` shapes) would back generation — reusing
the same fail-closed validation, prompt-versioning, and audit-log pattern
already proven in the Content Intelligence phase. Not implemented this
stage.

### 2.4 Integration registry (§15)

```sql
CREATE TABLE IF NOT EXISTS integration_registry(
  integration_id text PRIMARY KEY, -- e.g. 'commodity_prices', 'airnav', 'marinetraffic', 'polymarket', 'live_tv', 'x_social', 'ioda', 'ooni', 'cloudflare_radar'
  display_name text NOT NULL,
  provider text,
  status text NOT NULL DEFAULT 'not_configured', -- not_configured | configured | error
  auth_required boolean NOT NULL DEFAULT true,
  legal_notes text,
  update_frequency text,
  last_successful_fetch_at timestamptz,
  schema_ref text, -- doc/table this integration would populate
  cost_notes text,
  enabled boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now());
```

Seeded (rows inserted, `enabled=false`, no fetch code attached) for every
integration named in brief §15: commodity prices, AirNav, MarineTraffic,
Polymarket, Live TV, X/social, IODA, OONI, Cloudflare Radar. Seeding rows
describing an integration is not "calling" it — no network code accompanies
this table in this stage.

### 2.5 Social account registry (§13)

```sql
CREATE TABLE IF NOT EXISTS social_accounts(
  account_id bigserial PRIMARY KEY,
  platform text NOT NULL DEFAULT 'x',
  handle text NOT NULL,
  display_name text,
  category text NOT NULL, -- media | journalist | official_body | researcher | other
  status text NOT NULL DEFAULT 'connector_not_configured',
  added_at timestamptz NOT NULL DEFAULT now());
```

### 2.6 AI Analyst audit (§16)

```sql
CREATE TABLE IF NOT EXISTS ai_analyst_queries(
  query_id bigserial PRIMARY KEY,
  asked_by text,
  question text NOT NULL,
  answer text,
  citations jsonb NOT NULL DEFAULT '[]'::jsonb, -- [{item_id|event_id, quoted_span}]
  confidence_note text, -- e.g. 'insufficient_evidence'
  status text NOT NULL DEFAULT 'provider_not_configured',
  created_at timestamptz NOT NULL DEFAULT now());
```

## 3. Proposed API endpoints (not registered)

| Method & path | Purpose | Notes |
| --- | --- | --- |
| `GET /api/v1/brief/daily?date=` | Daily Intelligence Brief | 404/`not_generated` if that date has none |
| `GET /api/v1/map/events` | Geolocated events only | Returns `[]` honestly until §2.2 has real rows |
| `GET /api/v1/integrations` | Integration Registry list | Read-only, powers the transparency page and the disabled-state UI |
| `GET /api/v1/social/accounts` | Registered X accounts by category | No live pull; static registry read |
| `POST /api/v1/analyst/query` | AI Analyst | Returns `501`/`provider_not_configured` today; full contract (citations required in response, confidence field, refusal path) documented but not implemented |
| `GET /api/v1/review/events` | Event review queue | Mirrors `/api/v1/review/content`'s shape |
| `POST /api/v1/review/events/{event_id}/confirm` | Analyst confirms a proposed event | Sets `analyst_status='confirmed'`, writes `news_event_audit` |
| `POST /api/v1/review/events/{event_id}/merge` | Merge two proposed events | Writes `news_event_audit` for both event_ids, never deletes the losing event's history |
| `POST /api/v1/review/events/{event_id}/split` | Split members out into a new event | Writes `news_event_audit`; new event gets its own `event_id` |
| `PATCH /api/v1/news/{item_id}/location` (or event-level equivalent) | Human-entered/corrected location | The only way `event_locations.verified` becomes `true` without a licensed geocoding step |

Existing endpoints already usable without change: `/api/v1/events`,
`/api/v1/events/{id}`, `/api/v1/categories`, `/api/v1/categories/{id}`,
`/api/v1/sources`, `/api/v1/sources/{id}`, `/api/v1/stats/*`,
`/api/v1/ai/status`, `/api/v1/ai/usage`, `/api/v1/review/content*`.

## 4. Migration plan (for when a later stage is approved to apply it)

1. Add the SQL in §2 to `ops.py`'s `DDL` string, in the same file where
   every prior phase's migration lives — one continuously-growing,
   idempotent script, not a separate migration framework.
2. Before applying: snapshot `md5(string_agg(item_id,',' ORDER BY item_id))`
   over `news_items` (and the equivalent for `news_events`), exactly as done
   in the Content Intelligence phase.
3. Apply via a container restart (the existing `migrate()` runs on every
   API startup).
4. Re-run the same hash query; it must be identical. Confirm every new
   column defaults correctly (`NOT NULL DEFAULT` values, or nullable where
   "not yet assessed" is the honest state).
5. Prove rollback safety the same way as the Content Intelligence phase:
   execute an INSERT using the exact pre-migration column list against the
   migrated schema and confirm it still succeeds.
6. Run the full offline test suite (a hard gate in the Docker build, per
   existing project convention) before any deploy.

## 5. Rollback plan

Because every change above is additive (`ADD COLUMN IF NOT EXISTS` /
`CREATE TABLE IF NOT EXISTS`, all new columns nullable or safely defaulted),
rollback is: **revert the code** (git revert the migration commit, redeploy
the prior image). No `DROP COLUMN`/`DROP TABLE` is ever required or
proposed — the new columns/tables simply go unused by reverted code,
exactly as `news_item_translations`' new columns from the Content
Intelligence phase remain harmlessly unused by any code that doesn't know
about them. This is the same rollback discipline already exercised live in
this project (`docs/UI UX QA REPORT.md` §6: a real rollback→roll-forward
cycle was run against production and both states passed health checks) and
does not need to be re-invented.

**Nothing in this document has been applied.** This stage produced a plan,
not a schema change — the next explicit gate (Stage B/C/D approval) decides
what, if anything, gets built from it.

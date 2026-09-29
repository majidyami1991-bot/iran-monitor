"""Versioned, additive migrations for the reference-redesign phase.

Every statement is CREATE ... IF NOT EXISTS or ADD COLUMN IF NOT EXISTS:
nothing existing is altered, renamed, retyped or dropped, so the previous API
and web images keep working against a migrated database (that is the rollback
path — see docs/DEPLOYMENT AND ROLLBACK.md).

Each migration is recorded in schema_migrations with a checksum of its SQL, so
a later change to an already-applied migration is detected instead of
silently diverging between databases.
"""
import hashlib
import json

import psycopg

MIGRATIONS = [
    ('2026.09.28-01', 'taxonomy v3 assignments, history trigger, event metadata', '''
CREATE TABLE IF NOT EXISTS item_topic_assignments(
  item_id text NOT NULL REFERENCES news_items(item_id),
  taxonomy_version text NOT NULL,
  category_id text NOT NULL,
  category_label text NOT NULL,
  secondary jsonb NOT NULL DEFAULT '[]'::jsonb,
  subtopics jsonb NOT NULL DEFAULT '[]'::jsonb,
  evidence jsonb NOT NULL DEFAULT '[]'::jsonb,
  scores jsonb NOT NULL DEFAULT '{}'::jsonb,
  confidence real,
  other_reason_code text,
  method text NOT NULL,
  human_locked boolean NOT NULL DEFAULT false,
  human_note text,
  assigned_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(item_id, taxonomy_version));
CREATE INDEX IF NOT EXISTS item_topic_assignments_cat_idx ON item_topic_assignments(taxonomy_version, category_id);
CREATE TABLE IF NOT EXISTS item_topic_assignment_history(
  history_id bigserial PRIMARY KEY,
  item_id text NOT NULL,
  taxonomy_version text NOT NULL,
  category_id text NOT NULL,
  category_label text NOT NULL,
  secondary jsonb,
  subtopics jsonb,
  evidence jsonb,
  confidence real,
  other_reason_code text,
  method text,
  human_locked boolean,
  human_note text,
  change_kind text NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS item_topic_assignment_history_item_idx ON item_topic_assignment_history(item_id, recorded_at);
CREATE OR REPLACE FUNCTION log_item_topic_assignment() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'UPDATE' AND NEW.category_id IS NOT DISTINCT FROM OLD.category_id
     AND NEW.secondary IS NOT DISTINCT FROM OLD.secondary
     AND NEW.other_reason_code IS NOT DISTINCT FROM OLD.other_reason_code
     AND NEW.human_locked IS NOT DISTINCT FROM OLD.human_locked
     AND NEW.confidence IS NOT DISTINCT FROM OLD.confidence THEN
    RETURN NEW;
  END IF;
  INSERT INTO item_topic_assignment_history(item_id,taxonomy_version,category_id,category_label,secondary,subtopics,
    evidence,confidence,other_reason_code,method,human_locked,human_note,change_kind)
  VALUES(NEW.item_id,NEW.taxonomy_version,NEW.category_id,NEW.category_label,NEW.secondary,NEW.subtopics,
    NEW.evidence,NEW.confidence,NEW.other_reason_code,NEW.method,NEW.human_locked,NEW.human_note,
    CASE WHEN TG_OP='INSERT' THEN 'assigned' WHEN NEW.human_locked AND NOT OLD.human_locked THEN 'human_override'
         ELSE 'reclassified' END);
  RETURN NEW;
END $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS item_topic_assignment_history_trg ON item_topic_assignments;
CREATE TRIGGER item_topic_assignment_history_trg AFTER INSERT OR UPDATE ON item_topic_assignments
  FOR EACH ROW EXECUTE FUNCTION log_item_topic_assignment();
ALTER TABLE news_events ADD COLUMN IF NOT EXISTS primary_category text;
ALTER TABLE news_events ADD COLUMN IF NOT EXISTS confidence real;
ALTER TABLE news_events ADD COLUMN IF NOT EXISTS confidence_level text;
'''),
    ('2026.09.28-02', 'stories, daily briefings, integration registry', '''
CREATE TABLE IF NOT EXISTS stories(
  story_id text PRIMARY KEY,
  kind text NOT NULL,
  position integer NOT NULL,
  title_fa text NOT NULL,
  subtitle_fa text,
  collection_label text NOT NULL,
  target_type text NOT NULL,
  target_ref text,
  target_href text NOT NULL,
  frames jsonb NOT NULL DEFAULT '[]'::jsonb,
  visual jsonb NOT NULL DEFAULT '{}'::jsonb,
  rule_id text NOT NULL,
  rule_version text NOT NULL,
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  content_updated_at timestamptz,
  generated_at timestamptz NOT NULL DEFAULT now(),
  retired_at timestamptz);
CREATE INDEX IF NOT EXISTS stories_active_idx ON stories(position) WHERE retired_at IS NULL;
CREATE TABLE IF NOT EXISTS daily_briefings(
  briefing_id bigserial PRIMARY KEY,
  briefing_date date NOT NULL,
  window_start timestamptz NOT NULL,
  window_end timestamptz NOT NULL,
  generator text NOT NULL,
  generator_version text NOT NULL,
  ai_generated boolean NOT NULL DEFAULT false,
  ai_status text NOT NULL,
  ai_provider text,
  ai_model text,
  ai_prompt_version text,
  executive_summary_fa text,
  payload jsonb NOT NULL,
  generated_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS daily_briefings_date_idx ON daily_briefings(briefing_date DESC, generated_at DESC);
CREATE TABLE IF NOT EXISTS integrations(
  integration_id text PRIMARY KEY,
  kind text NOT NULL,
  name_fa text NOT NULL,
  status text NOT NULL,
  enabled boolean NOT NULL DEFAULT false,
  reason_fa text,
  contract jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now());
'''),
    ('2026.09.28-03', 'empty ingestion contracts: commodities, social, geo, alerts', '''
CREATE TABLE IF NOT EXISTS commodity_prices(
  observation_id bigserial PRIMARY KEY,
  commodity_code text NOT NULL,
  value numeric NOT NULL,
  unit text NOT NULL,
  currency text,
  observed_at timestamptz NOT NULL,
  provider text NOT NULL,
  provider_url text,
  license_ref text NOT NULL,
  ingested_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(commodity_code, observed_at, provider));
CREATE TABLE IF NOT EXISTS social_posts(
  post_id text PRIMARY KEY,
  platform text NOT NULL,
  account_handle text NOT NULL,
  posted_at timestamptz NOT NULL,
  text text,
  media jsonb NOT NULL DEFAULT '[]'::jsonb,
  url text NOT NULL,
  engagement jsonb,
  collected_at timestamptz NOT NULL DEFAULT now(),
  collection_method text NOT NULL,
  provenance jsonb NOT NULL DEFAULT '{}'::jsonb);
CREATE TABLE IF NOT EXISTS geo_mentions(
  geo_id bigserial PRIMARY KEY,
  item_id text REFERENCES news_items(item_id),
  event_id text REFERENCES news_events(event_id),
  place_name text NOT NULL,
  country_code text,
  lat double precision,
  lon double precision,
  precision text NOT NULL,
  method text NOT NULL,
  confidence real NOT NULL,
  evidence_span text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS alert_rules(
  rule_id text PRIMARY KEY,
  name_fa text NOT NULL,
  condition jsonb NOT NULL,
  enabled boolean NOT NULL DEFAULT false,
  created_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now());
'''),
    ('2026.09.29-01', 'AI audit: model that actually served a call and provider-reported cost', '''
ALTER TABLE ai_requests_log ADD COLUMN IF NOT EXISTS response_model text;
ALTER TABLE ai_requests_log ADD COLUMN IF NOT EXISTS reported_cost_usd numeric(12,6);
ALTER TABLE news_item_translations ADD COLUMN IF NOT EXISTS response_model text;
ALTER TABLE news_item_translation_history ADD COLUMN IF NOT EXISTS response_model text;
ALTER TABLE news_item_translation_history ADD COLUMN IF NOT EXISTS reported_cost_usd numeric(12,6);
'''),
    ('2026.09.29-02', "status semantics: a validation-failed translation is 'needs_review', never 'available'", '''
UPDATE news_item_translations SET status = 'needs_review', updated_at = now()
 WHERE status = 'available' AND review_status = 'needs_review' AND NOT human_reviewed;
'''),
    ('2026.09.29-03', 'X-FREE: manually monitored X accounts and analyst-registered posts', '''
CREATE TABLE IF NOT EXISTS x_accounts(
  id bigserial PRIMARY KEY,
  source_id text NOT NULL UNIQUE,
  handle text NOT NULL,
  handle_key text NOT NULL UNIQUE,
  display_name text,
  profile_url text NOT NULL,
  description text,
  category text,
  monitoring_mode text NOT NULL DEFAULT 'manual',
  status text NOT NULL DEFAULT 'manual_monitoring',
  last_manual_post_at timestamptz,
  post_count integer NOT NULL DEFAULT 0,
  provenance_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS x_posts(
  id bigserial PRIMARY KEY,
  post_id text NOT NULL UNIQUE,
  source_id text NOT NULL REFERENCES x_accounts(source_id),
  post_url text NOT NULL UNIQUE,
  author_handle text NOT NULL,
  original_text text,
  translated_text_fa text,
  summary_fa text,
  published_at timestamptz,
  manually_registered_at timestamptz NOT NULL DEFAULT now(),
  topic_id text,
  event_id text REFERENCES news_events(event_id),
  related_item_id text REFERENCES news_items(item_id),
  analyst_note text,
  importance text NOT NULL DEFAULT 'medium',
  verification_status text NOT NULL DEFAULT 'unverified',
  availability_status text NOT NULL DEFAULT 'link_only',
  provenance_json jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS x_posts_source_idx ON x_posts(source_id, manually_registered_at DESC);
CREATE TABLE IF NOT EXISTS x_post_media(
  id bigserial PRIMARY KEY,
  post_id text NOT NULL REFERENCES x_posts(post_id),
  media_type text NOT NULL,
  external_url text NOT NULL,
  alt_text text,
  provenance_json jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS x_post_history(
  id bigserial PRIMARY KEY,
  post_id text NOT NULL REFERENCES x_posts(post_id),
  action text NOT NULL,
  previous_value_json jsonb,
  new_value_json jsonb,
  actor text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS x_post_history_post_idx ON x_post_history(post_id, created_at);
UPDATE integrations SET status = 'manual_only',
  reason_fa = '۳۶ حساب X فقط به‌صورت دستی پایش می‌شوند: تحلیلگر نشانی پست مشخص را ثبت می‌کند. هیچ API پولی، scraping یا زمان‌بند فعال نیست.',
  updated_at = now()
 WHERE integration_id = 'x_social';
'''),
]

# Integration registry rows are facts about this deployment, not data about
# the world: what exists, what is deliberately not connected, and why.
INTEGRATIONS = [
    ('rss_collector', 'collection', 'گردآوری RSS منابع', 'active', True,
     'گردآوری زمان‌بندی‌شده هر ۹۰۰ ثانیه، یک درخواست برای هر منبع.', {'interval_seconds': 900}),
    ('ai_translation', 'ai', 'ترجمه ماشینی عنوان و خلاصه', 'blocked', False,
     'مسیر ترجمه ساخته و آزموده شده است؛ آخرین فراخوانی ارائه‌دهنده با خطای ۴۰۲ (اعتبار ناکافی حساب) متوقف شد.',
     {'provider_field': 'AI_PROVIDER', 'last_known_error': 'insufficient_credits'}),
    ('ai_briefing', 'ai', 'خلاصه مدیریتی هوش مصنوعی', 'not_configured', False,
     'تا فعال‌شدن ارائه‌دهنده هوش مصنوعی، خلاصه روزانه فقط با قواعد آماری تولید می‌شود.', {}),
    ('commodity_prices', 'market_data', 'قیمت کالاها و انرژی', 'not_configured', False,
     'هیچ منبع داده قیمت دارای مجوز قراردادی متصل نیست. قیمت تخمینی یا خراشیده‌شده نمایش داده نمی‌شود.',
     {'table': 'commodity_prices', 'required': ['commodity_code', 'value', 'unit', 'observed_at', 'provider', 'license_ref']}),
    ('x_social', 'social', 'حساب‌های X (توییتر)', 'not_configured', False,
     '۳۶ حساب X در فهرست منابع ثبت شده‌اند اما هیچ مسیر مجاز گردآوری (API رسمی) پیکربندی نشده است.',
     {'table': 'social_posts', 'registered_accounts_from': 'source-registry.json'}),
    ('geolocation', 'geo', 'مکان‌یابی خبر و رویداد', 'not_configured', False,
     'هیچ استخراج مکان با شواهد متنی اجرا نشده است. مختصات حدسی ساخته نمی‌شود.',
     {'table': 'geo_mentions', 'required': ['place_name', 'precision', 'method', 'confidence', 'evidence_span']}),
    ('connectivity', 'osint', 'سنجش اتصال اینترنت', 'not_configured', False, 'منبع سنجش اتصال متصل نیست.', {}),
    ('flight_marine', 'osint', 'ردیابی پرواز و دریایی', 'not_configured', False, 'منبع داده پرواز یا دریایی متصل نیست.', {}),
    ('alerts', 'alerting', 'قواعد هشدار', 'not_configured', False, 'هیچ قاعده هشداری تعریف نشده است.', {'table': 'alert_rules'}),
]


def _checksum(sql):
    return hashlib.sha256(sql.encode('utf-8')).hexdigest()


def apply(dsn):
    """Apply pending migrations in order; returns the list of applied ids."""
    applied = []
    with psycopg.connect(dsn) as c:
        c.execute('''CREATE TABLE IF NOT EXISTS schema_migrations(
            version text PRIMARY KEY, description text NOT NULL, checksum text NOT NULL,
            applied_at timestamptz NOT NULL DEFAULT now())''')
        done = dict(c.execute('SELECT version, checksum FROM schema_migrations').fetchall())
        for version, description, sql in MIGRATIONS:
            if version in done:
                if done[version] != _checksum(sql):
                    raise RuntimeError(f'migration {version} was changed after being applied')
                continue
            c.execute(sql)
            c.execute('INSERT INTO schema_migrations(version,description,checksum) VALUES(%s,%s,%s)',
                      (version, description, _checksum(sql)))
            applied.append(version)
        for iid, kind, name, status, enabled, reason, contract in INTEGRATIONS:
            # Insert-only: a status changed by an operator is never reset here.
            c.execute('''INSERT INTO integrations(integration_id,kind,name_fa,status,enabled,reason_fa,contract)
                VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(integration_id) DO NOTHING''',
                      (iid, kind, name, status, enabled, reason, json.dumps(contract, ensure_ascii=False)))
    return applied

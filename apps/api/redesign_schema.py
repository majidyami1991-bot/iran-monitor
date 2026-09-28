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

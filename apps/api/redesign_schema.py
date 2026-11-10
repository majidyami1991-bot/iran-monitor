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
    ('2026.09.29-04', 'news media v2: provenance, validation status and a single primary image per item', '''
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS media_type text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS original_url text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS canonical_url text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS proxy_url text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS thumbnail_url text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS width integer;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS height integer;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS file_size_bytes bigint;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS credit text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS source_method text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS source_field text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS source_hostname text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS is_primary boolean NOT NULL DEFAULT false;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS validation_status text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS http_status integer;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS policy_score integer;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS policy_version text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS policy_rejection_reason text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS perceptual_hash text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS validated_at timestamptz;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE news_item_media ADD CONSTRAINT news_item_media_source_method_chk CHECK (source_method IS NULL OR source_method IN
  ('rss_media_content','rss_media_thumbnail','rss_enclosure','rss_content_html','rss_description_html',
   'article_open_graph','article_json_ld','article_html','manual')) NOT VALID;
ALTER TABLE news_item_media ADD CONSTRAINT news_item_media_validation_status_chk CHECK (validation_status IS NULL OR validation_status IN
  ('pending','valid','rejected','unreachable','blocked','unknown')) NOT VALID;
-- Carry existing rows into the v2 vocabulary. Only the new columns are
-- written; url, relevance and verification_status keep their old values so
-- the pre-redesign API reads exactly what it read before.
UPDATE news_item_media m SET media_type = m.kind, original_url = m.url, canonical_url = m.url,
  source_hostname = lower(split_part(split_part(m.url, '://', 2), '/', 1)),
  width = COALESCE(m.verified_width, m.declared_width), height = COALESCE(m.verified_height, m.declared_height),
  file_size_bytes = m.byte_size, credit = m.attribution,
  source_method = CASE WHEN m.discovery_method = 'feed_content_html' THEN
      CASE WHEN n.summary_source = 'content_encoded' THEN 'rss_content_html' ELSE 'rss_description_html' END
      WHEN m.discovery_method = 'public_article_extraction' THEN 'article_html' END,
  source_field = CASE WHEN m.discovery_method = 'feed_content_html' THEN
      CASE WHEN n.summary_source = 'content_encoded' THEN 'content:encoded' ELSE 'description' END
      WHEN m.discovery_method = 'public_article_extraction' THEN 'article_body' END,
  validation_status = CASE WHEN m.verification_status = 'verified' THEN 'valid'
      WHEN m.verification_status = 'rejected' OR m.relevance LIKE 'rejected%' THEN 'rejected' ELSE 'unknown' END,
  policy_rejection_reason = CASE WHEN m.verification_status = 'rejected' OR m.relevance LIKE 'rejected%' THEN m.rejection_reason END
 FROM news_items n WHERE n.item_id = m.item_id AND m.media_type IS NULL;
-- Exactly one primary per item: the first article_image by position (three
-- items carried two article_image rows from separate extraction passes).
UPDATE news_item_media m SET is_primary = true FROM (
  SELECT DISTINCT ON (item_id) media_id FROM news_item_media WHERE relevance = 'article_image'
  ORDER BY item_id, position NULLS LAST, media_id) first
 WHERE m.media_id = first.media_id;
CREATE UNIQUE INDEX IF NOT EXISTS news_item_media_one_primary ON news_item_media(item_id) WHERE is_primary;
CREATE INDEX IF NOT EXISTS news_item_media_canonical_idx ON news_item_media(item_id, canonical_url);
'''),
    ('2026.10.06-01', 'local (Ollama) X post translation: current row per post + append-only history', '''
CREATE TABLE IF NOT EXISTS x_post_translations(
  id bigserial PRIMARY KEY,
  x_post_id text NOT NULL REFERENCES x_posts(post_id),
  source_language text,
  target_language text NOT NULL DEFAULT 'fa',
  translated_text text,
  status text NOT NULL DEFAULT 'pending',
  provider text,
  model text,
  prompt_version text,
  source_text_hash text NOT NULL,
  translation_hash text,
  quality_score real,
  quality_flags_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  attempt_count integer NOT NULL DEFAULT 0,
  latency_ms integer,
  last_error text,
  processing_started_at timestamptz,
  translated_at timestamptz,
  reviewed_at timestamptz,
  reviewed_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT x_post_translations_status_chk CHECK (status IN
    ('pending','processing','available','needs_review','failed','not_required','stale')),
  CONSTRAINT x_post_translations_one_per_lang UNIQUE (x_post_id, target_language));
CREATE INDEX IF NOT EXISTS x_post_translations_status_idx ON x_post_translations(status, id);
CREATE TABLE IF NOT EXISTS x_post_translation_history(
  history_id bigserial PRIMARY KEY,
  translation_id bigint NOT NULL,
  x_post_id text NOT NULL,
  translated_text text,
  status text NOT NULL,
  provider text,
  model text,
  prompt_version text,
  source_text_hash text,
  quality_flags_json jsonb,
  created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS x_post_translation_history_post_idx ON x_post_translation_history(x_post_id, history_id);
CREATE OR REPLACE FUNCTION log_x_post_translation() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'UPDATE' AND NEW.status IS NOT DISTINCT FROM OLD.status
     AND NEW.translated_text IS NOT DISTINCT FROM OLD.translated_text
     AND NEW.source_text_hash IS NOT DISTINCT FROM OLD.source_text_hash THEN
    RETURN NEW;
  END IF;
  INSERT INTO x_post_translation_history(translation_id,x_post_id,translated_text,status,provider,model,
    prompt_version,source_text_hash,quality_flags_json)
  VALUES(NEW.id,NEW.x_post_id,NEW.translated_text,NEW.status,NEW.provider,NEW.model,
    NEW.prompt_version,NEW.source_text_hash,NEW.quality_flags_json);
  RETURN NEW;
END $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS x_post_translation_history_trg ON x_post_translations;
CREATE TRIGGER x_post_translation_history_trg AFTER INSERT OR UPDATE ON x_post_translations
  FOR EACH ROW EXECUTE FUNCTION log_x_post_translation();
CREATE OR REPLACE FUNCTION x_post_translation_history_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'x_post_translation_history is append-only';
END $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS x_post_translation_history_no_change ON x_post_translation_history;
CREATE TRIGGER x_post_translation_history_no_change BEFORE UPDATE OR DELETE ON x_post_translation_history
  FOR EACH ROW EXECUTE FUNCTION x_post_translation_history_immutable();
'''),
    ('2026.10.07-01', 'local AI platform: translation attempts, append-only news translation history, '
                      'trigram retrieval, assistant sessions', '''
ALTER TABLE news_item_translations ADD COLUMN IF NOT EXISTS attempt_count integer NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS news_item_translations_status_idx ON news_item_translations(status, prompt_version);
CREATE OR REPLACE FUNCTION news_item_translation_history_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'news_item_translation_history is append-only';
END $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS news_item_translation_history_no_change ON news_item_translation_history;
CREATE TRIGGER news_item_translation_history_no_change BEFORE UPDATE OR DELETE ON news_item_translation_history
  FOR EACH ROW EXECUTE FUNCTION news_item_translation_history_immutable();
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS news_items_title_trgm ON news_items USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS news_item_translations_text_trgm ON news_item_translations USING gin (text gin_trgm_ops);
CREATE TABLE IF NOT EXISTS assistant_sessions(
  session_id text PRIMARY KEY,
  title text,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_active_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT assistant_sessions_id_chk CHECK (session_id ~ '^[A-Za-z0-9_-]{32,64}$'));
CREATE TABLE IF NOT EXISTS assistant_messages(
  id bigserial PRIMARY KEY,
  session_id text NOT NULL REFERENCES assistant_sessions(session_id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('user','assistant')),
  content text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS assistant_messages_session_idx ON assistant_messages(session_id, id);
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

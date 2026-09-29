-- Rollback for migration 2026.09.29-04 (news media v2). Removes only what it
-- added: the new constraints, indexes and columns on news_item_media, and the
-- v2-only rows the backfill inserted (discovery_method 'v2:%'). Legacy
-- columns and legacy rows are untouched. Take a backup first.
BEGIN;
DELETE FROM news_item_media WHERE discovery_method LIKE 'v2:%';
DROP INDEX IF EXISTS news_item_media_one_primary;
DROP INDEX IF EXISTS news_item_media_canonical_idx;
ALTER TABLE news_item_media DROP CONSTRAINT IF EXISTS news_item_media_source_method_chk;
ALTER TABLE news_item_media DROP CONSTRAINT IF EXISTS news_item_media_validation_status_chk;
ALTER TABLE news_item_media
  DROP COLUMN IF EXISTS media_type, DROP COLUMN IF EXISTS original_url, DROP COLUMN IF EXISTS canonical_url,
  DROP COLUMN IF EXISTS proxy_url, DROP COLUMN IF EXISTS thumbnail_url, DROP COLUMN IF EXISTS width,
  DROP COLUMN IF EXISTS height, DROP COLUMN IF EXISTS file_size_bytes, DROP COLUMN IF EXISTS credit,
  DROP COLUMN IF EXISTS source_method, DROP COLUMN IF EXISTS source_field, DROP COLUMN IF EXISTS source_hostname,
  DROP COLUMN IF EXISTS is_primary, DROP COLUMN IF EXISTS validation_status, DROP COLUMN IF EXISTS http_status,
  DROP COLUMN IF EXISTS policy_score, DROP COLUMN IF EXISTS policy_version, DROP COLUMN IF EXISTS policy_rejection_reason, DROP COLUMN IF EXISTS perceptual_hash,
  DROP COLUMN IF EXISTS validated_at, DROP COLUMN IF EXISTS created_at, DROP COLUMN IF EXISTS updated_at;
DELETE FROM schema_migrations WHERE version = '2026.09.29-04';
COMMIT;

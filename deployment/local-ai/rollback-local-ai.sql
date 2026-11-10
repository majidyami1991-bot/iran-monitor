-- Rollback for migration 2026.10.07-01 (local AI platform), for the isolated
-- local-AI database only. Removes the assistant tables (conversations are
-- deleted with them), the trigram indexes, the history guard and the
-- attempt_count column. Local translations stored in news_item_translations
-- and their history rows stay (they are ordinary rows the earlier schema
-- already supports). pg_trgm is left installed (harmless; other objects may use it).
-- The simplest full rollback of this stack is to stop its compose project.
BEGIN;
DROP TABLE IF EXISTS assistant_messages;
DROP TABLE IF EXISTS assistant_sessions;
DROP INDEX IF EXISTS news_items_title_trgm;
DROP INDEX IF EXISTS news_item_translations_text_trgm;
DROP INDEX IF EXISTS news_item_translations_status_idx;
DROP TRIGGER IF EXISTS news_item_translation_history_no_change ON news_item_translation_history;
DROP FUNCTION IF EXISTS news_item_translation_history_immutable();
ALTER TABLE news_item_translations DROP COLUMN IF EXISTS attempt_count;
DELETE FROM schema_migrations WHERE version = '2026.10.07-01';
COMMIT;

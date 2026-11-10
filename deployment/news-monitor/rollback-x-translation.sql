-- Rollback for migration 2026.10.06-01 (local Ollama X post translation).
-- Removes only what that migration created. x_posts, x_post_history and every
-- other table are untouched; an API image without the feature ignores the
-- missing tables. Take a pg_dump first: translations and their history are
-- deleted with the tables.
--
--   docker exec -i defence-monitor-news-news-db-1 sh -c \
--     'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' < rollback-x-translation.sql
BEGIN;
DROP TABLE IF EXISTS x_post_translation_history;
DROP TABLE IF EXISTS x_post_translations;
DROP FUNCTION IF EXISTS log_x_post_translation();
DROP FUNCTION IF EXISTS x_post_translation_history_immutable();
DELETE FROM schema_migrations WHERE version = '2026.10.06-01';
COMMIT;

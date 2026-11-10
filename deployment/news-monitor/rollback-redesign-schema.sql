-- Full schema rollback for the reference-redesign migrations
-- (2026.09.28-01 .. 2026.09.28-03). NOT needed for an application rollback:
-- the previous API/web images run unchanged against the migrated schema
-- (verified in the drill, docs/DEPLOYMENT AND ROLLBACK.md). Use only to return
-- the database to its exact pre-redesign shape, after a fresh backup.
--
-- Removes only what the redesign added: its tables, its three columns on
-- news_events, and the events produced by clustering v2. Collected news,
-- sources, translations, classifications and v1 events are not touched.
BEGIN;
DELETE FROM news_event_members WHERE event_id IN
  (SELECT event_id FROM news_events WHERE clustering_method = 'entity_idf_complete_linkage_v2');
DELETE FROM news_events WHERE clustering_method = 'entity_idf_complete_linkage_v2';
DROP TRIGGER IF EXISTS item_topic_assignment_history_trg ON item_topic_assignments;
DROP FUNCTION IF EXISTS log_item_topic_assignment();
DROP TABLE IF EXISTS item_topic_assignment_history, item_topic_assignments, stories, daily_briefings,
  integrations, commodity_prices, social_posts, geo_mentions, alert_rules;
ALTER TABLE news_events DROP COLUMN IF EXISTS primary_category, DROP COLUMN IF EXISTS confidence,
  DROP COLUMN IF EXISTS confidence_level;
DELETE FROM schema_migrations WHERE version IN ('2026.09.28-01', '2026.09.28-02', '2026.09.28-03');
COMMIT;

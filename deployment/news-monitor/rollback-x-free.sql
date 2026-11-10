-- Rollback for migration 2026.09.29-03 (X-FREE). Removes only the X-FREE
-- tables and restores the x_social integration status. News, sources,
-- translations and events are not touched. Take a backup first.
BEGIN;
DROP TABLE IF EXISTS x_post_history, x_post_media, x_posts, x_accounts;
UPDATE integrations SET status = 'not_configured',
  reason_fa = '۳۶ حساب X در فهرست منابع ثبت شده‌اند اما هیچ مسیر مجاز گردآوری (API رسمی) پیکربندی نشده است.',
  updated_at = now()
 WHERE integration_id = 'x_social';
DELETE FROM schema_migrations WHERE version = '2026.09.29-03';
COMMIT;

import os, psycopg

DSN = os.environ.get('DATABASE_URL', 'postgresql://iran_monitor_user:iran_monitor_secret_123@localhost:5433/iran_monitor')
with psycopg.connect(DSN) as conn:
    sources = conn.execute("SELECT source_id, name, feed_url FROM sources WHERE feed_url IS NOT NULL").fetchall()
    print(f"Total sources with feed_url: {len(sources)}")
    cnt = conn.execute("SELECT count(1) FROM news_items WHERE summary_source = 'content_encoded'").fetchone()[0]
    print(f"Contaminated items with summary_source = 'content_encoded': {cnt}")

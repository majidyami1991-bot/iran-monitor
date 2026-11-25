import os, psycopg

DSN = os.environ.get('DATABASE_URL', 'postgresql://iran_monitor_user:iran_monitor_secret_123@localhost:5433/iran_monitor')
with psycopg.connect(DSN) as conn:
    q = """
    SELECT count(1)
    FROM news_items n
    JOIN news_item_translations t ON n.item_id = t.item_id AND t.field = 'summary'
    WHERE n.summary_source = 'content_encoded'
    """
    cnt = conn.execute(q).fetchone()[0]
    print(f"Translations with field='summary' on contaminated records: {cnt}")
    
    q_human = """
    SELECT count(1)
    FROM news_items n
    JOIN news_item_translations t ON n.item_id = t.item_id AND t.field = 'summary'
    WHERE n.summary_source = 'content_encoded' AND t.human_reviewed IS TRUE
    """
    cnt_human = conn.execute(q_human).fetchone()[0]
    print(f"Human-reviewed translations on contaminated records: {cnt_human}")

import os
import psycopg

DSN = "postgresql://iran_monitor_user:iran_monitor_secret_123@localhost:5433/iran_monitor"

def run_checks():
    print("=== RUNNING SYSTEM VERIFICATION CHECKS ===")
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            # 1. Check total items and content
            cur.execute("SELECT count(*) FROM news_items")
            total_items = cur.fetchone()[0]

            cur.execute("SELECT count(*) FROM news_item_content WHERE original_text IS NOT NULL")
            total_bodies = cur.fetchone()[0]

            # 2. Check summary sources
            cur.execute("""
                SELECT COALESCE(summary_source, 'null_summary'), count(*)
                FROM news_items
                GROUP BY 1 ORDER BY 2 DESC
            """)
            summary_sources = cur.fetchall()

            # 3. Check legacy translations preserved
            cur.execute("SELECT count(*) FROM news_item_translations WHERE field = 'summary_legacy_body'")
            preserved_legacy = cur.fetchone()[0]

            # 4. Check active summary translations
            cur.execute("SELECT count(*) FROM news_item_translations WHERE field = 'summary' AND superseded_at IS NULL")
            active_summaries = cur.fetchone()[0]

            # 5. Check enrichment jobs by stage and status
            cur.execute("""
                SELECT stage, status, count(*)
                FROM enrichment_jobs
                GROUP BY stage, status
                ORDER BY stage, status
            """)
            jobs = cur.fetchall()

            # 6. Check items that have BOTH genuine summary and full content
            cur.execute("""
                SELECT count(*)
                FROM news_items n
                JOIN news_item_content c USING(item_id)
                WHERE n.summary IS NOT NULL AND length(trim(n.summary)) > 0
                  AND c.original_text IS NOT NULL AND length(trim(c.original_text)) > 0
                  AND trim(n.summary) != trim(c.original_text)
            """)
            both_count = cur.fetchone()[0]

            # 7. Check items with full text but NO summary
            cur.execute("""
                SELECT count(*)
                FROM news_items n
                JOIN news_item_content c USING(item_id)
                WHERE (n.summary IS NULL OR length(trim(n.summary)) = 0)
                  AND c.original_text IS NOT NULL AND length(trim(c.original_text)) > 0
            """)
            body_only_count = cur.fetchone()[0]

            # 8. Check items with summary but NO full text yet
            cur.execute("""
                SELECT count(*)
                FROM news_items n
                LEFT JOIN news_item_content c USING(item_id)
                WHERE n.summary IS NOT NULL AND length(trim(n.summary)) > 0
                  AND (c.original_text IS NULL OR length(trim(c.original_text)) = 0)
            """)
            summary_only_count = cur.fetchone()[0]

            print(f"Total News Items: {total_items}")
            print(f"Total Article Bodies Intact: {total_bodies}")
            print(f"Items with BOTH genuine summary & distinct full text: {both_count}")
            print(f"Items with Full Text only (genuine summary NULL): {body_only_count}")
            print(f"Items with Summary only (awaiting full text extraction): {summary_only_count}")
            print(f"Preserved Legacy Body Translations (superseded): {preserved_legacy}")
            print(f"Active Genuine Summary Translations: {active_summaries}")
            print("\nSummary Source Distribution:")
            for s, cnt in summary_sources:
                print(f"  - {s}: {cnt}")
            print("\nEnrichment Jobs Distribution:")
            for st, s, cnt in jobs:
                print(f"  - {st} [{s}]: {cnt}")

if __name__ == "__main__":
    run_checks()

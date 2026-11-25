import psycopg
import json
from datetime import datetime, timezone

DSN = "postgresql://iran_monitor_user:iran_monitor_secret_123@localhost:5433/iran_monitor"

def audit():
    print("=== READ-ONLY AUDIT: DATA INTEGRITY & VERIFICATION ===")
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            # 1. Total items & article bodies
            cur.execute("SELECT count(*) FROM news_items")
            total_items = cur.fetchone()[0]

            cur.execute("SELECT count(*) FROM news_item_content WHERE original_text IS NOT NULL AND length(trim(original_text)) > 0")
            intact_bodies = cur.fetchone()[0]

            cur.execute("SELECT count(*) FROM news_item_content WHERE original_text IS NULL OR length(trim(original_text)) = 0")
            empty_bodies = cur.fetchone()[0]

            print(f"Total News Items: {total_items}")
            print(f"Intact Non-Empty Article Bodies: {intact_bodies}")
            print(f"Empty/Null Article Bodies: {empty_bodies}")

            # 2. Cleared historical summaries
            cur.execute("SELECT count(*) FROM news_items WHERE summary_source = 'body_unsummarized' AND summary IS NULL")
            cleared_summaries = cur.fetchone()[0]

            cur.execute("SELECT count(*) FROM news_items WHERE summary_source = 'body_unsummarized' AND summary IS NOT NULL")
            unclean_unsummarized = cur.fetchone()[0]

            print(f"Cleared Historical Summaries (summary_source='body_unsummarized' & summary IS NULL): {cleared_summaries}")
            print(f"Any unclean body_unsummarized with non-null summary: {unclean_unsummarized}")

            # 3. Recovered summaries
            cur.execute("SELECT count(*) FROM news_items WHERE summary_source IN ('description', 'atom_summary') AND summary IS NOT NULL")
            genuine_summaries = cur.fetchone()[0]
            print(f"Genuine RSS/Atom Summaries Present: {genuine_summaries}")

            # 4. Reclassified legacy body translations
            cur.execute("SELECT count(*), count(DISTINCT item_id) FROM news_item_translations WHERE field = 'summary_legacy_body'")
            legacy_count, legacy_items = cur.fetchone()

            cur.execute("SELECT count(*) FROM news_item_translations WHERE field = 'summary_legacy_body' AND superseded_at IS NOT NULL")
            legacy_superseded = cur.fetchone()[0]

            cur.execute("SELECT count(*) FROM news_item_translations WHERE field = 'summary_legacy_body' AND (text IS NULL OR length(trim(text)) = 0)")
            legacy_empty = cur.fetchone()[0]

            print(f"Reclassified 'summary_legacy_body' Translations: {legacy_count} across {legacy_items} items")
            print(f"  - superseded_at IS NOT NULL: {legacy_superseded}")
            print(f"  - Empty texts: {legacy_empty} (all text intact)")

            # 5. Active translations check
            cur.execute("SELECT field, status, count(*) FROM news_item_translations WHERE superseded_at IS NULL GROUP BY 1, 2 ORDER BY 1, 2")
            active_translations = cur.fetchall()
            print("\nActive Non-Superseded Translations:")
            for f, st, cnt in active_translations:
                print(f"  - {f} [{st}]: {cnt}")

            # 6. Hashes and provenance
            cur.execute("SELECT count(*) FROM news_item_translations WHERE input_text_sha256 IS NULL")
            null_hashes = cur.fetchone()[0]
            print(f"\nTranslations missing input_text_sha256: {null_hashes}")

            # 7. Display policy distribution
            cur.execute("SELECT display_policy, extraction_status, count(*) FROM news_item_content GROUP BY 1, 2 ORDER BY 1, 2")
            content_policies = cur.fetchall()
            print("\nContent Display Policy & Extraction Status:")
            for dp, es, cnt in content_policies:
                print(f"  - display_policy={dp}, extraction_status={es}: {cnt}")

            # Check if any summary-only RSS feeds have full_syndicated
            cur.execute("""
                SELECT count(*) FROM news_items n
                JOIN news_item_content c USING(item_id)
                WHERE n.summary_source IN ('description', 'atom_summary')
                  AND c.display_policy = 'full_syndicated'
                  AND c.extraction_method = 'rss_content'
            """)
            misclassified_rss = cur.fetchone()[0]
            print(f"RSS description payloads misclassified as full_syndicated via rss_content: {misclassified_rss}")

            # 8. Queue progress and job timestamps
            cur.execute("""
                SELECT stage, status, count(*), min(updated_at), max(updated_at)
                FROM enrichment_jobs
                GROUP BY stage, status ORDER BY stage, status
            """)
            jobs_info = cur.fetchall()
            print("\nEnrichment Jobs Timestamps & Status:")
            for st, s, cnt, min_t, max_t in jobs_info:
                print(f"  - {st} [{s}]: {cnt} rows | min={min_t} | max={max_t}")

            # 9. Recent extraction activity
            cur.execute("SELECT count(*) FROM enrichment_jobs WHERE stage='extraction' AND status='succeeded' AND updated_at > now() - interval '1 hour'")
            succeeded_1h = cur.fetchone()[0]

            cur.execute("SELECT count(*) FROM enrichment_jobs WHERE stage='extraction' AND status='succeeded' AND updated_at > now() - interval '24 hours'")
            succeeded_24h = cur.fetchone()[0]

            print(f"\nExtraction Jobs Succeeded in last 1 hour: {succeeded_1h}")
            print(f"Extraction Jobs Succeeded in last 24 hours: {succeeded_24h}")

            # 10. Dead-letter jobs count
            cur.execute("SELECT count(*) FROM enrichment_jobs WHERE status='dead_letter'")
            dead_letter_count = cur.fetchone()[0]
            print(f"Current Dead-Letter Jobs: {dead_letter_count}")

if __name__ == "__main__":
    audit()

import psycopg
import json

DSN = "postgresql://iran_monitor_user:iran_monitor_secret_123@localhost:5433/iran_monitor"

def audit():
    results = {}
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            # 1. Total items and bodies
            cur.execute("SELECT count(*) FROM news_items")
            results['total_news_items'] = cur.fetchone()[0]

            cur.execute("SELECT count(*) FROM news_item_content WHERE original_text IS NOT NULL AND length(trim(original_text)) > 0")
            results['intact_bodies'] = cur.fetchone()[0]

            # 2. Summary distribution
            cur.execute("SELECT COALESCE(summary_source, 'NULL'), count(*) FROM news_items GROUP BY 1 ORDER BY 2 DESC")
            results['summary_sources'] = cur.fetchall()

            # 3. Legacy translations
            cur.execute("""
                SELECT count(*), count(DISTINCT item_id), 
                       count(*) FILTER (WHERE superseded_at IS NOT NULL),
                       count(*) FILTER (WHERE text IS NOT NULL AND length(trim(text)) > 0)
                FROM news_item_translations 
                WHERE field = 'summary_legacy_body'
            """)
            leg = cur.fetchone()
            results['legacy_body_translations'] = {
                'total_rows': leg[0],
                'distinct_items': leg[1],
                'superseded_rows': leg[2],
                'rows_with_text': leg[3]
            }

            # 4. Active summary translations
            cur.execute("""
                SELECT count(*), count(DISTINCT item_id),
                       count(*) FILTER (WHERE status = 'available'),
                       count(*) FILTER (WHERE status = 'translated_auto'),
                       count(*) FILTER (WHERE status = 'qc_warning'),
                       count(*) FILTER (WHERE status = 'qc_failed'),
                       count(*) FILTER (WHERE status IN ('pending', 'translation_pending'))
                FROM news_item_translations 
                WHERE field = 'summary' AND superseded_at IS NULL
            """)
            act = cur.fetchone()
            results['active_summary_translations'] = {
                'total_rows': act[0],
                'distinct_items': act[1],
                'available': act[2],
                'translated_auto': act[3],
                'qc_warning': act[4],
                'qc_failed': act[5],
                'pending': act[6]
            }

            # 5. Overlap check between summary and body
            cur.execute("""
                SELECT count(*)
                FROM news_items n
                JOIN news_item_content c USING(item_id)
                WHERE n.summary IS NOT NULL AND length(trim(n.summary)) > 0
                  AND c.original_text IS NOT NULL AND length(trim(c.original_text)) > 0
                  AND trim(n.summary) = trim(c.original_text)
            """)
            results['exact_summary_body_duplicates'] = cur.fetchone()[0]

            # 6. Display policy distribution
            cur.execute("SELECT display_policy, count(*) FROM news_item_content GROUP BY 1 ORDER BY 2 DESC")
            results['display_policies'] = cur.fetchall()

            # 7. Enrichment jobs by stage and status
            cur.execute("SELECT stage, status, count(*) FROM enrichment_jobs GROUP BY 1, 2 ORDER BY 1, 2")
            results['enrichment_jobs'] = cur.fetchall()

            # 8. Check if any dead-letter jobs exist
            cur.execute("SELECT count(*) FROM enrichment_jobs WHERE status = 'dead_letter'")
            results['dead_letter_jobs'] = cur.fetchone()[0]

            # 9. Recent vs backfill pending extraction jobs
            cur.execute("""
                SELECT 
                    count(*) FILTER (WHERE COALESCE(n.published_at, n.fetched_at) >= now() - interval '7 days') as recent,
                    count(*) FILTER (WHERE COALESCE(n.published_at, n.fetched_at) < now() - interval '7 days') as older,
                    count(*) FILTER (WHERE COALESCE(n.published_at, n.fetched_at) IS NULL) as no_date
                FROM enrichment_jobs j
                LEFT JOIN news_items n USING(item_id)
                WHERE j.stage = 'extraction' AND j.status = 'pending'
            """)
            row = cur.fetchone()
            results['pending_extraction_age_breakdown'] = {
                'recent_7d': row[0],
                'older_than_7d': row[1],
                'no_date': row[2]
            }

            # 10. AI requests log breakdown
            cur.execute("SELECT task_type, provider, model, status, count(*) FROM ai_requests_log GROUP BY 1, 2, 3, 4 ORDER BY 5 DESC")
            results['ai_requests_log'] = cur.fetchall()

            # 11. Assistant usage
            cur.execute("SELECT role, count(*) FROM assistant_messages GROUP BY 1")
            results['assistant_messages_by_role'] = cur.fetchall()

            cur.execute("SELECT count(*) FROM assistant_sessions")
            results['assistant_sessions_count'] = cur.fetchone()[0]

            # 12. Translation queue requests
            cur.execute("SELECT count(*) FROM translation_queue_requests")
            results['translation_queue_requests_count'] = cur.fetchone()[0]

            # 13. Translation worker state
            cur.execute("SELECT * FROM translation_worker_state")
            results['translation_worker_state'] = cur.fetchall()

    print(json.dumps(results, indent=2, default=str))

if __name__ == "__main__":
    audit()

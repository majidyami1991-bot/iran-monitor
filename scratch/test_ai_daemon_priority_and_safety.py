import os, sys, time, json, urllib.error
import psycopg
import enrichment_worker as ew
import ai_gateway as gw

dsn = os.environ.get('DATABASE_URL')

def run_tests():
    print("=== TEST 1: Priority Queue Selection (Cross-Article Prioritization) ===")
    with psycopg.connect(dsn, autocommit=True) as c:
        # Get two distinct items
        rows = c.execute("SELECT item_id, title FROM news_items ORDER BY id DESC LIMIT 2").fetchall()
        item_a = rows[0][0] # Recent item
        item_b = rows[1][0] # Older item
        
        # Enqueue item_b for translation_body (low priority)
        job_b_id = ew._job_id(item_b, 'translation_body')
        c.execute("""
            INSERT INTO enrichment_jobs(job_id, item_id, stage, status, available_at, created_at)
            VALUES(%s, %s, 'translation_body', 'pending', now(), now() - interval '30 minutes')
            ON CONFLICT(item_id, stage) DO UPDATE SET status='pending', available_at=now(), created_at=now() - interval '30 minutes'
        """, (job_b_id, item_b))

        # Enqueue item_a for translation_summary (high priority)
        job_a_id = ew._job_id(item_a, 'translation_summary')
        c.execute("""
            INSERT INTO enrichment_jobs(job_id, item_id, stage, status, available_at, created_at)
            VALUES(%s, %s, 'translation_summary', 'pending', now(), now())
            ON CONFLICT(item_id, stage) DO UPDATE SET status='pending', available_at=now(), created_at=now()
        """, (job_a_id, item_a))

        # Both stages are enabled in test parameters
        enabled_stages = ['translation_summary', 'translation_body']
        claimed = ew._claim_next_ai_job(enabled_stages, worker_id='test-worker')
        print("Claimed job:", claimed)
        assert claimed is not None, "Failed to claim any job!"
        assert claimed['stage'] == 'translation_summary', f"Expected translation_summary, got {claimed['stage']}!"
        assert claimed['item_id'] == item_a, f"Expected item_a, got {claimed['item_id']}!"
        print("PASS: Recent summary took priority over older body across different articles!")

        # Clean up test jobs
        c.execute("DELETE FROM enrichment_jobs WHERE job_id IN (%s, %s)", (job_a_id, job_b_id))

    print("\n=== TEST 2: Disabled-State Behavior & Queue Safety ===")
    with psycopg.connect(dsn, autocommit=True) as c:
        # Check current config
        enabled_stages, cfg = ew.get_enabled_ai_stages(dsn)
        print("Enabled stages with current config:", enabled_stages)
        assert len(enabled_stages) == 0, f"Expected 0 enabled stages, found {enabled_stages}"
        
        # Enqueue a dummy pending job
        job_test_id = ew._job_id(item_a, 'translation_summary')
        c.execute("""
            INSERT INTO enrichment_jobs(job_id, item_id, stage, status, available_at)
            VALUES(%s, %s, 'translation_summary', 'pending', now())
            ON CONFLICT(item_id, stage) DO UPDATE SET status='pending', available_at=now()
        """, (job_test_id, item_a))

        # Claim with empty enabled stages
        claimed = ew._claim_next_ai_job(enabled_stages, worker_id='test-worker')
        assert claimed is None, "Claimed a job even though capabilities are disabled!"
        
        # Verify job is still pending in DB
        status = c.execute("SELECT status, attempts FROM enrichment_jobs WHERE job_id=%s", (job_test_id,)).fetchone()
        print("Pending job status in DB:", status)
        assert status[0] == 'pending', f"Expected job to remain pending, got {status[0]}"
        print("PASS: Disabled state preserves queued work and claims nothing!")

    print("\n=== TEST 3: Ollama Circuit Breaker & Graceful Postponement ===")
    with psycopg.connect(dsn, autocommit=True) as c:
        # Test simulated connection error
        test_err = "URLError: <urlopen error [Errno 111] Connection refused>"
        ew.OllamaCircuitBreaker.record_failure(test_err)
        assert ew.OllamaCircuitBreaker.is_open(), "Circuit breaker should be OPEN after failure!"
        rem = ew.OllamaCircuitBreaker.remaining_cooldown()
        print(f"Circuit breaker is OPEN. Cooldown remaining: {rem}s")
        
        # Postpone job on connection error
        ew._postpone_connection_error(job_test_id, test_err, backoff_seconds=60)
        job_row = c.execute("SELECT status, attempts, last_error FROM enrichment_jobs WHERE job_id=%s", (job_test_id,)).fetchone()
        print("Postponed job row:", job_row)
        assert job_row[0] == 'pending', f"Expected status 'pending', got {job_row[0]}"
        assert job_row[1] == 0, f"Attempts should not be incremented on connection error! Got {job_row[1]}"
        assert 'Connection refused' in job_row[2], f"Expected connection refused error in last_error, got {job_row[2]}"
        
        # Reset circuit breaker
        ew.OllamaCircuitBreaker.record_success()
        assert not ew.OllamaCircuitBreaker.is_open(), "Circuit breaker should be CLOSED after reset"
        print("PASS: Ollama connection error postponed job without burning attempts, and opened breaker!")

        # Clean up test job
        c.execute("DELETE FROM enrichment_jobs WHERE job_id=%s", (job_test_id,))

    print("\n=== TEST 4: Controlled Single Translation Execution ===")
    with psycopg.connect(dsn, autocommit=True) as c:
        # Find an item with a short title
        item_row = c.execute("SELECT item_id, title FROM news_items WHERE title IS NOT NULL ORDER BY id DESC LIMIT 1").fetchone()
        item_id, title = item_row
        print(f"Translating sample title for item {item_id[:12]}: '{title[:40]}...'")
        
        # Temporarily enable title translation
        c.execute("UPDATE ai_runtime_config SET enabled_title_translation=true WHERE id=1")
        enabled_stages, cfg = ew.get_enabled_ai_stages(dsn)
        assert 'translation_title' in enabled_stages, "translation_title should be enabled!"
        
        job_id = ew._job_id(item_id, 'translation_title')
        c.execute("""
            INSERT INTO enrichment_jobs(job_id, item_id, stage, status, available_at)
            VALUES(%s, %s, 'translation_title', 'pending', now())
            ON CONFLICT(item_id, stage) DO UPDATE SET status='pending', available_at=now(), attempts=0
        """, (job_id, item_id))

        claimed = ew._claim_next_ai_job(enabled_stages, worker_id='test-worker')
        assert claimed is not None, "Failed to claim translation_title job!"
        
        # Execute the job
        ok = ew._execute_one_ai_job(claimed, cfg, worker_id='test-worker')
        print("Execution result:", ok)
        assert ok is True, "AI execution failed!"
        
        # Check translation record
        trans = c.execute("SELECT text, status, model FROM news_item_translations WHERE item_id=%s AND field='title' AND target_language='fa'", (item_id,)).fetchone()
        print(f"Persian translation created: '{trans[0]}' (status: {trans[1]}, model: {trans[2]})")
        assert trans[0] and len(trans[0]) > 0, "Translation text is empty!"
        
        # Check job status in enrichment_jobs
        j_status = c.execute("SELECT status FROM enrichment_jobs WHERE job_id=%s", (job_id,)).fetchone()
        print("Job status in enrichment_jobs:", j_status[0])
        assert j_status[0] == 'succeeded', f"Expected 'succeeded', got {j_status[0]}"
        print("PASS: Controlled translation succeeded end-to-end!")

    print("\n=== TEST 5: Reset All Capabilities to Disabled ===")
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute("""
            UPDATE ai_runtime_config SET
                enabled_title_translation=false,
                enabled_summary_translation=false,
                enabled_body_translation=false,
                enabled_executive_summary=false,
                enabled_why_it_matters=false,
                enabled_key_points=false,
                enabled_assistant=false,
                updated_at=now()
            WHERE id=1
        """)
        enabled_stages, cfg = ew.get_enabled_ai_stages(dsn)
        print("Enabled stages after reset:", enabled_stages)
        assert len(enabled_stages) == 0, "Not all stages disabled!"
        row = c.execute("""
            SELECT enabled_title_translation, enabled_summary_translation, enabled_body_translation,
                   enabled_executive_summary, enabled_why_it_matters, enabled_key_points, enabled_assistant
            FROM ai_runtime_config WHERE id=1
        """).fetchone()
        print("Database verification of all 7 flags:", row)
        assert all(x is False for x in row), "Database capability flag is still True!"
        print("PASS: All 7 capabilities strictly reset to DISABLED!")

if __name__ == '__main__':
    run_tests()
    print("\nALL 5 TEST SUITES PASSED SUCCESSFULLY!")

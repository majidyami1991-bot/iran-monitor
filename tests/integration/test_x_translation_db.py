"""DB integration tests for local X post translation.

Runs ONLY against a throwaway database whose name ends in `_xtrtest`
(schema copied from the real one, no data). Synthetic accounts and posts are
inserted there and nowhere else. The model is replaced by a scripted fake
gateway or by the fake Ollama server from the offline tests — no real model,
no network beyond 127.0.0.1.

    DATABASE_URL=postgresql://.../defence_monitor_xtrtest PYTHONPATH=/app \
      pytest -q tests/integration/test_x_translation_db.py
"""
import os
import sys
import threading
from pathlib import Path

import psycopg
import pytest

import ai_gateway as gw
import redesign_schema
import x_translate_worker as xw

DSN = os.environ['DATABASE_URL']
if not DSN.rsplit('/', 1)[-1].split('?')[0].endswith('_xtrtest'):
    pytest.exit('refusing to run: DATABASE_URL must point at a *_xtrtest database', returncode=2)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'monitoring'))
import test_x_translation as offline  # noqa: E402  (fake Ollama server + fixtures)

ROLLBACK = Path(__file__).resolve().parents[2] / 'deployment' / 'news-monitor' / 'rollback-x-translation.sql'
FIX = offline.FIX
GOOD = {f['case']: f for f in FIX['good']}


def q(sql, args=None):
    with psycopg.connect(DSN, autocommit=True) as c:
        cur = c.execute(sql, args)
        return cur.fetchall() if cur.description else None


def settings(**kw):
    s = xw.Settings(enabled=True, base_url='http://127.0.0.1:9', model='gemma4:e2b', expected_digest=None,
                    concurrency=1, batch_size=1, timeout_seconds=5, max_attempts=2, temperature=0.1, num_ctx=4096,
                    num_thread=8, keep_alive='5m', sleep_seconds=0, stuck_minutes=15)
    for k, v in kw.items():
        setattr(s, k, v)
    return s


class ScriptedGateway:
    """Stands in for AIGateway: returns queued results, counts calls."""

    def __init__(self, script=None):
        self.adapter = object()
        self.script = list(script or [])
        self.calls = 0

    def run(self, request):
        self.calls += 1
        text = xw.json.loads(request.content)['post_text']
        kind = self.script.pop(0) if self.script else 'good'
        good = next((f['translation'] for f in FIX['good'] if f['source'] == text), None)
        if kind == 'good':
            return gw.GatewayResult('available', {'detected_language': 'en', 'translation_fa': good,
                                                  'translation_not_required': False, 'quality_notes': []},
                                    'ollama/local', 'gemma4:e2b', xw.PROMPT_VERSION, xw.TASK, 'h', latency_ms=1234,
                                    response_model='gemma4:e2b', reported_cost_usd=0.0, estimated_cost_usd=0.0)
        if kind == 'bad':
            return gw.GatewayResult('available', {'detected_language': 'en', 'translation_fa': good + ' ۹۹۹',
                                                  'translation_not_required': False, 'quality_notes': []},
                                    'ollama/local', 'gemma4:e2b', xw.PROMPT_VERSION, xw.TASK, 'h', latency_ms=1000,
                                    response_model='gemma4:e2b')
        return gw.GatewayResult('error', None, 'ollama/local', 'gemma4:e2b', xw.PROMPT_VERSION, xw.TASK, 'h',
                                latency_ms=50, error=f'{kind}:test')


@pytest.fixture(scope='module', autouse=True)
def schema():
    applied = redesign_schema.apply(DSN)
    assert '2026.10.06-01' in applied or q("SELECT 1 FROM schema_migrations WHERE version='2026.10.06-01'")
    yield


@pytest.fixture(autouse=True)
def clean():
    q('DROP TRIGGER IF EXISTS x_post_translation_history_no_change ON x_post_translation_history')
    q('TRUNCATE x_post_translation_history, x_post_translations, x_post_history, x_post_media, x_posts, ai_response_cache CASCADE')
    q('DELETE FROM x_accounts')
    # restore append-only guards exactly as the migration defines them
    q('''CREATE TRIGGER x_post_translation_history_no_change BEFORE UPDATE OR DELETE ON x_post_translation_history
        FOR EACH ROW EXECUTE FUNCTION x_post_translation_history_immutable()''')
    q('''INSERT INTO x_accounts(source_id,handle,handle_key,profile_url) VALUES('synthetic-acct','synthetic_acct',
        '@synthetic_acct','https://x.com/synthetic_acct')''')
    xw.Stop.requested = False
    yield


def add_post(pid, text):
    q('''INSERT INTO x_posts(post_id,source_id,post_url,author_handle,original_text,availability_status,provenance_json)
        VALUES(%s,'synthetic-acct',%s,'synthetic_acct',%s,'text_recorded','{"synthetic": true}')''',
      (pid, f'https://x.com/synthetic_acct/status/{pid}', text))


def status_of(pid):
    r = q("SELECT status, attempt_count, translated_text, source_text_hash FROM x_post_translations WHERE x_post_id=%s", (pid,))
    return r[0] if r else None


def seed(n=3):
    cases = ['simple_english', 'number_percent', 'url', 'mention', 'military_acronym'][:n]
    for i, c in enumerate(cases):
        add_post(f'9000000000{i}', GOOD[c]['source'])
    return [f'9000000000{i}' for i in range(len(cases))]


# ------------------------------------------------------------------ migration
def test_migration_is_idempotent_and_recorded():
    assert redesign_schema.apply(DSN) == []
    cols = {r[0] for r in q("SELECT column_name FROM information_schema.columns WHERE table_name='x_post_translations'")}
    for c in ('id', 'x_post_id', 'source_language', 'target_language', 'translated_text', 'status', 'provider', 'model',
              'prompt_version', 'source_text_hash', 'translation_hash', 'quality_score', 'quality_flags_json',
              'attempt_count', 'latency_ms', 'translated_at', 'reviewed_at', 'reviewed_by', 'created_at', 'updated_at'):
        assert c in cols, c
    with pytest.raises(psycopg.errors.CheckViolation):
        add_post('91', 'Some English text that needs translating.')
        q("INSERT INTO x_post_translations(x_post_id,status,source_text_hash) VALUES('91','bogus','h')")


def test_history_is_append_only():
    seed(1)
    with psycopg.connect(DSN, autocommit=True) as c:
        xw.reconcile(c)
    assert q('SELECT count(*) FROM x_post_translation_history')[0][0] == 1
    # Row-level guards (UPDATE/DELETE). TRUNCATE is an owner-only DDL-level
    # operation and is not guarded (migrations may not contain that keyword).
    for sql in ('UPDATE x_post_translation_history SET status=\'available\'', 'DELETE FROM x_post_translation_history'):
        with pytest.raises(psycopg.errors.RaiseException):
            q(sql)
    assert q('SELECT count(*) FROM x_post_translation_history')[0][0] == 1


def test_rollback_then_reapply():
    seed(2)
    before = q('SELECT count(*) FROM x_posts')[0][0]
    with psycopg.connect(DSN, autocommit=True) as c:
        c.execute(ROLLBACK.read_text(encoding='utf-8'))
    assert not q("SELECT 1 FROM information_schema.tables WHERE table_name IN ('x_post_translations','x_post_translation_history')")
    assert not q("SELECT 1 FROM schema_migrations WHERE version='2026.10.06-01'")
    assert q('SELECT count(*) FROM x_posts')[0][0] == before  # nothing else touched
    assert redesign_schema.apply(DSN) == ['2026.10.06-01']
    assert q('SELECT count(*) FROM x_post_translations')[0][0] == 0


# ------------------------------------------------------------------ worker flows
def test_batch_translates_in_order_and_second_run_is_free():
    ids = seed(3)
    g = ScriptedGateway()
    rep = xw.run_batch(DSN, settings(), gateway=g)
    assert rep.attempted == 3 and rep.available == 3 and g.calls == 3 and rep.provider_calls == 3
    assert [status_of(i)[0] for i in ids] == ['available'] * 3
    hist = q("SELECT status FROM x_post_translation_history WHERE x_post_id=%s ORDER BY history_id", (ids[0],))
    assert [h[0] for h in hist] == ['pending', 'processing', 'available']
    g2 = ScriptedGateway()
    rep2 = xw.run_batch(DSN, settings(), gateway=g2)
    assert rep2.attempted == 0 and g2.calls == 0 and rep2.provider_calls == 0


def test_persian_post_is_not_required_without_model_call():
    add_post('92', FIX['persian_source']['source'])
    g = ScriptedGateway()
    rep = xw.run_batch(DSN, settings(), gateway=g)
    assert g.calls == 0 and status_of('92')[0] == 'not_required' and rep.reconcile['not_required'] == 1


def test_duplicate_worker_is_refused():
    seed(1)
    holder = psycopg.connect(DSN, autocommit=True)
    try:
        assert xw.try_lock(holder)
        with psycopg.connect(DSN, autocommit=True, row_factory=xw.dict_row) as c:
            assert xw.worker_running(c)
        g = ScriptedGateway()
        rep = xw.run_batch(DSN, settings(), gateway=g)
        assert rep.stopped_reason == 'worker_already_running' and g.calls == 0
    finally:
        xw.unlock(holder)
        holder.close()


def test_resume_after_partial_run():
    ids = seed(3)
    xw.run_batch(DSN, settings(), gateway=ScriptedGateway(), limit=1)
    assert [status_of(i)[0] for i in ids] == ['available', 'pending', 'pending']
    g = ScriptedGateway()
    xw.run_batch(DSN, settings(), gateway=g)
    assert g.calls == 2 and all(status_of(i)[0] == 'available' for i in ids)


def test_stuck_processing_is_recovered():
    ids = seed(1)
    with psycopg.connect(DSN, autocommit=True) as c:
        xw.reconcile(c)
    q("UPDATE x_post_translations SET status='processing', processing_started_at=now() - interval '2 hours'")
    rep = xw.run_batch(DSN, settings(), gateway=ScriptedGateway())
    assert rep.recovered == ids and status_of(ids[0])[0] == 'available'
    assert not q("SELECT 1 FROM x_post_translations WHERE status='processing'")


def test_transient_error_retried_once_then_succeeds():
    ids = seed(1)
    rep = xw.run_batch(DSN, settings(), gateway=ScriptedGateway(['transient_timeout', 'good']), sleep=lambda s: None)
    st = status_of(ids[0])
    assert rep.retries == 1 and st[0] == 'available' and st[1] == 2


def test_transient_error_twice_is_failed_not_processing():
    ids = seed(1)
    rep = xw.run_batch(DSN, settings(), gateway=ScriptedGateway(['transient_timeout', 'transient_timeout']),
                       sleep=lambda s: None)
    st = status_of(ids[0])
    assert rep.failed == 1 and st[0] == 'failed' and st[1] == 2


def test_ollama_unreachable_returns_post_to_pending_and_stops():
    ids = seed(2)
    rep = xw.run_batch(DSN, settings(), gateway=ScriptedGateway(['provider_unreachable']))
    assert rep.stopped_reason == 'provider_unreachable' and rep.attempted == 1
    assert status_of(ids[0])[0] == 'pending' and status_of(ids[0])[1] == 0 and status_of(ids[1])[0] == 'pending'
    assert q('SELECT count(*) FROM x_posts WHERE original_text IS NOT NULL')[0][0] == 2  # originals intact


def test_invalid_translation_needs_review_and_stops_on_review():
    ids = seed(3)
    rep = xw.run_batch(DSN, settings(), gateway=ScriptedGateway(['good', 'bad', 'good']), stop_on_review=True)
    assert rep.stopped_reason == 'stop_on_review:needs_review'
    assert [status_of(i)[0] for i in ids] == ['available', 'needs_review', 'pending']
    flags = q("SELECT quality_flags_json FROM x_post_translations WHERE x_post_id=%s", (ids[1],))[0][0]
    assert 'number_added' in flags


def test_source_change_marks_stale_and_keeps_history():
    ids = seed(1)
    xw.run_batch(DSN, settings(), gateway=ScriptedGateway())
    old_hash = status_of(ids[0])[3]
    q("UPDATE x_posts SET original_text=%s WHERE post_id=%s", (GOOD['url']['source'], ids[0]))
    with psycopg.connect(DSN, autocommit=True) as c:
        assert xw.reconcile(c)['stale'] == 1
    assert status_of(ids[0])[0] == 'stale' and status_of(ids[0])[3] != old_hash
    xw.run_batch(DSN, settings(), gateway=ScriptedGateway())
    st = status_of(ids[0])
    assert st[0] == 'available' and st[2] == GOOD['url']['translation']
    statuses = [h[0] for h in q("SELECT status FROM x_post_translation_history WHERE x_post_id=%s ORDER BY history_id", (ids[0],))]
    assert statuses.count('available') == 2 and 'stale' in statuses


def test_postgres_cache_answers_repeat_text_without_model_call():
    """Real AIGateway + PostgresCache + fake Ollama on loopback."""
    srv = offline.ThreadingHTTPServer(('127.0.0.1', 0), offline.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{srv.server_address[1]}'
    try:
        offline.Fake.mode, offline.Fake.reply, offline.Fake.chat_calls = 'ok', {
            'detected_language': 'en', 'translation_fa': GOOD['simple_english']['translation'],
            'translation_not_required': False, 'quality_notes': []}, 0
        offline.Fake.tags_models = [{'name': 'gemma4:e2b', 'digest': offline.DIGEST}]
        gw._BREAKERS.clear()
        s = settings(base_url=base, expected_digest='7fbdbf8f5e45')
        add_post('93', GOOD['simple_english']['source'])
        rep = xw.run_batch(DSN, s)
        assert rep.available == 1 and rep.provider_calls == 1 and offline.Fake.chat_calls == 1
        assert status_of('93')[0] == 'available'
        # same text on another post: the response cache answers it
        add_post('94', GOOD['simple_english']['source'])
        rep2 = xw.run_batch(DSN, s)
        assert rep2.cache_hits == 1 and rep2.provider_calls == 0 and offline.Fake.chat_calls == 1
        log = q("SELECT provider, model, estimated_cost_usd, cache_hit FROM ai_requests_log ORDER BY request_id DESC LIMIT 2")
        assert {r[0] for r in log} == {'ollama/local'} and all((r[2] or 0) == 0 for r in log)
    finally:
        srv.shutdown()

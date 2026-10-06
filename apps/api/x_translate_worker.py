"""Offline, non-real-time Persian translation of analyst-recorded X posts
with the local Ollama model (CPU only). Nothing here runs on page load or on
a schedule: an operator runs a batch, the batch translates pending posts one
at a time, and the process exits.

    python -m x_translate_worker x-status
    python -m x_translate_worker x-dry-run --limit 10
    python -m x_translate_worker x-translate --limit 3 [--post-ids a,b,c] [--stop-on-review]
    python -m x_translate_worker x-translate --all-pending
    python -m x_translate_worker x-retry-review --limit 10

Guarantees (see docs/LOCAL OLLAMA X TRANSLATION ARCHITECTURE.md):
  - x_posts is never written; the original text is the source of truth and
    stays visible whatever happens here.
  - concurrency is exactly 1: one advisory lock per database, one request at
    a time, batch size 1, a pause between jobs.
  - a translation becomes `available` only after the independent validator
    passes; otherwise `needs_review` (never shown as a translation).
  - the same source hash + model + prompt version never calls the model
    twice: done rows are not picked again, and the gateway cache answers a
    text it has already seen.
  - Ollama missing, the model missing or a different model answering stops
    the batch and puts the post back to `pending` (fail closed).
  - a crash or kill leaves no row in `processing`: the next run, holding the
    lock, returns orphaned rows to `pending`.
  - logs carry post ids, statuses, flags and latency — never post text.
"""
import argparse
import hashlib
import json
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass, field

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

import ai_gateway as gw
import x_translation_validator as xv

LOG = logging.getLogger('defence_monitor.x_translate')
TASK = 'x_post_translation'
PROMPT_VERSION = gw.LATEST_PROMPT_VERSION[TASK]
LOCK_KEY = 7_270_061  # pg advisory lock: one X translation worker per database
FINAL = ('available', 'needs_review', 'failed', 'not_required')
TRANSIENT = ('transient_timeout', 'provider_unavailable')
STOP_BATCH = ('provider_unreachable', 'model_not_found', 'model_digest_mismatch', 'model_identity_mismatch',
              'model_not_approved', 'provider_not_configured', 'circuit_open', 'ollama_host_not_local')


# ------------------------------------------------------------------ config
@dataclass
class Settings:
    enabled: bool
    base_url: str
    model: str
    expected_digest: str | None
    concurrency: int
    batch_size: int
    timeout_seconds: int
    max_attempts: int
    temperature: float
    num_ctx: int
    num_thread: int | None
    keep_alive: str
    sleep_seconds: float
    stuck_minutes: int
    errors: list = field(default_factory=list)


def _int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def load_settings():
    s = Settings(
        enabled=(os.getenv('X_TRANSLATION_ENABLED') or 'false').strip().lower() == 'true',
        base_url=(os.getenv('OLLAMA_BASE_URL') or 'http://host.docker.internal:11434').strip(),
        model=(os.getenv('OLLAMA_MODEL_TRANSLATION') or '').strip(),
        expected_digest=(os.getenv('OLLAMA_MODEL_DIGEST') or '').strip() or None,
        concurrency=_int('X_TRANSLATION_CONCURRENCY', 1),
        batch_size=_int('X_TRANSLATION_BATCH_SIZE', 1),
        timeout_seconds=min(_int('X_TRANSLATION_TIMEOUT_SECONDS', 600), 600),
        max_attempts=max(1, min(_int('X_TRANSLATION_MAX_ATTEMPTS', 2), 2)),
        temperature=float(os.getenv('X_TRANSLATION_TEMPERATURE', '0.1') or 0.1),
        num_ctx=max(1024, min(_int('OLLAMA_NUM_CTX', 4096), 4096)),
        num_thread=_int('OLLAMA_NUM_THREAD', 8) or None,
        keep_alive=(os.getenv('OLLAMA_KEEP_ALIVE') or '5m').strip(),
        sleep_seconds=max(0.0, float(os.getenv('X_TRANSLATION_SLEEP_SECONDS', '2') or 2)),
        stuck_minutes=max(1, _int('X_TRANSLATION_STUCK_MINUTES', 15)),
    )
    if s.concurrency != 1:
        s.errors.append('X_TRANSLATION_CONCURRENCY must be 1')
    if s.batch_size != 1:
        s.errors.append('X_TRANSLATION_BATCH_SIZE must be 1')
    if not s.model:
        s.errors.append('OLLAMA_MODEL_TRANSLATION is not set')
    elif not gw.model_is_approved('ollama', s.model):
        s.errors.append('OLLAMA_MODEL_TRANSLATION is not an approved model')
    return s


def gateway_config(s):
    return gw.GatewayConfig(
        mode=gw.Mode.LOCAL, provider='ollama', base_url=s.base_url, api_key='',
        models={TASK: s.model}, timeout_seconds=s.timeout_seconds, max_concurrency=1, daily_budget_usd=None,
        options={'expected_digest': s.expected_digest, 'num_ctx': s.num_ctx, 'num_thread': s.num_thread,
                 'temperature': s.temperature, 'keep_alive': s.keep_alive})


def build_gateway(s, dsn, use_cache=True):
    return gw.AIGateway(gateway_config(s), cache=gw.PostgresCache(dsn) if use_cache else None,
                        logger=gw.PostgresLogger(dsn))


def ollama_probe(s, timeout=3):
    """(reachable, model_found, digest12) without raising. Local hosts only."""
    try:
        adapter = gw.OllamaAdapter(s.base_url, s.model or 'unset', timeout, expected_digest=s.expected_digest)
    except gw.GatewayError:
        return False, False, None
    try:
        digest = adapter.verify_model(timeout=timeout)
        return True, True, digest[:12]
    except gw.GatewayError as exc:
        reachable = not str(exc).startswith(('provider_unreachable', 'transient_timeout'))
        return reachable, False, None


# ------------------------------------------------------------------ pure helpers
def source_hash(text):
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()


def model_input(text):
    return json.dumps({'task': 'translate_x_post_to_persian', 'source_language': 'auto', 'target_language': 'fa',
                       'post_text': text}, ensure_ascii=False)


def error_class(error):
    return (error or '').split(':', 1)[0]


def decide(source_text, result):
    """Map one gateway result to the translation row fields. Pure.

    Returns a dict with: status, translated_text, source_language, quality_score,
    flags, error, stop_batch (bool), retryable (bool)."""
    base = {'translated_text': None, 'source_language': None, 'quality_score': None, 'flags': [],
            'error': None, 'stop_batch': False, 'retryable': False}
    if result.status in ('available', 'cached'):
        p = result.payload or {}
        lang = (p.get('detected_language') or '').strip()[:16] or None
        text = (p.get('translation_fa') or '').strip()
        if p.get('translation_not_required'):
            if xv.is_persian_source(source_text):
                return {**base, 'status': 'not_required', 'source_language': lang or 'fa', 'quality_score': 1.0}
            return {**base, 'status': 'needs_review', 'source_language': lang, 'translated_text': text or None,
                    'quality_score': 0.0, 'flags': ['model_claimed_not_required']}
        v = xv.validate(source_text, text)
        return {**base, 'status': 'available' if v.passed else 'needs_review', 'source_language': lang,
                'translated_text': text or None, 'quality_score': v.quality_score, 'flags': v.flags}
    if result.status == 'invalid_response':
        return {**base, 'status': 'failed', 'flags': ['invalid_response'], 'error': (result.error or '')[:120]}
    cls = error_class(result.error) if result.status == 'error' else result.status
    if result.status in ('circuit_open', 'provider_not_configured') or cls in STOP_BATCH:
        return {**base, 'status': 'pending', 'error': cls, 'stop_batch': True}
    if cls in TRANSIENT or cls == 'output_truncated_num_predict':
        return {**base, 'status': 'failed', 'error': cls, 'retryable': cls in TRANSIENT}
    return {**base, 'status': 'failed', 'error': cls[:120] or 'unknown_error'}


# ------------------------------------------------------------------ db
def connect(dsn):
    return psycopg.connect(dsn, row_factory=dict_row, autocommit=True)


def _x(conn, sql, args=None):
    """Execute with dict rows whatever the connection's own row factory."""
    return conn.cursor(row_factory=dict_row).execute(sql, args)


def try_lock(conn):
    return _x(conn, 'SELECT pg_try_advisory_lock(%s) AS ok', (LOCK_KEY,)).fetchone()['ok']


def unlock(conn):
    _x(conn, 'SELECT pg_advisory_unlock(%s)', (LOCK_KEY,))


def worker_running(conn):
    r = _x(conn, """SELECT count(*) AS n FROM pg_locks WHERE locktype='advisory' AND granted
        AND objid = %s AND classid = 0""", (LOCK_KEY,)).fetchone()
    return r['n'] > 0


def reconcile(conn, post_ids=None):
    """DB only, no model call: create pending rows for posts with text,
    mark rows whose source text changed as stale, mark Persian sources as
    not_required. Returns counts."""
    where = "coalesce(btrim(p.original_text),'') <> '' AND p.availability_status <> 'withdrawn'"
    args = {}
    if post_ids:
        where += ' AND p.post_id = ANY(%(ids)s)'
        args['ids'] = list(post_ids)
    rows = _x(conn, f'''SELECT p.post_id, p.original_text, t.id AS tid, t.status, t.source_text_hash
        FROM x_posts p LEFT JOIN x_post_translations t ON t.x_post_id = p.post_id AND t.target_language = 'fa'
        WHERE {where}''', args).fetchall()
    created = stale = not_required = 0
    for r in rows:
        h = source_hash(r['original_text'])
        persian = xv.is_persian_source(r['original_text'])
        if r['tid'] is None:
            status = 'not_required' if persian else 'pending'
            _x(conn, '''INSERT INTO x_post_translations(x_post_id,target_language,status,source_text_hash,
                source_language,provider,model,prompt_version) VALUES(%s,'fa',%s,%s,%s,%s,%s,%s)
                ON CONFLICT (x_post_id, target_language) DO NOTHING''',
                         (r['post_id'], status, h, 'fa' if persian else None,
                          'rule' if persian else None, None, 'persian-source-rule-1.0.0' if persian else None))
            created += 1
            not_required += persian
        elif r['source_text_hash'] != h and r['status'] != 'processing':
            if persian:
                _x(conn, '''UPDATE x_post_translations SET status='not_required', source_text_hash=%s,
                    translated_text=NULL, source_language='fa', provider='rule', model=NULL,
                    prompt_version='persian-source-rule-1.0.0', updated_at=now() WHERE id=%s''', (h, r['tid']))
                not_required += 1
            else:
                # The previous translation stays in history; the row is
                # re-queued for the new text.
                _x(conn, '''UPDATE x_post_translations SET status='stale', source_text_hash=%s,
                    attempt_count=0, last_error=NULL, updated_at=now() WHERE id=%s''', (h, r['tid']))
                stale += 1
    return {'created': created, 'stale': stale, 'not_required': not_required, 'posts_with_text': len(rows)}


def recover_orphans(conn, stuck_minutes=None):
    """Called while holding the lock: every `processing` row belongs to a
    worker that no longer runs (crash, kill, timeout). With stuck_minutes,
    only rows older than that (used by status checks without the lock)."""
    cond = "status='processing'"
    if stuck_minutes:
        cond += f" AND processing_started_at < now() - interval '{int(stuck_minutes)} minutes'"
    rows = _x(conn, f'''UPDATE x_post_translations SET status='pending', processing_started_at=NULL,
        last_error='recovered_from_processing', updated_at=now() WHERE {cond} RETURNING x_post_id''').fetchall()
    return [r['x_post_id'] for r in rows]


def eligible(conn, limit, post_ids=None, statuses=('pending', 'stale')):
    args = {'st': list(statuses), 'l': limit}
    extra = ''
    if post_ids:
        extra = ' AND t.x_post_id = ANY(%(ids)s)'
        args['ids'] = list(post_ids)
    return _x(conn, f'''SELECT t.id, t.x_post_id, t.status, t.attempt_count, p.original_text
        FROM x_post_translations t JOIN x_posts p ON p.post_id = t.x_post_id
        WHERE t.status = ANY(%(st)s) AND t.target_language='fa'{extra}
          AND coalesce(btrim(p.original_text),'') <> '' AND p.availability_status <> 'withdrawn'
        ORDER BY t.id LIMIT %(l)s''', args).fetchall()


def counts(conn):
    rows = _x(conn, "SELECT status, count(*) AS n FROM x_post_translations GROUP BY status").fetchall()
    c = {s: 0 for s in ('pending', 'processing', 'available', 'needs_review', 'failed', 'not_required', 'stale')}
    c.update({r['status']: r['n'] for r in rows})
    p = _x(conn, '''SELECT count(*) AS total,
        count(*) FILTER (WHERE coalesce(btrim(original_text),'') <> '' AND availability_status <> 'withdrawn') AS with_text
        FROM x_posts''').fetchone()
    lat = _x(conn, '''SELECT avg(latency_ms)::int AS avg_ms, max(latency_ms) AS max_ms, max(translated_at) AS last
        FROM x_post_translations WHERE status='available' ''').fetchone()
    return {'total_x_posts': p['total'], 'posts_with_text': p['with_text'],
            'translatable': p['with_text'] - c['not_required'], **c,
            'average_latency_ms': lat['avg_ms'], 'max_latency_ms': lat['max_ms'], 'last_success_at': lat['last']}


# ------------------------------------------------------------------ batch
class Stop:
    requested = False


def _on_signal(signum, frame):
    Stop.requested = True
    LOG.warning('stop requested (signal %s); finishing the current post', signum)


@dataclass
class Report:
    attempted: int = 0
    available: int = 0
    needs_review: int = 0
    failed: int = 0
    not_required: int = 0
    returned_to_pending: int = 0
    provider_calls: int = 0
    cache_hits: int = 0
    retries: int = 0
    latencies_ms: list = field(default_factory=list)
    stopped_reason: str | None = None
    recovered: list = field(default_factory=list)
    reconcile: dict = field(default_factory=dict)

    def as_dict(self):
        lat = self.latencies_ms
        d = {k: v for k, v in self.__dict__.items() if k != 'latencies_ms'}
        d['average_latency_ms'] = int(sum(lat) / len(lat)) if lat else None
        d['max_latency_ms'] = max(lat) if lat else None
        return d


def _write(conn, row_id, decision, result, attempts):
    payload_lang = decision['source_language']
    text = decision['translated_text']
    status = decision['status']
    _x(conn, '''UPDATE x_post_translations SET status=%(st)s, translated_text=%(tx)s, source_language=%(sl)s,
        provider=%(pv)s, model=%(md)s, prompt_version=%(pr)s, translation_hash=%(th)s, quality_score=%(qs)s,
        quality_flags_json=%(fl)s, attempt_count=%(at)s, latency_ms=%(lt)s, last_error=%(er)s,
        processing_started_at=NULL,
        translated_at=CASE WHEN %(st)s IN ('available','needs_review','not_required') THEN now() ELSE translated_at END,
        updated_at=now() WHERE id=%(id)s''',
                 {'st': status, 'tx': text, 'sl': payload_lang, 'pv': result.provider or 'ollama/local',
                  'md': result.response_model or result.model, 'pr': result.prompt_version,
                  'th': hashlib.sha256(text.encode('utf-8')).hexdigest() if text else None,
                  'qs': decision['quality_score'], 'fl': Jsonb(decision['flags']), 'at': attempts,
                  'lt': result.latency_ms, 'er': decision['error'], 'id': row_id})


def translate_one(conn, row, gateway, s, report, sleep=time.sleep):
    """Translate one row; returns the final decision dict."""
    attempts = row['attempt_count']
    while True:
        attempts += 1
        _x(conn, '''UPDATE x_post_translations SET status='processing', attempt_count=%s,
            processing_started_at=now(), updated_at=now() WHERE id=%s''', (attempts, row['id']))
        result = gateway.run(gw.GatewayRequest(TASK, model_input(row['original_text']), prompt_version=PROMPT_VERSION))
        if result.cache_hit:
            report.cache_hits += 1
        elif result.latency_ms is not None:
            report.provider_calls += 1
        decision = decide(row['original_text'], result)
        if decision['retryable'] and attempts < s.max_attempts and not Stop.requested:
            report.retries += 1
            LOG.info('post=%s transient=%s attempt=%d; retrying once', row['x_post_id'], decision['error'], attempts)
            sleep(min(5.0, s.sleep_seconds + 1))
            continue
        if decision['stop_batch']:
            # Not the post's fault: put it back untouched (attempt not counted).
            _x(conn, '''UPDATE x_post_translations SET status=%s, attempt_count=%s, processing_started_at=NULL,
                last_error=%s, updated_at=now() WHERE id=%s''',
                         (row['status'], row['attempt_count'], decision['error'], row['id']))
            report.returned_to_pending += 1
            return decision
        _write(conn, row['id'], decision, result, attempts)
        if result.latency_ms is not None and not result.cache_hit:
            report.latencies_ms.append(result.latency_ms)
        setattr(report, decision['status'], getattr(report, decision['status']) + 1)
        LOG.info('post=%s status=%s latency_ms=%s attempts=%d flags=%s', row['x_post_id'], decision['status'],
                 result.latency_ms, attempts, ','.join(decision['flags']) or '-')
        return decision


def run_batch(dsn, s, *, limit=None, post_ids=None, stop_on_review=False, statuses=('pending', 'stale'),
              use_cache=True, gateway=None, sleep=time.sleep):
    """One batch, sequential, then return. Returns Report. Never raises for
    model/provider problems; raises RuntimeError only for misconfiguration."""
    report = Report()
    if s.errors:
        raise RuntimeError('; '.join(s.errors))
    if not s.enabled:
        report.stopped_reason = 'x_translation_disabled'
        return report
    lock_conn = connect(dsn)
    try:
        if not try_lock(lock_conn):
            report.stopped_reason = 'worker_already_running'
            return report
        with connect(dsn) as conn:
            report.recovered = recover_orphans(conn)
            report.reconcile = reconcile(conn, post_ids)
            g = gateway or build_gateway(s, dsn, use_cache=use_cache)
            if isinstance(g.adapter, gw.OllamaAdapter):
                try:
                    g.adapter.verify_model(timeout=10)  # fail closed before touching any row
                except gw.GatewayError as exc:
                    report.stopped_reason = error_class(str(exc))
                    return report
            elif isinstance(g.adapter, gw.DisabledAdapter):
                report.stopped_reason = 'provider_not_configured'
                return report
            done = 0
            while not Stop.requested and (limit is None or done < limit):
                rows = eligible(conn, 1, post_ids, statuses)  # batch size 1, resume from the first eligible
                if not rows:
                    break
                report.attempted += 1
                decision = translate_one(conn, rows[0], g, s, report, sleep=sleep)
                done += 1
                if decision['stop_batch']:
                    report.stopped_reason = decision['error']
                    break
                if stop_on_review and decision['status'] in ('needs_review', 'failed'):
                    report.stopped_reason = f'stop_on_review:{decision["status"]}'
                    break
                if s.sleep_seconds and (limit is None or done < limit):
                    sleep(s.sleep_seconds)
            if Stop.requested and not report.stopped_reason:
                report.stopped_reason = 'signal'
    finally:
        try:
            unlock(lock_conn)
        finally:
            lock_conn.close()
    return report


def requeue_for_retry(dsn, limit, post_ids=None):
    """needs_review/failed -> pending (attempts reset). History keeps the
    rejected output. Returns the post ids requeued."""
    with connect(dsn) as conn:
        args = {'l': limit}
        extra = ''
        if post_ids:
            extra = ' AND x_post_id = ANY(%(ids)s)'
            args['ids'] = list(post_ids)
        rows = _x(conn, f'''UPDATE x_post_translations SET status='pending', attempt_count=0, last_error=NULL,
            updated_at=now() WHERE id IN (SELECT id FROM x_post_translations WHERE status IN ('needs_review','failed')
            {extra} ORDER BY id LIMIT %(l)s) RETURNING x_post_id''', args).fetchall()
    return [r['x_post_id'] for r in rows]


def status_report(dsn, s):
    reachable, found, digest = ollama_probe(s)
    with connect(dsn) as conn:
        c = counts(conn)
        running = worker_running(conn)
    return {**c, 'ollama_reachable': reachable, 'model_found': found, 'model_digest': digest,
            'configured_model': s.model or None, 'provider': 'ollama/local', 'prompt_version': PROMPT_VERSION,
            'enabled': s.enabled, 'worker_running': running, 'concurrency': s.concurrency,
            'batch_size': s.batch_size, 'config_errors': s.errors}


def dry_run(dsn, s, limit, post_ids=None):
    """No writes, no model call: what a batch would do."""
    with connect(dsn) as conn:
        rows = _x(conn, '''SELECT p.post_id, p.original_text, t.status, t.source_text_hash FROM x_posts p
            LEFT JOIN x_post_translations t ON t.x_post_id=p.post_id AND t.target_language='fa'
            WHERE coalesce(btrim(p.original_text),'') <> '' AND p.availability_status <> 'withdrawn'
            ORDER BY t.id NULLS LAST, p.id''').fetchall()
    plan = []
    for r in rows:
        if post_ids and r['post_id'] not in post_ids:
            continue
        h = source_hash(r['original_text'])
        if xv.is_persian_source(r['original_text']):
            action = 'mark_not_required' if r['status'] != 'not_required' or r['source_text_hash'] != h else 'skip_done'
        elif r['status'] is None:
            action = 'create_and_translate'
        elif r['source_text_hash'] != h:
            action = 'mark_stale_and_translate'
        elif r['status'] in ('pending', 'stale', 'processing'):
            action = 'translate'
        else:
            action = 'skip_done'
        plan.append({'post_id': r['post_id'], 'chars': len(r['original_text']), 'current_status': r['status'],
                     'action': action})
    todo = [p for p in plan if p['action'] in ('create_and_translate', 'mark_stale_and_translate', 'translate')]
    return {'would_translate': todo[:limit], 'would_translate_total': len(todo),
            'skipped_done': sum(p['action'] == 'skip_done' for p in plan),
            'would_mark_not_required': sum(p['action'] == 'mark_not_required' for p in plan),
            'model_calls': 0, 'writes': 0}


# ------------------------------------------------------------------ CLI
def main(argv=None):
    logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'), format='%(asctime)s %(levelname)s %(name)s %(message)s')
    ap = argparse.ArgumentParser(prog='x_translate_worker')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('x-status')
    d = sub.add_parser('x-dry-run')
    d.add_argument('--limit', type=int, default=10)
    d.add_argument('--post-ids')
    t = sub.add_parser('x-translate')
    g = t.add_mutually_exclusive_group(required=True)
    g.add_argument('--limit', type=int)
    g.add_argument('--all-pending', action='store_true')
    t.add_argument('--post-ids')
    t.add_argument('--stop-on-review', action='store_true')
    r = sub.add_parser('x-retry-review')
    r.add_argument('--limit', type=int, default=10)
    r.add_argument('--post-ids')
    a = ap.parse_args(argv)
    dsn = os.environ['DATABASE_URL']
    s = load_settings()
    ids = [x for x in (getattr(a, 'post_ids', None) or '').split(',') if x] or None
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    def out(obj):
        print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))

    if a.cmd == 'x-status':
        out(status_report(dsn, s))
        return 0
    if a.cmd == 'x-dry-run':
        out(dry_run(dsn, s, a.limit, ids))
        return 0
    if s.errors:
        out({'error': 'configuration', 'details': s.errors})
        return 2
    if a.cmd == 'x-retry-review':
        if not s.enabled:
            out({'stopped_reason': 'x_translation_disabled'})
            return 3
        requeued = requeue_for_retry(dsn, a.limit, ids)
        # Bypass the response cache: a retry must ask the model again, not
        # replay the output that failed review.
        rep = run_batch(dsn, s, limit=len(requeued), post_ids=requeued, use_cache=False) if requeued else Report()
        out({'requeued': requeued, **rep.as_dict()})
        return 0
    rep = run_batch(dsn, s, limit=None if a.all_pending else a.limit, post_ids=ids, stop_on_review=a.stop_on_review)
    out(rep.as_dict())
    return 0 if rep.stopped_reason in (None, 'signal') or rep.stopped_reason.startswith('stop_on_review') else 3


if __name__ == '__main__':
    sys.exit(main())

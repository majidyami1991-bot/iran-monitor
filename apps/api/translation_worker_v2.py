"""Continuous Persian translation of news titles and summary leads for the
isolated 3003 lab: TranslateGemma 27B, pipeline v2.1 (no placeholders),
one inference at a time, persistent queue in the database.

    python -m translation_worker_v2 run        # long-running service (compose: ai-translator)
    python -m translation_worker_v2 once       # one job, then exit
    python -m translation_worker_v2 status

Statuses written to news_item_translations.status (target 'fa'):
    translation_pending   queued (new item, source changed, retry due)
    translated_auto       pipeline decision ACCEPT  — may be shown, labelled
                          "machine translation, not human-verified"
    qc_warning            REJECT_UNCERTAIN — some facts could not be verified;
                          shown only next to the original, with a warning
    qc_failed             REJECT_CRITICAL — a detectable critical error; the
                          text is kept for audit but never shown as a translation
    translation_error     inference failed (timeout, truncation, …); retried
                          with backoff, at most MAX_ATTEMPTS times
    not_required          the source is already Persian
ACCEPT is "no automated objection", not proof of correctness.

What is translated: the title, and the LEAD of the stored summary (whole
sentences up to SUMMARY_LEAD_CHARS; one sentence is always taken). The
English original is never modified. Every outcome appends a row to
news_item_translation_history (append-only, trigger-enforced).

Queue order: items asked for on demand (translation_queue_requests), then
items collected within NEW_HOURS (newest first), then the backfill window
BACKFILL_DAYS (newest first). Older items only on demand.
"""
import argparse
import hashlib
import json
import logging
import os
import re
import signal
import sys
import time
import unicodedata
from urllib.request import ProxyHandler, Request, build_opener

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

import local_ai
import model_identity as mi
import translation_tg as tg
import translation_v21 as v21
import x_translation_validator as xv

LOG = logging.getLogger('defence_monitor.translation_worker_v2')
WORKER_VERSION = 'translation-worker-v2.1.0'
PV = f'{tg.PROMPT_VERSION}+{v21.PIPELINE_VERSION}'          # prompt_version column value of this pipeline
STATUS = {'ACCEPT': 'translated_auto', 'REJECT_UNCERTAIN': 'qc_warning', 'REJECT_CRITICAL': 'qc_failed'}
DONE = ('translated_auto', 'qc_warning', 'qc_failed', 'not_required')
FIELDS = ('title', 'summary')
SUMMARY_SQL = "COALESCE(NULLIF(btrim(n.summary_text), ''), NULLIF(btrim(n.summary), ''))"


def _env_int(name, default, lo, hi):
    try:
        return max(lo, min(int(os.getenv(name, str(default))), hi))
    except ValueError:
        return default


SUMMARY_LEAD_CHARS = _env_int('LOCAL_TRANSLATION_SUMMARY_CHARS', 600, 200, 2000)
NEW_HOURS = _env_int('LOCAL_TRANSLATION_NEW_HOURS', 24, 1, 168)
BACKFILL_DAYS = _env_int('LOCAL_TRANSLATION_BACKFILL_DAYS', 3, 0, 60)
SLEEP_SECONDS = _env_int('LOCAL_TRANSLATION_SLEEP_SECONDS', 5, 0, 300)
IDLE_SECONDS = _env_int('LOCAL_TRANSLATION_IDLE_SECONDS', 30, 5, 600)
MAX_ATTEMPTS = _env_int('LOCAL_TRANSLATION_MAX_ATTEMPTS', 3, 1, 10)
KEEP_ALIVE = os.getenv('LOCAL_TRANSLATION_KEEP_ALIVE', '30m')
CALL_GAP_SECONDS = 2.0        # between two model calls: lets a waiting assistant take the inference lock


class Stop:
    requested = False


def _on_signal(signum, frame):
    Stop.requested = True
    LOG.warning('stop requested (signal %s); finishing the current call', signum)


class Paused(RuntimeError):
    """Provider/identity problem: the job goes back to the queue unchanged and the worker waits."""


class JobError(RuntimeError):
    """This job failed (counted as an attempt, retried with backoff)."""


def sha(t):
    return hashlib.sha256((t or '').encode('utf-8')).hexdigest()


_SENT = re.compile(r'(?<=[.!?…])\s+(?=[A-Z0-9"“‘(\[])')


def summary_lead(text, limit=SUMMARY_LEAD_CHARS):
    """Whole sentences up to limit chars; the first sentence is always taken
    (cut at the last space before 1.5×limit if it is extremely long)."""
    text = re.sub(r'\s+', ' ', (text or '').strip())
    if len(text) <= limit:
        return text
    out = ''
    for s in _SENT.split(text):
        if not out:
            out = s
        elif len(out) + 1 + len(s) <= limit:
            out += ' ' + s
        else:
            break
    if len(out) > int(limit * 1.5):
        cut = out.rfind(' ', 0, int(limit * 1.5))
        out = out[:cut if cut > limit // 2 else int(limit * 1.5)]
    return out


def source_of(field, title, summary):
    return title if field == 'title' else summary_lead(summary)


# ------------------------------------------------------------------ schema (3003 DB only, additive)
SCHEMA = '''
CREATE TABLE IF NOT EXISTS translation_queue_requests (
  item_id text PRIMARY KEY REFERENCES news_items(item_id), requested_at timestamptz NOT NULL DEFAULT now(), requested_by text);
CREATE TABLE IF NOT EXISTS translation_worker_state (
  worker text PRIMARY KEY, version text, state text, detail jsonb, beat_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS news_item_translations_queue_idx ON news_item_translations(status, prompt_version, updated_at);
'''


def ensure_schema(conn):
    conn.execute(SCHEMA)


def beat(conn, state, **detail):
    conn.execute('''INSERT INTO translation_worker_state(worker, version, state, detail, beat_at) VALUES ('ai-translator', %s, %s, %s, now())
        ON CONFLICT (worker) DO UPDATE SET version=EXCLUDED.version, state=EXCLUDED.state, detail=EXCLUDED.detail, beat_at=now()''',
                 (WORKER_VERSION, state, Jsonb(detail)))


# ------------------------------------------------------------------ queue
def _history(conn, item_id, f, status, text, h, flags, latency, error, model, approval_id, chars):
    v = conn.execute('''SELECT COALESCE(max(content_version),0)+1 AS v FROM news_item_translation_history
        WHERE item_id=%s AND field=%s AND target_language='fa' ''', (item_id, f)).fetchone()['v']
    conn.execute('''INSERT INTO news_item_translation_history(item_id,field,target_language,content_version,status,text,
        provider,model,prompt_version,input_text_sha256,quality_score,quality_flags,latency_ms,error,response_model,reported_cost_usd)
        VALUES(%s,%s,'fa',%s,%s,%s,%s,%s,%s,%s,NULL,%s,%s,%s,%s,0)''',
                 (item_id, f, v, status, text, 'ollama/local' if model else None, model, PV, h, Jsonb(flags), latency, error, approval_id))


def reconcile(conn, item_ids=None):
    """Queue fields of in-window items (and requested ones) whose current row is
    missing, from another pipeline, or stale (source changed). Never touches
    human-reviewed rows. Persian sources -> not_required."""
    where = f"""(n.collected_at >= now() - make_interval(days => %(bd)s) OR n.collected_at >= now() - make_interval(hours => %(nh)s)
                 OR n.item_id IN (SELECT item_id FROM translation_queue_requests))"""
    args = {'bd': BACKFILL_DAYS, 'nh': NEW_HOURS}
    if item_ids:
        where, args['ids'] = 'n.item_id = ANY(%(ids)s)', list(item_ids)
    rows = conn.execute(f'''SELECT n.item_id, n.title, {SUMMARY_SQL} AS summary,
        tt.status AS t_status, tt.input_text_sha256 AS t_hash, tt.prompt_version AS t_pv, COALESCE(tt.human_reviewed,false) AS t_h,
        ts.status AS s_status, ts.input_text_sha256 AS s_hash, ts.prompt_version AS s_pv, COALESCE(ts.human_reviewed,false) AS s_h
        FROM news_items n
        LEFT JOIN news_item_translations tt ON tt.item_id=n.item_id AND tt.field='title' AND tt.target_language='fa'
        LEFT JOIN news_item_translations ts ON ts.item_id=n.item_id AND ts.field='summary' AND ts.target_language='fa'
        WHERE {where}''', args).fetchall()
    c = {'queued': 0, 'stale': 0, 'not_required': 0}
    for r in rows:
        for f, p in (('title', 't'), ('summary', 's')):
            src = source_of(f, r['title'], r['summary'])
            if not src or not src.strip() or r[p + '_h']:
                continue
            h, status, pv = sha(src), r[p + '_status'], r[p + '_pv']
            persian = xv.is_persian_source(src)
            new = 'not_required' if persian else 'translation_pending'
            if status is None:
                conn.execute('''INSERT INTO news_item_translations(item_id,field,target_language,status,input_text_sha256,prompt_version,
                    source_chars,provider,review_status,attempt_count) VALUES(%s,%s,'fa',%s,%s,%s,%s,%s,'machine_unreviewed',0)
                    ON CONFLICT DO NOTHING''', (r['item_id'], f, new, h, PV, len(src), 'rule' if persian else None))
            elif status == 'processing':
                continue
            elif pv != PV or (r[p + '_hash'] != h and status in DONE + ('translation_error',)):
                stale = pv == PV
                conn.execute('''UPDATE news_item_translations SET status=%s, input_text_sha256=%s, prompt_version=%s, source_chars=%s,
                    attempt_count=0, error=NULL, review_status='machine_unreviewed', updated_at=now()
                    WHERE item_id=%s AND field=%s AND target_language='fa' AND NOT COALESCE(human_reviewed,false)''',
                             (new, h, PV, len(src), r['item_id'], f))
                if stale:
                    _history(conn, r['item_id'], f, new, None, h, ['source_changed'], None, None, None, None, len(src))
                c['stale' if stale else 'queued'] += 1
                continue
            else:
                continue
            c['not_required' if persian else 'queued'] += 1
    return c


def recover(conn):
    rows = conn.execute('''UPDATE news_item_translations SET status='translation_pending', error='recovered_after_restart', updated_at=now()
        WHERE status='processing' AND prompt_version=%s RETURNING item_id''', (PV,)).fetchall()
    return sorted({r['item_id'] for r in rows})


def next_job(conn, item_ids=None):
    """One item with eligible fields: requested > new (NEW_HOURS) > backfill; newest first.
    translation_error rows are eligible again after 2^attempt minutes, up to MAX_ATTEMPTS."""
    extra, args = '', {'pv': PV, 'nh': NEW_HOURS, 'max': MAX_ATTEMPTS}
    if item_ids:
        extra, args['ids'] = ' AND n.item_id = ANY(%(ids)s)', list(item_ids)
    return conn.execute(f'''SELECT n.item_id, n.title, {SUMMARY_SQL} AS summary,
        array_agg(t.field ORDER BY t.field DESC) AS fields, max(t.attempt_count) AS attempts
        FROM news_item_translations t JOIN news_items n ON n.item_id=t.item_id
        LEFT JOIN translation_queue_requests q ON q.item_id=n.item_id
        WHERE t.target_language='fa' AND t.field IN ('title','summary') AND t.prompt_version=%(pv)s AND NOT COALESCE(t.human_reviewed,false)
          AND (t.status='translation_pending'
               OR (t.status='translation_error' AND t.attempt_count < %(max)s
                   AND t.updated_at < now() - make_interval(mins => power(2, t.attempt_count)::int))){extra}
        GROUP BY n.item_id, n.title, n.summary_text, n.summary, n.collected_at, q.requested_at
        ORDER BY (q.requested_at IS NULL), (n.collected_at < now() - make_interval(hours => %(nh)s)), n.collected_at DESC, n.item_id
        LIMIT 1''', args).fetchone()


# ------------------------------------------------------------------ inference
class Model:
    def __init__(self, s, dsn):
        self.s, self.dsn = s, dsn
        self.approval = s.approval
        self.rt = self.approval['runtime']
        self.opener = build_opener(ProxyHandler({}))

    def preflight(self):
        try:
            mi.verify(self.approval, self.s.base_url, {'temperature': self.rt['temperature'], 'num_ctx': self.rt['num_ctx'],
                                                       'num_thread': self.rt['num_thread'], 'seed': self.rt['seed'],
                                                       'translation_max': self.rt['translation_max_output_tokens']}, timeout=10)
        except mi.IdentityError as exc:
            raise Paused(str(exc))

    def call(self, text):
        """(output, tokens_in, tokens_out, latency_ms) — one inference under INFERENCE_LOCK."""
        n = tg.predict_for(len(text), self.rt['translation_max_output_tokens'])
        body = tg.request_body(self.approval['tag'], text, seed=self.rt['seed'], num_ctx=self.rt['num_ctx'],
                               num_thread=self.rt['num_thread'], temperature=self.rt['temperature'], num_predict=n, keep_alive=KEEP_ALIVE)
        try:
            with local_ai.inference_lock(self.dsn, wait_seconds=1800, should_cancel=lambda: Stop.requested):
                t0 = time.monotonic()
                try:
                    with self.opener.open(Request(self.s.base_url.rstrip('/') + '/api/chat',
                                                  json.dumps(body, ensure_ascii=False).encode(),
                                                  {'Content-Type': 'application/json'}), timeout=self.s.timeout_seconds) as r:
                        out = json.loads(r.read())
                except TimeoutError as exc:
                    raise JobError('transient_timeout') from exc
                except OSError as exc:
                    raise Paused('provider_unreachable') from exc
                latency = int((time.monotonic() - t0) * 1000)
                if out.get('model') != self.approval['tag']:
                    raise Paused('model_identity_mismatch')
                try:
                    mi.check_loaded(self.approval, self.s.base_url)
                except mi.IdentityError as exc:
                    raise Paused(str(exc))
        except local_ai.Busy as exc:
            raise Paused(str(exc))
        if out.get('done_reason') == 'length':
            raise JobError('output_truncated_num_predict')
        text_out = (out.get('message') or {}).get('content') or ''
        return text_out, out.get('prompt_eval_count'), out.get('eval_count'), latency


# ------------------------------------------------------------------ job
def _write(conn, item_id, f, status, text, h, flags, latency, error, attempts, model, approval_id, chars, decision=None):
    conn.execute('''UPDATE news_item_translations SET status=%s, text=%s, provider=%s, model=%s, response_model=%s, input_text_sha256=%s,
        quality_status=%s, quality_flags=%s, review_status='machine_unreviewed', latency_ms=%s, error=%s, attempt_count=%s, prompt_version=%s,
        source_chars=%s, content_version=content_version+1, superseded_at=NULL, updated_at=now()
        WHERE item_id=%s AND field=%s AND target_language='fa' AND NOT COALESCE(human_reviewed,false)''',
                 (status, text, 'ollama/local' if model else None, model, approval_id, h, decision, Jsonb(flags), latency, error, attempts, PV,
                  chars, item_id, f))
    _history(conn, item_id, f, status, text, h, flags, latency, error, model, approval_id, chars)


def run_job(conn, job, model):
    """Translate the eligible fields of one item. Returns {field: status}."""
    item_id = job['item_id']
    fields = [f for f in FIELDS if f in job['fields']]
    attempts = (job['attempts'] or 0) + 1
    prev = {r['field']: r['status'] for r in conn.execute('''SELECT field, status FROM news_item_translations
        WHERE item_id=%s AND target_language='fa' AND field = ANY(%s)''', (item_id, fields)).fetchall()}
    conn.execute('''UPDATE news_item_translations SET status='processing', updated_at=now()
        WHERE item_id=%s AND target_language='fa' AND field = ANY(%s)''', (item_id, fields))
    out = {}
    try:
        for f in fields:
            src = source_of(f, job['title'], job['summary'])
            h = sha(src)
            try:
                text, tin, tout, latency = model.call(src)
            except JobError as exc:
                flags = {'error': str(exc), 'worker': WORKER_VERSION}
                _write(conn, item_id, f, 'translation_error', None, h, flags, None, str(exc), attempts, model.approval['tag'],
                       model.approval['id'], len(src))
                out[f] = 'translation_error'
                continue
            text = unicodedata.normalize('NFC', text.strip())
            try:
                decision, det = v21.decide(src, text)
            except Exception as exc:  # noqa: BLE001 - one item's QC crash must not stop the queue
                LOG.exception('qc crashed on item=%s field=%s', item_id, f)
                err = f'qc_internal_error:{type(exc).__name__}'
                _write(conn, item_id, f, 'translation_error', None, h, {'error': err, 'worker': WORKER_VERSION}, latency, err,
                       attempts, model.approval['tag'], model.approval['id'], len(src))
                out[f] = 'translation_error'
                continue
            status = STATUS[decision]
            full = job['summary'] or ''
            flags = {'decision': decision, 'critical': det.get('critical', []), 'uncertain': det.get('uncertain', []),
                     'verified': len(det.get('verified', [])), 'facts': det.get('facts'), 'pipeline': v21.PIPELINE_VERSION,
                     'facts_version': v21.FACTS_VERSION, 'worker': WORKER_VERSION, 'tokens_in': tin, 'tokens_out': tout,
                     'human_verified': False}
            if f == 'summary':
                flags['source_scope'] = 'lead' if len(src) < len(re.sub(r'\s+', ' ', full.strip())) else 'full'
                flags['lead_chars'], flags['full_chars'] = len(src), len(full)
            _write(conn, item_id, f, status, text, h, flags, latency, None, attempts, model.approval['tag'], model.approval['id'],
                   len(src), decision)
            out[f] = status
            LOG.info('item=%s field=%s status=%s latency_ms=%d', item_id, f, status, latency)
            if Stop.requested:
                break
            time.sleep(CALL_GAP_SECONDS)
    except Paused:
        for f in fields:   # put every not-yet-written field back exactly as it was
            if f not in out:
                conn.execute('''UPDATE news_item_translations SET status=%s, updated_at=now()
                    WHERE item_id=%s AND field=%s AND target_language='fa' AND status='processing' ''',
                             (prev.get(f, 'translation_pending'), item_id, f))
        raise
    finally:
        for f in fields:   # a stop between fields leaves the rest queued, never 'processing'
            if f not in out:
                conn.execute('''UPDATE news_item_translations SET status='translation_pending', updated_at=now()
                    WHERE item_id=%s AND field=%s AND target_language='fa' AND status='processing' ''', (item_id, f))
    conn.execute('DELETE FROM translation_queue_requests WHERE item_id=%s', (item_id,))
    return out


# ------------------------------------------------------------------ status / loop
def counts(conn):
    rows = conn.execute('''SELECT field, status, count(*) AS n FROM news_item_translations
        WHERE target_language='fa' AND field IN ('title','summary') AND prompt_version=%s GROUP BY 1,2''', (PV,)).fetchall()
    by = {}
    for r in rows:
        by.setdefault(r['field'], {})[r['status']] = r['n']
    lat = conn.execute('''SELECT avg(latency_ms)::int AS avg_ms, max(latency_ms) AS max_ms, count(*) AS n FROM news_item_translation_history
        WHERE prompt_version=%s AND latency_ms IS NOT NULL AND generated_at > now() - interval '24 hours' ''', (PV,)).fetchone()
    q = conn.execute('''SELECT count(DISTINCT item_id) AS n FROM news_item_translations
        WHERE prompt_version=%s AND status IN ('translation_pending','processing')''', (PV,)).fetchone()['n']
    return {'pipeline': PV, 'by_field': by, 'queue_items': q, 'latency_24h': lat}


def settings():
    s = local_ai.load_settings(role='translation')
    enabled = (os.getenv('LOCAL_TRANSLATION_ENABLED') or 'false').strip().lower() == 'true'
    return s, enabled


def loop(dsn, once=False, item_ids=None):
    s, enabled = settings()
    with local_ai.connect(dsn) as conn:
        ensure_schema(conn)
        if not enabled:
            beat(conn, 'disabled')
            LOG.warning('LOCAL_TRANSLATION_ENABLED is not true; nothing to do')
            return 0
        if s.errors or not s.approval:
            beat(conn, 'blocked', errors=s.errors)
            LOG.error('no servable translation artifact: %s', s.errors)
            return 2
        lock = local_ai.connect(dsn)
        if not lock.execute('SELECT pg_try_advisory_lock(%s) AS ok', (local_ai.BATCH_LOCK,)).fetchone()['ok']:
            beat(conn, 'blocked', errors=['worker_already_running'])
            return 3
        try:
            LOG.warning('recovered: %s', recover(conn))
            model = Model(s, dsn)
            last_reconcile, pause, db_errors = 0.0, 0, 0
            while not Stop.requested:
                try:
                    if time.monotonic() - last_reconcile > 60:
                        rc = reconcile(conn, item_ids)
                        last_reconcile = time.monotonic()
                        if any(rc.values()):
                            LOG.info('reconcile %s', rc)
                    job = next_job(conn, item_ids)
                    if not job:
                        beat(conn, 'idle', **counts(conn))
                        if once:
                            return 0
                        time.sleep(IDLE_SECONDS)
                        continue
                    if pause == 0 or pause % 5 == 0:
                        model.preflight()
                    beat(conn, 'working', item_id=job['item_id'], **counts(conn))
                    run_job(conn, job, model)
                    pause = 0
                    if once:
                        return 0
                    time.sleep(SLEEP_SECONDS)
                except Paused as exc:
                    pause += 1
                    wait = min(600, 30 * pause)
                    beat(conn, 'paused', reason=str(exc), retry_in_s=wait)
                    LOG.warning('paused (%s); retry in %ss', exc, wait)
                    if once:
                        return 4
                    for _ in range(wait):
                        if Stop.requested:
                            break
                        time.sleep(1)
                except psycopg.Error as exc:   # DB hiccup: back off, reconnect, record it in the heartbeat
                    db_errors += 1
                    wait = min(300, 10 * 2 ** min(db_errors - 1, 5))
                    LOG.exception('database error (%s in a row): %s; retry in %ss', db_errors, exc, wait)
                    time.sleep(wait)
                    try:
                        conn = local_ai.connect(dsn)
                        beat(conn, 'error', reason=str(exc)[:300], consecutive=db_errors, retry_in_s=wait)
                    except psycopg.Error:
                        pass
                    continue
                db_errors = 0
            beat(conn, 'stopped')
            return 0
        finally:
            try:
                lock.execute('SELECT pg_advisory_unlock(%s)', (local_ai.BATCH_LOCK,))
            finally:
                lock.close()


def main(argv=None):
    logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'), format='%(asctime)s %(levelname)s %(name)s %(message)s')
    ap = argparse.ArgumentParser(prog='translation_worker_v2')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('run')
    o = sub.add_parser('once')
    o.add_argument('--item-ids')
    sub.add_parser('status')
    a = ap.parse_args(argv)
    dsn = os.environ['DATABASE_URL']
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    if a.cmd == 'status':
        with local_ai.connect(dsn) as conn:
            ensure_schema(conn)
            st = conn.execute("SELECT * FROM translation_worker_state WHERE worker='ai-translator'").fetchone()
            print(json.dumps({'worker': st, **counts(conn)}, ensure_ascii=False, indent=1, default=str))
        return 0
    ids = [x for x in (getattr(a, 'item_ids', None) or '').split(',') if x] or None
    return loop(dsn, once=(a.cmd == 'once'), item_ids=ids)


if __name__ == '__main__':
    sys.exit(main())

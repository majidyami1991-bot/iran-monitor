"""Offline, sequential Persian translation of collected content with the
local Ollama model (CPU only). Operator-started; exits when the batch ends.

    python -m local_translation status
    python -m local_translation dry-run --limit 10
    python -m local_translation run --limit 3 [--item-ids a,b,c] [--stop-on-review]
    python -m local_translation run --all-pending
    python -m local_translation retry-review --limit 10

What is translated
    news   title + stored summary (COALESCE(summary_text, summary)) — written
           to news_item_translations (fields 'title' / 'summary') and
           news_item_translation_history, the tables the UI already reads.
    x      analyst-recorded X post text — x_post_translations (+ history).
Never translated: URLs, ids, metadata, empty or Persian text. Nothing is
crawled to obtain text; only what is already stored is used.

Budget
    One request carries title + the first summary chunk; a summary longer
    than one chunk continues in further requests. Each request asks for at
    most LOCAL_AI_MAX_OUTPUT_TOKENS (<= 512) output tokens, sized from the
    input length. Prompt translate-fa-v1.0.0 is short; no metadata is sent.

Guarantees
    - concurrency 1: BATCH_LOCK per batch, INFERENCE_LOCK per model call
      (shared with the assistant, which waits or reports "busy");
    - available only after the independent validator passes, else
      needs_review (never displayed);
    - cache: done rows are never picked again, and the gateway cache keys on
      sha256(task|prompt version|input) + provider + model;
    - source text changes -> stale -> re-translated; every outcome is a new
      history row (history is append-only, enforced by trigger);
    - Ollama down / wrong model -> the batch stops, the job returns to its
      previous status (fail closed); a crash leaves no row 'processing'.
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
from dataclasses import dataclass, field

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

import ai_gateway as gw
import local_ai
import x_translation_validator as xv

LOG = logging.getLogger('defence_monitor.local_translation')
PROMPT_VERSION = 'translate-fa-v1.0.0'
NEWS_FIELDS = ('title', 'summary')
TRANSIENT = ('transient_timeout', 'provider_unavailable')
STOP_BATCH = ('provider_unreachable', 'model_not_found', 'model_digest_mismatch', 'model_identity_mismatch',
              'model_not_approved', 'provider_not_configured', 'circuit_open', 'ollama_host_not_local', 'model_busy')
CHUNK_CHARS = 600          # ~ 0.7 output tokens per source char -> < 512 tokens per request
MAX_SOURCE_CHARS = 4000    # longer fields are not sent (they would need too many CPU minutes)
SUMMARY_SQL = "COALESCE(NULLIF(btrim(n.summary_text), ''), NULLIF(btrim(n.summary), ''))"


# ------------------------------------------------------------------ settings
@dataclass
class Settings:
    ai: local_ai.LocalAISettings
    enabled: bool
    sleep_seconds: float
    max_attempts: int
    errors: list = field(default_factory=list)


def load_settings():
    ai = local_ai.load_settings()
    s = Settings(ai=ai, enabled=(os.getenv('LOCAL_TRANSLATION_ENABLED') or 'false').strip().lower() == 'true',
                 sleep_seconds=max(0.0, min(float(os.getenv('LOCAL_TRANSLATION_SLEEP_SECONDS', '2') or 2), 3.0)),
                 max_attempts=2)
    s.errors = list(ai.errors)
    return s


# ------------------------------------------------------------------ pure helpers
def sha(text):
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()


_SENT = re.compile(r'(?<=[.!?؟…])\s+')


def chunks(text, first_budget=CHUNK_CHARS, budget=CHUNK_CHARS):
    """Split at sentence ends; a sentence longer than the budget is split at
    the last space before it. Pure; joining the parts with ' ' restores the
    text up to whitespace."""
    text = re.sub(r'\s+', ' ', (text or '').strip())
    if not text:
        return []
    out, cur, lim = [], '', first_budget
    for sent in _SENT.split(text):
        while len(sent) > lim:
            cut = sent.rfind(' ', 0, lim)
            cut = cut if cut > lim // 3 else lim
            if cur:
                out.append(cur)
                cur, lim = '', budget
                continue
            out.append(sent[:cut].strip())
            sent, lim = sent[cut:].strip(), budget
        if not cur:
            cur = sent
        elif len(cur) + 1 + len(sent) <= lim:
            cur += ' ' + sent
        else:
            out.append(cur)
            cur, lim = sent, budget
    if cur:
        out.append(cur)
    return [c for c in out if c]


def predict_for(chars, cap):
    return max(96, min(cap, 60 + int(chars * 0.75)))


def error_class(error):
    return (error or '').split(':', 1)[0]


def classify_failure(result):
    """(status, error, stop_batch, retryable) for a non-success gateway result."""
    if result.status == 'invalid_response':
        return 'failed', 'invalid_response:' + (result.error or '')[:60], False, False
    cls = error_class(result.error) if result.status == 'error' else result.status
    if result.status in ('circuit_open', 'provider_not_configured') or cls in STOP_BATCH:
        return 'pending', cls, True, False
    return 'failed', cls[:120] or 'unknown_error', False, cls in TRANSIENT


_GLITCH_FLAGS = frozenset(('stray_markup', 'invisible_characters'))


def decoding_glitch(payload_in, payload_out):
    """True when some output string carries debris (stray brackets/template
    tags/control characters, or a Devanagari danda) that its input lacks."""
    src = ' '.join(str(v) for v in (payload_in or {}).values())
    for k, v in (payload_out or {}).items():
        if not isinstance(v, str) or not v:
            continue
        if '।' in v and '।' not in src:
            return True
        flags = set(xv.validate(src, v).flags) if v.strip() else set()
        if flags & _GLITCH_FLAGS:
            return True
    return False


def judge(source, translated):
    """Validator verdict for one field. Returns (status, score, flags)."""
    v = xv.validate(source, translated)
    return ('available' if v.passed else 'needs_review'), v.quality_score, v.flags


# ------------------------------------------------------------------ db: news
def _x(conn, sql, args=None):
    return conn.cursor(row_factory=dict_row).execute(sql, args)


def reconcile_news(conn, item_ids=None):
    """DB only. Creates pending rows for fields with text, marks local rows
    whose source changed as stale, Persian sources as not_required. Rows
    written by other providers that are 'available', any human-reviewed row,
    and legacy 'needs_review' rows are left alone."""
    where, args = '', {}
    if item_ids:
        where, args = 'WHERE n.item_id = ANY(%(ids)s)', {'ids': list(item_ids)}
    rows = _x(conn, f'''SELECT n.item_id, n.title, {SUMMARY_SQL} AS summary,
        tt.status AS t_status, tt.input_text_sha256 AS t_hash, tt.prompt_version AS t_pv, tt.human_reviewed AS t_h,
        ts.status AS s_status, ts.input_text_sha256 AS s_hash, ts.prompt_version AS s_pv, ts.human_reviewed AS s_h
        FROM news_items n
        LEFT JOIN news_item_translations tt ON tt.item_id=n.item_id AND tt.field='title' AND tt.target_language='fa'
        LEFT JOIN news_item_translations ts ON ts.item_id=n.item_id AND ts.field='summary' AND ts.target_language='fa'
        {where}''', args).fetchall()
    c = {'created': 0, 'stale': 0, 'not_required': 0, 'reset_legacy': 0}
    for r in rows:
        for f, p in (('title', 't'), ('summary', 's')):
            text = r[f]
            if not text or not text.strip() or len(text) > MAX_SOURCE_CHARS:
                continue
            h, status, pv, human = sha(text), r[p + '_status'], r[p + '_pv'], r[p + '_h']
            persian = xv.is_persian_source(text)
            if status is None:
                _x(conn, '''INSERT INTO news_item_translations(item_id,field,target_language,status,input_text_sha256,
                    prompt_version,source_chars,provider,review_status) VALUES(%s,%s,'fa',%s,%s,%s,%s,%s,'not_applicable')
                    ON CONFLICT DO NOTHING''',
                   (r['item_id'], f, 'not_required' if persian else 'pending', h, PROMPT_VERSION, len(text),
                    'rule' if persian else None))
                c['created'] += 1
                c['not_required'] += persian
            elif human:
                continue
            elif pv == PROMPT_VERSION and r[p + '_hash'] != h and status != 'processing':
                new = 'not_required' if persian else 'stale'
                _x(conn, '''UPDATE news_item_translations SET status=%s, input_text_sha256=%s, source_chars=%s,
                    review_status='not_applicable', error=NULL, updated_at=now() WHERE item_id=%s AND field=%s AND target_language='fa' ''',
                   (new, h, len(text), r['item_id'], f))
                _history_news(conn, r['item_id'], f, new, None, h, None, [], None, None)
                c['stale' if new == 'stale' else 'not_required'] += 1
            elif pv != PROMPT_VERSION and status in ('pending', 'error'):
                # Legacy queued/failed rows from the earlier cloud pilot: adopt them.
                _x(conn, '''UPDATE news_item_translations SET status='pending', input_text_sha256=%s, prompt_version=%s,
                    source_chars=%s, error=NULL, updated_at=now() WHERE item_id=%s AND field=%s AND target_language='fa' ''',
                   (h, PROMPT_VERSION, len(text), r['item_id'], f))
                c['reset_legacy'] += 1
    return c


def _history_news(conn, item_id, f, status, text, h, score, flags, latency, error, model=None, provider=None):
    v = _x(conn, '''SELECT COALESCE(max(content_version),0)+1 AS v FROM news_item_translation_history
        WHERE item_id=%s AND field=%s AND target_language='fa' ''', (item_id, f)).fetchone()['v']
    _x(conn, '''INSERT INTO news_item_translation_history(item_id,field,target_language,content_version,status,text,
        provider,model,prompt_version,input_text_sha256,quality_score,quality_flags,latency_ms,error,response_model,
        reported_cost_usd) VALUES(%s,%s,'fa',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0)''',
       (item_id, f, v, status, text, provider, model, PROMPT_VERSION, h, score, Jsonb(flags or []), latency, error, model))
    return v


def news_jobs(conn, limit, item_ids=None, statuses=('pending', 'stale')):
    """Items with at least one eligible field, newest first (deterministic)."""
    args = {'st': list(statuses), 'l': limit}
    extra = ''
    if item_ids:
        extra, args['ids'] = ' AND n.item_id = ANY(%(ids)s)', list(item_ids)
    return _x(conn, f'''SELECT n.item_id, n.title, {SUMMARY_SQL} AS summary,
        array_agg(t.field ORDER BY t.field DESC) AS fields, max(t.attempt_count) AS attempts
        FROM news_item_translations t JOIN news_items n ON n.item_id=t.item_id
        WHERE t.target_language='fa' AND t.field IN ('title','summary') AND t.status = ANY(%(st)s)
          AND t.prompt_version = %(pv)s AND NOT COALESCE(t.human_reviewed, false){extra}
        GROUP BY n.item_id, n.title, n.summary_text, n.summary, n.published_at, n.fetched_at
        ORDER BY COALESCE(n.published_at, n.fetched_at) DESC NULLS LAST, n.item_id LIMIT %(l)s''',
              {**args, 'pv': PROMPT_VERSION}).fetchall()


def recover_orphans(conn):
    a = _x(conn, '''UPDATE news_item_translations SET status='pending', error='recovered_from_processing', updated_at=now()
        WHERE status='processing' AND prompt_version=%s RETURNING item_id''', (PROMPT_VERSION,)).fetchall()
    b = _x(conn, '''UPDATE x_post_translations SET status='pending', processing_started_at=NULL,
        last_error='recovered_from_processing', updated_at=now() WHERE status='processing' RETURNING x_post_id''').fetchall()
    return sorted({r['item_id'] for r in a} | {r['x_post_id'] for r in b})


def counts(conn):
    rows = _x(conn, '''SELECT field, status, count(*) AS n FROM news_item_translations
        WHERE target_language='fa' AND field IN ('title','summary') GROUP BY 1,2''').fetchall()
    by = {}
    for r in rows:
        by.setdefault(r['field'], {})[r['status']] = r['n']
    x = {r['status']: r['n'] for r in _x(conn, 'SELECT status, count(*) AS n FROM x_post_translations GROUP BY 1').fetchall()}
    items = _x(conn, f'''SELECT count(*) AS items, count(*) FILTER (WHERE {SUMMARY_SQL} IS NOT NULL) AS with_summary,
        (SELECT count(*) FROM x_posts WHERE coalesce(btrim(original_text),'')<>'') AS x_with_text FROM news_items n''').fetchone()
    lat = _x(conn, '''SELECT avg(latency_ms)::int AS avg_ms, max(latency_ms) AS max_ms, count(*) AS n
        FROM news_item_translation_history WHERE prompt_version=%s AND status='available' AND latency_ms IS NOT NULL''',
             (PROMPT_VERSION,)).fetchone()
    return {'news_items': items['items'], 'news_with_summary': items['with_summary'], 'news_title': by.get('title', {}),
            'news_summary': by.get('summary', {}), 'x_posts_with_text': items['x_with_text'], 'x': x,
            'local_available_fields': lat['n'], 'average_latency_ms': lat['avg_ms'], 'max_latency_ms': lat['max_ms']}


# ------------------------------------------------------------------ batch
class Stop:
    requested = False


def _on_signal(signum, frame):
    Stop.requested = True
    LOG.warning('stop requested (signal %s); finishing the current job', signum)


@dataclass
class Report:
    jobs: int = 0
    fields_available: int = 0
    fields_needs_review: int = 0
    fields_failed: int = 0
    fields_not_required: int = 0
    returned_to_pending: int = 0
    inferences: int = 0
    cache_hits: int = 0
    retries: int = 0
    glitch_retries: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    job_latencies_ms: list = field(default_factory=list)
    stopped_reason: str | None = None
    recovered: list = field(default_factory=list)
    reconcile: dict = field(default_factory=dict)

    def as_dict(self):
        lat = self.job_latencies_ms
        d = {k: v for k, v in self.__dict__.items() if k != 'job_latencies_ms'}
        d['average_job_latency_ms'] = int(sum(lat) / len(lat)) if lat else None
        d['max_job_latency_ms'] = max(lat) if lat else None
        d['cost_usd'] = 0
        return d


class Infer:
    """One gateway per task type, every call under INFERENCE_LOCK."""

    def __init__(self, s, dsn, report, gateways=None, use_cache=True, sleep=time.sleep, fresh_gateways=None):
        self.s, self.dsn, self.report, self.sleep = s, dsn, report, sleep
        self.g = gateways or {t: local_ai.build_gateway(s.ai, dsn, t, use_cache) for t in ('translate_news', 'translate_text')}
        self._fresh = fresh_gateways

    def fresh(self, task):
        """Cache-bypassing gateway for the one decoding-glitch re-ask."""
        if self._fresh is None:
            self._fresh = {t: local_ai.build_gateway(self.s.ai, self.dsn, t, use_cache=False)
                           for t in ('translate_news', 'translate_text')}
        return self._fresh[task]

    def call(self, task, payload, chars):
        g = self.g[task]
        content = json.dumps(payload, ensure_ascii=False)
        for attempt in (1, 2):
            if isinstance(g.adapter, gw.OllamaAdapter):
                g.adapter.predict_override = predict_for(chars, self.s.ai.max_output_tokens)
            try:
                with local_ai.inference_lock(self.dsn, wait_seconds=self.s.ai.timeout_seconds,
                                             should_cancel=lambda: Stop.requested):
                    r = g.run(gw.GatewayRequest(task, content, prompt_version=PROMPT_VERSION))
            except local_ai.Busy as exc:
                return None, ('pending', str(exc), True, False)
            if r.cache_hit:
                self.report.cache_hits += 1
            elif r.latency_ms is not None:
                self.report.inferences += 1
                self.report.tokens_in += r.tokens_in or 0
                self.report.tokens_out += r.tokens_out or 0
            if r.status in ('available', 'cached'):
                if attempt == 1 and decoding_glitch(payload, r.payload) and not Stop.requested:
                    # Special-token / template debris in an otherwise valid
                    # answer is a decoder fault, not a translation judgement:
                    # ask once more without the cache (counts as the retry).
                    self.report.retries += 1
                    self.report.glitch_retries += 1
                    g = self.fresh(task)
                    continue
                return r, None
            failure = classify_failure(r)
            if failure[3] and attempt < self.s.max_attempts and not Stop.requested:
                self.report.retries += 1
                self.sleep(min(5.0, self.s.sleep_seconds + 1))
                continue
            return r, failure
        return r, failure


def translate_parts(infer, parts):
    """Translate pre-split parts in order with translate_text. Returns
    (translation, failure). A part whose output hits the token cap is split
    once more and retried as two halves."""
    out = []
    for part in parts:
        r, failure = infer.call('translate_text', {'text': part}, len(part))
        if failure and failure[1] == 'output_truncated_num_predict' and len(part) > 200:
            sub = []
            for h in chunks(part, len(part) // 2 + 1, len(part) // 2 + 1):
                r, failure = infer.call('translate_text', {'text': h}, len(h))
                if failure:
                    return None, failure
                sub.append(r.payload['text_fa'].strip())
            out.append(' '.join(sub))
            continue
        if failure:
            return None, failure
        if r.payload.get('translation_not_required'):
            return None, ('needs_review', 'model_claimed_not_required', False, False)
        out.append(r.payload['text_fa'].strip())
    return ' '.join(o for o in out if o), None


def _set_news(conn, item_id, f, status, text, h, score, flags, latency, error, attempts, model):
    review = {'available': 'pending_review', 'needs_review': 'needs_review'}.get(status, 'not_applicable')
    _x(conn, '''UPDATE news_item_translations SET status=%s, text=%s, provider=%s, model=%s, response_model=%s,
        input_text_sha256=%s, quality_score=%s, quality_flags=%s, review_status=%s, latency_ms=%s, error=%s,
        attempt_count=%s, prompt_version=%s, content_version=content_version+1, superseded_at=NULL, updated_at=now()
        WHERE item_id=%s AND field=%s AND target_language='fa' AND NOT COALESCE(human_reviewed,false)''',
       (status, text, 'ollama/local' if model else None, model, model, h, score, Jsonb(flags or []), review, latency,
        error, attempts, PROMPT_VERSION, item_id, f))
    _history_news(conn, item_id, f, status, text, h, score, flags, latency, error, model, 'ollama/local' if model else None)


def translate_news_job(conn, job, infer, s, report):
    """Returns 'ok' | 'review' | 'stop:<reason>'."""
    item_id, fields = job['item_id'], [f for f in job['fields'] if f in NEWS_FIELDS]
    src = {'title': job['title'], 'summary': job['summary']}
    attempts = (job['attempts'] or 0) + 1
    prev = {r['field']: r['status'] for r in _x(conn, '''SELECT field, status FROM news_item_translations
        WHERE item_id=%s AND target_language='fa' AND field = ANY(%s)''', (item_id, fields)).fetchall()}
    _x(conn, '''UPDATE news_item_translations SET status='processing', attempt_count=%s, updated_at=now()
        WHERE item_id=%s AND target_language='fa' AND field = ANY(%s)''', (attempts, item_id, fields))
    started = time.monotonic()
    model = s.ai.model
    results, failure = {}, None
    want_title, want_summary = 'title' in fields, 'summary' in fields
    parts = []
    if want_summary:
        first_budget = CHUNK_CHARS - (len(src['title']) if want_title else 0)
        parts = chunks(src['summary'], max(200, first_budget), CHUNK_CHARS)
    if want_title:
        payload = {'title': src['title'], 'summary': parts[0] if parts else ''}
        r, failure = infer.call('translate_news', payload, len(payload['title']) + len(payload['summary']))
        if not failure and r.payload.get('translation_not_required'):
            failure = ('needs_review', 'model_claimed_not_required', False, False)
        if not failure:
            results['title'] = r.payload['title_fa'].strip()
            if want_summary:
                rest, failure = translate_parts(infer, parts[1:]) if len(parts) > 1 else ('', None)
                if not failure:
                    results['summary'] = (r.payload['summary_fa'].strip() + ' ' + rest).strip()
    elif want_summary:
        tr, failure = translate_parts(infer, parts)
        if not failure:
            results['summary'] = tr
    latency = int((time.monotonic() - started) * 1000)

    if failure and failure[2]:  # stop batch: put fields back exactly as they were
        for f in fields:
            _x(conn, '''UPDATE news_item_translations SET status=%s, attempt_count=%s, error=%s, updated_at=now()
                WHERE item_id=%s AND field=%s AND target_language='fa' ''', (prev.get(f, 'pending'), job['attempts'] or 0,
                                                                              failure[1], item_id, f))
        report.returned_to_pending += 1
        return 'stop:' + failure[1]
    outcome = 'ok'
    for f in fields:
        h = sha(src[f])
        if f in results:
            status, score, flags = judge(src[f], results[f])
            _set_news(conn, item_id, f, status, results[f], h, score, flags, latency, None, attempts, model)
        else:
            status = failure[0] if failure else 'failed'
            _set_news(conn, item_id, f, status, None, h, None, [failure[1]] if failure else [], latency,
                      failure[1] if failure else 'no_output', attempts, model)
        report_key = {'available': 'fields_available', 'needs_review': 'fields_needs_review'}.get(status, 'fields_failed')
        setattr(report, report_key, getattr(report, report_key) + 1)
        if status != 'available':
            outcome = 'review'
    report.job_latencies_ms.append(latency)
    LOG.info('news item=%s fields=%s outcome=%s latency_ms=%d', item_id, ','.join(fields), outcome, latency)
    return outcome


def translate_x_job(conn, row, infer, s, report):
    import x_translate_worker as xw
    attempts = row['attempt_count'] + 1
    _x(conn, '''UPDATE x_post_translations SET status='processing', attempt_count=%s, processing_started_at=now(),
        updated_at=now() WHERE id=%s''', (attempts, row['id']))
    started = time.monotonic()
    tr, failure = translate_parts(infer, chunks(row['original_text']))
    latency = int((time.monotonic() - started) * 1000)
    if failure and failure[2]:
        _x(conn, '''UPDATE x_post_translations SET status=%s, attempt_count=%s, processing_started_at=NULL, last_error=%s,
            updated_at=now() WHERE id=%s''', (row['status'], row['attempt_count'], failure[1], row['id']))
        report.returned_to_pending += 1
        return 'stop:' + failure[1]
    if failure:
        status, score, flags, text = failure[0], None, [failure[1]], None
    else:
        status, score, flags = judge(row['original_text'], tr)
        text = tr
    _x(conn, '''UPDATE x_post_translations SET status=%s, translated_text=%s, provider='ollama/local', model=%s,
        prompt_version=%s, translation_hash=%s, quality_score=%s, quality_flags_json=%s, attempt_count=%s, latency_ms=%s,
        last_error=%s, processing_started_at=NULL, source_language=COALESCE(source_language,'en'),
        translated_at=CASE WHEN %s IN ('available','needs_review') THEN now() ELSE translated_at END, updated_at=now()
        WHERE id=%s''', (status, text, s.ai.model, PROMPT_VERSION, sha(text) if text else None, score, Jsonb(flags),
                         attempts, latency, failure[1] if failure else None, status, row['id']))
    key = {'available': 'fields_available', 'needs_review': 'fields_needs_review'}.get(status, 'fields_failed')
    setattr(report, key, getattr(report, key) + 1)
    report.job_latencies_ms.append(latency)
    LOG.info('x post=%s outcome=%s latency_ms=%d', row['x_post_id'], status, latency)
    return 'ok' if status == 'available' else 'review'


def run_batch(dsn, s, *, limit=None, item_ids=None, stop_on_review=False, statuses=('pending', 'stale'),
              use_cache=True, gateways=None, sleep=time.sleep, content=('news', 'x')):
    report = Report()
    if s.errors:
        raise RuntimeError('; '.join(s.errors))
    if not s.enabled:
        report.stopped_reason = 'local_translation_disabled'
        return report
    lock = local_ai.connect(dsn)
    try:
        if not lock.execute('SELECT pg_try_advisory_lock(%s) AS ok', (local_ai.BATCH_LOCK,)).fetchone()['ok']:
            report.stopped_reason = 'worker_already_running'
            return report
        with local_ai.connect(dsn) as conn:
            report.recovered = recover_orphans(conn)
            report.reconcile = reconcile_news(conn, item_ids)
            if 'x' in content and not item_ids:
                import x_translate_worker as xw
                xr = xw.reconcile(conn)
                report.reconcile['x'] = xr
            infer = Infer(s, dsn, report, gateways, use_cache, sleep)
            first = next(iter(infer.g.values()))
            if isinstance(first.adapter, gw.OllamaAdapter):
                try:
                    first.adapter.verify_model(timeout=10)
                except gw.GatewayError as exc:
                    report.stopped_reason = error_class(str(exc))
                    return report
            done = 0
            while not Stop.requested and (limit is None or done < limit):
                outcome = None
                if 'news' in content:
                    jobs = news_jobs(conn, 1, item_ids, statuses)
                    if jobs:
                        report.jobs += 1
                        outcome = translate_news_job(conn, jobs[0], infer, s, report)
                if outcome is None and 'x' in content and not item_ids:
                    import x_translate_worker as xw
                    rows = xw.eligible(conn, 1, None, statuses)
                    if rows:
                        report.jobs += 1
                        outcome = translate_x_job(conn, rows[0], infer, s, report)
                if outcome is None:
                    break
                done += 1
                if outcome.startswith('stop:'):
                    report.stopped_reason = outcome[5:]
                    break
                if stop_on_review and outcome == 'review':
                    report.stopped_reason = 'stop_on_review'
                    break
                if s.sleep_seconds and (limit is None or done < limit):
                    sleep(s.sleep_seconds)  # the assistant can take the model between jobs
            if Stop.requested and not report.stopped_reason:
                report.stopped_reason = 'signal'
    finally:
        try:
            lock.execute('SELECT pg_advisory_unlock(%s)', (local_ai.BATCH_LOCK,))
        finally:
            lock.close()
    return report


def requeue_review(dsn, limit, item_ids=None):
    with local_ai.connect(dsn) as conn:
        args, extra = {'l': limit, 'pv': PROMPT_VERSION}, ''
        if item_ids:
            extra, args['ids'] = ' AND item_id = ANY(%(ids)s)', list(item_ids)
        rows = _x(conn, f'''UPDATE news_item_translations SET status='pending', attempt_count=0, error=NULL, updated_at=now()
            WHERE (item_id, field) IN (SELECT item_id, field FROM news_item_translations
              WHERE status IN ('needs_review','failed') AND prompt_version=%(pv)s AND NOT COALESCE(human_reviewed,false){extra}
              ORDER BY updated_at LIMIT %(l)s) RETURNING item_id''', args).fetchall()
    return sorted({r['item_id'] for r in rows})


def dry_run(dsn, s, limit, item_ids=None):
    """No writes, no model call."""
    with local_ai.connect(dsn) as conn:
        rows = _x(conn, f'''SELECT n.item_id, length(n.title) AS t_len, length({SUMMARY_SQL}) AS s_len,
            tt.status AS t_status, ts.status AS s_status
            FROM news_items n
            LEFT JOIN news_item_translations tt ON tt.item_id=n.item_id AND tt.field='title' AND tt.target_language='fa'
            LEFT JOIN news_item_translations ts ON ts.item_id=n.item_id AND ts.field='summary' AND ts.target_language='fa'
            ORDER BY COALESCE(n.published_at, n.fetched_at) DESC NULLS LAST, n.item_id''').fetchall()
    todo = []
    for r in rows:
        if item_ids and r['item_id'] not in item_ids:
            continue
        fields = [f for f, st, ln in (('title', r['t_status'], r['t_len']), ('summary', r['s_status'], r['s_len']))
                  if ln and ln <= MAX_SOURCE_CHARS and st in (None, 'pending', 'stale', 'error')]
        if fields:
            req = 1 + (max(0, len(chunks('x' * (r['s_len'] or 0))) - 1) if 'summary' in fields else 0)
            todo.append({'item_id': r['item_id'], 'fields': fields, 'requests': req,
                         'source_chars': (r['t_len'] or 0) * ('title' in fields) + (r['s_len'] or 0) * ('summary' in fields)})
    return {'would_translate': todo[:limit], 'jobs_total': len(todo),
            'requests_total_estimate': sum(t['requests'] for t in todo),
            'source_chars_total': sum(t['source_chars'] for t in todo), 'model_calls': 0, 'writes': 0}


def status_report(dsn, s):
    reachable, found, digest = local_ai.probe(s.ai, ttl=0)
    with local_ai.connect(dsn) as conn:
        c = counts(conn)
        running = local_ai.lock_held(conn, local_ai.BATCH_LOCK)
        busy = local_ai.lock_held(conn, local_ai.INFERENCE_LOCK)
    return {**c, 'ollama_reachable': reachable, 'model_found': found, 'model_digest': digest, 'model': s.ai.model,
            'provider': 'ollama/local', 'prompt_version': PROMPT_VERSION, 'enabled': s.enabled,
            'batch_running': running, 'model_busy': busy, 'config_errors': s.errors, 'cost_usd': 0}


def main(argv=None):
    logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'), format='%(asctime)s %(levelname)s %(name)s %(message)s')
    ap = argparse.ArgumentParser(prog='local_translation')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('status')
    d = sub.add_parser('dry-run')
    d.add_argument('--limit', type=int, default=10)
    d.add_argument('--item-ids')
    r = sub.add_parser('run')
    g = r.add_mutually_exclusive_group(required=True)
    g.add_argument('--limit', type=int)
    g.add_argument('--all-pending', action='store_true')
    r.add_argument('--item-ids')
    r.add_argument('--stop-on-review', action='store_true')
    rr = sub.add_parser('retry-review')
    rr.add_argument('--limit', type=int, default=10)
    rr.add_argument('--item-ids')
    a = ap.parse_args(argv)
    dsn = os.environ['DATABASE_URL']
    s = load_settings()
    ids = [x for x in (getattr(a, 'item_ids', None) or '').split(',') if x] or None
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    def out(o):
        print(json.dumps(o, ensure_ascii=False, indent=2, default=str))

    if a.cmd == 'status':
        out(status_report(dsn, s))
        return 0
    if a.cmd == 'dry-run':
        out(dry_run(dsn, s, a.limit, ids))
        return 0
    if s.errors:
        out({'error': 'configuration', 'details': s.errors})
        return 2
    if a.cmd == 'retry-review':
        if not s.enabled:
            out({'stopped_reason': 'local_translation_disabled'})
            return 3
        req = requeue_review(dsn, a.limit, ids)
        rep = run_batch(dsn, s, limit=len(req), item_ids=req, use_cache=False) if req else Report()
        out({'requeued': req, **rep.as_dict()})
        return 0
    rep = run_batch(dsn, s, limit=None if a.all_pending else a.limit, item_ids=ids, stop_on_review=a.stop_on_review)
    out(rep.as_dict())
    return 0 if rep.stopped_reason in (None, 'signal', 'stop_on_review') else 3


if __name__ == '__main__':
    sys.exit(main())

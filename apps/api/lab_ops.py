"""Operational status of the isolated 3003 lab for the admin page.

Read-only. Every value comes from the 3003 database or from host status files
mounted read-only (/ops-status: health monitor + backup manifests written by
host scripts; /ops-sync: the news-sync scheduler log). A source that is not
available is reported as status 'unknown' with a reason — never filled in.
Alerts are derived from the same values with fixed thresholds.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

import model_identity as mi

DSN = os.environ.get('DATABASE_URL', '')
OPS_DIR = Path(os.getenv('LAB_OPS_DIR', '/ops-status'))
SYNC_DIR = Path(os.getenv('LAB_SYNC_DIR', '/ops-sync'))
SYNC_STALE_MIN = 45
WORKER_STALE_MIN = 10
EVENTS_STALE_MIN = 45
BACKUP_STALE_HOURS = 26
HEALTH_STALE_MIN = 10


def _q(c, sql, args=None, one=False):
    try:
        cur = c.execute(sql, args or ())
        return cur.fetchone() if one else cur.fetchall()
    except psycopg.Error:
        c.rollback()
        return None


def _tail(path, n=1):
    try:
        lines = [x for x in path.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
    except OSError:
        return None
    out = []
    for x in lines[-n:]:
        try:
            out.append(json.loads(x))
        except ValueError:
            continue
    return out


def _age_min(ts, now):
    if not ts:
        return None
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except ValueError:
            return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return round((now - ts).total_seconds() / 60, 1)


def status():
    now = datetime.now(timezone.utc)
    out, alerts = {'checked_at': now.isoformat()}, []
    with psycopg.connect(DSN, row_factory=dict_row) as c:
        c.execute('SET TRANSACTION READ ONLY')
        n = _q(c, '''SELECT count(*) AS items, max(collected_at) AS latest_collected, max(published_at) FILTER (WHERE published_at <= now()) AS latest_published,
            count(*) FILTER (WHERE collected_at > now() - interval '24 hours') AS items_24h FROM news_items''', one=True)
        prod = _q(c, '''SELECT started_at, finished_at, status FROM collection_runs ORDER BY started_at DESC LIMIT 1''', one=True)
        out['news'] = {**(n or {}), 'production_collector_last_run': prod}
        runs = _q(c, '''SELECT run_id, mode, status, started_at, finished_at, counts, note FROM news_sync_runs ORDER BY finished_at DESC NULLS LAST LIMIT 8''')
        last_ok = _q(c, "SELECT max(finished_at) AS t FROM news_sync_runs WHERE status='succeeded'", one=True)
        fails = _q(c, "SELECT count(*) AS n FROM news_sync_runs WHERE status<>'succeeded' AND finished_at > now()-interval '24 hours'", one=True)
        sched = _tail(SYNC_DIR / 'scheduler.jsonl', 5)
        out['sync'] = {'runs': [{**r, 'counts': {k: v for k, v in (r['counts'] or {}).items() if k == 'news_items' or k == '_deferred_new_items'}}
                                for r in (runs or [])],
                       'last_success': (last_ok or {}).get('t'), 'failures_24h': (fails or {}).get('n'),
                       'scheduler_log': sched, 'scheduler': 'unknown' if sched is None else ('seen' if sched else 'empty')}
        age = _age_min(out['sync']['last_success'], now)
        out['sync']['last_success_age_min'] = age
        if age is None or age > SYNC_STALE_MIN:
            alerts.append({'key': 'sync_stale', 'severity': 'high', 'value': age})
        w = _q(c, "SELECT state, version, detail, beat_at FROM translation_worker_state WHERE worker='ai-translator'", one=True)
        tr = _q(c, '''SELECT field, status, count(*) AS n FROM news_item_translations WHERE target_language='fa' AND field IN ('title','summary')
            AND prompt_version LIKE %s GROUP BY 1,2''', ('%translation-pipeline-v2.1.0',))
        lat = _q(c, '''SELECT avg(latency_ms)::int AS avg_ms, count(*) AS calls FROM news_item_translation_history
            WHERE prompt_version LIKE %s AND latency_ms IS NOT NULL AND generated_at > now()-interval '24 hours'
              AND NOT (quality_flags ? 'requalified_from') ''', ('%translation-pipeline-v2.1.0',), one=True)
        qs = _q(c, '''SELECT
              count(DISTINCT t.item_id) FILTER (WHERE COALESCE(n.collected_at, 'epoch'::timestamptz) >= now()-interval '24 hours'
                                                 OR t.item_id IN (SELECT item_id FROM translation_queue_requests)) AS fresh_items,
              count(DISTINCT t.item_id) FILTER (WHERE COALESCE(n.collected_at, 'epoch'::timestamptz) < now()-interval '24 hours'
                                                 AND t.item_id NOT IN (SELECT item_id FROM translation_queue_requests)) AS archive_items
            FROM news_item_translations t JOIN news_items n USING (item_id)
            WHERE t.status IN ('translation_pending','processing') AND t.prompt_version LIKE %s''', ('%translation-pipeline-v2.1.0',), one=True)
        rate = _q(c, '''SELECT count(*) FILTER (WHERE generated_at > now()-interval '1 hour') AS fields_1h,
              count(*) FILTER (WHERE generated_at > now()-interval '24 hours') AS fields_24h,
              count(*) FILTER (WHERE status='translation_error' AND generated_at > now()-interval '24 hours') AS errors_24h
            FROM news_item_translation_history WHERE prompt_version LIKE %s AND status <> 'translation_pending'
              AND NOT (quality_flags ? 'requalified_from') '''   # model outputs only: QC re-decisions are not throughput,
                  ('%translation-pipeline-v2.1.0',), one=True)
        prog = _q(c, '''SELECT
              count(*) FILTER (WHERE field='title' AND status IN ('translated_auto','qc_warning','qc_failed','not_required','no_source_text','translation_failed')) AS titles_processed,
              count(*) FILTER (WHERE field='summary' AND status IN ('translated_auto','qc_warning','qc_failed','not_required','no_source_text','translation_failed')) AS summaries_processed,
              count(DISTINCT item_id) FILTER (WHERE field='title' AND status='translated_auto') AS items_title_fa_shown,
              count(DISTINCT item_id) FILTER (WHERE status IN ('translated_auto','qc_warning')) AS items_with_any_fa,
              max(updated_at) FILTER (WHERE status='translated_auto') AS last_accepted_at,
              max(updated_at) FILTER (WHERE status IN ('translated_auto','qc_warning','qc_failed')) AS last_processed_at
            FROM news_item_translations WHERE target_language='fa' AND prompt_version LIKE %s''', ('%translation-pipeline-v2.1.0',), one=True)
        untouched = _q(c, '''SELECT count(*) AS n FROM news_items n WHERE NOT EXISTS (SELECT 1 FROM news_item_translations t
            WHERE t.item_id=n.item_id AND t.field='title' AND t.prompt_version LIKE %s)''', ('%translation-pipeline-v2.1.0',), one=True)
        by = {}
        for r in tr or []:
            by.setdefault(r['field'], {})[r['status']] = r['n']
        queue = sum(v for f in by.values() for k, v in f.items() if k in ('translation_pending', 'processing'))
        r1 = (rate or {}).get('fields_1h') or 0
        out['translation'] = {'worker': w, 'by_field': by, 'queue_fields': queue, 'latency_24h': lat,
                              'queue_fresh_items': (qs or {}).get('fresh_items'), 'queue_archive_items': (qs or {}).get('archive_items'),
                              'items_not_yet_queued': (untouched or {}).get('n'), 'fields_last_hour': r1,
                              'fields_last_24h': (rate or {}).get('fields_24h'), 'errors_24h': (rate or {}).get('errors_24h'),
                              'eta_hours_queue': round(queue / r1, 1) if r1 else None, 'progress': prog,
                              'pipeline': 'translategemma-official-en-fa-v1+translation-pipeline-v2.1.0'}
        wage = _age_min((w or {}).get('beat_at'), now)
        out['translation']['heartbeat_age_min'] = wage
        if not w or wage is None or wage > WORKER_STALE_MIN:
            alerts.append({'key': 'translator_heartbeat_stale', 'severity': 'high', 'value': wage})
        elif w['state'] in ('paused', 'error', 'blocked'):
            alerts.append({'key': 'translator_' + w['state'], 'severity': 'medium', 'value': (w.get('detail') or {}).get('reason')})
        err = sum(f.get('translation_error', 0) for f in by.values())
        if err:
            alerts.append({'key': 'translation_errors', 'severity': 'low', 'value': err})
        ev = _q(c, 'SELECT count(*) AS events, max(updated_at) AS last_update FROM news_events', one=True)
        miss = _q(c, '''SELECT count(*) AS n FROM news_items n WHERE NOT EXISTS (SELECT 1 FROM item_topic_assignments a WHERE a.item_id=n.item_id)''', one=True)
        out['clustering'] = {**(ev or {}), 'items_without_topic': (miss or {}).get('n')}
        eage = _age_min((ev or {}).get('last_update'), now)
        out['clustering']['last_update_age_min'] = eage
        if eage is None or eage > EVENTS_STALE_MIN:
            alerts.append({'key': 'clustering_stale', 'severity': 'medium', 'value': eage})
        asst = _q(c, '''SELECT count(*) FILTER (WHERE created_at > now()-interval '24 hours') AS answers_24h, max(created_at) AS last_answer
            FROM assistant_messages WHERE role='assistant' ''', one=True)
    contract = mi.load_contract()
    state = mi.approval_state(contract)
    serv = [{'id': a['id'], 'role': mi.role_of(a), 'tag': a['tag'], 'state': state.get(a['id'])} for a in contract['approvals']
            if state.get(a['id']) in mi.servable_states()]
    out['models'] = {'servable': serv, 'lab_mode': mi.lab_mode()}
    out['assistant'] = {**(asst or {}), 'approval': next((m for m in serv if m['role'] == 'assistant_extractive'), None)}
    bk = _tail(OPS_DIR / 'backups' / 'manifest.jsonl', 3)
    out['backup'] = {'status': 'unknown', 'reason': 'no backup manifest mounted'} if bk is None else {'status': 'seen' if bk else 'empty', 'last': bk}
    bage = _age_min((bk or [{}])[-1].get('ts') if bk else None, now)
    out['backup']['last_age_hours'] = round(bage / 60, 1) if bage is not None else None
    if bage is None or bage > BACKUP_STALE_HOURS * 60:
        alerts.append({'key': 'backup_missing_or_stale', 'severity': 'medium', 'value': out['backup']['last_age_hours']})
    hm_files = sorted((OPS_DIR / 'health').glob('20*.jsonl')) if (OPS_DIR / 'health').is_dir() else []
    hm = _tail(hm_files[-1], 1) if hm_files else None
    out['health_monitor'] = {'status': 'unknown', 'reason': 'no health monitor output'} if not hm else {'status': 'seen', 'last': hm[-1]}
    hage = _age_min(hm[-1].get('ts') if hm else None, now)
    out['health_monitor']['last_age_min'] = hage
    if hage is None or hage > HEALTH_STALE_MIN:
        alerts.append({'key': 'health_monitor_not_running', 'severity': 'medium', 'value': hage})
    elif hm and hm[-1].get('alerts'):
        for a in hm[-1]['alerts']:
            alerts.append({'key': 'host:' + a, 'severity': 'high', 'value': None})
    out['known_risks'] = [{'key': 'docker_requires_user_sign_in', 'severity': 'high'},
                          {'key': 'host_unclean_resets_16_in_47_days', 'severity': 'high'},
                          {'key': 'translation_not_human_verified', 'severity': 'medium'},
                          {'key': 'assistant_not_human_reviewed', 'severity': 'medium'}]
    out['alerts'] = alerts
    return out


ALLOWED_ORIGINS = {o.strip() for o in (os.getenv('ASSISTANT_ALLOWED_ORIGINS') or '').split(',') if o.strip()}


def register_lab_ops(app):
    from fastapi import HTTPException, Request

    @app.get('/api/v1/local-ai/ops')
    def lab_ops():
        return status()

    @app.post('/api/v1/news/{item_id}/translation/request')
    def request_translation(item_id: str, request: Request):
        """Queue an older item for translation on demand (the worker translates
        recent items by itself). Writes one queue row; never translates inline."""
        origin = request.headers.get('x-im-origin') or ''   # set by the web proxy from the browser's own Origin
        if origin not in ALLOWED_ORIGINS:
            raise HTTPException(403, 'origin_not_allowed')
        with psycopg.connect(DSN) as c:
            if not c.execute('SELECT 1 FROM news_items WHERE item_id=%s', (item_id,)).fetchone():
                raise HTTPException(404, 'not_found')
            c.execute('''CREATE TABLE IF NOT EXISTS translation_queue_requests (item_id text PRIMARY KEY REFERENCES news_items(item_id),
                requested_at timestamptz NOT NULL DEFAULT now(), requested_by text)''')
            c.execute('''INSERT INTO translation_queue_requests(item_id, requested_by) VALUES (%s, 'ui') ON CONFLICT (item_id) DO NOTHING''', (item_id,))
        return {'queued': True, 'item_id': item_id}

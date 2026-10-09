"""One-way incremental news sync: Production (news-db, READ ONLY) → Local AI (ai-db, 3003).

Safety model
  * Production is only READ: every Production session runs with
    PGOPTIONS='-c default_transaction_read_only=on' inside a READ ONLY
    transaction. Nothing that could write is ever sent to Production.
  * Host-mediated: data moves through files under runtime/news-sync/<run>/
    via `docker exec` on each database container. No Docker network, port,
    role or container is changed; no second collector exists.
  * One writer per table. The sync writes only the SOURCE tables below.
    3003's own jobs (apps/api/experience.py, same code version as
    Production) recompute topics (taxonomy 3.0.0), events and memberships
    (clustering v2 2.0.0), briefings and stories from the synced content;
    those tables are never written by the sync (DERIVED_LOCAL), so two
    clustering runs are never mixed. news_item_media is INSERT-ONLY because
    3003's media job converts existing rows.
  * Local-AI-owned tables (translations and their history, assistant
    sessions/messages, AI logs/caches, X/social, key points, enrichment jobs,
    briefings, stories, contracts…) are fingerprinted INSIDE the apply
    transaction (REPEATABLE READ: start and end of the same snapshot), so a
    change made by the sync aborts and rolls back the whole run, and
    concurrent 3003 jobs cannot cause a false alarm.
  * Change detection = full-row hash md5(row::text) on both sides (same
    PostgreSQL 16.14, identical schemas — verified), keyed by the natural
    key; not publication time. Unchanged rows are never staged, so re-runs
    are idempotent. Rows existing only in 3003 are never deleted (reported).
  * A data backup of every written 3003 table is saved before an apply.

  python scripts/news_sync.py dry-run
  python scripts/news_sync.py apply --limit-new 20      # limited trial: N oldest new items + their item rows only
  python scripts/news_sync.py apply                     # full incremental run (manual)
"""
import argparse
import csv
import hashlib
import io
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'runtime' / 'news-sync'
PROD = 'defence-monitor-news-news-db-1'
LOCAL = 'iran-monitor-local-ai-ai-db-1'
SYNC_VERSION = 'news-sync-v1.0.0'
csv.field_size_limit(1 << 30)

# (table, natural key, serial columns, policy, item-scoped column)
TABLES = [
    ('sources', ['source_id'], ['id'], 'upsert', None),
    ('news_items', ['item_id'], ['id'], 'upsert', 'item_id'),
    ('news_item_content', ['item_id'], [], 'upsert', 'item_id'),
    ('news_item_media', ['media_id'], [], 'insert_only', 'item_id'),
    ('news_item_provenance', ['item_id'], ['id'], 'upsert', 'item_id'),
    ('item_classifications', ['item_id'], [], 'upsert', 'item_id'),
    ('collection_runs', ['run_id'], [], 'insert_only', None),
    ('source_run_results', ['run_id', 'source_id'], [], 'insert_only', None),
]
DERIVED_LOCAL = ['item_topic_assignments', 'item_topic_assignment_history', 'news_events', 'news_event_members', 'geo_mentions']
PROTECTED = ['news_item_translations', 'news_item_translation_history', 'assistant_sessions', 'assistant_messages',
             'ai_requests_log', 'ai_response_cache', 'x_posts', 'x_post_translations', 'x_post_translation_history', 'x_post_history',
             'x_post_media', 'x_accounts', 'social_posts', 'content_key_points', 'enrichment_jobs', 'daily_briefings', 'stories',
             'alert_rules', 'integrations', 'commodity_prices', 'import_runs', 'schema_migrations',
             'item_topic_assignments', 'item_topic_assignment_history', 'news_events', 'news_event_members', 'geo_mentions']
# Production values must already exist in 3003 (no new algorithm/taxonomy version is imported silently)
VERSION_GUARD = {'item_classifications': 'coalesce(taxonomy_version, \'-\')', 'news_items': 'coalesce(taxonomy_version, \'-\')'}


def psql(container, sql, *, read_only):
    env = ['-e', 'PGOPTIONS=-c default_transaction_read_only=on'] if read_only else []
    cmd = ['docker', 'exec', '-i', *env, container, 'sh', '-c',
           'psql -X -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -F "\t"']
    r = subprocess.run(cmd, input=sql.encode('utf-8'), capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f'psql {container} failed: {r.stderr.decode("utf-8", "replace")[:1500]}')
    return r.stdout.decode('utf-8')


def copy_out(container, query, *, read_only):
    sql = ('BEGIN READ ONLY;\n' if read_only else 'BEGIN;\n') + f'COPY ({query}) TO STDOUT WITH (FORMAT csv, HEADER true);\nCOMMIT;\n'
    return psql(container, sql, read_only=read_only)


def key_expr(keys, alias='t'):
    return "concat_ws('|', " + ', '.join(f'{alias}.{k}::text' for k in keys) + ')'


def hashes(container, table, keys):
    out = copy_out(container, f'SELECT {key_expr(keys)} AS k, md5(t::text) AS h FROM {table} t', read_only=True)
    return {row['k']: row['h'] for row in csv.DictReader(io.StringIO(out))}


def fp_query(tables):
    return ' UNION ALL '.join(f"SELECT '{t}'::text AS t, count(*) AS n, coalesce(md5(string_agg(md5(x::text), '' ORDER BY md5(x::text))), '-') AS h FROM {t} x"
                              for t in tables)


def fingerprint(tables):
    out = copy_out(LOCAL, fp_query(tables), read_only=True)
    return {r['t']: {'rows': int(r['n']), 'md5': r['h']} for r in csv.DictReader(io.StringIO(out))}


def contract_hash():
    return hashlib.sha256((ROOT / 'apps' / 'api' / 'model_approvals.json').read_bytes()).hexdigest()


def plan(limit_new=None):
    """Compare both sides (read-only on both) → per-table plan."""
    for table, expr in VERSION_GUARD.items():
        vals = lambda c: {r['v'] for r in csv.DictReader(io.StringIO(copy_out(c, f'SELECT DISTINCT {expr} AS v FROM {table}', read_only=True)))}
        extra = vals(PROD) - vals(LOCAL)
        if extra:
            raise RuntimeError(f'version guard: {table} has versions not present in 3003: {sorted(extra)} — stop')
    p = {}
    for table, keys, _, policy, _ in TABLES:
        ph, lh = hashes(PROD, table, keys), hashes(LOCAL, table, keys)
        changed = sorted(k for k in set(ph) & set(lh) if ph[k] != lh[k])
        p[table] = {'new': sorted(set(ph) - set(lh)), 'changed': changed if policy == 'upsert' else [],
                    'changed_not_applied': changed if policy == 'insert_only' else [],
                    'local_only': sorted(set(lh) - set(ph)), 'prod_rows': len(ph), 'local_rows': len(lh)}
    if limit_new is not None:
        order = [r['item_id'] for r in csv.DictReader(io.StringIO(copy_out(PROD, 'SELECT item_id FROM news_items ORDER BY collected_at, item_id', read_only=True)))]
        newset = set(p['news_items']['new'])
        chosen = set([i for i in order if i in newset][:limit_new])
        for table, keys, _, _, scoped in TABLES:
            if table == 'news_items':
                p[table]['new'], p[table]['changed'] = sorted(chosen), []
            elif scoped == 'item_id':
                rows = copy_out(PROD, f'SELECT {key_expr(keys)} AS k, t.item_id FROM {table} t', read_only=True)
                ok = {r['k'] for r in csv.DictReader(io.StringIO(rows)) if r['item_id'] in chosen}
                p[table]['new'] = [k for k in p[table]['new'] if k in ok]
                p[table]['changed'] = []
            elif table == 'sources':
                p[table]['changed'] = []      # a new source (if any) is still inserted for the FK
            else:
                p[table]['new'], p[table]['changed'] = [], []
    stale = []
    changed_items = set(p['news_items']['changed']) | set(p['news_item_content']['changed'])
    if changed_items:
        lit = ','.join("'" + k.replace("'", "''") + "'" for k in changed_items)
        stale = [r['item_id'] for r in csv.DictReader(io.StringIO(copy_out(
            LOCAL, f'SELECT DISTINCT item_id FROM news_item_translations WHERE item_id IN ({lit})', read_only=True)))]
    return p, stale


def payload(table, keys, wanted):
    if not wanted:
        return ''
    lit = ','.join("'" + k.replace("'", "''") + "'" for k in wanted)
    return copy_out(PROD, f'SELECT * FROM {table} t WHERE {key_expr(keys)} IN ({lit})', read_only=True)


def build_apply_sql(p, run_id, mode):
    parts = ['BEGIN ISOLATION LEVEL REPEATABLE READ;',
             """CREATE TABLE IF NOT EXISTS news_sync_runs (run_id text PRIMARY KEY, sync_version text, mode text, started_at timestamptz,
                finished_at timestamptz, status text, source text, counts jsonb, protected_check text, note text);""",
             f'CREATE TEMP TABLE fp_before ON COMMIT DROP AS {fp_query(PROTECTED)};']
    counts = {}
    for table, keys, serials, policy, _ in TABLES:
        wanted = p[table]['new'] + p[table]['changed']
        counts[table] = {'inserted': len(p[table]['new']), 'updated': len(p[table]['changed']),
                         'changed_not_applied': len(p[table]['changed_not_applied']), 'local_only_untouched': len(p[table]['local_only'])}
        if not wanted:
            continue
        data = payload(table, keys, wanted)
        header = next(csv.reader(io.StringIO(data)))
        cols = ', '.join(f'"{c}"' for c in header)
        if policy == 'insert_only':
            action = 'DO NOTHING'
        else:
            upd = ', '.join(f'"{c}" = EXCLUDED."{c}"' for c in header if c not in keys and c not in serials)
            action = f'DO UPDATE SET {upd}' + (' WHERE item_classifications.human_locked IS NOT TRUE' if table == 'item_classifications' else '')
        parts.append(f'CREATE TEMP TABLE s_{table} (LIKE {table} INCLUDING DEFAULTS) ON COMMIT DROP;')
        parts.append(f'COPY s_{table} ({cols}) FROM STDIN WITH (FORMAT csv, HEADER true);\n{data.rstrip()}\n\\.')
        parts.append(f'INSERT INTO {table} ({cols}) SELECT {cols} FROM s_{table} ON CONFLICT ({", ".join(keys)}) {action};')
        for s in serials:
            parts.append(f"SELECT setval(pg_get_serial_sequence('{table}', '{s}'), (SELECT max({s}) FROM {table}));")
    parts.append(f"""DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM fp_before b FULL JOIN ({fp_query(PROTECTED)}) a USING (t) WHERE a.h IS DISTINCT FROM b.h OR a.n IS DISTINCT FROM b.n)
  THEN RAISE EXCEPTION 'protected Local AI data changed inside the sync transaction — rolled back'; END IF; END $$;""")
    note = json.dumps(counts).replace("'", "''")
    parts.append(f"""INSERT INTO news_sync_runs VALUES ('{run_id}', '{SYNC_VERSION}', '{mode}', now(), clock_timestamp(), 'succeeded',
        '{PROD} (read-only)', '{note}'::jsonb, 'protected tables identical at start and end of the transaction snapshot', NULL);""")
    parts.append('COMMIT;')
    return '\n'.join(parts) + '\n', counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['dry-run', 'apply'])
    ap.add_argument('--limit-new', type=int)
    a = ap.parse_args()
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:6]
    rd = RUNS / run_id
    rd.mkdir(parents=True, exist_ok=False)
    log = {'run_id': run_id, 'sync_version': SYNC_VERSION, 'mode': a.mode, 'limit_new': a.limit_new,
           'started': datetime.now(timezone.utc).isoformat(), 'status': 'started'}
    t0 = time.time()
    try:
        log['contract_sha256_before'] = contract_hash()
        log['protected_before'] = fingerprint(PROTECTED)
        log['written_tables_before'] = fingerprint([t for t, *_ in TABLES])
        p, stale = plan(a.limit_new)
        log['plan'] = {t: {k: (v if isinstance(v, int) else len(v)) for k, v in d.items()} for t, d in p.items()}
        log['plan_keys'] = {t: {k: d[k] for k in ('new', 'changed', 'changed_not_applied', 'local_only')} for t, d in p.items()}
        log['translations_whose_source_changed'] = stale
        if a.mode == 'apply':
            backup = psql(LOCAL, 'BEGIN READ ONLY;\n' + ''.join(
                f'COPY (SELECT * FROM {t}) TO STDOUT WITH (FORMAT csv, HEADER true);\n' for t, *_ in TABLES) + 'COMMIT;\n', read_only=True)
            (rd / 'backup-3003-written-tables.csv').write_text(backup, encoding='utf-8')
            log['backup_sha256'] = hashlib.sha256(backup.encode('utf-8')).hexdigest()
            sql, counts = build_apply_sql(p, run_id, 'trial' if a.limit_new else 'full')
            (rd / 'apply.sql').write_text(sql, encoding='utf-8')
            psql(LOCAL, sql, read_only=False)
            log['applied'] = counts
            log['contract_sha256_after'] = contract_hash()
            if log['contract_sha256_before'] != log['contract_sha256_after']:
                raise RuntimeError('model contract file changed during the run')
            p2, _ = plan(None)
            log['residual_after'] = {t: {k: len(d[k]) for k in ('new', 'changed', 'changed_not_applied', 'local_only')} for t, d in p2.items()}
        log['status'] = 'succeeded'
    except Exception as exc:
        log['status'] = 'failed'
        log['error'] = str(exc)[:3000]
    log['seconds'] = round(time.time() - t0, 1)
    (rd / 'run.json').write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding='utf-8')
    summary = {k: log.get(k) for k in ('run_id', 'mode', 'limit_new', 'status', 'error', 'seconds', 'plan', 'applied', 'residual_after')}
    summary['translations_whose_source_changed'] = len(log.get('translations_whose_source_changed') or [])
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    sys.exit(0 if log['status'] == 'succeeded' else 1)


if __name__ == '__main__':
    main()

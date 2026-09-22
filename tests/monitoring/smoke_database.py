"""Non-destructive live DB safety probes for the additive 8B schema."""
import os,uuid,sys
sys.path.insert(0,'/app')
import psycopg
import ops
dsn=os.environ['DATABASE_URL'];schema='phase8b_rollback_'+uuid.uuid4().hex[:12]
class RollbackProbe(Exception):pass
try:
    with psycopg.connect(dsn) as c:
        with c.transaction():
            c.execute(psycopg.sql.SQL('CREATE SCHEMA {}').format(psycopg.sql.Identifier(schema)))
            c.execute(psycopg.sql.SQL('SET LOCAL search_path TO {}').format(psycopg.sql.Identifier(schema)))
            c.execute('CREATE TABLE sources(id serial PRIMARY KEY,source_id text UNIQUE,name text,source_type text,canonical_url text,hostname text,collection_tier text,enabled boolean,created_at timestamptz,updated_at timestamptz)')
            c.execute('CREATE TABLE news_items(id serial PRIMARY KEY,item_id text UNIQUE,source_id text,title text,summary text,canonical_url text UNIQUE,external_guid text,published_at timestamptz,collected_at timestamptz,language text,adapter_type text,provenance_status text,content_hash text,first_seen_at timestamptz,last_seen_at timestamptz,created_at timestamptz,updated_at timestamptz)')
            c.execute(ops.DDL)
            cols={r[0] for r in c.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name='sources'",(schema,)).fetchall()}
            assert {'display_name','feed_url','last_success_at','health_status'}<=cols
            news_cols={r[0] for r in c.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name='news_items'",(schema,)).fetchall()}
            assert {'summary_raw','summary_text','summary_source','summary_available','content_language','fetched_at'}<=news_cols
            assert c.execute("SELECT to_regclass(%s)",(schema+'.collection_runs',)).fetchone()[0]
            raise RollbackProbe()
except RollbackProbe:pass
with psycopg.connect(dsn) as c:assert c.execute('SELECT to_regnamespace(%s)',(schema,)).fetchone()[0] is None
key=0x4952414E4D4F4E
with psycopg.connect(dsn,autocommit=True) as a:
    assert a.execute('SELECT pg_try_advisory_lock(%s)',(key,)).fetchone()[0]
    with psycopg.connect(dsn,autocommit=True) as b:assert not b.execute('SELECT pg_try_advisory_lock(%s)',(key,)).fetchone()[0]
    assert a.execute('SELECT pg_advisory_unlock(%s)',(key,)).fetchone()[0]
with psycopg.connect(dsn) as c:
    assert c.execute('SELECT count(*) FROM news_items').fetchone()[0]>=282
    # Follows the executable set rather than a count frozen when it was 11.
    assert c.execute('SELECT count(*) FROM sources').fetchone()[0]==len(ops.EXEC)
    assert c.execute('SELECT count(*) FROM news_item_provenance').fetchone()[0]>=282
    assert c.execute('SELECT count(*) FROM item_classifications').fetchone()[0]>=282
    assert c.execute('SELECT count(*) FROM collection_runs WHERE trigger_type=\'manual\' AND collector_version=\'8a-pilot\'').fetchone()[0]==1
    assert c.execute('SELECT count(*) FROM source_run_results WHERE status=\'succeeded\' AND run_id LIKE \'phase-8a-%\'').fetchone()[0]==11
    for table in ('news_item_content','news_item_translations','news_item_media'):
        assert c.execute('SELECT to_regclass(%s)',('public.'+table,)).fetchone()[0],table
    # Every content row must point at an item that exists.
    assert c.execute('SELECT count(*) FROM news_item_content x LEFT JOIN news_items n USING(item_id) WHERE n.item_id IS NULL').fetchone()[0]==0
    assert c.execute('SELECT count(*) FROM news_item_media x LEFT JOIN news_items n USING(item_id) WHERE n.item_id IS NULL').fetchone()[0]==0
    # No translation text may exist without a provider recorded against it.
    assert c.execute("SELECT count(*) FROM news_item_translations WHERE status='available' AND (text IS NULL OR provider IS NULL)").fetchone()[0]==0
    # Canonical URL and item id both stay unique, so duplicates cannot accumulate.
    assert c.execute('SELECT count(*) FROM news_items').fetchone()[0]==c.execute('SELECT count(DISTINCT canonical_url) FROM news_items').fetchone()[0]
    stuck=c.execute("SELECT count(*) FROM collection_runs WHERE status='running' AND started_at < now()-interval '1 hour'").fetchone()[0]
    assert stuck==0,('runs_stuck_in_running',stuck)
print(f'DATABASE_PROBES_PASS migration_rollback=pass lock=pass baseline_rows=preserved sources={len(ops.EXEC)} content_fk=ok no_stuck_runs=ok')

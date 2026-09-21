"""Apply only additive collector recovery schema changes; no row backfills."""
from ops import DSN
import psycopg

DDL = '''
ALTER TABLE source_run_results ADD COLUMN IF NOT EXISTS http_requests integer NOT NULL DEFAULT 0;
ALTER TABLE source_run_results ADD COLUMN IF NOT EXISTS updates integer;
ALTER TABLE source_run_results ADD COLUMN IF NOT EXISTS response_sha256 text;
ALTER TABLE source_run_results ADD COLUMN IF NOT EXISTS checkpoint_payload jsonb;
ALTER TABLE collection_runs ADD COLUMN IF NOT EXISTS repaired_at timestamptz;
ALTER TABLE collection_runs ADD COLUMN IF NOT EXISTS repair_reason text;
ALTER TABLE collection_runs ALTER COLUMN updates DROP NOT NULL;
'''

def migrate(conn=None):
    if conn is not None:
        with conn.transaction():conn.execute(DDL)
        return
    with psycopg.connect(DSN) as c:
        with c.transaction():c.execute(DDL)

if __name__=='__main__':
    migrate()
    print('collector_recovery_schema=ready')

import json,os,sys,time
from pathlib import Path
import psycopg
p=Path(os.getenv('COLLECTOR_STATE_DIR','/state'))
try:
 h=json.loads((p/'health.json').read_text(encoding='utf-8'))
 stamp=h.get('heartbeat_at') or h.get('started_at')
 if not stamp or time.time()-__import__('datetime').datetime.fromisoformat(stamp.replace('Z','+00:00')).timestamp()>150:raise RuntimeError()
 with psycopg.connect(os.environ['DATABASE_URL'],connect_timeout=5) as c:
  if not c.execute("SELECT to_regclass('public.collection_runs'),to_regclass('public.source_run_results')").fetchone()[0]:raise RuntimeError()
 print('healthy')
except Exception:sys.exit(1)

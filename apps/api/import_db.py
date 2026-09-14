import os,json,hashlib,uuid
from pathlib import Path
import psycopg
root=Path('/project'); items=[]
for f in (root/'data/runtime/collector').rglob('normalized-items.jsonl'):
 for l in f.read_text(encoding='utf-8').splitlines():
  try: items.append((json.loads(l),str(f.relative_to(root))))
  except json.JSONDecodeError: pass
ins=upd=rej=0
with psycopg.connect(os.environ['DATABASE_URL']) as c:
 for i,ref in items:
  sid=i['source_id']; c.execute('INSERT INTO sources(source_id,name,source_type,enabled) VALUES(%s,%s,%s,false) ON CONFLICT(source_id) DO NOTHING',(sid,sid,'news'))
  c.execute('select 1 from news_items where item_id=%s',(i['item_id'],)); exists=c.fetchone() is not None
  c.execute('INSERT INTO news_items(item_id,source_id,title,canonical_url,external_guid,published_at,adapter_type,provenance_status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(item_id) DO NOTHING',(i['item_id'],sid,i['title'],i['canonical_url'],i.get('external_id'),i.get('published_at'),'rss','COMPLETE'))
  if exists: upd+=1
  else: ins+=1
  c.execute('INSERT INTO news_item_provenance(item_id,source_id,staging_reference,evidence_status) VALUES(%s,%s,%s,%s) ON CONFLICT(item_id) DO NOTHING',(i['item_id'],sid,ref,'COMPLETE'))
print(json.dumps({'items':len(items),'inserted':ins,'updated':upd,'rejected':rej,'duplicate':upd}))

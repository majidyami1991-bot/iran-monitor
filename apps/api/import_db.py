import os,json,hashlib,uuid
from pathlib import Path
import psycopg
root=Path('/project'); dsn=os.environ['DATABASE_URL']; items=[]
for f in (root/'data/runtime/collector').rglob('normalized-items.jsonl'):
 for l in f.read_text().splitlines():
  try: items.append((json.loads(l),str(f.relative_to(root))))
  except: pass
with psycopg.connect(dsn) as c:
 for i,ref in items:
  sid=i['source_id']; c.execute('INSERT INTO sources(source_id,name,source_type,canonical_url,hostname,enabled) VALUES(%s,%s,%s,%s,%s,false) ON CONFLICT(source_id) DO NOTHING',(sid,sid,'news',None,None))
  c.execute('INSERT INTO news_items(item_id,source_id,title,canonical_url,external_guid,published_at,adapter_type,provenance_status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(item_id) DO NOTHING',(i['item_id'],sid,i['title'],i['canonical_url'],i.get('external_id'),i.get('published_at'),'rss','COMPLETE'))
  c.execute('INSERT INTO news_item_provenance(item_id,source_id,staging_reference,evidence_status) VALUES(%s,%s,%s,%s) ON CONFLICT(item_id) DO NOTHING',(i['item_id'],sid,ref,'COMPLETE'))
print(json.dumps({'items':len(items)}))

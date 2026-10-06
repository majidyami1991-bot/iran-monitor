from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
import os, psycopg, re
from datetime import date
from collections import Counter
app=FastAPI(title='Defence Monitor News API',version='0.3.0'); DSN=os.environ['DATABASE_URL']
from ops import register_ops
register_ops(app)
from experience import register_experience
register_experience(app)
from social import register_social
register_social(app)
from media_api import register_media
register_media(app)
def q(sql,args=()):
 with psycopg.connect(DSN) as c:
  with c.cursor() as cur:
   cur.execute(sql,args); cols=[d.name for d in cur.description] if cur.description else []; return [dict(zip(cols,r)) for r in cur.fetchall()] if cols else []
def count(t): return q(f'select count(*)::int n from {t}')[0]['n']
@app.get('/api/v1/health')
def health(): return {'status':'ok','items':count('news_items'),'database':'ready'}
@app.get('/api/v1/meta')
def meta(): return {'name':'Defence Monitor','version':'0.2.0','item_count':count('news_items')}
@app.get('/api/v1/items')
def items(search:str|None=None,source_id:str|None=None,source_type:str|None=None,date_from:str|None=None,date_to:str|None=None,provenance:str|None=None,sort:str='newest',page:int=1,page_size:int=20):
 for value in (date_from,date_to):
  if value:
   try: date.fromisoformat(value)
   except ValueError: raise HTTPException(422,'تاریخ نامعتبر است؛ قالب سال-ماه-روز را وارد کنید.')
 if date_from and date_to and date_from>date_to: raise HTTPException(422,'تاریخ شروع باید قبل از تاریخ پایان باشد.')
 page=max(page,1); size=min(max(page_size,1),100); w=[]; a=[]
 if search: w.append('(n.title ilike %s or coalesce(n.summary,\'\') ilike %s)'); a += [f'%{search}%',f'%{search}%']
 if source_id: w.append('n.source_id=%s'); a.append(source_id)
 if source_type: w.append('s.source_type=%s'); a.append(source_type)
 if date_from: w.append('n.published_at >= %s'); a.append(date_from)
 if date_to: w.append('n.published_at < (%s::date + interval \'1 day\')'); a.append(date_to)
 if provenance: w.append('n.provenance_status=%s'); a.append(provenance)
 where=(' where '+' and '.join(w)) if w else ''; order='n.published_at asc nulls last' if sort=='oldest' else 'n.published_at desc nulls last'
 total=q('select count(*)::int n from news_items n join sources s on s.source_id=n.source_id'+where,a)[0]['n']
 rows=q('select n.item_id,n.source_id,n.title,n.summary,n.canonical_url,n.published_at,n.provenance_status,s.name publisher,s.hostname,s.source_type from news_items n join sources s on s.source_id=n.source_id'+where+' order by '+order+' limit %s offset %s',a+[size,(page-1)*size]); return {'items':rows,'total':total,'page':page,'page_size':size}
@app.get('/api/v1/items/{item_id}')
def item(item_id:str): return (q('select n.*,s.name publisher,s.hostname,s.source_type from news_items n join sources s on s.source_id=n.source_id where n.item_id=%s',(item_id,)) or [{}])[0]
@app.get('/api/v1/sources')
def source_list():
 r=q('select s.source_id,s.name,s.source_type,s.canonical_url,s.hostname,s.collection_tier,s.enabled,count(n.item_id)::int item_count,max(n.published_at) latest from sources s left join news_items n on n.source_id=s.source_id group by s.id order by s.name'); return {'sources':r,'total':len(r)}
@app.get('/api/v1/stats/overview')
def overview(): return {'total_items':count('news_items'),'sources':count('sources'),'provenance_complete':q("select count(*)::int n from news_items where provenance_status='COMPLETE'")[0]['n']}
@app.get('/api/v1/stats/topics')
def topics():
 rows=q("select title,summary from news_items order by item_id limit 10000")
 return {'topics':topic_counts(rows)}

STOPWORDS=set("the and with from this that these those their they them have has had been being are was were for into onto about after before over under its our your you not but will would could should can may more most than then also first next new now all any one two three در به از با برای این آن یک را که است بود شد می های شود شده بر تا و یا اما نیز خود هر همان خواهد گفت شده‌اند سال خبر گزارش the of on at as is it be by an a us".split())
def topic_counts(rows):
 counts=Counter()
 for row in rows:
  text=((row.get('title') or '')+' '+(row.get('summary') or '')).lower().translate(str.maketrans({'ي':'ی','ك':'ک','\u200c':' '}))
  text=re.sub(r'https?://\S+',' ',text)
  words=re.findall(r'[^\W\d_]+',text,flags=re.UNICODE)
  counts.update(w for w in words if len(w)>=3 and w not in STOPWORDS)
 return [{'topic':word,'count':count} for word,count in sorted(counts.items(),key=lambda x:(-x[1],x[0]))[:20]]
# append supplemental routes
@app.get('/api/v1/stats/timeline')
def stats_timeline(group_by:str='day'):
 if group_by not in ('hour','day','week'): group_by='day'
 unit={'hour':'hour','day':'day','week':'week'}[group_by]
 return {'group_by':group_by,'series':q(f"select date_trunc('{unit}',published_at at time zone 'UTC') bucket,count(*)::int count from news_items where published_at is not null group by 1 order by 1 desc limit 90")}
@app.get('/api/v1/stats/sources')
def stats_sources(): return {'sources':q('select s.name,count(n.item_id)::int count from sources s left join news_items n on n.source_id=s.source_id group by s.name order by count desc,s.name limit 10')}
@app.get('/api/v1/stats/provenance')
def stats_provenance(): return {'provenance':q('select coalesce(provenance_status,\'UNKNOWN\') status,count(*)::int count from news_items group by 1 order by 1')}

from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import mimetypes
mimetypes.add_type('font/woff2','.woff2')
WEB=Path(__file__).parent/'web'
app.mount('/assets', StaticFiles(directory=WEB), name='assets')
@app.get('/api/v1/sources/{source_id}')
def source_detail(source_id: str):
 rows=q("select s.source_id,s.name,s.hostname,s.canonical_url,s.source_type,s.collection_tier,s.enabled,count(n.item_id)::int item_count,min(n.published_at) first,max(n.published_at) latest from sources s left join news_items n on n.source_id=s.source_id where s.source_id=%s group by s.id",(source_id,))
 if not rows: raise HTTPException(404,'???? ???? ???')
 r=rows[0]
 r['timeline']=q("select date_trunc('day',published_at at time zone 'UTC') bucket,count(*)::int count from news_items where source_id=%s and published_at is not null group by 1 order by 1 limit 90",(source_id,))
 r['provenance']=q("select provenance_status status,count(*)::int count from news_items where source_id=%s group by 1 order by 1",(source_id,))
 return r
@app.get('/api/v1/stats/import')
def latest_import():
 return {'latest':next(iter(q('select completed_at,status,input_item_count,inserted_count from import_runs order by started_at desc limit 1')),None)}
@app.get('/news/{item_id}')
def news_detail_page(item_id: str):
 return FileResponse(WEB/'index.html',status_code=200 if q('select 1 from news_items where item_id=%s',(item_id,)) else 404)
@app.get('/sources/{source_id}')
def source_detail_page(source_id: str):
 return FileResponse(WEB/'index.html',status_code=200 if q('select 1 from sources where source_id=%s',(source_id,)) else 404)
@app.get('/')
@app.get('/news')
@app.get('/sources')
@app.get('/analytics')
@app.get('/about')
def dashboard(): return FileResponse(WEB/'index.html')
@app.get('/{path:path}')
def missing_page(path: str): return FileResponse(WEB/'index.html',status_code=404)

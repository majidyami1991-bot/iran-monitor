from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os, psycopg
app=FastAPI(title='Iran Monitor News API',version='0.1.0'); DSN=os.environ['DATABASE_URL']
def q(sql,args=()):
 with psycopg.connect(DSN) as c:
  with c.cursor() as cur:
   cur.execute(sql,args); cols=[d.name for d in cur.description] if cur.description else []; return [dict(zip(cols,r)) for r in cur.fetchall()] if cols else []
@app.get('/api/v1/health')
def health(): return {'status':'ok','items':q('select count(*)::int n from news_items')[0]['n']}
@app.get('/api/v1/meta')
def meta(): return {'name':'Iran Monitor','version':'0.1.0','item_count':health()['items']}
@app.get('/api/v1/items')
def items(search:str|None=None,source_id:str|None=None,page:int=1,page_size:int=20):
 w=[]; a=[]
 if search: w.append('(title ilike %s or canonical_url ilike %s)'); a += [f'%{search}%',f'%{search}%']
 if source_id: w.append('source_id=%s'); a.append(source_id)
 s=(' where '+' and '.join(w)) if w else ''; total=q('select count(*)::int n from news_items'+s,a)[0]['n']; page_size=min(max(page_size,1),100)
 return {'items':q('select item_id,source_id,title,canonical_url,published_at,provenance_status from news_items'+s+' order by published_at desc nulls last limit %s offset %s',a+[page_size,(page-1)*page_size]),'total':total,'page':page,'page_size':page_size}
@app.get('/api/v1/items/{item_id}')
def item(item_id:str): return (q('select * from news_items where item_id=%s',(item_id,)) or [{}])[0]
@app.get('/api/v1/sources')
def source_list():
 r=q('select source_id,name,source_type,canonical_url,hostname,enabled from sources order by name'); return {'sources':r,'total':len(r)}
@app.get('/api/v1/stats/overview')
def overview(): return {'total_items':q('select count(*)::int n from news_items')[0]['n'],'sources':q('select count(*)::int n from sources')[0]['n'],'provenance_complete':q("select count(*)::int n from news_items where provenance_status='COMPLETE'")[0]['n']}
@app.get('/',response_class=HTMLResponse)
def dashboard(): return HTMLResponse('<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><title>Iran Monitor</title><body><h1>Iran Monitor</h1><div id="stats"></div><div id="news"></div><script>async function l(){let s=await(await fetch("/api/v1/stats/overview")).json();stats.innerHTML=JSON.stringify(s);let d=await(await fetch("/api/v1/items?page_size=20")).json();news.innerHTML=d.items.map(x=>`<article><h3>${x.title}</h3><p>${x.published_at||""}</p></article>`).join("")}l()</script></body></html>')

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
import os, psycopg, re
app=FastAPI(title='Iran Monitor News API',version='0.2.0'); DSN=os.environ['DATABASE_URL']
def q(sql,args=()):
 with psycopg.connect(DSN) as c:
  with c.cursor() as cur:
   cur.execute(sql,args); cols=[d.name for d in cur.description] if cur.description else []; return [dict(zip(cols,r)) for r in cur.fetchall()] if cols else []
def count(t): return q(f'select count(*)::int n from {t}')[0]['n']
@app.get('/api/v1/health')
def health(): return {'status':'ok','items':count('news_items'),'database':'ready'}
@app.get('/api/v1/meta')
def meta(): return {'name':'Iran Monitor','version':'0.2.0','item_count':count('news_items')}
@app.get('/api/v1/items')
def items(search:str|None=None,source_id:str|None=None,source_type:str|None=None,date_from:str|None=None,date_to:str|None=None,provenance:str|None=None,sort:str='newest',page:int=1,page_size:int=20):
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
 r=q('select s.source_id,s.name,s.source_type,s.canonical_url,s.hostname,s.enabled,count(n.item_id)::int item_count,max(n.published_at) latest from sources s left join news_items n on n.source_id=s.source_id group by s.source_id order by s.name'); return {'sources':r,'total':len(r)}
@app.get('/api/v1/stats/overview')
def overview(): return {'total_items':count('news_items'),'sources':count('sources'),'provenance_complete':q("select count(*)::int n from news_items where provenance_status='COMPLETE'")[0]['n']}
@app.get('/api/v1/stats/topics')
def topics():
 rows=q("select lower(regexp_replace(word,'[^[:alnum:]آ-ی]+','','g')) topic,count(*)::int count from (select unnest(regexp_split_to_array(coalesce(title,'')||' '||coalesce(summary,''),'\\s+')) word from news_items) x where length(word)>=4 group by 1 order by count desc,topic limit 20"); return {'topics':rows}
@app.get('/',response_class=HTMLResponse)
def dashboard(): return HTMLResponse('''<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ایران مانیتور</title><style>@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700&display=swap');*{box-sizing:border-box}body{margin:0;background:#071426;color:#e8f1ff;font-family:Vazirmatn,Tahoma,sans-serif}header{padding:22px 5%;border-bottom:1px solid #234666;background:#0b1d34}main{max-width:1300px;margin:auto;padding:24px 5%}.sub{color:#9db4cc}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}.card{background:#10243d;border:1px solid #285078;border-radius:14px;padding:18px;margin:12px 0}.num{font-size:2rem;color:#6dd6ff;font-weight:700}.toolbar{display:flex;gap:10px;flex-wrap:wrap}input,select,button{background:#0b1d34;color:#e8f1ff;border:1px solid #386184;border-radius:8px;padding:10px;font:inherit}button{cursor:pointer;background:#155b83}.news h3{margin:0 0 8px}.muted{color:#9db4cc;font-size:.9rem}@media(max-width:500px){main{padding:14px}.card{padding:14px}}
</style></head><body><header><h1>ایران مانیتور</h1><div class=sub>پایش هوشمند اخبار و منابع تحلیلی</div></header><main><section id=stats class=grid></section><section class=card><div class=toolbar><input id=search placeholder="جست‌وجو در عنوان و خلاصه"><select id=sort><option value=newest>جدیدترین</option><option value=oldest>قدیمی‌ترین</option></select><button onclick="load()">اعمال فیلتر</button><button onclick="search.value='';load()">پاک‌کردن</button></div><p id=count class=muted></p></section><section id=news class=news></section></main><script>async function load(){let p=new URLSearchParams({page_size:20,sort:sort.value});if(search.value)p.set('search',search.value);let [s,d]=await Promise.all([fetch('/api/v1/stats/overview').then(x=>x.json()),fetch('/api/v1/items?'+p).then(x=>x.json())]);stats.innerHTML=[['کل اخبار',s.total_items],['منابع',s.sources],['provenance کامل',s.provenance_complete]].map(x=>`<div class=card><div class=num>${x[1]}</div><div>${x[0]}</div></div>`).join('');count.textContent=`${d.total} نتیجه`;news.innerHTML=d.items.map(x=>`<article class=card><h3>${x.title||'بدون عنوان'}</h3><div class=muted>${x.publisher||''} · ${x.published_at||''}</div><p>${x.summary||''}</p><a href="${x.canonical_url}" target=_blank rel="noopener noreferrer">مشاهده منبع اصلی</a></article>`).join('')||'<div class=card>نتیجه‌ای یافت نشد</div>'}load()</script></body></html>''')

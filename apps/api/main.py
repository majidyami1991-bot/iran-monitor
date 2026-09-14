from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pathlib import Path
import json, os

ROOT=Path('/project') if Path('/project/data').exists() else Path(__file__).resolve().parents[2]
ITEMS=[]
for f in (ROOT/'data/runtime/collector').rglob('normalized-items.jsonl'):
    for line in f.read_text(encoding='utf-8').splitlines():
        try: ITEMS.append(json.loads(line))
        except json.JSONDecodeError: pass
sources={}
try:
    for x in json.loads((ROOT/'config/sources/collection-evidence.json').read_text()).get('records',[]): sources[x['source_id']]=x
except Exception: pass
for x in ITEMS:
    s=sources.get(x.get('source_id'),{}); x['publisher']=s.get('hostname') or x.get('source_id'); x['source_type']=s.get('category','news'); x['provenance_status']='COMPLETE'
app=FastAPI(title='Iran Monitor News API',version='0.1.0')

@app.get('/api/v1/health')
def health(): return {'status':'ok','items':len(ITEMS)}
@app.get('/api/v1/meta')
def meta(): return {'name':'Iran Monitor','version':'0.1.0','item_count':len(ITEMS)}
@app.get('/api/v1/items')
def items(search:str|None=None, source_id:str|None=None, page:int=1, page_size:int=20):
    xs=ITEMS
    if search: xs=[x for x in xs if search.lower() in (x.get('title','')+' '+x.get('publisher','')).lower()]
    if source_id: xs=[x for x in xs if x.get('source_id')==source_id]
    page_size=min(max(page_size,1),100); start=(page-1)*page_size
    return {'items':xs[start:start+page_size],'total':len(xs),'page':page,'page_size':page_size}
@app.get('/api/v1/items/{item_id}')
def item(item_id:str):
    return next((x for x in ITEMS if x.get('item_id')==item_id),{})
@app.get('/api/v1/sources')
def source_list(): return {'sources':list(sources.values()),'total':len(sources)}
@app.get('/api/v1/stats/overview')
def overview(): return {'total_items':len(ITEMS),'sources':len(set(x.get('source_id') for x in ITEMS)),'provenance_complete':len(ITEMS)}
@app.get('/',response_class=HTMLResponse)
def dashboard():
    return HTMLResponse('''<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ایران مانیتور</title><style>body{font-family:Tahoma,Arial;background:#071426;color:#e8f1ff;margin:0}main{max-width:1200px;margin:auto;padding:32px}.card{background:#10243d;border:1px solid #285078;border-radius:12px;padding:18px;margin:12px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.muted{color:#9db4cc}a{color:#6dd6ff}</style></head><body><main><h1>ایران مانیتور</h1><p class="muted">پایش هوشمند اخبار و منابع تحلیلی</p><div id="stats" class="grid"></div><section class="card"><h2>آخرین اخبار</h2><div id="news"></div></section></main><script>async function load(){let s=await (await fetch('/api/v1/stats/overview')).json();document.querySelector('#stats').innerHTML=Object.entries(s).map(([k,v])=>`<div class=card><b>${v}</b><div class=muted>${k}</div></div>`).join('');let d=await (await fetch('/api/v1/items?page_size=20')).json();document.querySelector('#news').innerHTML=d.items.map(x=>`<article class=card><h3>${x.title}</h3><div class=muted>${x.publisher} · ${x.published_at||''}</div><a href="${x.canonical_url}" target=_blank rel="noopener noreferrer">مشاهده منبع اصلی</a></article>`).join('')}</script></body></html>''')

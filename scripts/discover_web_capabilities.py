import json,urllib.request,time,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
R=Path('config/sources/source-registry.json'); O=Path('config/sources'); UA='DefenceMonitor-SourceDiscovery/0.1'
def check(s):
 u=s['url']; h=urlparse(u).netloc; out={'source_id':s['source_id'],'canonical_url':u,'category':s['canonical_category'],'hostname':h,'recommended_method':'html_listing','discovery_status':'completed','javascript_required':False,'authentication_required':False,'rate_limited':False,'access_status':'unreachable','feed_type':None,'verified_feed_url':None,'sitemap_url':None,'review_reasons':[]}
 for label,url in [('robots','https://'+h+'/robots.txt'),('homepage','https://'+h+'/')]:
  try:
   q=urllib.request.Request(url,headers={'User-Agent':UA}); t=time.time()
   with urllib.request.urlopen(q,timeout=10) as r: b=r.read(2*1024*1024+1); out[label+'_status']=r.status; out['final_url']=r.geturl(); out[label+'_hash']=hashlib.sha256(b[:100000]).hexdigest(); out[label+'_seconds']=round(time.time()-t,2); out['access_status']='accessible'
  except Exception as e: out[label+'_status']=getattr(e,'code',None); out[label+'_error']=type(e).__name__
 out['robots_allowed']=out.get('robots_status') not in (401,403,429); return out
def main():
 import sys
 d=json.loads(R.read_text()); s=[x for x in d if x['source_type']!='x_account']
 if '--execute' not in sys.argv: print(json.dumps({'planned_sources':len(s),'network_requests':0})); return
 with ThreadPoolExecutor(max_workers=2) as ex: a=list(ex.map(check,s))
 O.mkdir(exist_ok=True); (O/'collection-capabilities.json').write_text(json.dumps(a,indent=2)+'\n'); (O/'collection-evidence.json').write_text(json.dumps({'user_agent':UA,'max_concurrency':2,'records':a},indent=2)+'\n'); print(json.dumps({'sources':len(a),'requests':len(a)*2}))
if __name__=='__main__': main()

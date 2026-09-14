import json,re,time,urllib.request,urllib.error,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin,urlparse
O=Path('config/sources'); caps=json.load(open(O/'collection-capabilities.json')); UA='IranMonitor-SourceDiscovery/0.1'
def get(u):
 try:
  q=urllib.request.Request(u,headers={'User-Agent':UA});
  with urllib.request.urlopen(q,timeout=10) as r: b=r.read(5*1024*1024+1); return r.status,r.geturl(),r.headers.get('Content-Type',''),b
 except Exception as e:return getattr(e,'code',None),u,'',b''
def one(s):
 if s['access_status']!='accessible': return None
 base=s['canonical_url']; host=urlparse(base).netloc; h,rurl,rt,rb=get('https://'+host+'/'); rr,_,_,rbody=get('https://'+host+'/robots.txt'); text=rb.decode('utf8','ignore'); robots=rbody.decode('utf8','ignore'); urls=[]
 urls += re.findall(r'<link[^>]+(?:rss|atom)[^>]+href=["\']([^"\']+)',text,re.I)
 urls += re.findall(r'(?im)^sitemap:\s*(\S+)',robots)
 if not urls: urls=['/feed/','/feed','/rss','/rss.xml','/feed.xml','/atom.xml','/index.xml'][:3]
 feeds=[]; seen=set()
 for u in urls[:8]:
  u=urljoin('https://'+host+'/',u)
  if u in seen: continue
  seen.add(u); time.sleep(2); st,fu,ct,b=get(u)
  if st and 200<=st<300 and (('xml' in ct.lower()) or b.lstrip().startswith((b'<rss',b'<feed',b'<?xml',b'<urlset',b'<sitemapindex'))): feeds.append({'url':u,'status':st,'content_type':ct,'xml_valid':True,'sample_hash':hashlib.sha256(b[:500000]).hexdigest(),'bytes_read':len(b)})
 return s['source_id'],feeds,h,rr

def main():
 targets=[s for s in caps if s['access_status']=='accessible']; out=[]
 with ThreadPoolExecutor(max_workers=2) as ex:
  for f in ex.map(one,targets):
   sid,feeds,hs,rs=f; out.append({'source_id':sid,'feed_checks':feeds,'homepage_status':hs,'robots_status':rs,'discovery_status':'completed'})
 json.dump(out,open(O/'feed-sitemap-discovery.json','w'),indent=2)
 print(json.dumps({'targets':len(targets),'feeds':sum(bool(x['feed_checks']) for x in out),'sitemaps':sum(any('sitemap' in f['content_type'].lower() or 'sitemap' in f['url'] for f in x['feed_checks']) for x in out)}))
if __name__=='__main__':main()

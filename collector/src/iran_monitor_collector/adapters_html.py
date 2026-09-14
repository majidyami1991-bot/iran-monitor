import re
from urllib.parse import urljoin
def parse_html(data,base_url='https://example.test/'):
 text=data.decode() if isinstance(data,bytes) else data; out=[]
 for href,title in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',text,re.I|re.S): out.append({'title':re.sub('<[^>]+>','',title).strip(),'canonical_url':urljoin(base_url,href)})
 return out
def fetch(*a,**k): raise RuntimeError('LIVE_NETWORK_NOT_APPROVED')

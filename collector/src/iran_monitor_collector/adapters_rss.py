import xml.etree.ElementTree as ET
from ..core import normalize_url,stable_item_id
def parse_bytes(data,source_id='fixture',category='news'):
 root=ET.fromstring(data); out=[]
 for n in root.findall('.//item')+root.findall('{*}entry'):
  title=(n.findtext('title') or n.findtext('{*}title') or '').strip(); link=n.findtext('link') or n.findtext('{*}link') or ''; out.append({'item_id':stable_item_id(source_id,link),'source_id':source_id,'title':title,'canonical_url':normalize_url(link),'content_text':None})
 return out
def fetch(*a,**k): raise RuntimeError('LIVE_NETWORK_NOT_APPROVED')

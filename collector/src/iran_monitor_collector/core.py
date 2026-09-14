import hashlib
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
def normalize_url(u):
 p=urlsplit(u.strip()); q=[(k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith(('utm_','fbclid','gclid'))]; return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path or '/',urlencode(q),''))
def stable_item_id(source_id,url): return hashlib.sha256((source_id+'|'+normalize_url(url)).encode()).hexdigest()
def deduplicate(items): return list({x['canonical_url']:x for x in items}.values())

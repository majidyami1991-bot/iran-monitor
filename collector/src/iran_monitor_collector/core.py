import hashlib
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
def normalize_url(u):
 p=urlsplit(u.strip()); q=[(k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith(('utm_','fbclid','gclid'))]; return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path or '/',urlencode(q),''))
def stable_item_id(source_id,url): return hashlib.sha256((source_id+'|'+normalize_url(url)).encode()).hexdigest()
def deduplicate(items): return list({x['canonical_url']:x for x in items}.values())
def update_candidate(old,new):
 if old.get('canonical_url')!=new.get('canonical_url'): return 'NEW_ITEM'
 if old.get('normalized_content_hash')==new.get('normalized_content_hash') and old.get('published_at')==new.get('published_at') and old.get('summary')==new.get('summary'): return 'DUPLICATE_UNCHANGED'
 return 'UPDATE_CANDIDATE'

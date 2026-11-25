import os, psycopg, urllib.request, re, html
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

DSN = os.environ.get('DATABASE_URL', 'postgresql://iran_monitor_user:iran_monitor_secret_123@localhost:5433/iran_monitor')

def clean(s):
    if not s: return None
    t = re.sub(r'<[^>]+>', ' ', s)
    t = ' '.join(html.unescape(t).split())
    return t[:2000] if t else None

with psycopg.connect(DSN) as conn:
    sources = conn.execute("SELECT source_id, name, feed_url FROM sources WHERE feed_url IS NOT NULL").fetchall()
    
    total_recovered = 0
    recoverable_by_source = {}
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'}
    
    for sid, name, feed_url in sources:
        try:
            req = urllib.request.Request(feed_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
            
            try:
                root = ET.fromstring(data)
            except Exception:
                text_data = data.decode('utf-8', errors='ignore')
                cleaned = re.sub(r'&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', text_data)
                root = ET.fromstring(cleaned.encode('utf-8'))
                
            nodes = root.findall('.//{*}item') or root.findall('.//{*}entry')
            source_rec = 0
            for n in nodes:
                # check description
                desc = clean(n.findtext('description') or n.findtext('{*}description') or n.findtext('{*}summary'))
                encoded = clean(n.findtext('{http://purl.org/rss/1.0/modules/content/}encoded') or n.findtext('{*}content'))
                
                # find link
                link = n.findtext('link') or n.findtext('{*}link') or ''
                if not link:
                    for x in n.findall('link') + n.findall('{*}link'):
                        href = x.attrib.get('href')
                        if href:
                            link = href
                            break
                            
                u = urlsplit(link or '')
                if not u.hostname: continue
                canonical = urlunsplit((u.scheme.lower(), u.netloc.lower(), u.path or '/', urlencode([(k,v) for k,v in parse_qsl(u.query) if not k.lower().startswith(('utm_','fbclid','gclid'))]), ''))
                
                if desc and encoded and desc != encoded:
                    # check if this item is in news_items with summary_source = 'content_encoded'
                    row = conn.execute("SELECT item_id, summary_source FROM news_items WHERE canonical_url = %s", (canonical,)).fetchone()
                    if row and row[1] == 'content_encoded':
                        source_rec += 1
                        total_recovered += 1
            if source_rec > 0:
                recoverable_by_source[name] = source_rec
        except Exception as e:
            # print(f"Error fetching {name}: {e}")
            pass

    print(f"Total items in live feeds recoverable with true description: {total_recovered}")
    print("Recoverable breakdown by source:", recoverable_by_source)

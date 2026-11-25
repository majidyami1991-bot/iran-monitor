import os, psycopg, urllib.request, re, html
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

DSN = os.environ.get('DATABASE_URL', 'postgresql://iran_monitor_user:iran_monitor_secret_123@localhost:5433/iran_monitor')

def clean(s):
    if not s: return None
    t = re.sub(r'<[^>]+>', ' ', s)
    t = ' '.join(html.unescape(t).split())
    return t[:2000] if t else None

def run():
    with psycopg.connect(DSN) as conn:
        sources = conn.execute("SELECT source_id, name, feed_url FROM sources WHERE feed_url IS NOT NULL").fetchall()
        
        recovered_count = 0
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'}
        
        print("1. Scanning live feeds for recoverable publisher descriptions...")
        for sid, name, feed_url in sources:
            try:
                req = urllib.request.Request(feed_url, headers=headers)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = resp.read()
                
                try:
                    root = ET.fromstring(data)
                except Exception:
                    text_data = data.decode('utf-8', errors='ignore')
                    cleaned = re.sub(r'&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', text_data)
                    root = ET.fromstring(cleaned.encode('utf-8'))
                    
                nodes = root.findall('.//{*}item') or root.findall('.//{*}entry')
                for n in nodes:
                    desc = clean(n.findtext('description') or n.findtext('{*}description') or n.findtext('{*}summary'))
                    encoded = clean(n.findtext('{http://purl.org/rss/1.0/modules/content/}encoded') or n.findtext('{*}content'))
                    
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
                    
                    if desc and desc != encoded:
                        # Check if this item is in news_items with summary_source = 'content_encoded'
                        row = conn.execute("SELECT item_id, summary_source FROM news_items WHERE canonical_url = %s", (canonical,)).fetchone()
                        if row and row[1] == 'content_encoded':
                            conn.execute("""
                                UPDATE news_items 
                                SET summary = %s, summary_text = %s, summary_raw = %s, 
                                    summary_source = 'description', summary_available = TRUE, updated_at = now()
                                WHERE item_id = %s
                            """, (desc, desc, desc, row[0]))
                            recovered_count += 1
            except Exception as e:
                pass
                
        conn.commit()
        print(f"Successfully recovered {recovered_count} true summaries from live feeds.")

        # 2. Handle remaining contaminated records where recovery is impossible
        print("2. Handling remaining contaminated historical records...")
        unrecovered = conn.execute("SELECT count(1) FROM news_items WHERE summary_source = 'content_encoded'").fetchone()[0]
        print(f"Remaining contaminated records: {unrecovered}")

        # Preserve translations: mark them as superseded so they aren't lost but aren't treated as current summary translations
        superseded_trans = conn.execute("""
            UPDATE news_item_translations t
            SET superseded_at = now(), field = 'summary_legacy_body', updated_at = now()
            FROM news_items n
            WHERE t.item_id = n.item_id AND t.field = 'summary' AND n.summary_source = 'content_encoded'
        """).rowcount
        print(f"Preserved and superseded {superseded_trans} legacy body-translations.")

        # Update news_items so truncated body is not presented as a genuine summary
        cleared_items = conn.execute("""
            UPDATE news_items
            SET summary = NULL, summary_text = NULL, summary_raw = NULL,
                summary_available = FALSE, summary_source = 'body_unsummarized', updated_at = now()
            WHERE summary_source = 'content_encoded'
        """).rowcount
        print(f"Cleared {cleared_items} fake summaries to prevent duplication.")
        conn.commit()
        print("Completed summary recovery and historical classification update successfully.")

if __name__ == '__main__':
    run()

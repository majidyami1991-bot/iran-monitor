"""Publication discovery for sources without public RSS feeds (IISS, Janes)."""
import hashlib
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
import psycopg
from psycopg.types.json import Jsonb

DSN = os.environ.get('DATABASE_URL')
IISS_SOURCE_ID = '3572e0d1-8fb2-5506-a814-9886d9ec41a7'
JANES_SOURCE_ID = 'd512c8e2-4d1f-542b-aad5-364dde147263'

def _item_id(source_id, canonical_url):
    return hashlib.sha256(f"{source_id}|{canonical_url}".encode()).hexdigest()

def discover_iiss():
    """Discover recent publications from IISS Online Analysis using Playwright."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[IISS Discovery] Playwright not installed")
        return 0

    url = 'https://www.iiss.org/online-analysis/online-analysis/'
    items = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            try:
                page = browser.new_page(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
                )
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                cards = page.eval_on_selector_all(
                    'a[href*="/online-analysis/online-analysis/"]',
                    'els => els.map(e => ({href: e.href, text: e.innerText.trim()}))'
                )
                seen_urls = set()
                for c in cards:
                    href = c['href'].split('?')[0].rstrip('/')
                    if href != 'https://www.iiss.org/online-analysis/online-analysis' and len(href.split('/')) > 5:
                        if href not in seen_urls:
                            seen_urls.add(href)
                            title_lines = [l.strip() for l in c['text'].split('\n') if l.strip()]
                            # Filter out non-title category label lines
                            filtered_titles = [l for l in title_lines if l.upper() != 'ONLINE ANALYSIS' and not re.match(r'^\d{1,2}(st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4}', l)]
                            title = filtered_titles[0] if filtered_titles else (title_lines[0] if title_lines else href.split('/')[-1].replace('-', ' ').title())
                            items.append({
                                'source_id': IISS_SOURCE_ID,
                                'canonical_url': href,
                                'title': title
                            })
            finally:
                browser.close()
    except Exception as e:
        print(f"[IISS Discovery] Error fetching page: {e}")
        return 0

    inserted = 0
    now = datetime.now(timezone.utc)
    with psycopg.connect(DSN, autocommit=True) as conn:
        for it in items:
            iid = _item_id(it['source_id'], it['canonical_url'])
            row = conn.execute('''
                INSERT INTO news_items (item_id, source_id, title, canonical_url, collected_at, fetched_at, adapter_type, provenance_status, topics)
                VALUES (%s, %s, %s, %s, %s, %s, 'html_listing', 'COMPLETE', '[]'::jsonb)
                ON CONFLICT (canonical_url) DO NOTHING
                RETURNING item_id
            ''', (iid, it['source_id'], it['title'], it['canonical_url'], now, now)).fetchone()
            
            if row:
                inserted += 1
                job_id = hashlib.sha256(f"{iid}|extraction".encode()).hexdigest()[:32]
                conn.execute('''
                    INSERT INTO enrichment_jobs (job_id, item_id, stage, status, available_at)
                    VALUES (%s, %s, 'extraction', 'pending', now())
                    ON CONFLICT (item_id, stage) DO NOTHING
                ''', (job_id, iid))

    print(f"[IISS Discovery] Discovered {len(items)} items, inserted {inserted} new items")
    return inserted


def discover_janes():
    """Discover defence news from Janes All Defence News over HTTP."""
    url = 'https://www.janes.com/defence-intelligence-insights/all-defence-news'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    items = []
    try:
        req = urllib.request.Request(url, headers=headers)
        html_data = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', 'ignore')
        matches = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html_data, re.DOTALL)
        seen = set()
        for href, title in matches:
            clean_title = ' '.join(re.sub(r'<[^>]+>', ' ', title).split())
            clean_title = re.sub(r'^(Sea|Air|Land|Defence|C4ISR)\s+\d{1,2}\s+[A-Za-z]+\s+\d{4}\s+', '', clean_title).strip()
            clean_title = re.sub(r'\s+Read Article$', '', clean_title).strip()
            if ('/defence-news/' in href or '/osint-analysis/' in href or '/defence-equipment-intelligence/' in href) and len(clean_title) > 15:
                full_url = 'https://www.janes.com' + href if href.startswith('/') else href
                if full_url not in seen:
                    seen.add(full_url)
                    items.append({
                        'source_id': JANES_SOURCE_ID,
                        'canonical_url': full_url,
                        'title': clean_title
                    })
    except Exception as e:
        print(f"[Janes Discovery] Error fetching page: {e}")
        return 0

    inserted = 0
    now = datetime.now(timezone.utc)
    with psycopg.connect(DSN, autocommit=True) as conn:
        for it in items:
            iid = _item_id(it['source_id'], it['canonical_url'])
            row = conn.execute('''
                INSERT INTO news_items (item_id, source_id, title, canonical_url, collected_at, fetched_at, adapter_type, provenance_status, topics)
                VALUES (%s, %s, %s, %s, %s, %s, 'html_listing', 'COMPLETE', '[]'::jsonb)
                ON CONFLICT (canonical_url) DO NOTHING
                RETURNING item_id
            ''', (iid, it['source_id'], it['title'], it['canonical_url'], now, now)).fetchone()
            
            if row:
                inserted += 1
                job_id = hashlib.sha256(f"{iid}|extraction".encode()).hexdigest()[:32]
                conn.execute('''
                    INSERT INTO enrichment_jobs (job_id, item_id, stage, status, available_at)
                    VALUES (%s, %s, 'extraction', 'pending', now())
                    ON CONFLICT (item_id, stage) DO NOTHING
                ''', (job_id, iid))

    print(f"[Janes Discovery] Discovered {len(items)} items, inserted {inserted} new items")
    return inserted

def run_discovery():
    """Run all discovery pipelines."""
    iiss_cnt = discover_iiss()
    janes_cnt = discover_janes()
    return {'iiss_new': iiss_cnt, 'janes_new': janes_cnt}

if __name__ == '__main__':
    run_discovery()

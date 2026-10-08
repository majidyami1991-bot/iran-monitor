"""Lexical retrieval for the local assistant (PostgreSQL only).

The query is built by this module from a fixed SQL shape; user input only
ever reaches the database as bound parameters (tokens, dates, ids). No SQL is
ever produced by the model. LIKE wildcards in user tokens are escaped.

Scoring (deterministic):
  title / Persian title hit  3 per token
  Persian summary hit        2 per token
  summary / topic / source   1 per token
  + trigram word_similarity of the whole question to the title (0..2)
  + small recency and importance terms
When the question has no searchable token (e.g. «مهم‌ترین اخبار امروز») or
nothing matches, the most important recent records in the window are used.

Results are de-duplicated by canonical URL and by event (one record per
event), capped at RESULT_LIMIT records, EXCERPT_CHARS per record and
CONTEXT_CHARS in total.
"""
import re
import time
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.rows import dict_row

RESULT_LIMIT = 8
EXCERPT_CHARS = 700
CONTEXT_CHARS = 5500
CACHE_TTL = 120.0
_CACHE: dict = {}

_FA_NORM = str.maketrans({'ي': 'ی', 'ك': 'ک', 'ۀ': 'ه', 'ة': 'ه', 'ؤ': 'و', 'إ': 'ا', 'أ': 'ا', '٠': '0', '١': '1',
                          '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
                          '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'})
STOP = frozenset('''
از به با در که را این آن برای یا و تا هم چه چی چگونه کدام کدامیک آیا است هست بود شد شده می نمی های ها ای
یک دو درباره مورد چیست کجا کی چرا بگو بده لطفا لطفاً اخبار خبر خبرها خبری منابع منبع روایت روند اطلاعات موجود
کافی شواهد ادعا ترین تر اتفاق اتفاقاتی افتاده افتاد منتشر شده‌اند نوشته‌اند نوشته مهم مهمترین مهم‌ترین امروز دیروز گذشته
ساعت روز هفته ماه اخیر جدید تفاوت چگونه بوده دارد دارند کرده کردند گزارش سامانه
the a an of to in on for and or is are was were be been what which who how why when where about any some
news latest today yesterday last past week month hours hour day days report reports source sources tell me please
did does do happened happen there their with from by this that these those than then into over under
'''.split())


def normalize(text):
    t = (text or '').translate(_FA_NORM).replace('‌', ' ')
    t = re.sub(r'[،؛؟٪-٭۔«»]', ' ', t)  # Persian punctuation
    return re.sub(r'\s+', ' ', t).strip()


def tokens(question):
    words = re.findall(r'[A-Za-z][A-Za-z0-9\-]{1,}|[0-9]{2,}|[؀-ۿ]{2,}', normalize(question).lower())
    out = []
    for w in words:
        if w in STOP or len(w) < 2:
            continue
        if w not in out:
            out.append(w)
    return out[:8]


def detect_window(question, now=None):
    """(start, label) from phrases in the question; None when absent."""
    q = normalize(question).lower()
    now = now or datetime.now(timezone.utc)
    if re.search(r'امروز|today', q):
        return now - timedelta(hours=24), '24h'
    if re.search(r'(24|۲۴)\s*ساعت|24\s*hours?|دیروز|yesterday', q):
        return now - timedelta(hours=48 if 'دیروز' in q or 'yesterday' in q else 24), '24h'
    if re.search(r'هفته|week', q):
        return now - timedelta(days=7), '7d'
    if re.search(r'ماه|month', q):
        return now - timedelta(days=30), '30d'
    return None, None


WINDOWS = {'24h': timedelta(hours=24), '7d': timedelta(days=7), '30d': timedelta(days=30)}


def _like(tok):
    return '%' + tok.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'


def _hit(col, weight):
    return (f"(SELECT count(*) FROM unnest(%(likes)s::text[]) AS lk WHERE {col} ILIKE lk ESCAPE '\\') * {weight}")


NEWS_SQL = '''
SELECT 'news' AS type, n.item_id AS record_id, n.title, COALESCE(NULLIF(btrim(n.summary_text), ''), n.summary) AS summary,
  CASE WHEN tt.status='available' AND tt.review_status IS DISTINCT FROM 'needs_review' THEN tt.text END AS title_fa,
  CASE WHEN ts.status='available' AND ts.review_status IS DISTINCT FROM 'needs_review' THEN ts.text END AS summary_fa,
  n.canonical_url, COALESCE(n.published_at, n.fetched_at, n.collected_at) AS published_at,
  COALESCE(NULLIF(s.display_name, ''), s.hostname) AS source_name, n.source_id, a.category_id, a.category_label,
  ev.event_id,
  ({title_hit} + {title_fa_hit} + {sum_fa_hit} + {sum_hit} + {meta_hit}) AS hits,
  GREATEST(word_similarity(%(q)s, n.title), word_similarity(%(q)s, COALESCE(tt.text, ''))) AS sim
FROM news_items n
JOIN sources s ON s.source_id = n.source_id
LEFT JOIN item_topic_assignments a ON a.item_id = n.item_id AND a.taxonomy_version = %(taxv)s
LEFT JOIN news_item_translations tt ON tt.item_id=n.item_id AND tt.field='title' AND tt.target_language='fa'
LEFT JOIN news_item_translations ts ON ts.item_id=n.item_id AND ts.field='summary' AND ts.target_language='fa'
LEFT JOIN LATERAL (SELECT em.event_id FROM news_event_members em JOIN news_events e USING (event_id)
  WHERE em.item_id = n.item_id AND NOT em.manually_removed ORDER BY e.source_count DESC LIMIT 1) ev ON TRUE
WHERE COALESCE(n.published_at, n.fetched_at, n.collected_at) >= %(since)s
  AND (%(source)s::text IS NULL OR n.source_id = %(source)s)
  AND (%(topic)s::text IS NULL OR a.category_id = %(topic)s)
'''.format(title_hit=_hit('n.title', 3), title_fa_hit=_hit("COALESCE(tt.text, '')", 3),
           sum_fa_hit=_hit("COALESCE(ts.text, '')", 2),
           sum_hit=_hit("COALESCE(n.summary_text, n.summary, '')", 1),
           meta_hit=_hit("COALESCE(a.category_label, '') || ' ' || COALESCE(s.display_name, s.hostname, '')", 1))

X_SQL = '''
SELECT 'x' AS type, p.post_id AS record_id, ('@' || p.author_handle) AS title, p.original_text AS summary,
  NULL::text AS title_fa, CASE WHEN t.status='available' THEN t.translated_text END AS summary_fa,
  p.post_url AS canonical_url, COALESCE(p.published_at, p.manually_registered_at) AS published_at,
  ('X · @' || p.author_handle) AS source_name, p.source_id, p.topic_id AS category_id, NULL::text AS category_label,
  p.event_id,
  ({text_hit} + {tr_hit} + {handle_hit}) AS hits,
  word_similarity(%(q)s, COALESCE(p.original_text, '')) AS sim
FROM x_posts p
LEFT JOIN x_post_translations t ON t.x_post_id = p.post_id AND t.target_language='fa'
WHERE coalesce(btrim(p.original_text), '') <> '' AND p.availability_status <> 'withdrawn'
  AND COALESCE(p.published_at, p.manually_registered_at) >= %(since)s
  AND (%(source)s::text IS NULL OR p.source_id = %(source)s)
  AND (%(topic)s::text IS NULL OR p.topic_id = %(topic)s)
'''.format(text_hit=_hit('p.original_text', 2), tr_hit=_hit("COALESCE(t.translated_text, '')", 3),
           handle_hit=_hit('p.author_handle', 2))


def _excerpt(r):
    """Persian when a validated translation exists, the original otherwise."""
    title = r['title_fa'] or r['title'] or ''
    body = r['summary_fa'] or r['summary'] or ''
    lang = 'fa' if (r['title_fa'] or r['summary_fa']) else 'original'
    text = normalize(body)[:EXCERPT_CHARS]
    if len(normalize(body)) > EXCERPT_CHARS:
        text = text.rsplit(' ', 1)[0] + ' …'
    return title.strip(), text, lang


def search(dsn, question, *, window=None, source_id=None, topic=None, content_type='all', taxonomy_version='3.0.0',
           now=None, use_cache=True):
    """Returns {'records': [...], 'mode': 'keyword'|'recent', 'tokens': [...], 'window': label, 'context_chars': n}."""
    now = now or datetime.now(timezone.utc)
    q = normalize(question)[:500]
    toks = tokens(q)
    detected_since, detected_label = detect_window(q, now)
    if window in WINDOWS:
        since, label = now - WINDOWS[window], window
    elif window == 'all':
        since, label = datetime(2000, 1, 1, tzinfo=timezone.utc), 'all'
    elif detected_since:
        since, label = detected_since, detected_label
    else:
        since, label = now - timedelta(days=30), '30d'
    key = (q.lower(), label, source_id, topic, content_type, int(since.timestamp() // 60))
    if use_cache and key in _CACHE and time.monotonic() - _CACHE[key][0] < CACHE_TTL:
        out = dict(_CACHE[key][1])
        out['cache_hit'] = True
        return out

    args = {'likes': [_like(t) for t in toks] or ['\x00never\x00'], 'q': q, 'since': since,
            'source': source_id or None, 'topic': topic or None, 'taxv': taxonomy_version}
    parts = []
    if content_type in ('all', 'news'):
        parts.append(NEWS_SQL)
    if content_type in ('all', 'x'):
        parts.append(X_SQL)
    sql = ' UNION ALL '.join(f'({p})' for p in parts)
    order = '''ORDER BY (hits + 2 * sim) DESC, published_at DESC NULLS LAST, record_id LIMIT 60'''
    with psycopg.connect(dsn, row_factory=dict_row) as c:
        rows = c.execute(f'SELECT * FROM ({sql}) r WHERE hits > 0 OR sim > 0.45 {order}', args).fetchall()
        mode = 'keyword'
        if not rows:
            mode = 'recent'
            rows = c.execute(f'''SELECT * FROM ({sql}) r ORDER BY
                (CASE WHEN category_id IN ('security_defense','regional_geopolitics') THEN 1 ELSE 0 END) DESC,
                published_at DESC NULLS LAST, record_id LIMIT 60''', args).fetchall()

    records, seen_url, seen_event, total = [], set(), set(), 0
    for r in rows:
        url = (r['canonical_url'] or '').rstrip('/').lower()
        if url and url in seen_url:
            continue
        if r['event_id'] and r['event_id'] in seen_event:
            continue
        title, text, lang = _excerpt(r)
        size = len(title) + len(text)
        if total + size > CONTEXT_CHARS:
            if records:
                break
            text = text[:max(0, CONTEXT_CHARS - len(title))]
            size = len(title) + len(text)
        seen_url.add(url)
        if r['event_id']:
            seen_event.add(r['event_id'])
        total += size
        records.append({
            'evidence_id': f'E{len(records) + 1}', 'type': r['type'], 'record_id': r['record_id'],
            'title': title, 'title_original': r['title'], 'excerpt': text, 'excerpt_language': lang,
            'source_name': r['source_name'], 'source_id': r['source_id'],
            'published_at': r['published_at'].isoformat() if r['published_at'] else None,
            'canonical_url': r['canonical_url'], 'category_id': r['category_id'], 'category_label': r['category_label'],
            'event_id': r['event_id'],
            'internal_url': (f"/news/{r['record_id']}" if r['type'] == 'news' else f"/social/posts/{r['record_id']}"),
        })
        if len(records) >= RESULT_LIMIT:
            break
    out = {'records': records, 'mode': mode, 'tokens': toks, 'window': label, 'context_chars': total, 'cache_hit': False}
    if use_cache:
        _CACHE[key] = (time.monotonic(), out)
        if len(_CACHE) > 256:
            for k in sorted(_CACHE, key=lambda k: _CACHE[k][0])[:64]:
                _CACHE.pop(k, None)
    return out

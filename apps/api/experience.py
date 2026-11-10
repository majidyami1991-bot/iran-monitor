"""Read APIs and derived views for the redesigned newsroom experience.

Everything here is computed from PostgreSQL. Derived views (importance,
breaking, stories, the rule-based daily briefing, event clusters, taxonomy v3
assignments) are produced by versioned, documented rules; each response names
the rule and version that produced it so a reader can audit why an item was,
for example, flagged as breaking. Nothing is estimated, sampled or invented:
where the data does not exist the response says so with a status code.

Rules are documented in docs/STORIES AND BRIEFING CONTRACT.md and
docs/EVENT AND TOPIC MODEL.md.
"""
import hashlib
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from fastapi import HTTPException, Query

import classify_v3 as c3
import clustering_v2 as cl2
import redesign_schema

log = logging.getLogger('experience')
DSN = os.environ['DATABASE_URL']
TAXV = c3.get().version
REFRESH_SECONDS = int(os.getenv('EXPERIENCE_REFRESH_SECONDS', '900'))
JOBS_ENABLED = os.getenv('EXPERIENCE_JOBS_ENABLED', 'true') == 'true'
METADATA_DIR = Path(os.getenv('COLLECTOR_METADATA_DIR', '/app/sources'))

IMPORTANCE_RULE = {
    'id': 'importance_v1',
    'description_fa': 'امتیاز اهمیت = ۳ × (تعداد منابع مستقل پوشش‌دهنده رویداد − ۱، حداکثر ۹) + وزن دسته '
                      '(امنیت و دفاع یا منطقه: ۲، سایر دسته‌های موضوعی: ۱، سایر: ۰، خارج از مأموریت: −۲) '
                      '+ ۱ اگر اطمینان دسته‌بندی ≥ ۰٫۷ + ۲ اگر ناشر عنوان را «BREAKING» علامت زده باشد. '
                      'سطح: زیاد ≥ ۶، متوسط ≥ ۳، در غیر این صورت کم.',
}
BREAKING_RULE = {
    'id': 'breaking_v1',
    'description_fa': 'خبر در ۲۴ ساعت گذشته منتشر شده و یا سطح اهمیت «زیاد» دارد، یا دست‌کم دو منبع مستقل '
                      'همان رویداد را پوشش داده‌اند، یا ناشر آن را «BREAKING» علامت زده است.',
}
STORY_RULE_VERSION = 'stories_v1'
BRIEFING_VERSION = 'rule_briefing_v1'

# One place for the SQL that turns an item into a card, so the feed, the
# ticker, stories and the briefing can never disagree about an item.
ITEM_SQL = '''
SELECT n.item_id, n.title, COALESCE(n.summary_text, n.summary) AS summary, n.summary_available,
  n.content_language, n.canonical_url, n.published_at, COALESCE(n.fetched_at, n.collected_at) AS fetched_at,
  n.provenance_status, n.source_id,
  COALESCE(NULLIF(s.display_name, ''), s.hostname) AS source_name, s.hostname, s.source_type,
  a.category_id, a.category_label, a.secondary, a.subtopics, a.confidence, a.other_reason_code,
  tt.status AS title_fa_status, tt.text AS title_fa, tt.review_status AS title_fa_review,
  ts.status AS summary_fa_status, ts.text AS summary_fa, ts.review_status AS summary_fa_review,
  COALESCE(tt.provider, ts.provider) AS translation_provider, COALESCE(tt.model, ts.model) AS translation_model,
  COALESCE(tt.response_model, ts.response_model) AS translation_served_by,
  tt.quality_flags AS title_fa_flags, ts.quality_flags AS summary_fa_flags,
  COALESCE(ts.updated_at, tt.updated_at) AS translation_updated_at,
  img.url AS image_url, img.alt_text AS image_alt, img.verification_status AS image_verification,
  img.media_id AS pm_id, img.caption AS pm_caption, img.credit AS pm_credit, img.width AS pm_width, img.height AS pm_height,
  img.source_method AS pm_source_method, img.validation_status AS pm_validation_status, img.thumbnail_url AS pm_thumbnail_url,
  COALESCE(ms.usable, 0) AS media_count, ms.blocked AS ms_blocked, ms.unreachable AS ms_unreachable,
  ms.pending AS ms_pending, ms.rejected AS ms_rejected,
  ev.event_id, COALESCE(ev.src, 0) AS event_sources, COALESCE(ev.members, 0) AS event_members,
  (LEAST(9, GREATEST(COALESCE(ev.src, 1) - 1, 0) * 3)
   + CASE WHEN a.category_id IN ('security_defense', 'regional_geopolitics') THEN 2
          WHEN a.category_id = 'other' AND a.other_reason_code = 'off_mission_lifestyle' THEN -2
          WHEN a.category_id = 'other' OR a.category_id IS NULL THEN 0 ELSE 1 END
   + CASE WHEN a.confidence >= 0.7 THEN 1 ELSE 0 END
   + CASE WHEN n.title ~* '^\\s*breaking\\M' THEN 2 ELSE 0 END) AS importance
FROM news_items n
JOIN sources s ON s.source_id = n.source_id
LEFT JOIN item_topic_assignments a ON a.item_id = n.item_id AND a.taxonomy_version = %(taxv)s
LEFT JOIN news_item_translations tt ON tt.item_id = n.item_id AND tt.field = 'title' AND tt.target_language = 'fa'
LEFT JOIN news_item_translations ts ON ts.item_id = n.item_id AND ts.field = 'summary' AND ts.target_language = 'fa'
LEFT JOIN LATERAL (SELECT m.media_id, COALESCE(m.canonical_url, m.url) AS url, m.alt_text, m.verification_status,
    m.caption, m.credit, COALESCE(m.width, m.verified_width, m.declared_width) AS width,
    COALESCE(m.height, m.verified_height, m.declared_height) AS height, m.source_method, m.validation_status, m.thumbnail_url
  FROM news_item_media m
  WHERE m.item_id = n.item_id AND m.kind = 'image' AND m.is_primary
    AND COALESCE(m.validation_status, 'unknown') NOT IN ('rejected', 'blocked', 'unreachable') LIMIT 1) img ON TRUE
LEFT JOIN LATERAL (SELECT count(*) FILTER (WHERE COALESCE(m.validation_status, 'unknown') NOT IN ('rejected', 'blocked', 'unreachable')) AS usable,
    bool_or(m.validation_status = 'blocked') AS blocked, bool_or(m.validation_status = 'unreachable') AS unreachable,
    bool_or(m.validation_status = 'pending') AS pending, bool_or(m.validation_status = 'rejected') AS rejected
  FROM news_item_media m WHERE m.item_id = n.item_id AND m.kind = 'image') ms ON TRUE
LEFT JOIN LATERAL (SELECT (array_agg(e.event_id ORDER BY e.source_count DESC, e.member_count DESC))[1] AS event_id,
  max(e.source_count) AS src, max(e.member_count) AS members
  FROM news_event_members em JOIN news_events e USING (event_id)
  WHERE em.item_id = n.item_id AND NOT em.manually_removed) ev ON TRUE
'''
TS = 'COALESCE(n.published_at, n.fetched_at, n.collected_at)'


def level(score):
    if score is None:
        return 'low'
    return 'high' if score >= 6 else 'medium' if score >= 3 else 'low'


def rows(sql, args=None):
    with psycopg.connect(DSN, row_factory=dict_row) as c:
        return c.execute(sql, args or {}).fetchall()


def one(sql, args=None):
    r = rows(sql, args)
    return r[0] if r else None


def media_fields(r):
    """(primary_media, media_status) for one item row. Additive to the
    legacy image_url/image_alt fields, which keep their meaning."""
    pm = None
    if r.get('image_url'):
        pm = {'id': r.get('pm_id'), 'type': 'image', 'url': r['image_url'], 'thumbnail_url': r.get('pm_thumbnail_url'),
              'width': r.get('pm_width'), 'height': r.get('pm_height'), 'alt_text': r.get('image_alt'),
              'caption': r.get('pm_caption'), 'credit': r.get('pm_credit'),
              'source_method': r.get('pm_source_method'), 'validation_status': r.get('pm_validation_status') or 'unknown'}
    if pm:
        status = 'available'
    elif r.get('ms_blocked'):
        status = 'blocked'
    elif r.get('ms_unreachable'):
        status = 'unreachable'
    elif r.get('ms_pending'):
        status = 'pending'
    elif r.get('ms_rejected'):
        status = 'rejected'
    else:
        status = 'missing'
    for k in ('pm_id', 'pm_caption', 'pm_credit', 'pm_width', 'pm_height', 'pm_source_method', 'pm_validation_status',
              'pm_thumbnail_url', 'ms_blocked', 'ms_unreachable', 'ms_pending', 'ms_rejected'):
        r.pop(k, None)
    return pm, status


def card(r):
    """API shape of one item. Persian fields are only ever the stored
    translation text; when absent the status says why, never a guess."""
    r = dict(r)
    r['importance_level'] = level(r.get('importance'))
    r['title_fa_status'] = r.get('title_fa_status') or 'pending'
    r['summary_fa_status'] = r.get('summary_fa_status') or 'pending'
    # A translation that failed the independent validator stays stored for
    # review but is never displayed as if it were a usable translation.
    for f in ('title', 'summary'):
        if r[f + '_fa_status'] == 'available' and r.get(f + '_fa_review') == 'needs_review':
            r[f + '_fa_status'] = 'needs_review'
    # 3003 lab pipeline (translation_worker_v2): translated_auto = QC found no
    # objection (shown, labelled "not human-verified"); qc_warning = shown only
    # next to the original with a warning (separate *_fa_unverified field);
    # qc_failed / errors = never shown as a translation.
    for f in ('title', 'summary'):
        st, text = r[f + '_fa_status'], r.get(f + '_fa')
        flags = r.pop(f + '_fa_flags', None) or {}
        if not isinstance(flags, dict):
            flags = {}
        r[f + '_fa_unverified'] = text if st == 'qc_warning' else None
        if st not in ('available', 'translated_auto'):
            r[f + '_fa'] = None
        r[f + '_fa_qc'] = {'decision': flags.get('decision'), 'critical': len(flags.get('critical') or []),
                           'uncertain': len(flags.get('uncertain') or []), 'scope': flags.get('source_scope'),
                           'lead_chars': flags.get('lead_chars'), 'full_chars': flags.get('full_chars'),
                           'pipeline': flags.get('pipeline'), 'human_verified': False} if flags.get('decision') else None
    r['machine_translated'] = r['title_fa'] is not None or r['summary_fa'] is not None
    r['primary_media'], r['media_status'] = media_fields(r)
    r['breaking'] = is_breaking(r)
    return r


def is_breaking(r, now=None):
    now = now or datetime.now(timezone.utc)
    ts = r.get('published_at') or r.get('fetched_at')
    if not ts or ts < now - timedelta(hours=24) or ts > now + timedelta(minutes=5):
        return False
    return (level(r.get('importance')) == 'high' or (r.get('event_sources') or 0) >= 2
            or (r.get('title') or '').strip().lower().startswith('breaking'))


def feed_query(*, q=None, source_id=None, category=None, topic=None, window='all', date_from=None, date_to=None,
               lang=None, importance=None, translation=None, has_image=None, sort='newest', limit=30, offset=0):
    where, args = [], {'taxv': TAXV}
    if q:
        where.append("(n.title ILIKE %(q)s OR COALESCE(n.summary_text, n.summary, '') ILIKE %(q)s OR tt.text ILIKE %(q)s)")
        args['q'] = f'%{q[:200]}%'
    if source_id:
        where.append('n.source_id = %(source_id)s'); args['source_id'] = source_id
    if category:
        where.append('a.category_id = %(category)s'); args['category'] = category[:80]
    if topic:
        where.append('(a.subtopics @> %(topic)s::jsonb OR a.secondary @> %(topic)s::jsonb)')
        args['topic'] = json.dumps([{'id': topic[:80]}])
    if window in ('1h', '24h', '7d', '30d'):
        where.append(f"{TS} >= now() - %(win)s::interval AND {TS} <= now() + interval '5 minutes'")
        args['win'] = {'1h': '1 hour', '24h': '24 hours', '7d': '7 days', '30d': '30 days'}[window]
    if date_from:
        where.append(f'{TS} >= %(date_from)s::date'); args['date_from'] = date_from
    if date_to:
        where.append(f"{TS} < %(date_to)s::date + interval '1 day'"); args['date_to'] = date_to
    if lang == 'en':
        where.append("n.content_language ILIKE 'en%%'")
    elif lang == 'fa':
        where.append("(n.content_language ILIKE 'fa%%' OR tt.status IN ('available', 'translated_auto'))")
    elif lang == 'unknown':
        where.append('n.content_language IS NULL')
    # 3003 lab statuses map onto the existing filter values (+ warning / failed)
    groups = {'available': ('available', 'translated_auto'), 'pending': ('pending', 'translation_pending', 'processing', 'stale'),
              'error': ('error', 'failed', 'translation_error', 'translation_failed'), 'warning': ('qc_warning',), 'failed': ('qc_failed', 'needs_review')}
    if translation in groups:
        where.append("COALESCE(tt.status, 'pending') = ANY(%(tr)s)"); args['tr'] = list(groups[translation])
    if has_image is not None:
        where.append('img.url IS ' + ('NOT NULL' if has_image else 'NULL'))
    base = ITEM_SQL + (' WHERE ' + ' AND '.join(where) if where else '')
    order = {'newest': f'{TS} DESC NULLS LAST', 'oldest': f'{TS} ASC NULLS LAST',
             'important': f'importance DESC, {TS} DESC NULLS LAST',
             'coverage': f'event_members DESC, event_sources DESC, {TS} DESC NULLS LAST'}[sort]
    wrapped = f'SELECT * FROM ({base}) x'
    if importance in ('high', 'medium', 'low'):
        wrapped += {'high': ' WHERE importance >= 6', 'medium': ' WHERE importance >= 3 AND importance < 6',
                    'low': ' WHERE importance < 3'}[importance]
    total = one(f'SELECT count(*) AS n FROM ({wrapped}) y', args)['n']
    order = order.replace(TS, 'COALESCE(published_at, fetched_at)')
    data = rows(f'{wrapped} ORDER BY {order}, item_id LIMIT %(limit)s OFFSET %(offset)s',
                {**args, 'limit': limit, 'offset': offset})
    return total, [card(r) for r in data]


# ------------------------------------------------------------------ jobs
def reclassify_missing():
    """Assign taxonomy v3 to every item without a v3 row. Human-locked rows
    are never touched; changed assignments are captured by the history
    trigger, so reclassification never loses the previous state."""
    todo = rows('''SELECT n.item_id, n.title, COALESCE(cn.original_text, n.summary_text, n.summary, '') AS body
        FROM news_items n LEFT JOIN news_item_content cn USING (item_id)
        LEFT JOIN item_topic_assignments a ON a.item_id = n.item_id AND a.taxonomy_version = %(v)s
        WHERE a.item_id IS NULL''', {'v': TAXV})
    if not todo:
        return 0
    with psycopg.connect(DSN) as c:
        for r in todo:
            res = c3.classify(r['title'], r['body'])
            c.execute('''INSERT INTO item_topic_assignments(item_id,taxonomy_version,category_id,category_label,secondary,
                subtopics,evidence,scores,confidence,other_reason_code,method)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(item_id,taxonomy_version) DO NOTHING''',
                      (r['item_id'], res.taxonomy_version, res.category_id, res.category_label, Jsonb(res.secondary),
                       Jsonb(res.subtopics), Jsonb(res.evidence), Jsonb(res.scores), res.confidence,
                       res.other_reason_code, 'rule:' + res.taxonomy_version))
    return len(todo)


def recluster():
    """Run event clustering v2 over the corpus and persist it idempotently.
    Event ids derive from the sorted member set; events of other methods
    (the v1 pilot) are left untouched."""
    data = rows('''SELECT n.item_id, n.title, n.published_at, n.source_id, a.category_id,
        COALESCE(n.summary_text, n.summary, '') AS text FROM news_items n
        LEFT JOIN item_topic_assignments a ON a.item_id = n.item_id AND a.taxonomy_version = %(v)s''', {'v': TAXV})
    items = [cl2.Item(r['item_id'], r['title'], r['published_at'], r['source_id'], r['category_id'], r['text'])
             for r in data]
    clusters = cl2.cluster(items)
    by_id = {i.item_id: i for i in items}
    keep = []
    with psycopg.connect(DSN) as c:
        for cl in clusters:
            members = [by_id[m] for m in cl['members']]
            eid = 'e2-' + hashlib.sha256('|'.join(cl['members']).encode()).hexdigest()[:20]
            keep.append(eid)
            pubs = [m.published_at for m in members if m.published_at]
            cats = [m.category_id for m in members if m.category_id and m.category_id != 'other']
            primary = max(set(cats), key=lambda x: (cats.count(x), x)) if cats else None
            conf = sum(e['score'] for e in cl['edges']) / len(cl['edges']) if cl['edges'] else None
            lvl = None if conf is None else 'high' if conf >= 0.7 else 'medium' if conf >= 0.55 else 'low'
            c.execute('''INSERT INTO news_events(event_id,title,first_published_at,last_updated_at,source_count,member_count,
                clustering_method,algorithm_version,primary_category,confidence,confidence_level)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(event_id) DO UPDATE SET title=EXCLUDED.title,first_published_at=EXCLUDED.first_published_at,
                last_updated_at=EXCLUDED.last_updated_at,source_count=EXCLUDED.source_count,member_count=EXCLUDED.member_count,
                primary_category=EXCLUDED.primary_category,confidence=EXCLUDED.confidence,
                confidence_level=EXCLUDED.confidence_level,updated_at=now()''',
                      (eid, cl2.event_title(members), min(pubs) if pubs else None, max(pubs) if pubs else None,
                       len({m.source_id for m in members}), len(members), cl2.METHOD, cl2.ALGORITHM_VERSION,
                       primary, conf, lvl))
            for m in cl['members']:
                best = max((e for e in cl['edges'] if m in (e['a'], e['b'])), key=lambda e: e['score'], default=None)
                c.execute('''INSERT INTO news_event_members(event_id,item_id,similarity_score,membership_reason)
                    VALUES(%s,%s,%s,%s) ON CONFLICT(event_id,item_id) DO UPDATE SET
                    similarity_score=EXCLUDED.similarity_score,membership_reason=EXCLUDED.membership_reason''',
                          (eid, m, best['score'] if best else None, Jsonb(best['reasons'] if best else {})))
        # Memberships of this method that the new run no longer produces are
        # removed together with events left empty — derived rows only, which
        # the same deterministic run can always reproduce.
        c.execute('''DELETE FROM news_event_members WHERE event_id IN (SELECT event_id FROM news_events
            WHERE clustering_method=%s) AND NOT (event_id = ANY(%s))''', (cl2.METHOD, keep))
        c.execute('''DELETE FROM news_events e WHERE clustering_method=%s AND NOT (event_id = ANY(%s))
            AND NOT EXISTS (SELECT 1 FROM news_event_members m WHERE m.event_id=e.event_id)''', (cl2.METHOD, keep))
    return len(clusters)


def _frame_item(r):
    return {'kind': 'item', 'href': f"/news/{r['item_id']}", 'item_id': r['item_id'],
            'headline': r['title_fa'] or r['title'], 'headline_lang': 'fa' if r['title_fa'] else 'en',
            'subline': r['summary_fa'] or (r['summary'] or '')[:220] or None,
            'subline_lang': 'fa' if r['summary_fa'] else 'en',
            'source_name': r['source_name'], 'published_at': r['published_at'], 'image_url': r['image_url'],
            'category_id': r['category_id'], 'category_label': r['category_label'],
            'importance_level': r['importance_level']}


def _jsonable(v):
    return json.loads(json.dumps(v, default=lambda o: o.isoformat() if hasattr(o, 'isoformat') else str(o)))


def build_stories():
    now = datetime.now(timezone.utc)
    out = []

    def add(kind, ref, title, subtitle, collection, target_type, href, frames, category=None, evidence=None):
        if not frames:
            return
        lead_img = next((f.get('image_url') for f in frames if f.get('image_url')), None)
        updated = max((f['published_at'] for f in frames if f.get('published_at')), default=None)
        out.append({'story_id': f'{kind}:{ref}', 'kind': kind, 'title_fa': title, 'subtitle_fa': subtitle,
                    'collection_label': collection, 'target_type': target_type, 'target_ref': ref,
                    'target_href': href, 'frames': frames,
                    'visual': {'image_url': lead_img, 'category_id': category or frames[0].get('category_id'),
                               'monogram': title[:1]},
                    'evidence': evidence or {}, 'content_updated_at': updated})

    _, top = feed_query(window='24h', sort='important', limit=5)
    top = [t for t in top if t['category_id'] != 'other']
    if top:
        add('today', top[0]['item_id'], 'مهم‌ترین تحول امروز', 'بر اساس قاعده اهمیت، ۲۴ ساعت گذشته',
            'تحول روز', 'item', f"/news/{top[0]['item_id']}", [_frame_item(t) for t in top],
            evidence={'rule': IMPORTANCE_RULE['id'], 'item_ids': [t['item_id'] for t in top]})
    _, recent = feed_query(window='24h', sort='newest', limit=100)
    breaking = [r for r in recent if r['breaking']][:6]
    if breaking:
        add('breaking', now.strftime('%Y%m%d'), 'خبرهای فوری', f'{len(breaking)} خبر مطابق قاعده فوری',
            'فوری', 'news_list', '/news?importance=high&window=24h', [_frame_item(r) for r in breaking],
            evidence={'rule': BREAKING_RULE['id'], 'item_ids': [r['item_id'] for r in breaking]})
    evs = rows('''SELECT e.event_id, e.title, e.source_count, e.member_count, e.last_updated_at, e.primary_category
        FROM news_events e WHERE e.last_updated_at >= now() - interval '72 hours'
        ORDER BY e.source_count DESC, e.member_count DESC, e.last_updated_at DESC LIMIT 6''')
    if evs:
        imgs = {r['event_id']: r for r in rows('''SELECT DISTINCT ON (em.event_id) em.event_id, m.url
            FROM news_event_members em JOIN news_item_media m ON m.item_id = em.item_id
            WHERE m.kind='image' AND m.is_primary AND COALESCE(m.validation_status,'unknown') NOT IN ('rejected','blocked','unreachable')
            AND em.event_id = ANY(%(ids)s) ORDER BY em.event_id, m.position NULLS LAST''',
                                                   {'ids': [e['event_id'] for e in evs]})}
        add('events', now.strftime('%Y%m%d'), 'رویدادهای در حال تحول', f'{len(evs)} رویداد در ۷۲ ساعت گذشته',
            'رویدادها', 'events', '/events',
            [{'kind': 'event', 'href': f"/events/{e['event_id']}", 'headline': e['title'], 'headline_lang': 'en',
              'subline': f"{e['member_count']} خبر از {e['source_count']} منبع", 'subline_lang': 'fa',
              'published_at': e['last_updated_at'], 'category_id': e['primary_category'],
              'image_url': imgs.get(e['event_id'], {}).get('url')} for e in evs],
            category=evs[0]['primary_category'], evidence={'event_ids': [e['event_id'] for e in evs]})
    hot = rows(f'''SELECT a.category_id, a.category_label,
        count(*) FILTER (WHERE {TS} >= now() - interval '24 hours') AS now_n,
        count(*) FILTER (WHERE {TS} < now() - interval '24 hours' AND {TS} >= now() - interval '48 hours') AS prev_n
        FROM news_items n JOIN item_topic_assignments a ON a.item_id = n.item_id AND a.taxonomy_version = %(taxv)s
        WHERE a.category_id <> 'other' AND {TS} >= now() - interval '48 hours'
        GROUP BY 1, 2 HAVING count(*) FILTER (WHERE {TS} >= now() - interval '24 hours') > 0
        ORDER BY 3 DESC, 1 LIMIT 3''', {'taxv': TAXV})
    for h in hot:
        _, its = feed_query(category=h['category_id'], window='24h', sort='important', limit=4)
        delta = h['now_n'] - h['prev_n']
        add('topic', h['category_id'], h['category_label'],
            f"{h['now_n']} خبر در ۲۴ ساعت ({'+' if delta >= 0 else '−'}{abs(delta)} نسبت به روز قبل)",
            'موضوع داغ', 'topic', f"/topics/{h['category_id']}", [_frame_item(t) for t in its],
            category=h['category_id'], evidence={'now': h['now_n'], 'previous': h['prev_n']})
    b = latest_briefing()
    if b:
        devs = b['payload'].get('key_developments', [])[:6]
        add('briefing', str(b['briefing_date']), 'گزارش روزانه', 'خلاصه آماری قاعده‌محور', 'گزارش',
            'briefing', '/briefing',
            [{**d, 'kind': 'item', 'subline': d.get('summary'), 'subline_lang': d.get('summary_lang', 'en')} for d in devs],
            evidence={'briefing_id': b['briefing_id']})
    srcs = rows(f'''SELECT s.source_id, COALESCE(NULLIF(s.display_name,''), s.hostname) AS name, count(*) AS n,
        max({TS}) AS last FROM news_items n JOIN sources s USING (source_id)
        WHERE {TS} >= now() - interval '24 hours' GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 5''')
    if srcs:
        add('sources', now.strftime('%Y%m%d'), 'منابع فعال', f'{len(srcs)} منبع پرکار ۲۴ ساعت گذشته', 'منابع',
            'sources', '/sources',
            [{'kind': 'source', 'href': f"/sources/{s['source_id']}", 'headline': s['name'], 'headline_lang': 'en',
              'subline': f"{s['n']} خبر در ۲۴ ساعت گذشته", 'subline_lang': 'fa', 'published_at': s['last'],
              'source_name': s['name']} for s in srcs])
    sig = weak_signals(limit=5)['signals']
    if sig:
        add('weak_signals', now.strftime('%Y%m%d'), 'سیگنال‌های ضعیف', 'نام‌های تازه با بسامد کم — توصیفی، نه پیش‌بینی',
            'سیگنال', 'foresight', '/foresight/weak-signals',
            [{'kind': 'term', 'href': f"/news/{s['example_item_id']}", 'headline': s['term'], 'headline_lang': 'en',
              'subline': f"{s['count_7d']} خبر در ۷ روز، {s['sources_7d']} منبع؛ ۳۰ روز قبل: صفر",
              'subline_lang': 'fa', 'published_at': s['last_seen']} for s in sig])
    _, dossier = feed_query(topic='iran_axis', window='7d', sort='newest', limit=5)
    if dossier:
        add('dossier', 'iran_axis', 'پرونده: ایران و محور مقاومت', 'پرونده موضوعی قاعده‌محور، ۷ روز', 'پرونده',
            'topic', '/topics/iran_axis', [_frame_item(t) for t in dossier], category='regional_geopolitics')

    ids = []
    with psycopg.connect(DSN) as c:
        for pos, s in enumerate(out):
            ids.append(s['story_id'])
            c.execute('''INSERT INTO stories(story_id,kind,position,title_fa,subtitle_fa,collection_label,target_type,target_ref,
                target_href,frames,visual,rule_id,rule_version,evidence,content_updated_at,generated_at,retired_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),NULL)
                ON CONFLICT(story_id) DO UPDATE SET position=EXCLUDED.position,title_fa=EXCLUDED.title_fa,
                subtitle_fa=EXCLUDED.subtitle_fa,frames=EXCLUDED.frames,visual=EXCLUDED.visual,evidence=EXCLUDED.evidence,
                content_updated_at=EXCLUDED.content_updated_at,generated_at=now(),retired_at=NULL,target_href=EXCLUDED.target_href''',
                      (s['story_id'], s['kind'], pos, s['title_fa'], s['subtitle_fa'], s['collection_label'],
                       s['target_type'], s['target_ref'], s['target_href'], Jsonb(_jsonable(s['frames'])),
                       Jsonb(s['visual']), s['kind'], STORY_RULE_VERSION, Jsonb(_jsonable(s['evidence'])),
                       s['content_updated_at']))
        c.execute('UPDATE stories SET retired_at=now() WHERE retired_at IS NULL AND NOT (story_id = ANY(%s))', (ids,))
    return len(out)


def ai_state():
    """What an AI-written briefing would face right now, without calling
    anything and without reading the key itself."""
    try:
        import ai_gateway as aig
        cfg = aig.load_config()
        external = cfg.mode == aig.Mode.EXTERNAL_PROVIDER
        provider, key = (cfg.provider if external else None), bool(cfg.api_key)
    except Exception:  # noqa: BLE001 - status reporting must not fail the page
        external, provider, key = False, None, False
    last = one("SELECT status, error, provider, model, created_at FROM ai_requests_log ORDER BY created_at DESC LIMIT 1")
    if not external or not key:
        status = 'provider_not_configured'
    elif last and last['status'] not in ('available', 'cached'):
        status = 'provider_unavailable'
    else:
        status = 'configured'
    return {'status': status, 'provider': provider, 'api_key_configured': key,
            'last_request_status': last['status'] if last else None,
            'last_request_error_class': (last['error'] or '')[:60] if last and last['error'] else None,
            'last_request_at': last['created_at'] if last else None}


def build_briefing():
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=24)
    counts = one(f'''SELECT count(*) FILTER (WHERE {TS} >= now()-interval '24 hours' AND {TS} <= now()) AS now_n,
        count(*) FILTER (WHERE {TS} >= now()-interval '48 hours' AND {TS} < now()-interval '24 hours') AS prev_n,
        count(DISTINCT n.source_id) FILTER (WHERE {TS} >= now()-interval '24 hours' AND {TS} <= now()) AS sources
        FROM news_items n''')
    _, cand = feed_query(window='24h', sort='important', limit=60)
    devs, seen_events = [], set()
    for c in cand:
        if c['category_id'] == 'other':
            continue
        if c['event_id'] and c['event_id'] in seen_events:
            continue
        if c['event_id']:
            seen_events.add(c['event_id'])
        devs.append({'item_id': c['item_id'], 'href': f"/news/{c['item_id']}", 'headline': c['title_fa'] or c['title'],
                     'headline_lang': 'fa' if c['title_fa'] else 'en', 'summary': c['summary_fa'] or (c['summary'] or '')[:260] or None,
                     'summary_lang': 'fa' if c['summary_fa'] else 'en', 'source_name': c['source_name'],
                     'headline_en': c['title'], 'summary_en': (c['summary'] or '')[:260] or None,
                     'published_at': c['published_at'], 'category_id': c['category_id'], 'category_label': c['category_label'],
                     'event_id': c['event_id'], 'event_sources': c['event_sources'], 'importance': c['importance'],
                     'importance_level': c['importance_level'], 'image_url': c['image_url']})
        if len(devs) == 8:
            break
    topics = rows(f'''SELECT a.category_id AS id, a.category_label AS label,
        count(*) FILTER (WHERE {TS} >= now()-interval '24 hours') AS now_n,
        count(*) FILTER (WHERE {TS} < now()-interval '24 hours') AS prev_n
        FROM news_items n JOIN item_topic_assignments a ON a.item_id=n.item_id AND a.taxonomy_version=%(taxv)s
        WHERE {TS} >= now()-interval '48 hours' AND {TS} <= now() AND a.category_id <> 'other' GROUP BY 1,2''', {'taxv': TAXV})
    for t in topics:
        t['delta'] = t['now_n'] - t['prev_n']
    rising = sorted([t for t in topics if t['delta'] > 0], key=lambda t: -t['delta'])[:5]
    falling = sorted([t for t in topics if t['delta'] < 0], key=lambda t: t['delta'])[:5]
    top_sources = rows(f'''SELECT s.source_id, COALESCE(NULLIF(s.display_name,''), s.hostname) AS name, count(*) AS n
        FROM news_items n JOIN sources s USING (source_id) WHERE {TS} >= now()-interval '24 hours' AND {TS} <= now()
        GROUP BY 1,2 ORDER BY 3 DESC, 2 LIMIT 5''')
    silent = rows(f'''SELECT s.source_id, COALESCE(NULLIF(s.display_name,''), s.hostname) AS name FROM sources s
        WHERE NOT EXISTS (SELECT 1 FROM news_items n WHERE n.source_id=s.source_id AND {TS} >= now()-interval '24 hours')
        ORDER BY 2''')
    gaps = one(f'''SELECT count(*) FILTER (WHERE COALESCE(tt.status,'pending') <> 'available') AS untranslated,
        count(*) FILTER (WHERE n.summary_available IS FALSE OR COALESCE(n.summary_text,n.summary,'') = '') AS no_summary,
        count(*) FILTER (WHERE a.category_id = 'other') AS other_n, count(*) AS total
        FROM news_items n LEFT JOIN news_item_translations tt ON tt.item_id=n.item_id AND tt.field='title' AND tt.target_language='fa'
        LEFT JOIN item_topic_assignments a ON a.item_id=n.item_id AND a.taxonomy_version=%(taxv)s
        WHERE {TS} >= now()-interval '24 hours' AND {TS} <= now()''', {'taxv': TAXV})
    failing = rows("SELECT COALESCE(NULLIF(display_name,''),hostname) AS name, consecutive_failures FROM sources WHERE consecutive_failures > 0")
    change_pct = None if not counts['prev_n'] else round(100 * (counts['now_n'] - counts['prev_n']) / counts['prev_n'])
    lead_cat = max(topics, key=lambda t: t['now_n'], default=None)
    narrative = (f"در ۲۴ ساعت گذشته {counts['now_n']} خبر از {counts['sources']} منبع ثبت شد"
                 + (f" ({'+' if change_pct >= 0 else '−'}{abs(change_pct)}٪ نسبت به ۲۴ ساعت قبل)" if change_pct is not None else '')
                 + (f"؛ بیشترین پوشش به «{lead_cat['label']}» با {lead_cat['now_n']} خبر اختصاص داشت" if lead_cat and lead_cat['now_n'] else '')
                 + (f" و {len(seen_events)} رویداد چندخبری در این بازه به‌روز شد." if seen_events else '.'))
    narrative_en = (f"In the past 24 hours, {counts['now_n']} stories were recorded from {counts['sources']} sources"
                    + (f" ({change_pct:+d}% compared with the previous 24 hours)" if change_pct is not None else '')
                    + (f"; the leading category recorded {lead_cat['now_n']} stories" if lead_cat and lead_cat['now_n'] else '')
                    + (f", and {len(seen_events)} multi-story events were updated." if seen_events else '.'))
    payload = _jsonable({
        'narrative_fa': narrative, 'narrative_en': narrative_en,
        'narrative_method': 'قالب ثابت متنی که فقط شمارش‌های پایگاه داده را درج می‌کند.',
        'narrative_method_en': 'Fixed text template populated only with database counts.',
        'totals': {'items_24h': counts['now_n'], 'items_prev_24h': counts['prev_n'], 'change_pct': change_pct,
                   'active_sources': counts['sources'], 'events_in_window': len(seen_events)},
        'key_developments': devs, 'rising_topics': rising, 'falling_topics': falling, 'top_sources': top_sources,
        'coverage_gaps': {'silent_sources': silent, 'untranslated_24h': gaps['untranslated'],
                          'without_summary_24h': gaps['no_summary'], 'other_category_24h': gaps['other_n'],
                          'items_24h': gaps['total'], 'sources_with_failures': failing},
        'rules': {'importance': IMPORTANCE_RULE['id'], 'taxonomy': TAXV, 'clustering': cl2.METHOD},
    })
    ai = ai_state()
    digest = hashlib.sha256(json.dumps({k: v for k, v in payload.items()}, sort_keys=True).encode()).hexdigest()
    payload['digest'] = digest
    last = one('SELECT payload->>%(k)s AS d FROM daily_briefings WHERE briefing_date=%(d)s ORDER BY generated_at DESC LIMIT 1',
               {'k': 'digest', 'd': now.date()})
    if last and last['d'] == digest:
        return False
    with psycopg.connect(DSN) as c:
        c.execute('''INSERT INTO daily_briefings(briefing_date,window_start,window_end,generator,generator_version,ai_generated,
            ai_status,ai_provider,ai_model,ai_prompt_version,executive_summary_fa,payload)
            VALUES(%s,%s,%s,'rule_based',%s,false,%s,%s,NULL,NULL,NULL,%s)''',
                  (now.date(), start, now, BRIEFING_VERSION, ai['status'], ai['provider'], Jsonb(payload)))
    return True


def latest_briefing(date=None):
    if date:
        return one('SELECT * FROM daily_briefings WHERE briefing_date=%(d)s ORDER BY generated_at DESC LIMIT 1', {'d': date})
    return one('SELECT * FROM daily_briefings ORDER BY generated_at DESC LIMIT 1')


def weak_signals(limit=20):
    """Capitalised names that appear in >= 2 items in the last 7 days and in
    none of the 30 days before. Descriptive novelty, not a prediction."""
    data = rows(f'''SELECT n.item_id, n.title, n.source_id, {TS} AS ts, COALESCE(n.summary_text, n.summary, '') AS text
        FROM news_items n WHERE {TS} >= now() - interval '37 days' AND {TS} <= now()''')
    now = datetime.now(timezone.utc)
    recent, prior = {}, set()
    corpus = cl2.Corpus([cl2.Item(r['item_id'], r['title'], r['ts'], r['source_id'], None, r['text']) for r in data])
    ts = {r['item_id']: r['ts'] for r in data}
    for it in corpus.items:
        for e in it.entities:
            if ts[it.item_id] >= now - timedelta(days=7):
                recent.setdefault(e, []).append(it)
            else:
                prior.add(e)
    out = []
    for term, its in recent.items():
        if term in prior or len(its) < 2:
            continue
        its.sort(key=lambda i: ts[i.item_id], reverse=True)
        out.append({'term': term.title(), 'count_7d': len(its), 'sources_7d': len({i.source_id for i in its}),
                    'first_seen': min(ts[i.item_id] for i in its), 'last_seen': ts[its[0].item_id],
                    'example_item_id': its[0].item_id, 'example_title': its[0].title,
                    'item_ids': [i.item_id for i in its[:10]]})
    out.sort(key=lambda s: (-s['sources_7d'], -s['count_7d'], s['term']))
    return {'method_fa': 'نام‌های خاص (کلمات با حرف بزرگ که در متن‌ها با حرف کوچک نیامده‌اند) که در ۷ روز اخیر دست‌کم در دو خبر '
                         'آمده‌اند و در ۳۰ روز پیش از آن در هیچ خبری نبوده‌اند. این یک شمارش توصیفی از تازگی است، نه پیش‌بینی '
                         'یا ارزیابی اهمیت.', 'signals': out[:limit], 'total': len(out)}


def run_jobs_once():
    with psycopg.connect(DSN) as c:
        got = c.execute('SELECT pg_try_advisory_lock(772031)').fetchone()[0]
        if not got:
            return {'skipped': 'another instance holds the job lock'}
        try:
            t0 = time.time()
            n_cls = reclassify_missing()
            n_ev = recluster()
            new_b = build_briefing()
            n_st = build_stories()
            return {'classified': n_cls, 'events': n_ev, 'briefing_written': new_b, 'stories': n_st,
                    'seconds': round(time.time() - t0, 1)}
        finally:
            c.execute('SELECT pg_advisory_unlock(772031)')


def _loop():
    # Newly collected items get their v3 topic within a minute (cheap: only
    # rows without an assignment); clustering, briefing and stories run on
    # the collection cadence.
    last_full = 0.0
    while True:
        try:
            if time.time() - last_full >= REFRESH_SECONDS:
                log.warning('experience jobs: %s', run_jobs_once())
                last_full = time.time()
            else:
                n = reclassify_missing()
                if n:
                    log.warning('experience: classified %s new items', n)
            # Media v2 for rows written by the (pre-v2) production collector:
            # offline mapping + primary selection, no network.
            import media_pipeline as mp
            with psycopg.connect(DSN) as mc:
                synced = mp.sync_legacy_rows(mc)
            if synced:
                log.warning('experience: media v2 synced %s legacy rows', synced)
        except Exception:  # noqa: BLE001 - keep serving; next cycle retries
            log.exception('experience jobs failed')
        time.sleep(60)


# ------------------------------------------------------------------ API
def register_experience(app):
    @app.on_event('startup')
    def _start():
        redesign_schema.apply(DSN)
        if JOBS_ENABLED:
            threading.Thread(target=_loop, name='experience-jobs', daemon=True).start()

    @app.get('/api/v1/rules')
    def rules():
        return {'importance': IMPORTANCE_RULE, 'breaking': BREAKING_RULE, 'taxonomy_version': TAXV,
                'clustering': {'method': cl2.METHOD, 'version': cl2.ALGORITHM_VERSION},
                'stories': STORY_RULE_VERSION, 'briefing': BRIEFING_VERSION}

    @app.get('/api/v1/breaking')
    def breaking(limit: int = Query(12, ge=1, le=40)):
        _, recent = feed_query(window='24h', sort='newest', limit=200)
        hits = [r for r in recent if r['breaking']][:limit]
        mode = 'breaking'
        if not hits:
            _, hits = feed_query(window='all', sort='newest', limit=min(limit, 8))
            mode = 'latest_fallback'
        return {'mode': mode, 'rule': BREAKING_RULE, 'items': hits}

    @app.get('/api/v1/feed')
    def feed(q: str | None = None, source_id: str | None = None, category: str | None = None, topic: str | None = None,
             window: str = 'all', date_from: str | None = None, date_to: str | None = None, lang: str | None = None,
             importance: str | None = None, translation: str | None = None, has_image: bool | None = None,
             sort: str = 'newest', page: int = Query(1, ge=1, le=1000), page_size: int = Query(24, ge=1, le=60)):
        if sort not in ('newest', 'oldest', 'important', 'coverage'):
            raise HTTPException(422, 'invalid_sort')
        if window not in ('all', '1h', '24h', '7d', '30d'):
            raise HTTPException(422, 'invalid_window')
        for d in (date_from, date_to):
            if d:
                try:
                    datetime.strptime(d, '%Y-%m-%d')
                except ValueError:
                    raise HTTPException(422, 'invalid_date')
        total, items = feed_query(q=q, source_id=source_id, category=category, topic=topic, window=window,
                                  date_from=date_from, date_to=date_to, lang=lang, importance=importance,
                                  translation=translation, has_image=has_image, sort=sort,
                                  limit=page_size, offset=(page - 1) * page_size)
        return {'items': items, 'total': total, 'page': page, 'page_size': page_size,
                'has_next': page * page_size < total, 'taxonomy_version': TAXV, 'importance_rule': IMPORTANCE_RULE['id']}

    @app.get('/api/v1/feed/{item_id}/context')
    def item_context(item_id: str):
        r = one(ITEM_SQL + ' WHERE n.item_id = %(id)s', {'taxv': TAXV, 'id': item_id})
        if not r:
            raise HTTPException(404, 'news_item_not_found')
        item = card(r)
        a = one('SELECT * FROM item_topic_assignments WHERE item_id=%(id)s AND taxonomy_version=%(v)s', {'id': item_id, 'v': TAXV})
        hist = rows('''SELECT taxonomy_version, category_id, category_label, other_reason_code, confidence, change_kind,
            human_locked, recorded_at FROM item_topic_assignment_history WHERE item_id=%(id)s ORDER BY recorded_at''', {'id': item_id})
        legacy = one('SELECT category_id, category_label, taxonomy_version, confidence FROM item_classifications WHERE item_id=%(id)s', {'id': item_id})
        related = []
        if item['event_id']:
            related = rows(f'''SELECT n.item_id, n.title, n.published_at, COALESCE(NULLIF(s.display_name,''),s.hostname) AS source_name
                FROM news_event_members em JOIN news_items n USING (item_id) JOIN sources s ON s.source_id=n.source_id
                WHERE em.event_id=%(e)s AND NOT em.manually_removed AND n.item_id <> %(id)s ORDER BY n.published_at''',
                           {'e': item['event_id'], 'id': item_id})
        same_topic = []
        if item['category_id'] and item['category_id'] != 'other':
            _, same_topic = feed_query(category=item['category_id'], window='7d', sort='important', limit=6)
            same_topic = [s for s in same_topic if s['item_id'] != item_id][:5]
        reason_label = c3.get().reason_label(a['other_reason_code']) if a and a['other_reason_code'] else None
        return {'item': item, 'assignment': a, 'other_reason_label': reason_label, 'history': hist,
                'legacy_classification': legacy, 'event_items': related, 'same_topic': same_topic,
                'importance_rule': IMPORTANCE_RULE}

    @app.patch('/api/v1/feed/{item_id}/topic')
    def override_topic(item_id: str, category_id: str = Query(...), note: str = Query(..., min_length=3, max_length=300)):
        """Human override: locks the v3 assignment; the history trigger keeps
        what it was before."""
        labels = c3.get().labels
        if category_id not in labels and category_id != 'other':
            raise HTTPException(422, 'unknown_category')
        with psycopg.connect(DSN) as c:
            cur = c.execute('''UPDATE item_topic_assignments SET category_id=%s, category_label=%s, human_locked=true,
                human_note=%s, method='human_override', assigned_at=now() WHERE item_id=%s AND taxonomy_version=%s''',
                            (category_id, labels.get(category_id, 'سایر'), note, item_id, TAXV))
            if cur.rowcount == 0:
                raise HTTPException(404, 'assignment_not_found')
        return item_context(item_id)

    @app.get('/api/v1/stories')
    def stories():
        data = rows('''SELECT story_id, kind, position, title_fa, subtitle_fa, collection_label, target_type, target_ref,
            target_href, visual, jsonb_array_length(frames) AS frame_count, content_updated_at, generated_at, rule_version
            FROM stories WHERE retired_at IS NULL ORDER BY position''')
        return {'stories': data, 'total': len(data), 'rule_version': STORY_RULE_VERSION}

    @app.get('/api/v1/stories/{story_id}')
    def story(story_id: str):
        s = one('SELECT * FROM stories WHERE story_id=%(id)s', {'id': story_id})
        if not s:
            raise HTTPException(404, 'story_not_found')
        return s

    @app.get('/api/v1/briefing/daily')
    def briefing(date: str | None = None):
        b = latest_briefing(date)
        ai = ai_state()
        if not b:
            return {'status': 'not_generated', 'ai': ai, 'briefing': None}
        age_h = (datetime.now(timezone.utc) - b['generated_at']).total_seconds() / 3600
        history = rows('SELECT briefing_id, briefing_date, generated_at FROM daily_briefings ORDER BY generated_at DESC LIMIT 14')
        return {'status': 'fresh' if age_h <= 1 else 'stale' if age_h <= 24 else 'outdated',
                'age_hours': round(age_h, 2), 'ai': ai, 'briefing': b, 'history': history}

    @app.get('/api/v1/timeline/events')
    def timeline_events(sort: str = 'latest', category: str | None = None, window: str = 'all',
                        page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=60)):
        order = {'latest': 'e.last_updated_at DESC NULLS LAST', 'important': 'e.source_count DESC, e.member_count DESC, e.last_updated_at DESC',
                 'largest': 'e.member_count DESC, e.last_updated_at DESC'}.get(sort)
        if not order:
            raise HTTPException(422, 'invalid_sort')
        where, args = [], {}
        if category:
            where.append('e.primary_category = %(cat)s'); args['cat'] = category
        if window in ('24h', '7d', '30d'):
            where.append('e.last_updated_at >= now() - %(w)s::interval'); args['w'] = {'24h': '24 hours', '7d': '7 days', '30d': '30 days'}[window]
        w = (' WHERE ' + ' AND '.join(where)) if where else ''
        total = one('SELECT count(*) AS n FROM news_events e' + w, args)['n']
        data = rows(f'''SELECT e.*, (SELECT json_agg(json_build_object('source_id', s.source_id,
              'name', COALESCE(NULLIF(s.display_name,''), s.hostname)) ORDER BY s.hostname)
              FROM (SELECT DISTINCT n.source_id FROM news_event_members em JOIN news_items n USING (item_id)
                    WHERE em.event_id = e.event_id AND NOT em.manually_removed) x JOIN sources s USING (source_id)) AS sources,
            (SELECT json_agg(json_build_object('t', n.published_at, 'item_id', n.item_id) ORDER BY n.published_at)
              FROM news_event_members em JOIN news_items n USING (item_id)
              WHERE em.event_id = e.event_id AND NOT em.manually_removed) AS pulses,
            (SELECT m.url FROM news_event_members em JOIN news_item_media m ON m.item_id = em.item_id
              WHERE em.event_id = e.event_id AND m.kind='image' AND m.is_primary
              AND COALESCE(m.validation_status,'unknown') NOT IN ('rejected','blocked','unreachable')
              AND m.verification_status <> 'rejected' ORDER BY m.position NULLS LAST LIMIT 1) AS image_url
            FROM news_events e{w} ORDER BY {order} LIMIT %(l)s OFFSET %(o)s''', {**args, 'l': page_size, 'o': (page - 1) * page_size})
        labels = c3.get().labels
        for e in data:
            e['primary_category_label'] = labels.get(e['primary_category']) if e['primary_category'] else None
        return {'events': data, 'total': total, 'page': page, 'page_size': page_size, 'has_next': page * page_size < total,
                'method': {'current': cl2.METHOD, 'version': cl2.ALGORITHM_VERSION}}

    @app.get('/api/v1/timeline/events/{event_id}')
    def timeline_event(event_id: str):
        e = one('SELECT * FROM news_events WHERE event_id=%(id)s', {'id': event_id})
        if not e:
            raise HTTPException(404, 'event_not_found')
        members = rows(ITEM_SQL + ''' JOIN news_event_members em2 ON em2.item_id = n.item_id AND em2.event_id = %(id)s
            AND NOT em2.manually_removed ORDER BY n.published_at ASC NULLS LAST''', {'taxv': TAXV, 'id': event_id})
        reasons = {r['item_id']: r for r in rows('''SELECT item_id, similarity_score, membership_reason FROM news_event_members
            WHERE event_id=%(id)s''', {'id': event_id})}
        items = []
        for m in members:
            x = card(m)
            x['similarity_score'] = reasons.get(m['item_id'], {}).get('similarity_score')
            x['membership_reason'] = reasons.get(m['item_id'], {}).get('membership_reason')
            items.append(x)
        e['primary_category_label'] = c3.get().labels.get(e['primary_category']) if e.get('primary_category') else None
        return {'event': e, 'items': items,
                'sources': sorted({(i['source_id'], i['source_name']) for i in items}, key=lambda s: s[1] or ''),
                'method_note_fa': 'خوشه‌بندی قطعی: اشتراک نام‌های خاص کم‌بسامد در عنوان‌ها + هم‌پوشانی واژگان وزن‌دار + '
                                  'فاصله زمانی حداکثر ۷۲ ساعت؛ همه اعضای یک رویداد باید دوبه‌دو شرط را داشته باشند.'}

    @app.get('/api/v1/topics')
    def topics(window: str = '30d'):
        win = {'24h': '24 hours', '7d': '7 days', '30d': '30 days', 'all': '100 years'}.get(window)
        if not win:
            raise HTTPException(422, 'invalid_window')
        tax = c3.get().tax
        counts = {r['category_id']: r for r in rows(f'''SELECT a.category_id, count(*) AS n,
            count(*) FILTER (WHERE {TS} >= now()-interval '7 days') AS n7,
            count(*) FILTER (WHERE {TS} < now()-interval '7 days' AND {TS} >= now()-interval '14 days') AS p7
            FROM item_topic_assignments a JOIN news_items n USING (item_id) WHERE a.taxonomy_version=%(v)s
            AND {TS} >= now()-%(w)s::interval GROUP BY 1''', {'v': TAXV, 'w': win})}
        subs = {r['id']: r['n'] for r in rows(f'''SELECT x->>'id' AS id, count(*) AS n FROM item_topic_assignments a
            JOIN news_items n USING (item_id), jsonb_array_elements(a.subtopics) x
            WHERE a.taxonomy_version=%(v)s AND {TS} >= now()-%(w)s::interval GROUP BY 1''', {'v': TAXV, 'w': win})}
        total = sum(c['n'] for c in counts.values())
        cats = []
        for cat in tax['categories']:
            c = counts.get(cat['id'], {'n': 0, 'n7': 0, 'p7': 0})
            cats.append({'id': cat['id'], 'label': cat['label'], 'label_en': cat.get('label_en'), 'count': c['n'],
                         'share': round(100 * c['n'] / total, 1) if total else 0, 'last_7d': c['n7'], 'prev_7d': c['p7'],
                         'subtopics': [{'id': s['id'], 'label': s['label'], 'count': subs.get(s['id'], 0)}
                                       for s in cat.get('subtopics', [])]})
        o = counts.get('other', {'n': 0, 'n7': 0, 'p7': 0})
        reasons = rows(f'''SELECT other_reason_code AS id, count(*) AS n FROM item_topic_assignments a JOIN news_items n USING (item_id)
            WHERE a.taxonomy_version=%(v)s AND a.category_id='other' AND {TS} >= now()-%(w)s::interval GROUP BY 1 ORDER BY 2 DESC''',
                       {'v': TAXV, 'w': win})
        for r in reasons:
            r['label'] = c3.get().reason_label(r['id'])
        legacy = one("SELECT count(*) FILTER (WHERE category_id='other') AS other_n, count(*) AS n FROM item_classifications")
        return {'taxonomy_version': TAXV, 'method': tax['method'], 'window': window, 'total': total, 'categories': cats,
                'other': {'count': o['n'], 'share': round(100 * o['n'] / total, 1) if total else 0, 'reasons': reasons},
                'legacy_v2_other_share': round(100 * legacy['other_n'] / legacy['n'], 1) if legacy and legacy['n'] else None}

    @app.get('/api/v1/topics/{slug}')
    def topic(slug: str):
        tax = c3.get().tax
        cat = next((c for c in tax['categories'] if c['id'] == slug), None)
        sub, parent = None, None
        if not cat:
            for c in tax['categories']:
                s = next((s for s in c.get('subtopics', []) if s['id'] == slug), None)
                if s:
                    sub, parent = s, c
        if slug == 'other':
            cat = {'id': 'other', 'label': 'سایر', 'subtopics': []}
        if not cat and not sub:
            raise HTTPException(404, 'topic_not_found')
        cond = 'a.category_id = %(slug)s' if cat else 'a.subtopics @> %(sj)s::jsonb'
        args = {'v': TAXV, 'slug': slug, 'sj': json.dumps([{'id': slug}])}
        series = rows(f'''SELECT date_trunc('day', {TS}) AS day, count(*) AS n FROM news_items n
            JOIN item_topic_assignments a ON a.item_id=n.item_id AND a.taxonomy_version=%(v)s
            WHERE {cond} AND {TS} >= now()-interval '30 days' AND {TS} <= now() GROUP BY 1 ORDER BY 1''', args)
        srcs = rows(f'''SELECT s.source_id, COALESCE(NULLIF(s.display_name,''),s.hostname) AS name, count(*) AS n FROM news_items n
            JOIN sources s USING (source_id) JOIN item_topic_assignments a ON a.item_id=n.item_id AND a.taxonomy_version=%(v)s
            WHERE {cond} GROUP BY 1,2 ORDER BY 3 DESC LIMIT 8''', args)
        total = one(f'''SELECT count(*) AS n FROM item_topic_assignments a WHERE a.taxonomy_version=%(v)s AND {cond}''', args)['n']
        evs = rows(f'''SELECT e.event_id, e.title, e.member_count, e.source_count, e.last_updated_at FROM news_events e
            WHERE e.primary_category = %(slug)s ORDER BY e.last_updated_at DESC LIMIT 6''', args) if cat else []
        return {'slug': slug, 'kind': 'category' if cat else 'subtopic',
                'label': (cat or sub)['label'], 'parent': {'id': parent['id'], 'label': parent['label']} if parent else None,
                'subtopics': [{'id': s['id'], 'label': s['label']} for s in (cat or {}).get('subtopics', [])],
                'keywords_en': (cat or sub).get('keywords_en', [])[:40], 'total': total, 'series_30d': series,
                'top_sources': srcs, 'events': evs, 'taxonomy_version': TAXV}

    @app.get('/api/v1/source-profiles')
    def source_profiles():
        data = rows(f'''SELECT s.source_id, COALESCE(NULLIF(s.display_name,''), s.hostname) AS name,
            s.display_name IS NOT NULL AND s.display_name <> '' AS has_official_name, s.hostname, s.canonical_url,
            s.source_type, s.category, s.language, s.feed_url, s.collection_tier, s.enabled_for_scheduler,
            s.last_attempt_at, s.last_success_at, s.last_http_status, s.consecutive_failures, s.health_status,
            count(n.item_id) AS item_count,
            count(n.item_id) FILTER (WHERE {TS} >= now()-interval '24 hours' AND {TS} <= now()) AS items_24h,
            count(n.item_id) FILTER (WHERE {TS} >= now()-interval '7 days' AND {TS} <= now()) AS items_7d,
            max(n.published_at) AS last_published, max(COALESCE(n.fetched_at, n.collected_at)) AS last_received,
            count(n.item_id) FILTER (WHERE n.provenance_status='COMPLETE') AS provenance_complete,
            count(n.item_id) FILTER (WHERE tt.status='available') AS translated,
            count(n.item_id) FILTER (WHERE n.summary_available) AS with_summary
            FROM sources s LEFT JOIN news_items n USING (source_id)
            LEFT JOIN news_item_translations tt ON tt.item_id=n.item_id AND tt.field='title' AND tt.target_language='fa'
            GROUP BY s.id ORDER BY 2''')
        runs = {r['source_id']: r for r in rows('''SELECT source_id, count(*) AS runs,
            count(*) FILTER (WHERE status='succeeded') AS ok FROM source_run_results
            WHERE started_at >= now()-interval '7 days' GROUP BY 1''')}
        total = sum(d['item_count'] for d in data) or 1
        for d in data:
            r = runs.get(d['source_id'], {'runs': 0, 'ok': 0})
            d['runs_7d'], d['runs_ok_7d'] = r['runs'], r['ok']
            d['success_rate_7d'] = round(100 * r['ok'] / r['runs'], 1) if r['runs'] else None
            d['coverage_share'] = round(100 * d['item_count'] / total, 1)
            d['translation_pct'] = round(100 * d['translated'] / d['item_count'], 1) if d['item_count'] else None
            d['provenance_pct'] = round(100 * d['provenance_complete'] / d['item_count'], 1) if d['item_count'] else None
            d['country'] = None
            d['country_status'] = 'not_recorded'
            d['language_provenance'] = 'feed_declared' if d['language'] else 'not_declared'
            d['channels'] = {'rss': 'active' if d['enabled_for_scheduler'] else 'inactive',
                             'html': 'not_configured', 'x': 'not_configured'}
            d['freshness_minutes'] = int((datetime.now(timezone.utc) - d['last_received']).total_seconds() / 60) if d['last_received'] else None
        fields = ['has_official_name', 'hostname', 'source_type', 'language', 'feed_url', 'canonical_url']
        filled = sum(1 for d in data for f in fields if d.get(f)) + 0
        return {'sources': data, 'total': len(data),
                'metadata_completeness': {'fields': fields + ['country'], 'filled': filled,
                                          'possible': len(data) * (len(fields) + 1),
                                          'pct': round(100 * filled / (len(data) * (len(fields) + 1)), 1) if data else None}}

    @app.get('/api/v1/source-profiles/{source_id}')
    def source_profile(source_id: str):
        base = next((s for s in source_profiles()['sources'] if s['source_id'] == source_id), None)
        if not base:
            raise HTTPException(404, 'source_not_found')
        args = {'id': source_id, 'v': TAXV}
        base['topics'] = rows('''SELECT a.category_id, a.category_label, count(*) AS n FROM news_items n
            JOIN item_topic_assignments a ON a.item_id=n.item_id AND a.taxonomy_version=%(v)s WHERE n.source_id=%(id)s
            GROUP BY 1,2 ORDER BY 3 DESC''', args)
        base['timeline_30d'] = rows(f'''SELECT date_trunc('day', {TS}) AS day, count(*) AS n FROM news_items n
            WHERE n.source_id=%(id)s AND {TS} >= now()-interval '30 days' AND {TS} <= now() GROUP BY 1 ORDER BY 1''', args)
        base['runs'] = rows('''SELECT run_id, started_at, status, http_status, observed, inserted, duplicates, error_class
            FROM source_run_results WHERE source_id=%(id)s ORDER BY started_at DESC LIMIT 20''', args)
        base['hours'] = rows(f'''SELECT extract(hour FROM {TS} AT TIME ZONE 'Asia/Tehran')::int AS h, count(*) AS n
            FROM news_items n WHERE n.source_id=%(id)s GROUP BY 1 ORDER BY 1''', args)
        _, base['recent'] = feed_query(source_id=source_id, sort='newest', limit=10)
        return base

    @app.get('/api/v1/activity')
    def activity():
        a = one(f'''SELECT count(*) FILTER (WHERE {TS} >= now()-interval '1 hour' AND {TS} <= now()) AS h1,
            count(*) FILTER (WHERE {TS} >= now()-interval '24 hours' AND {TS} <= now()) AS h24,
            count(*) FILTER (WHERE {TS} >= now()-interval '48 hours' AND {TS} < now()-interval '24 hours') AS prev24,
            count(*) FILTER (WHERE {TS} >= now()-interval '7 days' AND {TS} <= now()) AS d7, count(*) AS total
            FROM news_items n''')
        hourly = rows(f'''SELECT date_trunc('hour', {TS}) AS t, count(*) AS n FROM news_items n
            WHERE {TS} >= now()-interval '48 hours' AND {TS} <= now() GROUP BY 1 ORDER BY 1''')
        run = one('''SELECT run_id, started_at, finished_at, status, sources_succeeded, sources_failed, items_inserted
            FROM collection_runs ORDER BY started_at DESC LIMIT 1''')
        src = one('''SELECT count(*) AS total, count(*) FILTER (WHERE consecutive_failures=0 AND last_success_at >= now()-interval '1 hour') AS fresh,
            count(*) FILTER (WHERE consecutive_failures>0) AS failing FROM sources''')
        ev = one("SELECT count(*) FILTER (WHERE last_updated_at >= now()-interval '24 hours') AS updated, count(*) AS total FROM news_events")
        tr = one("SELECT count(*) FILTER (WHERE status='available') AS available, count(*) FILTER (WHERE status='error') AS error FROM news_item_translations WHERE field='title' AND target_language='fa'")
        by_cat = rows(f'''SELECT a.category_id, a.category_label, count(*) AS n FROM news_items n
            JOIN item_topic_assignments a ON a.item_id=n.item_id AND a.taxonomy_version=%(v)s
            WHERE {TS} >= now()-interval '24 hours' AND {TS} <= now() GROUP BY 1,2 ORDER BY 3 DESC''', {'v': TAXV})
        return {'items': a, 'hourly_48h': hourly, 'last_run': run, 'sources': src, 'events': ev,
                'translations': {**tr, 'total_items': a['total']}, 'categories_24h': by_cat,
                'collection_interval_seconds': 900, 'timezone_note': 'bucket boundaries in UTC'}

    @app.get('/api/v1/integrations')
    def integrations():
        data = rows('SELECT * FROM integrations ORDER BY kind, integration_id')
        ai = ai_state()
        for d in data:
            if d['integration_id'] == 'ai_translation':
                d['live_status'] = {'provider_not_configured': 'not_configured', 'provider_unavailable': 'blocked',
                                    'configured': 'configured'}[ai['status']]
                d['live_detail'] = ai
            elif d['integration_id'] == 'rss_collector':
                last = one('SELECT started_at, status FROM collection_runs ORDER BY started_at DESC LIMIT 1')
                d['live_status'] = 'active' if last and last['started_at'] >= datetime.now(timezone.utc) - timedelta(minutes=35) else 'stale'
                d['live_detail'] = last
            else:
                d['live_status'] = d['status']
        return {'integrations': data}

    def _integration(iid):
        return next((i for i in integrations()['integrations'] if i['integration_id'] == iid), None)

    @app.get('/api/v1/commodities')
    def commodities():
        obs = rows('''SELECT commodity_code, value, unit, currency, observed_at, provider, provider_url FROM commodity_prices
            ORDER BY commodity_code, observed_at DESC LIMIT 500''')
        return {'integration': _integration('commodity_prices'), 'observations': obs, 'total': len(obs)}

    @app.get('/api/v1/social')
    def social():
        reg = []
        p = METADATA_DIR / 'source-registry.json'
        if p.is_file():
            reg = [{'handle': x.get('x_handle') or x.get('display_value'), 'collection_status': x.get('collection_status'),
                    'enabled': x.get('enabled')} for x in json.loads(p.read_text(encoding='utf-8-sig'))
                   if x.get('source_type') == 'x_account']
        posts = rows('SELECT * FROM social_posts ORDER BY posted_at DESC LIMIT 50')
        return {'integration': _integration('x_social'), 'registered_accounts': reg, 'posts': posts, 'total_posts': len(posts)}

    @app.get('/api/v1/geo')
    def geo():
        pts = rows('''SELECT g.*, n.title FROM geo_mentions g LEFT JOIN news_items n USING (item_id)
            WHERE g.lat IS NOT NULL AND g.lon IS NOT NULL ORDER BY g.created_at DESC LIMIT 2000''')
        return {'integration': _integration('geolocation'), 'points': pts, 'total': len(pts),
                'layers_available': [], 'note_fa': 'مختصات فقط از استخراج دارای شواهد متنی ثبت می‌شود؛ هیچ نقطه حدسی ساخته نمی‌شود.'}

    @app.get('/api/v1/notifications')
    def notifications():
        out = []
        for s in rows("SELECT source_id, COALESCE(NULLIF(display_name,''),hostname) AS name, consecutive_failures, last_attempt_at FROM sources WHERE consecutive_failures > 0"):
            out.append({'kind': 'source_failure', 'severity': 'error' if s['consecutive_failures'] >= 3 else 'warning',
                        'title': f"{s['name']}: {s['consecutive_failures']} تلاش ناموفق پیاپی", 'at': s['last_attempt_at'],
                        'href': f"/sources/{s['source_id']}"})
        run = one('SELECT run_id, started_at, status, sources_failed FROM collection_runs ORDER BY started_at DESC LIMIT 1')
        if run and run['status'] not in ('succeeded', 'running'):
            out.append({'kind': 'run', 'severity': 'warning', 'title': f"آخرین چرخه گردآوری: {run['status']}",
                        'at': run['started_at'], 'href': '/monitoring'})
        if run and run['started_at'] < datetime.now(timezone.utc) - timedelta(minutes=35):
            out.append({'kind': 'run_stale', 'severity': 'error', 'title': 'بیش از ۳۵ دقیقه از آخرین چرخه گردآوری گذشته است',
                        'at': run['started_at'], 'href': '/monitoring'})
        for b in breaking(limit=5)['items']:
            if b.get('breaking'):
                out.append({'kind': 'breaking', 'severity': 'info', 'title': b['title_fa'] or b['title'],
                            'title_lang': 'fa' if b['title_fa'] else 'en', 'at': b['published_at'], 'href': f"/news/{b['item_id']}"})
        return {'notifications': out, 'total': len(out)}

    # ------------------------------------------------------------ insights
    @app.get('/api/v1/insights/overview')
    def insights():
        vol = rows(f'''SELECT date_trunc('day', {TS}) AS day, count(*) AS n, count(DISTINCT n.source_id) AS sources
            FROM news_items n WHERE {TS} >= now()-interval '30 days' AND {TS} <= now() GROUP BY 1 ORDER BY 1''')
        heat = rows(f'''SELECT extract(isodow FROM {TS} AT TIME ZONE 'Asia/Tehran')::int AS dow,
            extract(hour FROM {TS} AT TIME ZONE 'Asia/Tehran')::int AS h, count(*) AS n
            FROM news_items n WHERE {TS} >= now()-interval '30 days' AND {TS} <= now() GROUP BY 1,2''')
        matrix = rows('''SELECT n.source_id, COALESCE(NULLIF(s.display_name,''),s.hostname) AS source, a.category_id, count(*) AS n
            FROM news_items n JOIN sources s USING (source_id)
            JOIN item_topic_assignments a ON a.item_id=n.item_id AND a.taxonomy_version=%(v)s GROUP BY 1,2,3''', {'v': TAXV})
        change = rows(f'''SELECT a.category_id, a.category_label,
            count(*) FILTER (WHERE {TS} >= now()-interval '7 days') AS n7,
            count(*) FILTER (WHERE {TS} < now()-interval '7 days') AS p7
            FROM news_items n JOIN item_topic_assignments a ON a.item_id=n.item_id AND a.taxonomy_version=%(v)s
            WHERE {TS} >= now()-interval '14 days' AND {TS} <= now() GROUP BY 1,2 ORDER BY 3 DESC''', {'v': TAXV})
        tr = rows('''SELECT f.field, COALESCE(t.status,'pending') AS status, count(*) AS n FROM news_items n
            CROSS JOIN (VALUES ('title'),('summary')) f(field)
            LEFT JOIN news_item_translations t ON t.item_id=n.item_id AND t.field=f.field AND t.target_language='fa'
            GROUP BY 1,2 ORDER BY 1,2''')
        prov = rows('''SELECT COALESCE(NULLIF(s.display_name,''),s.hostname) AS source, n.provenance_status AS status, count(*) AS n
            FROM news_items n JOIN sources s USING (source_id) GROUP BY 1,2 ORDER BY 1''')
        velocity = rows('''SELECT date_trunc('day', first_published_at) AS day, count(*) AS events, sum(member_count) AS items
            FROM news_events WHERE first_published_at >= now()-interval '30 days' GROUP BY 1 ORDER BY 1''')
        conf = rows('''SELECT width_bucket(COALESCE(confidence,0), 0, 1, 10) AS bucket, count(*) AS n
            FROM item_topic_assignments WHERE taxonomy_version=%(v)s AND category_id <> 'other' GROUP BY 1 ORDER BY 1''', {'v': TAXV})
        activity_src = rows(f'''SELECT COALESCE(NULLIF(s.display_name,''),s.hostname) AS source, date_trunc('day', {TS}) AS day, count(*) AS n
            FROM news_items n JOIN sources s USING (source_id) WHERE {TS} >= now()-interval '14 days' AND {TS} <= now()
            GROUP BY 1,2 ORDER BY 2''')
        return {'volume_30d': vol, 'heatmap_30d': heat, 'heatmap_timezone': 'Asia/Tehran', 'source_topic': matrix,
                'topic_change_7d': change, 'translation_coverage': tr, 'provenance': prov, 'event_velocity_30d': velocity,
                'confidence_histogram': conf, 'source_activity_14d': activity_src, 'taxonomy_version': TAXV,
                'labels': c3.get().labels}

    # ------------------------------------------------------------ foresight (descriptive)
    @app.get('/api/v1/foresight/trends')
    def trends():
        cats = rows(f'''SELECT a.category_id, a.category_label, date_trunc('day', {TS}) AS day, count(*) AS n FROM news_items n
            JOIN item_topic_assignments a ON a.item_id=n.item_id AND a.taxonomy_version=%(v)s
            WHERE {TS} >= now()-interval '28 days' AND {TS} <= now() AND a.category_id <> 'other' GROUP BY 1,2,3 ORDER BY 3''', {'v': TAXV})
        subs = rows(f'''SELECT x->>'id' AS id, x->>'label' AS label,
            count(*) FILTER (WHERE {TS} >= now()-interval '7 days') AS n7,
            count(*) FILTER (WHERE {TS} < now()-interval '7 days' AND {TS} >= now()-interval '14 days') AS p7
            FROM news_items n JOIN item_topic_assignments a ON a.item_id=n.item_id AND a.taxonomy_version=%(v)s,
            jsonb_array_elements(a.subtopics) x WHERE {TS} >= now()-interval '14 days' AND {TS} <= now()
            GROUP BY 1,2 ORDER BY 3 DESC''', {'v': TAXV})
        for s in subs:
            s['momentum'] = s['n7'] - s['p7']
        return {'method_fa': 'مقایسه توصیفی حجم پوشش خبری در دو بازه ۷روزه. تغییر حجم پوشش به معنای تغییر در واقعیت یا پیش‌بینی آینده نیست.',
                'category_daily': cats, 'subtopic_momentum': subs}

    @app.get('/api/v1/foresight/weak-signals')
    def ws():
        return weak_signals(limit=40)

    @app.get('/api/v1/foresight/uncertainties')
    def uncertainties():
        low = rows('''SELECT a.item_id, n.title, a.category_label, a.confidence, a.secondary FROM item_topic_assignments a
            JOIN news_items n USING (item_id) WHERE a.taxonomy_version=%(v)s AND a.category_id <> 'other'
            AND jsonb_array_length(a.secondary) > 0 AND a.confidence < 0.6 ORDER BY n.published_at DESC NULLS LAST LIMIT 30''', {'v': TAXV})
        summary = one('''SELECT count(*) FILTER (WHERE category_id='other') AS other_n,
            count(*) FILTER (WHERE category_id<>'other' AND confidence < 0.5) AS low_conf,
            count(*) FILTER (WHERE jsonb_array_length(secondary) > 0) AS multi_topic, count(*) AS total
            FROM item_topic_assignments WHERE taxonomy_version=%(v)s''', {'v': TAXV})
        ev = one("SELECT count(*) FILTER (WHERE confidence_level='low') AS low, count(*) FILTER (WHERE confidence_level IS NULL) AS unknown, count(*) AS total FROM news_events")
        gaps = one("SELECT count(*) FILTER (WHERE summary_available IS NOT TRUE) AS no_summary, count(*) FILTER (WHERE published_at IS NULL) AS no_date, count(*) AS total FROM news_items")
        return {'scope_fa': 'این صفحه عدم‌قطعیت «داده و پردازش» را نشان می‌دهد: دسته‌بندی‌های کم‌اطمینان یا چندموضوعی، رویدادهای '
                            'کم‌اطمینان و شکاف‌های پوشش. عدم‌قطعیت‌های راهبردی (به معنای آینده‌پژوهی) نیازمند تحلیلگر است و ثبت نشده است.',
                'classification': summary, 'events': ev, 'coverage_gaps': gaps, 'ambiguous_items': low,
                'strategic_uncertainties': [], 'strategic_status': 'not_recorded'}

    @app.get('/api/v1/foresight/drivers')
    def drivers():
        steep = {'S': ['society_human_rights'], 'T': ['technology_cyber_ai', 'aerospace_maritime'],
                 'E': ['economy_trade_sanctions', 'energy_infrastructure', 'defense_industry'],
                 'En': ['environment_crisis'],
                 'P': ['politics_governance', 'diplomacy_international', 'regional_geopolitics', 'security_defense']}
        names = {'S': 'اجتماعی', 'T': 'فناورانه', 'E': 'اقتصادی', 'En': 'محیط‌زیستی', 'P': 'سیاسی'}
        counts = {r['category_id']: r for r in rows(f'''SELECT a.category_id, count(*) FILTER (WHERE {TS} >= now()-interval '30 days') AS n30,
            count(*) AS n FROM news_items n JOIN item_topic_assignments a ON a.item_id=n.item_id AND a.taxonomy_version=%(v)s GROUP BY 1''', {'v': TAXV})}
        labels = c3.get().labels
        out = [{'key': k, 'label': names[k], 'categories': [{'id': c, 'label': labels[c], 'n30': counts.get(c, {}).get('n30', 0),
                'total': counts.get(c, {}).get('n', 0)} for c in v]} for k, v in steep.items()]
        co = rows('''SELECT a.category_id AS a, x->>'id' AS b, count(*) AS n FROM item_topic_assignments a,
            jsonb_array_elements(a.secondary) x WHERE a.taxonomy_version=%(v)s GROUP BY 1,2''', {'v': TAXV})
        return {'scope_fa': 'نگاشت موضوعات پوشش خبری به چارچوب STEEP و هم‌رخدادی موضوعات در یک خبر. این نگاشت شناسایی پیشران '
                            'نیست؛ تعیین پیشران‌ها و اثر متقابل آن‌ها قضاوت تحلیلگر است و هنوز ثبت نشده است.',
                'steep': out, 'co_occurrence': co, 'labels': labels, 'drivers': [], 'drivers_status': 'not_recorded'}

    @app.get('/api/v1/foresight/scenarios')
    def scenarios():
        return {'scenarios': [], 'status': 'not_recorded', 'ai': ai_state(),
                'scope_fa': 'سناریونویسی نیازمند پیشران‌های تأییدشده تحلیلگر و در صورت استفاده از هوش مصنوعی، شواهد قابل پیگیری است. '
                            'هیچ سناریویی ثبت نشده و هیچ سناریوی نمایشی تولید نمی‌شود.'}

    @app.get('/api/v1/alerts')
    def alerts():
        rules_ = rows('SELECT * FROM alert_rules ORDER BY created_at DESC')
        return {'rules': rules_, 'integration': _integration('alerts'), 'system_notifications': notifications()['notifications']}

    return app

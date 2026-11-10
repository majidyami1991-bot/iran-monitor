"""X-FREE: manual monitoring of the 36 X accounts in the source registry.

Nothing here talks to X. There is no official API client, no scraper, no
headless browser, no cookie or session, and no scheduler. An analyst
registers the URL of one specific post (optionally with its text, entered by
hand); this module validates the URL against the registry, stores it with
explicit provenance, and keeps an append-only history of every change.

Writes are off unless SOCIAL_MANUAL_INGEST_ENABLED=true (preview only), and
every write needs a same-origin CSRF token. Optional AI actions run only when
an analyst asks for them, and only on text the analyst entered.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
from fastapi import Header, HTTPException, Query
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field

DSN = os.environ['DATABASE_URL']
METADATA_DIR = Path(os.getenv('COLLECTOR_METADATA_DIR', '/app/sources'))
MANIFEST = 'x-free-readiness.json'

# Exact hosts only: a look-alike (x.com.evil.io, twitter.co, xcom.io) or a
# shortener (t.co) never matches, because nothing here does suffix matching.
ALLOWED_HOSTS = frozenset(('x.com', 'www.x.com', 'mobile.x.com', 'twitter.com', 'www.twitter.com', 'mobile.twitter.com'))
MEDIA_HOSTS = frozenset(('pbs.twimg.com', 'video.twimg.com'))
_PATH = re.compile(r'^/([A-Za-z0-9_]{1,15})/status/(\d{5,25})/?$')
IMPORTANCE = ('high', 'medium', 'low')
VERIFICATION = ('unverified', 'verified', 'disputed', 'false')
AVAILABILITY = ('link_only', 'text_recorded', 'withdrawn', 'unavailable')
TEXT_MAX, NOTE_MAX = 4000, 2000
_CONTROL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
_ANALYST = re.compile(r'^[\w؀-ۿ‌ .\-]{2,60}$')

CSRF_TTL_SECONDS = 2 * 3600
_CSRF_KEY = secrets.token_bytes(32)  # per process; never leaves the server


class SocialError(ValueError):
    """Carries a stable machine-readable code for the API and the tests."""


# ------------------------------------------------------------------ pure helpers (unit-tested)
def ingest_enabled():
    return (os.getenv('SOCIAL_MANUAL_INGEST_ENABLED') or 'false').strip().lower() == 'true'


def load_manifest(path=None):
    p = path or (METADATA_DIR / MANIFEST)
    if not p.is_file():
        local = Path(__file__).resolve().parents[2] / 'config' / 'sources' / MANIFEST
        p = local if local.is_file() else p
    return json.loads(p.read_text(encoding='utf-8-sig'))


def validate_x_url(url, known_handle_keys):
    """Return (canonical_url, handle_key, post_id) or raise SocialError.
    Deterministic: the post id is the numeric path segment, nothing else."""
    if not isinstance(url, str) or not url.strip() or len(url) > 300:
        raise SocialError('url_missing_or_too_long')
    u = url.strip()
    try:
        p = urlsplit(u)
    except ValueError as exc:
        raise SocialError('url_unparseable') from exc
    if p.scheme != 'https':
        raise SocialError('url_not_https')
    if p.username or p.password or p.port:
        raise SocialError('url_has_credentials_or_port')
    host = (p.hostname or '').lower()
    if host not in ALLOWED_HOSTS:
        raise SocialError('url_host_not_x')
    m = _PATH.match(p.path)
    if not m:
        raise SocialError('url_not_a_status_link')
    handle, post_id = m.group(1), m.group(2)
    key = '@' + handle.lower()
    if key not in known_handle_keys:
        raise SocialError('handle_not_in_registry')
    return f'https://x.com/{handle}/status/{post_id}', key, post_id


def clean_text(value, limit, field):
    if value is None:
        return None
    if not isinstance(value, str):
        raise SocialError(f'{field}_not_text')
    v = value.strip()
    if not v:
        return None
    if _CONTROL.search(v):
        raise SocialError(f'{field}_control_characters')
    if len(v) > limit:
        raise SocialError(f'{field}_too_long')
    return v  # stored as plain text; the UI renders it as text, never as HTML


def parse_published(value, now=None):
    if value in (None, ''):
        return None
    now = now or datetime.now(timezone.utc)
    try:
        d = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError as exc:
        raise SocialError('published_at_invalid') from exc
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    if d > now + timedelta(days=1) or d.year < 2006:
        raise SocialError('published_at_out_of_range')
    return d


def validate_media(items):
    out = []
    for m in items or []:
        url = (m or {}).get('external_url') or ''
        p = urlsplit(url)
        if p.scheme != 'https' or (p.hostname or '').lower() not in MEDIA_HOSTS or p.username or p.port:
            raise SocialError('media_url_not_x_cdn')
        kind = (m or {}).get('media_type')
        if kind not in ('image', 'video'):
            raise SocialError('media_type_invalid')
        out.append({'media_type': kind, 'external_url': url,
                    'alt_text': clean_text((m or {}).get('alt_text'), 500, 'alt_text')})
    if len(out) > 4:
        raise SocialError('media_too_many')
    return out


def make_csrf_token(now=None):
    ts = str(int(now if now is not None else time.time()))
    sig = hmac.new(_CSRF_KEY, ts.encode(), hashlib.sha256).hexdigest()
    return f'{ts}.{sig}'


def verify_csrf_token(token, now=None):
    if not token or '.' not in token:
        return False
    ts, sig = token.split('.', 1)
    if not ts.isdigit():
        return False
    good = hmac.new(_CSRF_KEY, ts.encode(), hashlib.sha256).hexdigest()
    age = (now if now is not None else time.time()) - int(ts)
    return hmac.compare_digest(sig, good) and 0 <= age <= CSRF_TTL_SECONDS


def build_provenance(analyst, has_text, now=None):
    now = now or datetime.now(timezone.utc)
    return {
        'collection': 'manual', 'fetched_from_x': False, 'official_api': False,
        'registered_via': 'manual_form', 'registered_by': analyst, 'registered_at': now.isoformat(),
        'url_source': 'analyst_entered',
        'text_source': 'analyst_entered' if has_text else 'not_recorded',
        'text_is_x_api_output': False,
        'note_fa': ('متن این پست توسط تحلیلگر وارد شده است و خروجی مستقیم X نیست.' if has_text
                    else 'متن محلی ثبت نشده است؛ فقط پیوند رسمی پست نگه داشته می‌شود.'),
    }


# ------------------------------------------------------------------ db helpers
def _rows(sql, args=None):
    with psycopg.connect(DSN, row_factory=dict_row) as c:
        return c.execute(sql, args or {}).fetchall()


def _one(sql, args=None):
    r = _rows(sql, args)
    return r[0] if r else None


def seed_accounts():
    """Insert-only: an account row once created is never overwritten here."""
    m = load_manifest()
    with psycopg.connect(DSN) as c:
        for a in m['accounts']:
            c.execute('''INSERT INTO x_accounts(source_id,handle,handle_key,profile_url,monitoring_mode,status,provenance_json)
                VALUES(%s,%s,%s,%s,'manual','manual_monitoring',%s) ON CONFLICT(source_id) DO NOTHING''',
                      (a['source_id'], a['handle'], a['handle_key'], a['canonical_profile_url'], Jsonb(a['provenance'])))
    return len(m['accounts'])


def _known_keys():
    return {r['handle_key']: r['source_id'] for r in _rows('SELECT handle_key, source_id FROM x_accounts')}


def _refresh_account(c, source_id):
    c.execute('''UPDATE x_accounts SET post_count=(SELECT count(*) FROM x_posts WHERE source_id=%(s)s AND availability_status<>'withdrawn'),
        last_manual_post_at=(SELECT max(manually_registered_at) FROM x_posts WHERE source_id=%(s)s AND availability_status<>'withdrawn'),
        updated_at=now() WHERE source_id=%(s)s''', {'s': source_id})


def _history(c, post_id, action, before, after, actor):
    c.execute('''INSERT INTO x_post_history(post_id,action,previous_value_json,new_value_json,actor)
        VALUES(%s,%s,%s,%s,%s)''', (post_id, action, Jsonb(before) if before is not None else None,
                                     Jsonb(after) if after is not None else None, actor))


def _jsonable(d):
    return json.loads(json.dumps(d, default=lambda o: o.isoformat() if hasattr(o, 'isoformat') else str(o)))


def _topic_ok(topic_id):
    if not topic_id:
        return True
    import classify_v3 as c3
    tax = c3.get().tax
    ids = {c['id'] for c in tax['categories']} | {s['id'] for c in tax['categories'] for s in c.get('subtopics', [])}
    return topic_id in ids


def _require_write(csrf, origin):
    if not ingest_enabled():
        raise HTTPException(403, 'manual_ingest_disabled')
    allowed = [o.strip() for o in (os.getenv('SOCIAL_ALLOWED_ORIGINS') or 'http://127.0.0.1:3002,http://localhost:3002').split(',') if o.strip()]
    if origin not in allowed:
        # The web proxy always sets this from the browser's Origin header; a
        # missing or foreign origin is refused.
        raise HTTPException(403, 'origin_not_allowed')
    if not verify_csrf_token(csrf):
        raise HTTPException(403, 'csrf_token_invalid')


class MediaIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    media_type: str
    external_url: str
    alt_text: str | None = None


class ManualPostIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    url: str
    analyst: str
    original_text: str | None = None
    published_at: str | None = None
    topic_id: str | None = None
    importance: str = 'medium'
    analyst_note: str | None = None
    event_id: str | None = None
    related_item_id: str | None = None
    verification_status: str = 'unverified'
    media: list[MediaIn] = Field(default_factory=list)
    dry_run: bool = False  # the form's "preview before saving"


class ManualPostPatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    analyst: str
    original_text: str | None = None
    published_at: str | None = None
    topic_id: str | None = None
    importance: str | None = None
    analyst_note: str | None = None
    event_id: str | None = None
    related_item_id: str | None = None
    verification_status: str | None = None
    availability_status: str | None = None


class AiActionIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    analyst: str
    action: str


POST_COLS = '''p.post_id, p.source_id, p.post_url, p.author_handle, p.original_text, p.translated_text_fa, p.summary_fa,
  p.published_at, p.manually_registered_at, p.topic_id, p.event_id, p.related_item_id, p.analyst_note, p.importance,
  p.verification_status, p.availability_status, p.provenance_json, p.created_at, p.updated_at,
  a.profile_url, a.display_name, e.title AS event_title, n.title AS related_item_title,
  CASE WHEN t.id IS NULL THEN NULL ELSE json_build_object(
    'status', t.status, 'source_language', t.source_language, 'provider', t.provider, 'model', t.model,
    'prompt_version', t.prompt_version, 'quality_score', t.quality_score, 'quality_flags', t.quality_flags_json,
    'latency_ms', t.latency_ms, 'translated_at', t.translated_at, 'reviewed_at', t.reviewed_at,
    'reviewed_by', t.reviewed_by, 'updated_at', t.updated_at,
    'translated_text', CASE WHEN t.status = 'available' THEN t.translated_text END) END AS translation'''
# Only an `available` local translation's text leaves the database; a
# needs_review candidate is never sent to the public UI.
POST_FROM = '''FROM x_posts p JOIN x_accounts a USING (source_id)
  LEFT JOIN news_events e ON e.event_id = p.event_id LEFT JOIN news_items n ON n.item_id = p.related_item_id
  LEFT JOIN x_post_translations t ON t.x_post_id = p.post_id AND t.target_language = 'fa'
'''


def _check_analyst(name):
    if not name or not _ANALYST.match(name.strip()):
        raise HTTPException(422, 'analyst_name_invalid')
    return name.strip()


def _check_links(event_id, item_id):
    if event_id and not _one('SELECT 1 AS x FROM news_events WHERE event_id=%(e)s', {'e': event_id}):
        raise HTTPException(422, 'event_not_found')
    if item_id and not _one('SELECT 1 AS x FROM news_items WHERE item_id=%(i)s', {'i': item_id}):
        raise HTTPException(422, 'news_item_not_found')


def _err(exc):
    return HTTPException(422, str(exc))


# ------------------------------------------------------------------ API
def register_social(app):
    @app.on_event('startup')
    def _seed():
        seed_accounts()

    @app.get('/api/v1/social/status')
    def status():
        m = load_manifest()
        counts = _one('''SELECT (SELECT count(*) FROM x_accounts) AS accounts,
            (SELECT count(*) FROM x_posts WHERE availability_status<>'withdrawn') AS posts''')
        integ = _one("SELECT status, reason_fa FROM integrations WHERE integration_id='x_social'")
        return {'mode': 'manual', 'official_api': False, 'scraping': False, 'scheduler': False,
                'manual_ingest_enabled': ingest_enabled(), 'manifest_version': m['version'],
                'manifest_summary': m['summary'], 'accounts': counts['accounts'], 'posts': counts['posts'],
                'integration': integ,
                'embed': {'provider': 'X official embed (platform.twitter.com)', 'loads': 'on_click_only',
                          'used_as_data_source': False}}

    @app.get('/api/v1/social/csrf')
    def csrf():
        if not ingest_enabled():
            raise HTTPException(403, 'manual_ingest_disabled')
        return {'token': make_csrf_token(), 'expires_in': CSRF_TTL_SECONDS}

    @app.get('/api/v1/social/accounts')
    def accounts():
        data = _rows('''SELECT source_id, handle, display_name, profile_url, description, category, monitoring_mode, status,
            last_manual_post_at, post_count, provenance_json FROM x_accounts ORDER BY post_count DESC, lower(handle)''')
        return {'accounts': data, 'total': len(data)}

    @app.get('/api/v1/social/accounts/{source_id}')
    def account(source_id: str):
        a = _one('SELECT * FROM x_accounts WHERE source_id=%(s)s', {'s': source_id})
        if not a:
            raise HTTPException(404, 'account_not_found')
        a['posts'] = _rows(f'SELECT {POST_COLS} {POST_FROM} WHERE p.source_id=%(s)s ORDER BY p.manually_registered_at DESC LIMIT 100',
                           {'s': source_id})
        return a

    @app.get('/api/v1/social/posts')
    def posts(source_id: str | None = None, topic: str | None = None, date_from: str | None = None,
              date_to: str | None = None, importance: str | None = None, verification: str | None = None,
              has_translation: bool | None = None, has_event: bool | None = None, include_withdrawn: bool = False,
              page: int = Query(1, ge=1, le=1000), page_size: int = Query(20, ge=1, le=100)):
        w, a = [], {}
        if not include_withdrawn:
            w.append("p.availability_status <> 'withdrawn'")
        if source_id:
            w.append('p.source_id = %(source_id)s'); a['source_id'] = source_id
        if topic:
            w.append('p.topic_id = %(topic)s'); a['topic'] = topic
        for name, val, op in (('date_from', date_from, '>='), ('date_to', date_to, '<')):
            if val:
                try:
                    datetime.strptime(val, '%Y-%m-%d')
                except ValueError:
                    raise HTTPException(422, 'invalid_date')
                expr = '%(' + name + ')s::date' + (" + interval '1 day'" if name == 'date_to' else '')
                w.append(f'COALESCE(p.published_at, p.manually_registered_at) {op} {expr}'); a[name] = val
        if importance:
            if importance not in IMPORTANCE:
                raise HTTPException(422, 'invalid_importance')
            w.append('p.importance = %(importance)s'); a['importance'] = importance
        if verification:
            if verification not in VERIFICATION:
                raise HTTPException(422, 'invalid_verification')
            w.append('p.verification_status = %(verification)s'); a['verification'] = verification
        if has_translation is not None:
            has = ("(p.translated_text_fa IS NOT NULL OR EXISTS (SELECT 1 FROM x_post_translations xt "
                   "WHERE xt.x_post_id = p.post_id AND xt.status = 'available'))")
            w.append(has if has_translation else 'NOT ' + has)
        if has_event is not None:
            w.append('p.event_id IS ' + ('NOT NULL' if has_event else 'NULL'))
        where = (' WHERE ' + ' AND '.join(w)) if w else ''
        total = _one(f'SELECT count(*) AS n FROM x_posts p{where}', a)['n']
        data = _rows(f'''SELECT {POST_COLS} {POST_FROM}{where}
            ORDER BY COALESCE(p.published_at, p.manually_registered_at) DESC, p.post_id DESC
            LIMIT %(l)s OFFSET %(o)s''', {**a, 'l': page_size, 'o': (page - 1) * page_size})
        return {'posts': data, 'total': total, 'page': page, 'page_size': page_size, 'has_next': page * page_size < total}

    @app.get('/api/v1/social/posts/{post_id}')
    def post(post_id: str):
        p = _one(f'SELECT {POST_COLS} {POST_FROM} WHERE p.post_id=%(p)s', {'p': post_id})
        if not p:
            raise HTTPException(404, 'post_not_found')
        p['media'] = _rows('SELECT media_type, external_url, alt_text, provenance_json FROM x_post_media WHERE post_id=%(p)s ORDER BY id', {'p': post_id})
        p['history'] = _rows('SELECT action, previous_value_json, new_value_json, actor, created_at FROM x_post_history WHERE post_id=%(p)s ORDER BY id', {'p': post_id})
        return p

    @app.get('/api/v1/social/stats')
    def stats():
        s = _one('''SELECT (SELECT count(*) FROM x_accounts) AS accounts,
            (SELECT count(*) FROM x_posts WHERE availability_status<>'withdrawn') AS posts,
            (SELECT count(*) FROM x_posts WHERE availability_status<>'withdrawn'
               AND (manually_registered_at AT TIME ZONE 'Asia/Tehran')::date = (now() AT TIME ZONE 'Asia/Tehran')::date) AS posts_today,
            (SELECT count(*) FROM x_accounts WHERE post_count = 0) AS accounts_without_posts,
            (SELECT count(DISTINCT topic_id) FROM x_posts WHERE topic_id IS NOT NULL AND availability_status<>'withdrawn'
               AND manually_registered_at >= now() - interval '7 days') AS active_topics_7d,
            (SELECT max(manually_registered_at) FROM x_posts) AS last_registered_at,
            (SELECT count(*) FROM x_posts xp WHERE translated_text_fa IS NOT NULL OR EXISTS (SELECT 1 FROM x_post_translations xt
               WHERE xt.x_post_id = xp.post_id AND xt.status = 'available')) AS translated,
            (SELECT count(*) FROM x_posts WHERE event_id IS NOT NULL) AS with_event''')
        s['by_importance'] = _rows("SELECT importance, count(*) AS n FROM x_posts WHERE availability_status<>'withdrawn' GROUP BY 1")
        s['by_verification'] = _rows("SELECT verification_status, count(*) AS n FROM x_posts WHERE availability_status<>'withdrawn' GROUP BY 1")
        return s

    @app.post('/api/v1/social/manual-posts')
    def create(body: ManualPostIn, x_im_csrf: str | None = Header(None), x_im_origin: str | None = Header(None)):
        _require_write(x_im_csrf, x_im_origin)
        analyst = _check_analyst(body.analyst)
        try:
            url, key, post_id = validate_x_url(body.url, _known_keys().keys())
            text = clean_text(body.original_text, TEXT_MAX, 'original_text')
            note = clean_text(body.analyst_note, NOTE_MAX, 'analyst_note')
            published = parse_published(body.published_at)
            media = validate_media([m.model_dump() for m in body.media])
        except SocialError as exc:
            raise _err(exc)
        if body.importance not in IMPORTANCE:
            raise HTTPException(422, 'invalid_importance')
        if body.verification_status not in VERIFICATION:
            raise HTTPException(422, 'invalid_verification')
        if not _topic_ok(body.topic_id):
            raise HTTPException(422, 'unknown_topic')
        _check_links(body.event_id, body.related_item_id)
        existing = _one('SELECT post_id FROM x_posts WHERE post_id=%(p)s OR post_url=%(u)s', {'p': post_id, 'u': url})
        if existing:
            raise HTTPException(409, 'duplicate_post')
        source_id = _known_keys()[key]
        handle = _one('SELECT handle FROM x_accounts WHERE source_id=%(s)s', {'s': source_id})['handle']
        prov = build_provenance(analyst, bool(text))
        record = {'post_id': post_id, 'source_id': source_id, 'post_url': url, 'author_handle': handle,
                  'original_text': text, 'published_at': published, 'topic_id': body.topic_id,
                  'event_id': body.event_id, 'related_item_id': body.related_item_id, 'analyst_note': note,
                  'importance': body.importance, 'verification_status': body.verification_status,
                  'availability_status': 'text_recorded' if text else 'link_only', 'provenance_json': prov,
                  'media': media}
        if body.dry_run:
            return {'dry_run': True, 'would_create': _jsonable(record)}
        with psycopg.connect(DSN) as c:
            try:
                c.execute('''INSERT INTO x_posts(post_id,source_id,post_url,author_handle,original_text,published_at,topic_id,
                    event_id,related_item_id,analyst_note,importance,verification_status,availability_status,provenance_json)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                          (post_id, source_id, url, handle, text, published, body.topic_id, body.event_id,
                           body.related_item_id, note, body.importance, body.verification_status,
                           record['availability_status'], Jsonb(prov)))
            except psycopg.errors.UniqueViolation:
                raise HTTPException(409, 'duplicate_post')
            for m in media:
                c.execute('INSERT INTO x_post_media(post_id,media_type,external_url,alt_text,provenance_json) VALUES(%s,%s,%s,%s,%s)',
                          (post_id, m['media_type'], m['external_url'], m['alt_text'],
                           Jsonb({'source': 'analyst_entered', 'registered_by': analyst})))
            _history(c, post_id, 'created', None, _jsonable({k: v for k, v in record.items() if k != 'provenance_json'}), analyst)
            _refresh_account(c, source_id)
        return post(post_id)

    @app.patch('/api/v1/social/manual-posts/{post_id}')
    def update(post_id: str, body: ManualPostPatch, x_im_csrf: str | None = Header(None), x_im_origin: str | None = Header(None)):
        _require_write(x_im_csrf, x_im_origin)
        analyst = _check_analyst(body.analyst)
        before = _one('SELECT * FROM x_posts WHERE post_id=%(p)s', {'p': post_id})
        if not before:
            raise HTTPException(404, 'post_not_found')
        changes = {}
        data = body.model_dump(exclude_unset=True)
        data.pop('analyst', None)
        try:
            if 'original_text' in data:
                changes['original_text'] = clean_text(data['original_text'], TEXT_MAX, 'original_text')
            if 'analyst_note' in data:
                changes['analyst_note'] = clean_text(data['analyst_note'], NOTE_MAX, 'analyst_note')
            if 'published_at' in data:
                changes['published_at'] = parse_published(data['published_at'])
        except SocialError as exc:
            raise _err(exc)
        for key, allowed in (('importance', IMPORTANCE), ('verification_status', VERIFICATION), ('availability_status', AVAILABILITY)):
            if key in data and data[key] is not None:
                if data[key] not in allowed:
                    raise HTTPException(422, f'invalid_{key}')
                changes[key] = data[key]
        if 'topic_id' in data:
            if not _topic_ok(data['topic_id']):
                raise HTTPException(422, 'unknown_topic')
            changes['topic_id'] = data['topic_id'] or None
        if 'event_id' in data or 'related_item_id' in data:
            _check_links(data.get('event_id'), data.get('related_item_id'))
            for k in ('event_id', 'related_item_id'):
                if k in data:
                    changes[k] = data[k] or None
        if 'original_text' in changes:
            prov = dict(before['provenance_json'])
            prov['text_source'] = 'analyst_entered' if changes['original_text'] else 'not_recorded'
            prov['text_updated_by'] = analyst
            changes['provenance_json'] = prov
            if 'availability_status' not in changes and before['availability_status'] in ('link_only', 'text_recorded'):
                changes['availability_status'] = 'text_recorded' if changes['original_text'] else 'link_only'
        changes = {k: v for k, v in changes.items() if before.get(k) != v}
        if not changes:
            return post(post_id)
        sets = ', '.join(f'{k}=%({k})s' for k in changes)
        params = {k: (Jsonb(v) if k == 'provenance_json' else v) for k, v in changes.items()}
        with psycopg.connect(DSN) as c:
            c.execute(f'UPDATE x_posts SET {sets}, updated_at=now() WHERE post_id=%(post_id)s', {**params, 'post_id': post_id})
            action = 'availability_changed' if set(changes) == {'availability_status'} else 'updated'
            _history(c, post_id, action, _jsonable({k: before.get(k) for k in changes}), _jsonable(changes), analyst)
            _refresh_account(c, before['source_id'])
        if 'original_text' in changes:
            # DB only: the local translation of the old text becomes stale at once.
            import x_translate_worker as xw
            with xw.connect(DSN) as conn:
                xw.reconcile(conn, [post_id])
        return post(post_id)

    @app.post('/api/v1/social/posts/{post_id}/ai')
    def ai_action(post_id: str, body: AiActionIn, x_im_csrf: str | None = Header(None), x_im_origin: str | None = Header(None)):
        """Runs only on an analyst's request, only on analyst-entered text.
        The result is labelled and written to the history."""
        _require_write(x_im_csrf, x_im_origin)
        analyst = _check_analyst(body.analyst)
        p = _one('SELECT * FROM x_posts WHERE post_id=%(p)s', {'p': post_id})
        if not p:
            raise HTTPException(404, 'post_not_found')
        if not p['original_text']:
            raise HTTPException(422, 'no_analyst_text_recorded')
        result = run_ai_action(body.action, p)
        with psycopg.connect(DSN) as c:
            prov = dict(p['provenance_json'])
            prov.setdefault('ai', {})[body.action] = result['audit']
            updates = {'provenance_json': Jsonb(prov)}
            if result.get('field') and result.get('value') is not None:
                updates[result['field']] = result['value']
            sets = ', '.join(f'{k}=%({k})s' for k in updates)
            c.execute(f'UPDATE x_posts SET {sets}, updated_at=now() WHERE post_id=%(post_id)s', {**updates, 'post_id': post_id})
            _history(c, post_id, 'ai_' + body.action, None, _jsonable(result['audit']), analyst)
        return {'action': body.action, 'status': result['audit']['status'], 'audit': result['audit'], 'post': post(post_id)}

    register_translation(app)
    return app


# ------------------------------------------------------------------ local X translation (Ollama)
_PROBE = {'at': 0.0, 'value': (False, False, None)}
_PROBE_TTL = 30.0


def _probe(s):
    """Cached Ollama /api/tags probe (no generation, local host only)."""
    import x_translate_worker as xw
    now = time.monotonic()
    if now - _PROBE['at'] > _PROBE_TTL:
        _PROBE['value'] = xw.ollama_probe(s, timeout=2)
        _PROBE['at'] = now
    return _PROBE['value']


def admin_token_ok(token):
    expected = (os.getenv('SOCIAL_ADMIN_TOKEN') or '').strip()
    if len(expected) < 24:
        return False  # not configured (or too weak): admin writes stay closed
    return bool(token) and hmac.compare_digest(token.strip().encode(), expected.encode())


def _require_admin(admin, csrf, origin, need_csrf=True):
    if not admin_token_ok(admin):
        raise HTTPException(403, 'admin_required')
    allowed = [o.strip() for o in (os.getenv('SOCIAL_ALLOWED_ORIGINS') or 'http://127.0.0.1:3002,http://localhost:3002').split(',') if o.strip()]
    if origin not in allowed:
        raise HTTPException(403, 'origin_not_allowed')
    if need_csrf and not verify_csrf_token(csrf):
        raise HTTPException(403, 'csrf_token_invalid')


class RunBatchIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    limit: int = Field(3, ge=1, le=50)


TRANSLATION_PUBLIC_FIELDS = '''x_post_id, status, source_language, target_language, provider, model, prompt_version,
  quality_score, quality_flags_json AS quality_flags, attempt_count, latency_ms, last_error, translated_at,
  reviewed_at, reviewed_by, created_at, updated_at,
  CASE WHEN status = 'available' THEN translated_text END AS translated_text'''


def register_translation(app):
    import x_translate_worker as xw

    @app.get('/api/v1/social/translation/status')
    def translation_status():
        s = xw.load_settings()
        reachable, found, digest = _probe(s)
        with xw.connect(DSN) as conn:
            running = xw.worker_running(conn)
        return {'mode': 'offline_batch', 'realtime': False, 'scheduler': False, 'provider': 'ollama/local',
                'configured_model': s.model or None, 'prompt_version': xw.PROMPT_VERSION, 'enabled': s.enabled,
                'ollama_reachable': reachable, 'model_found': found, 'model_digest': digest,
                'concurrency': s.concurrency, 'batch_size': s.batch_size, 'max_attempts': s.max_attempts,
                'timeout_seconds': s.timeout_seconds, 'worker_running': running, 'config_errors': s.errors,
                'external_providers': False, 'cost_usd': 0}

    @app.get('/api/v1/social/translations/stats')
    def translation_stats():
        s = xw.load_settings()
        reachable, _, _ = _probe(s)
        with xw.connect(DSN) as conn:
            c = xw.counts(conn)
            running = xw.worker_running(conn)
        return {**c, 'ollama_reachable': reachable, 'configured_model': s.model or None, 'worker_running': running}

    @app.get('/api/v1/social/posts/{post_id}/translation')
    def post_translation(post_id: str):
        if not _one('SELECT 1 AS x FROM x_posts WHERE post_id=%(p)s', {'p': post_id}):
            raise HTTPException(404, 'post_not_found')
        t = _one(f"SELECT {TRANSLATION_PUBLIC_FIELDS} FROM x_post_translations WHERE x_post_id=%(p)s AND target_language='fa'",
                 {'p': post_id})
        hist = _rows('''SELECT status, provider, model, prompt_version, source_text_hash, quality_flags_json AS quality_flags,
            created_at FROM x_post_translation_history WHERE x_post_id=%(p)s ORDER BY history_id''', {'p': post_id})
        return {'post_id': post_id, 'translation': t, 'history': hist}

    @app.post('/api/v1/social/translations/csrf')
    def translation_csrf(x_im_admin: str | None = Header(None), x_im_origin: str | None = Header(None)):
        _require_admin(x_im_admin, None, x_im_origin, need_csrf=False)
        return {'token': make_csrf_token(), 'expires_in': CSRF_TTL_SECONDS}

    @app.post('/api/v1/social/posts/{post_id}/translation/enqueue')
    def translation_enqueue(post_id: str, x_im_admin: str | None = Header(None), x_im_csrf: str | None = Header(None),
                            x_im_origin: str | None = Header(None)):
        """DB only: (re)queues one post by its internal id; never calls the model."""
        _require_admin(x_im_admin, x_im_csrf, x_im_origin)
        p = _one('SELECT post_id, original_text, availability_status FROM x_posts WHERE post_id=%(p)s', {'p': post_id})
        if not p:
            raise HTTPException(404, 'post_not_found')
        if not (p['original_text'] or '').strip() or p['availability_status'] == 'withdrawn':
            raise HTTPException(422, 'no_analyst_text_recorded')
        with xw.connect(DSN) as conn:
            xw.reconcile(conn, [post_id])
            conn.execute('''UPDATE x_post_translations SET status='pending', attempt_count=0, last_error=NULL, updated_at=now()
                WHERE x_post_id=%s AND status IN ('failed','needs_review')''', (post_id,))
        return post_translation(post_id)

    @app.post('/api/v1/social/translations/run-batch', status_code=202)
    def translation_run_batch(body: RunBatchIn, x_im_admin: str | None = Header(None), x_im_csrf: str | None = Header(None),
                              x_im_origin: str | None = Header(None)):
        """Starts one bounded batch in the background and returns at once;
        the request never waits for a translation."""
        _require_admin(x_im_admin, x_im_csrf, x_im_origin)
        s = xw.load_settings()
        if s.errors:
            raise HTTPException(409, 'configuration_error')
        if not s.enabled:
            raise HTTPException(409, 'x_translation_disabled')
        with xw.connect(DSN) as conn:
            if xw.worker_running(conn):
                raise HTTPException(409, 'worker_already_running')

        def _run():
            try:
                rep = xw.run_batch(DSN, s, limit=body.limit)
                xw.LOG.info('api batch finished: %s', json.dumps(rep.as_dict(), default=str))
            except Exception as exc:  # a background batch must never take the API down
                xw.LOG.error('api batch failed: %s', type(exc).__name__)

        threading.Thread(target=_run, name='x-translate-batch', daemon=True).start()
        return {'started': True, 'limit': body.limit, 'concurrency': 1}


# ------------------------------------------------------------------ AI actions
AI_ACTIONS = ('translate', 'summarize', 'classify', 'entities', 'suggest_event')


def run_ai_action(action, p, gateway=None):
    """Returns {'field': column or None, 'value': ..., 'audit': {...}}.
    translate/summarize call the AI gateway (free-only guard applies);
    classify/entities/suggest_event are deterministic rules and say so."""
    now = datetime.now(timezone.utc).isoformat()
    text = p['original_text']
    if action not in AI_ACTIONS:
        raise HTTPException(422, 'unknown_action')
    if action == 'translate':
        # X post translation runs only through the local offline batch
        # (x_translate_worker, Ollama on this machine); never an external provider.
        raise HTTPException(422, 'translation_is_local_batch_only')
    if action in ('translate', 'summarize'):
        import ai_gateway as gw
        import content_intelligence as ci
        import content_validator as cv
        g = gateway or gw.build_default_gateway(DSN)
        r = ci.translate_to_persian(text, gateway=g) if action == 'translate' else ci._run_validated(
            g, 'summary', text, cv.validate_summary)
        ok = r['status'] in ('available', 'cached') and (r.get('validation') or {}).get('passed', False)
        audit = {'kind': 'ai', 'status': 'available' if ok else ('needs_review' if r['status'] in ('available', 'cached') else r['status']),
                 'provider': r.get('provider'), 'model': r.get('model'), 'response_model': r.get('response_model'),
                 'prompt_version': r.get('prompt_version'), 'reported_cost_usd': r.get('reported_cost_usd'),
                 'validation': r.get('validation'), 'error': (r.get('error') or '')[:120] or None, 'at': now,
                 'label_fa': 'تولیدشده با هوش مصنوعی · بازبینی انسانی نشده'}
        return {'field': ('translated_text_fa' if action == 'translate' else 'summary_fa') if ok else None,
                'value': r['text'] if ok else None, 'audit': audit}
    if action == 'classify':
        import classify_v3 as c3
        res = c3.classify(text, '')
        return {'field': None, 'value': None, 'audit': {
            'kind': 'rule', 'rule': 'taxonomy ' + res.taxonomy_version, 'status': 'suggested', 'at': now,
            'suggested_topic': res.category_id, 'suggested_label': res.category_label, 'confidence': res.confidence,
            'evidence': res.evidence, 'label_fa': 'پیشنهاد قاعده‌محور؛ موضوع ثبت‌شده تحلیلگر تغییر نمی‌کند'}}
    import clustering_v2 as cl2
    names = sorted(cl2._capitalised(text))
    if action == 'entities':
        return {'field': None, 'value': None, 'audit': {
            'kind': 'rule', 'rule': 'capitalised-name extraction (clustering v2 tokenizer)', 'status': 'suggested',
            'at': now, 'entities': names, 'label_fa': 'استخراج قاعده‌محور نام‌ها؛ نیازمند بازبینی'}}
    # suggest_event: events whose member titles share at least two names with the post
    candidates = []
    if names:
        rows = _rows('''SELECT e.event_id, e.title, string_agg(n.title, ' ') AS titles FROM news_events e
            JOIN news_event_members m USING (event_id) JOIN news_items n USING (item_id)
            WHERE NOT m.manually_removed GROUP BY e.event_id, e.title''')
        for r in rows:
            shared = sorted(set(names) & set(cl2._capitalised(r['titles'])))
            if len(shared) >= 2:
                candidates.append({'event_id': r['event_id'], 'title': r['title'], 'shared_names': shared})
        candidates.sort(key=lambda c: -len(c['shared_names']))
    return {'field': None, 'value': None, 'audit': {
        'kind': 'rule', 'rule': 'shared capitalised names >= 2', 'status': 'suggested', 'at': now,
        'events': candidates[:5], 'label_fa': 'پیشنهاد قاعده‌محور؛ اتصال فقط با تأیید تحلیلگر ثبت می‌شود'}}

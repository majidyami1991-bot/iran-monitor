"""News media pipeline v2: extraction, policy and validation.

Pure functions (extraction, canonicalisation, rejection, scoring, primary
selection) make no network request and are fixture-tested. The two network
functions — `fetch_article_meta` (one guarded HTML request, flag-gated) and
`validate_image` (one guarded, ranged GET) — go through net_guard, which
resolves DNS itself and refuses loopback, private, link-local and metadata
addresses on every hop.

Policy is documented in docs/NEWS MEDIA POLICY.md; POLICY_VERSION changes
whenever a rule changes.
"""
import hashlib
import ipaddress
import json
import os
import re
from dataclasses import dataclass, field, asdict
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode

POLICY_VERSION = 'media_policy_v1'
NS = {'media': 'http://search.yahoo.com/mrss/', 'content': 'http://purl.org/rss/1.0/modules/content/'}

SOURCE_METHODS = ('rss_media_content', 'rss_media_thumbnail', 'rss_enclosure', 'rss_content_html',
                  'rss_description_html', 'article_open_graph', 'article_json_ld', 'article_html', 'manual')
BASE_SCORE = {'rss_media_content': 100, 'article_open_graph': 95, 'article_json_ld': 90, 'rss_enclosure': 70,
              'rss_media_thumbnail': 60, 'rss_content_html': 40, 'rss_description_html': 35, 'article_html': 30, 'manual': 100}
# Publisher declarations that name the article's own image explicitly. These
# may become primary before a network validation, as long as no URL/size rule
# rejects them (docs/NEWS MEDIA POLICY.md, "Trusted declarations").
TRUSTED_DECLARATIONS = frozenset(('rss_media_content', 'rss_enclosure', 'article_open_graph', 'article_json_ld', 'manual'))
MIN_W, MIN_H = 480, 270
AR_MIN, AR_MAX = 0.8, 2.2
ALLOWED_MIME = frozenset(('image/jpeg', 'image/png', 'image/webp', 'image/avif'))
EXT_MIME = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.avif': 'image/avif',
            '.gif': 'image/gif', '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.bmp': 'image/bmp'}

# Whole filename tokens (split on non-alphanumerics), so "share-ramp" in a
# real photo name no longer matches the social "share" pattern (a false
# positive found in the 2026-09-29 audit: c-5-c-17-share-ramp.jpg).
DENY_TOKENS = {
    'logo': 'logo', 'logos': 'logo', 'avatar': 'avatar', 'avatars': 'avatar', 'gravatar': 'avatar',
    'icon': 'icon', 'icons': 'icon', 'favicon': 'icon', 'sprite': 'icon', 'sprites': 'icon', 'emoji': 'icon',
    'banner': 'banner_ad', 'advert': 'banner_ad', 'advertisement': 'banner_ad', 'ads': 'banner_ad', 'ad': 'banner_ad',
    'adserver': 'banner_ad', 'sponsored': 'banner_ad',
    'pixel': 'tracking_pixel', 'tracking': 'tracking_pixel', 'tracker': 'tracking_pixel', 'beacon': 'tracking_pixel',
    'spacer': 'tracking_pixel', 'blank': 'tracking_pixel',
    'placeholder': 'placeholder', 'newsletter': 'newsletter', 'subscribe': 'newsletter',
}
DENY_BIGRAMS = {('default', 'image'): 'placeholder', ('no', 'image'): 'placeholder', ('share', 'icon'): 'icon',
                ('share', 'button'): 'icon', ('social', 'icon'): 'icon'}
DENY_PATH_SEGMENTS = ('/emoji/', '/wp-includes/', '/themes/', '/plugins/', '/ads/', '/adserver/', '/banners/', '/avatars/')
AD_HOSTS = ('doubleclick.net', 'googlesyndication.com', 'googleadservices.com', 'adservice.google.com',
            'amazon-adsystem.com', 'adnxs.com', 'taboola.com', 'outbrain.com', 'criteo.com', 'scorecardresearch.com',
            'pixel.wp.com', 'stats.wp.com', 's.w.org', 'gravatar.com', 'feedburner.com', 'facebook.com', 'quantserve.com')
TRACKING_PARAMS = ('utm_', 'fbclid', 'gclid', 'mc_cid', 'mc_eid', '_hsenc', '_hsmi')


@dataclass
class Candidate:
    url: str                     # canonical
    original_url: str
    source_method: str
    source_field: str
    width: int | None = None
    height: int | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    alt_text: str | None = None
    caption: str | None = None
    credit: str | None = None
    position: int = 0
    insecure_http: bool = False
    rejection_reason: str | None = None
    score: int = 0

    def to_dict(self):
        return asdict(self)


# ------------------------------------------------------------------ canonicalisation
def _is_blocked_literal(host):
    try:
        ip = ipaddress.ip_address(host.strip('[]'))
    except ValueError:
        return host.lower() in ('localhost', 'localhost.localdomain') or host.lower().endswith(('.local', '.internal'))
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified


def canonical_media_url(value, base=None):
    """Return (canonical_url, insecure_http) or (None, reason)."""
    if not value or not isinstance(value, str):
        return None, 'empty_url'
    v = value.strip()
    if re.match(r'^(data|javascript|file|blob|about|vbscript):', v, re.I):
        return None, 'unsafe_scheme'
    if v.startswith('//'):
        v = 'https:' + v
    if not re.match(r'^https?://', v, re.I):
        # Relative: only against a valid absolute http(s) base.
        if not base or not re.match(r'^https?://', base, re.I):
            return None, 'relative_without_base'
        v = urljoin(base, v)
    p = urlsplit(v)
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        return None, 'invalid_url'
    if _is_blocked_literal(p.hostname):
        return None, 'private_or_loopback_host'
    # Conservative: only well-known tracking parameters are dropped; anything
    # else (signatures, sizes, tokens) is kept exactly.
    query = urlencode([(k, val) for k, val in parse_qsl(p.query, keep_blank_values=True)
                       if not k.lower().startswith(TRACKING_PARAMS)])
    netloc = p.hostname.lower() + (f':{p.port}' if p.port else '')
    return urlunsplit((p.scheme.lower(), netloc, p.path, query, '')), p.scheme.lower() == 'http'


def _ext(url):
    path = urlsplit(url).path.lower()
    dot = path.rfind('.')
    return path[dot:] if dot > 0 and len(path) - dot <= 6 else ''


def _int(v):
    try:
        n = int(str(v).strip().rstrip('px'))
        return n if 0 < n < 100000 else None
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ policy
def reject_reason(c):
    """A deterministic rejection reason, or None."""
    p = urlsplit(c.url)
    host = (p.hostname or '').lower()
    if any(host == h or host.endswith('.' + h) for h in AD_HOSTS):
        return 'ad_or_tracking_host'
    path = p.path.lower()
    if any(seg in path for seg in DENY_PATH_SEGMENTS):
        return 'chrome_path'
    base = path.rsplit('/', 1)[-1]
    stem = base.rsplit('.', 1)[0]
    tokens = [t for t in re.split(r'[^a-z0-9]+', stem) if t]
    for t in tokens:
        if t in DENY_TOKENS:
            return DENY_TOKENS[t]
    for a, b in zip(tokens, tokens[1:]):
        if (a, b) in DENY_BIGRAMS:
            return DENY_BIGRAMS[(a, b)]
    ext = _ext(c.url)
    mime = c.mime_type or EXT_MIME.get(ext)
    if mime == 'image/svg+xml' or ext == '.svg':
        return 'svg_not_allowed'
    if mime and mime.startswith('image/') and mime not in ALLOWED_MIME:
        return 'unsupported_mime'
    if mime and not mime.startswith('image/'):
        return 'not_an_image'
    w, h = c.width, c.height
    if w is not None and h is not None and w <= 2 and h <= 2:
        return 'tracking_pixel'
    if (w is not None and w < MIN_W) or (h is not None and h < MIN_H):
        return 'too_small'
    if w and h and not (AR_MIN <= w / h <= AR_MAX):
        return 'aspect_ratio'
    return None


def score(c):
    s = BASE_SCORE.get(c.source_method, 0)
    if c.width and c.height:
        s += 5
    if c.insecure_http:
        s -= 50
    return s


def evaluate(cands):
    """Apply rejection and scoring in place, drop duplicate canonical URLs
    (first — highest-priority — occurrence wins), return the list."""
    out, seen = [], set()
    for c in cands:
        if c.url in seen:
            continue
        seen.add(c.url)
        c.rejection_reason = reject_reason(c)
        c.score = score(c)
        out.append(c)
    return out


def eligible_for_primary(c, validation_status=None):
    """Valid after validation, or — before validation — a trusted publisher
    declaration that passed every URL/size rule. Never an insecure http URL,
    and never a rejected, blocked or unreachable image."""
    if c.rejection_reason or c.insecure_http:
        return False
    if validation_status in ('rejected', 'blocked', 'unreachable'):
        return False
    if validation_status == 'valid':
        return True
    if c.source_method in TRUSTED_DECLARATIONS:
        return True
    # Other sources (inline HTML images, thumbnails) qualify only when their
    # declared dimensions prove the size rules — reject_reason already
    # checked those dimensions, so "declared" here means "declared and passing".
    return bool(c.width and c.height)


def select_primary(cands, statuses=None):
    statuses = statuses or {}
    pool = [c for c in cands if eligible_for_primary(c, statuses.get(c.url))]
    pool.sort(key=lambda c: (-c.score, SOURCE_METHODS.index(c.source_method), c.position, c.url))
    return pool[0] if pool else None


# ------------------------------------------------------------------ RSS extraction
class _Imgs(HTMLParser):
    """Collects <img> attributes only; never executes or keeps markup."""
    SKIP = {'script', 'style', 'iframe', 'object', 'svg', 'noscript', 'template'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.images = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.SKIP:
            self.depth += 1
            return
        if tag == 'img' and not self.depth:
            a = {k.lower(): (v or '') for k, v in attrs}
            src = a.get('src') or a.get('data-src') or ''
            if a.get('srcset'):
                best, bw = None, -1
                for part in a['srcset'].split(','):
                    bits = part.split()
                    if bits:
                        w = _int(bits[1][:-1]) if len(bits) > 1 and bits[1].endswith('w') else 0
                        if (w or 0) > bw:
                            best, bw = bits[0], w or 0
                src = best or src
            self.images.append({'src': src, 'alt': a.get('alt') or None, 'width': _int(a.get('width')),
                                'height': _int(a.get('height'))})

    def handle_endtag(self, tag):
        if tag.lower() in self.SKIP and self.depth:
            self.depth -= 1


def html_images(markup, base, method, field_name, start=0):
    p = _Imgs()
    try:
        p.feed(markup or '')
        p.close()
    except Exception:
        return []
    out = []
    for i, img in enumerate(p.images):
        url, flag = canonical_media_url(img['src'], base)
        if not url:
            continue
        out.append(Candidate(url, img['src'], method, field_name, img['width'], img['height'],
                             EXT_MIME.get(_ext(url)), None, img['alt'], None, None, start + i, flag))
    return out


def _txt(el):
    return (''.join(el.itertext()).strip() or None) if el is not None else None


def rss_candidates(node, item_url):
    """All image candidates an RSS/Atom item declares, in policy priority
    order. `node` is a (defusedxml) ElementTree element; no network."""
    out, pos = [], 0

    def add(url_value, method, field_name, **kw):
        nonlocal pos
        url, flag = canonical_media_url(url_value, item_url)
        if url:
            out.append(Candidate(url, url_value, method, field_name, position=pos, insecure_http=flag, **kw))
            pos += 1

    groups = [node] + node.findall('media:group', NS)
    for g in groups:
        for e in g.findall('media:content', NS):
            medium, typ = (e.get('medium') or '').lower(), (e.get('type') or '').lower()
            u = e.get('url') or ''
            is_img = medium == 'image' or typ.startswith('image/') or (not medium and not typ and EXT_MIME.get(_ext(u), '').startswith('image/'))
            if is_img:
                add(u, 'rss_media_content', 'media:content', width=_int(e.get('width')), height=_int(e.get('height')),
                    mime_type=typ or None, file_size_bytes=_int(e.get('fileSize')),
                    caption=_txt(e.find('media:description', NS)) or _txt(g.find('media:description', NS)),
                    credit=_txt(e.find('media:credit', NS)) or _txt(g.find('media:credit', NS)),
                    alt_text=_txt(e.find('media:title', NS)))
    for g in groups:
        for e in g.findall('media:thumbnail', NS):
            add(e.get('url') or '', 'rss_media_thumbnail', 'media:thumbnail', width=_int(e.get('width')), height=_int(e.get('height')))
    for e in node.findall('enclosure'):
        typ = (e.get('type') or '').lower()
        if typ.startswith('image/'):
            add(e.get('url') or '', 'rss_enclosure', 'enclosure', mime_type=typ, file_size_bytes=_int(e.get('length')))
    ce = node.find('content:encoded', NS)
    out += html_images(_txt(ce), item_url, 'rss_content_html', 'content:encoded', start=pos)
    pos = len(out)
    out += html_images(_txt(node.find('description')), item_url, 'rss_description_html', 'description', start=pos)
    return evaluate(out)


# ------------------------------------------------------------------ article metadata (fallback)
class _Meta(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.ld = []
        self._in_ld = False
        self._buf = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or '') for k, v in attrs}
        if tag.lower() == 'meta':
            key = (a.get('property') or a.get('name') or '').lower()
            if key and a.get('content') and key not in self.meta:
                self.meta[key] = a['content']
        elif tag.lower() == 'script' and a.get('type', '').lower() == 'application/ld+json':
            self._in_ld, self._buf = True, []

    def handle_data(self, data):
        if self._in_ld:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == 'script' and self._in_ld:
            self._in_ld = False
            self.ld.append(''.join(self._buf))


def _ld_images(obj, depth=0):
    """Yield (url, width, height, caption) from a JSON-LD article's `image`."""
    if depth > 6 or obj is None:
        return
    if isinstance(obj, list):
        for x in obj:
            yield from _ld_images(x, depth + 1)
        return
    if not isinstance(obj, dict):
        return
    if '@graph' in obj:
        yield from _ld_images(obj['@graph'], depth + 1)
    types = obj.get('@type')
    types = types if isinstance(types, list) else [types]
    if any(t in ('Article', 'NewsArticle', 'ReportageNewsArticle', 'BlogPosting', 'AnalysisNewsArticle', 'WebPage') for t in types):
        img = obj.get('image')
        for it in (img if isinstance(img, list) else [img]):
            if isinstance(it, str):
                yield it, None, None, None
            elif isinstance(it, dict) and (it.get('url') or it.get('contentUrl')):
                yield it.get('url') or it.get('contentUrl'), _int(it.get('width')), _int(it.get('height')), it.get('caption')


def article_candidates(html_text, base_url):
    """Image candidates from one article page's metadata only (Open Graph,
    Twitter card, JSON-LD). The page body is not kept."""
    p = _Meta()
    try:
        p.feed(html_text or '')
        p.close()
    except Exception:
        return []
    m, out = p.meta, []
    w, h = _int(m.get('og:image:width')), _int(m.get('og:image:height'))
    for key, field_name in (('og:image', 'og:image'), ('og:image:secure_url', 'og:image:secure_url'), ('twitter:image', 'twitter:image')):
        url, flag = canonical_media_url(m.get(key), base_url)
        if url:
            out.append(Candidate(url, m.get(key), 'article_open_graph', field_name, w if key != 'twitter:image' else None,
                                 h if key != 'twitter:image' else None, EXT_MIME.get(_ext(url)), None,
                                 m.get('og:image:alt') if key != 'twitter:image' else None, None, None, len(out), flag))
    for block in p.ld:
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for u, lw, lh, cap in _ld_images(data):
            url, flag = canonical_media_url(u, base_url)
            if url:
                out.append(Candidate(url, u, 'article_json_ld', 'json-ld:image', lw, lh, EXT_MIME.get(_ext(url)), None,
                                     None, cap if isinstance(cap, str) else None, None, len(out), flag))
    return evaluate(out)


def fallback_enabled():
    return (os.getenv('NEWS_ARTICLE_MEDIA_FALLBACK_ENABLED') or 'false').strip().lower() == 'true'


ARTICLE_MAX_BYTES = 1_500_000
ARTICLE_MAX_REDIRECTS = 2


def fetch_article_meta(url, *, fetch=None):
    """One guarded HTML request; returns (candidates, audit). Refuses to run
    unless NEWS_ARTICLE_MEDIA_FALLBACK_ENABLED=true. No retry."""
    if not fallback_enabled():
        return [], {'status': 'disabled'}
    import net_guard as ng
    fetch = fetch or (lambda u: ng.guarded_get(u, max_bytes=ARTICLE_MAX_BYTES, max_redirects=ARTICLE_MAX_REDIRECTS))
    try:
        r = fetch(url)
    except Exception as exc:  # GuardError or network error: recorded, never retried
        return [], {'status': 'error', 'error': str(exc)[:120], 'requests': 1}
    ctype = (r.headers.get('content-type') or '').lower()
    audit = {'status': r.status, 'content_type': ctype.split(';')[0], 'final_url': r.final_url,
             'redirects': max(len(r.redirect_chain) - 1, 0), 'bytes': len(r.body), 'requests': 1}
    if r.status in (401, 403, 429):
        audit['status_class'] = 'blocked'
        return [], audit
    if r.status != 200:
        audit['status_class'] = 'unreachable'
        return [], audit
    if not ctype.startswith('text/html'):
        audit['status_class'] = 'not_html'
        return [], audit
    text = r.body.decode('utf-8', 'replace')
    return article_candidates(text, r.final_url), audit


# ------------------------------------------------------------------ validation
VALIDATE_MAX_BYTES = 6 * 1024 * 1024
RANGE_BYTES = 65535


def classify_image_response(status, headers, body):
    """(validation_status, reason, info) from one response. Pure."""
    import image_verify as iv
    if status in (401, 403):
        return 'blocked', f'http_{status}_hotlink_or_forbidden', None
    if status == 429:
        return 'blocked', 'http_429_rate_limited', None
    if status in (404, 410):
        return 'unreachable', f'http_{status}_missing', None
    if status >= 500:
        return 'unreachable', f'http_{status}_server_error', None
    if status not in (200, 206):
        return 'unreachable', f'http_{status}', None
    ctype = (headers.get('content-type') or '').split(';')[0].strip().lower()
    info = iv.verify_image(body)
    if info is None:
        if body[:64].lstrip().lower().startswith((b'<!doctype', b'<html', b'<svg', b'<?xml')):
            return 'rejected', 'html_or_svg_disguised_as_image', None
        return 'rejected', 'signature_not_image', None
    if ctype and ctype.startswith('image/') and ctype != info.mime_type and not (ctype == 'image/jpg' and info.mime_type == 'image/jpeg'):
        return 'rejected', f'mime_mismatch:{ctype}!={info.mime_type}', info
    if info.mime_type not in ALLOWED_MIME:
        return 'rejected', 'unsupported_mime', info
    if info.width and info.height:
        if info.width <= 2 and info.height <= 2:
            return 'rejected', 'tracking_pixel', info
        if info.width < MIN_W or info.height < MIN_H:
            return 'rejected', 'too_small', info
        if not (AR_MIN <= info.width / info.height <= AR_MAX):
            return 'rejected', 'aspect_ratio', info
        return 'valid', None, info
    return 'unknown', 'dimensions_not_in_header', info


def validate_image(url, *, mode='range_get', fetch=None, head=None):
    """Returns dict(validation_status, reason, http_status, final_url, width,
    height, mime, requests). `mode='head_then_get'` sends HEAD first and falls
    back to the ranged GET when HEAD is 405/501."""
    import net_guard as ng
    fetch = fetch or (lambda u: ng.guarded_fetch(u, method='GET', max_bytes=VALIDATE_MAX_BYTES, max_redirects=3,
                                                 extra_headers={'Range': f'bytes=0-{RANGE_BYTES}', 'Accept': 'image/*'}))
    head = head or (lambda u: ng.guarded_head(u, max_redirects=3))
    requests = 0
    if mode == 'head_then_get':
        try:
            h = head(url)
            requests += 1
            if h.status in (401, 403, 404, 410, 429) or h.status >= 500:
                vs, reason, _ = classify_image_response(h.status, h.headers, b'')
                return {'validation_status': vs, 'reason': reason, 'http_status': h.status, 'final_url': h.final_url,
                        'requests': requests}
        except Exception as exc:
            return {'validation_status': 'unreachable', 'reason': str(exc)[:120], 'http_status': None, 'requests': requests + 1}
    try:
        r = fetch(url)
        requests += 1
    except Exception as exc:
        reason = str(exc)[:120]
        status = 'rejected' if 'response_too_large' in reason else 'blocked' if 'blocked' in reason else 'unreachable'
        return {'validation_status': status, 'reason': reason, 'http_status': None, 'requests': requests + 1}
    if not r.final_url.lower().startswith('https://'):
        return {'validation_status': 'rejected', 'reason': 'final_url_not_https', 'http_status': r.status,
                'final_url': r.final_url, 'requests': requests}
    vs, reason, info = classify_image_response(r.status, r.headers, r.body)
    return {'validation_status': vs, 'reason': reason, 'http_status': r.status, 'final_url': r.final_url,
            'width': info.width if info else None, 'height': info.height if info else None,
            'mime': info.mime_type if info else None, 'requests': requests,
            'content_hash': hashlib.sha256(r.body).hexdigest() if r.body and vs == 'valid' and len(r.body) < RANGE_BYTES else None}


# ------------------------------------------------------------------ persistence
def media_id(item_id, url):
    return hashlib.sha256((item_id + '|' + url).encode('utf-8')).hexdigest()


def persist(c, item_id, cands, *, now_sql='now()'):
    """Upsert candidates for one item and recompute its single primary.
    Writes only v2 columns on rows that already exist; new rows get
    relevance 'article_media' (or 'rejected_policy') so the pre-redesign
    lead-image logic (relevance='article_image') is never changed by this.
    Idempotent: re-running with the same candidates changes nothing."""
    written = 0
    for cand in cands:
        mid = media_id(item_id, cand.url)
        vs = 'rejected' if cand.rejection_reason else 'pending' if cand.insecure_http else 'unknown'
        cur = c.execute('''INSERT INTO news_item_media(media_id,item_id,kind,url,mime_type,declared_width,declared_height,alt_text,position,
              relevance,rejection_reason,discovery_method,verification_status,caption,attribution,
              media_type,original_url,canonical_url,width,height,file_size_bytes,credit,source_method,source_field,source_hostname,
              validation_status,policy_score,policy_version)
            VALUES(%s,%s,'image',%s,%s,%s,%s,%s,%s,%s,%s,%s,'unverified',%s,%s,'image',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT(media_id) DO UPDATE SET
              source_method = CASE WHEN news_item_media.policy_score IS NULL OR EXCLUDED.policy_score > news_item_media.policy_score
                  THEN EXCLUDED.source_method ELSE news_item_media.source_method END,
              source_field = CASE WHEN news_item_media.policy_score IS NULL OR EXCLUDED.policy_score > news_item_media.policy_score
                  THEN EXCLUDED.source_field ELSE news_item_media.source_field END,
              policy_score = GREATEST(COALESCE(news_item_media.policy_score, 0), EXCLUDED.policy_score),
              width = COALESCE(news_item_media.width, EXCLUDED.width), height = COALESCE(news_item_media.height, EXCLUDED.height),
              caption = COALESCE(news_item_media.caption, EXCLUDED.caption), credit = COALESCE(news_item_media.credit, EXCLUDED.credit),
              file_size_bytes = COALESCE(news_item_media.file_size_bytes, EXCLUDED.file_size_bytes),
              validation_status = CASE WHEN news_item_media.validation_status IN ('valid','blocked','unreachable')
                  THEN news_item_media.validation_status ELSE EXCLUDED.validation_status END,
              rejection_reason = COALESCE(EXCLUDED.rejection_reason, news_item_media.rejection_reason),
              policy_version = EXCLUDED.policy_version, updated_at = now()
            WHERE (news_item_media.policy_score, news_item_media.policy_version, news_item_media.validation_status, news_item_media.width)
              IS DISTINCT FROM (GREATEST(COALESCE(news_item_media.policy_score, 0), EXCLUDED.policy_score), EXCLUDED.policy_version,
                CASE WHEN news_item_media.validation_status IN ('valid','blocked','unreachable') THEN news_item_media.validation_status
                     ELSE EXCLUDED.validation_status END, COALESCE(news_item_media.width, EXCLUDED.width))''',
                        (mid, item_id, cand.url, cand.mime_type, cand.width, cand.height, cand.alt_text, cand.position,
                         'rejected_policy' if cand.rejection_reason else 'article_media', cand.rejection_reason,
                         'v2:' + cand.source_method, cand.caption, cand.credit, cand.original_url, cand.url, cand.width,
                         cand.height, cand.file_size_bytes, cand.credit, cand.source_method, cand.source_field,
                         (urlsplit(cand.url).hostname or '').lower(), vs, cand.score, POLICY_VERSION))
        written += cur.rowcount
    return written + reselect_primary(c, item_id)


def _row_to_candidate(r):
    cand = Candidate(r['canonical_url'] or r['url'], r['original_url'] or r['url'], r['source_method'] or 'rss_content_html',
                     r['source_field'] or '', r['width'], r['height'], r['mime_type'], r['file_size_bytes'], r['alt_text'],
                     r['caption'], r['credit'], r['position'] or 0, (r['canonical_url'] or r['url']).startswith('http://'))
    cand.rejection_reason = reject_reason(cand)
    cand.score = score(cand)
    return cand


def reselect_primary(c, item_id):
    """Recompute the one primary image for an item from its stored rows under
    the current policy. Returns 1 if the primary changed, else 0."""
    from psycopg.rows import dict_row
    cur = c.cursor(row_factory=dict_row)
    rows = cur.execute('''SELECT media_id, url, canonical_url, original_url, source_method, source_field, width, height, mime_type,
        file_size_bytes, alt_text, caption, credit, position, validation_status, is_primary FROM news_item_media
        WHERE item_id=%s AND kind='image' ''', (item_id,)).fetchall()
    cands = {r['media_id']: _row_to_candidate(r) for r in rows}
    statuses = {cands[r['media_id']].url: r['validation_status'] for r in rows}
    best = select_primary(list(cands.values()), statuses)
    best_id = next((mid for mid, cd in cands.items() if cd is best), None)
    current = next((r['media_id'] for r in rows if r['is_primary']), None)
    if best_id == current:
        return 0
    c.execute('UPDATE news_item_media SET is_primary=false, updated_at=now() WHERE item_id=%s AND is_primary', (item_id,))
    if best_id:
        c.execute('UPDATE news_item_media SET is_primary=true, updated_at=now() WHERE media_id=%s', (best_id,))
    return 1

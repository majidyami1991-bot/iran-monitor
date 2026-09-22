"""Article body, media and translation extraction from already-fetched feed payloads.

Every function here works on bytes the collector already retrieved for a feed.
Nothing in this module performs network access: article pages, images and
documents are never fetched here, so no source access policy can be bypassed.
"""
import hashlib, html, re
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit, urljoin, parse_qsl, urlencode

CONTENT_VERSION = 1
MAX_TEXT_CHARS = 200000
MAX_MEDIA_PER_ITEM = 25

# A feed that ships the whole article in content:encoded has syndicated it
# deliberately; a bare description has not. The distinction drives what the
# product is allowed to render in full versus summarise and link.
FULL_TEXT_SOURCES = {'content_encoded', 'atom_content'}
SUMMARY_SOURCES = {'description', 'atom_summary'}

DOCUMENT_EXTENSIONS = {'.pdf': 'application/pdf', '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.ppt': 'application/vnd.ms-powerpoint',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.csv': 'text/csv', '.txt': 'text/plain'}
IMAGE_EXTENSIONS = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
    '.gif': 'image/gif', '.webp': 'image/webp', '.avif': 'image/avif', '.svg': 'image/svg+xml'}

# Substrings that mark chrome rather than editorial imagery. Matched against the
# URL path so a query string cannot smuggle one in or out.
CHROME_PATTERNS = ('logo', 'icon', 'favicon', 'avatar', 'gravatar', 'sprite', 'spacer',
    'placeholder', 'default-image', 'default_image', 'banner-ad', 'banner_ad', 'advert',
    'doubleclick', 'adsystem', 'adservice', 'pixel', 'beacon', 'tracking', 'track.gif',
    'emoji', 'button', 'badge', 'watermark', 'social-', 'share-', 'subscribe', 'newsletter',
    'feedburner', 'gravatar.com', 'wp-includes', 'themes/', 'plugins/')
MIN_DIMENSION = 200


class _Extract(HTMLParser):
    """Collects plain text, image candidates and document links in one pass."""
    BLOCKED = {'script', 'style', 'iframe', 'object', 'svg', 'noscript', 'form', 'button'}
    BREAKING = {'br', 'p', 'div', 'li', 'section', 'article', 'h1', 'h2', 'h3', 'h4', 'tr', 'blockquote'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts = []
        self.images = []
        self.links = []
        self.order = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        a = {k.lower(): (v or '') for k, v in attrs}
        if tag in self.BLOCKED:
            self.skip += 1
        if tag in self.BREAKING:
            self.parts.append('\n')
        if tag == 'img' and not self.skip:
            self.order += 1
            self.images.append({'src': a.get('src') or a.get('data-src') or a.get('data-lazy-src') or '',
                'srcset': a.get('srcset', ''), 'alt': a.get('alt', ''), 'title': a.get('title', ''),
                'width': _int(a.get('width')), 'height': _int(a.get('height')),
                'klass': a.get('class', ''), 'order': self.order})
        if tag == 'a' and not self.skip and a.get('href'):
            self.links.append({'href': a['href'], 'title': a.get('title', '')})

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.BLOCKED and self.skip:
            self.skip -= 1
        if tag in self.BREAKING:
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def _int(value):
    try:
        n = int(str(value).strip().rstrip('px'))
        return n if 0 < n < 20000 else None
    except (TypeError, ValueError):
        return None


def normalize_text(raw):
    """Collapse whitespace while keeping paragraph breaks readable."""
    if not raw:
        return None
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
    text = re.sub(r'[ \t ]+', ' ', text)
    text = re.sub(r' *\n *', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text[:MAX_TEXT_CHARS] or None


def safe_url(value, base=None):
    """Return an absolute https/http URL with tracking parameters removed."""
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if value.startswith(('data:', 'javascript:', 'blob:', '#')):
        return None
    if base:
        try:
            value = urljoin(base, value)
        except ValueError:
            return None
    p = urlsplit(value)
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        return None
    query = urlencode([(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
                       if not k.lower().startswith(('utm_', 'fbclid', 'gclid', 'mc_cid', 'mc_eid'))])
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, query, ''))


def _extension(url):
    path = urlsplit(url).path.lower()
    dot = path.rfind('.')
    return path[dot:] if dot > 0 and len(path) - dot <= 6 else ''


def _best_from_srcset(srcset, base):
    """Pick the widest candidate a srcset offers."""
    best, best_width = None, -1
    for candidate in srcset.split(','):
        parts = candidate.split()
        if not parts:
            continue
        url = safe_url(parts[0], base)
        if not url:
            continue
        width = 0
        if len(parts) > 1 and parts[1].endswith('w'):
            width = _int(parts[1][:-1]) or 0
        if width > best_width:
            best, best_width = url, width
    return best, (best_width if best_width > 0 else None)


def classify_image(url, meta):
    """Decide whether an image is editorial. Returns (relevance, reason)."""
    path = urlsplit(url).path.lower()
    haystack = path + ' ' + (meta.get('klass') or '').lower()
    for pattern in CHROME_PATTERNS:
        if pattern in haystack:
            return 'rejected_chrome', f'matched_pattern:{pattern}'
    extension = _extension(url)
    if extension == '.svg':
        return 'rejected_chrome', 'vector_asset_usually_iconography'
    if extension and extension not in IMAGE_EXTENSIONS:
        return 'rejected_type', f'unsupported_extension:{extension}'
    width, height = meta.get('width'), meta.get('height')
    if width is not None and height is not None and width <= 2 and height <= 2:
        return 'rejected_tracking_pixel', f'dimensions:{width}x{height}'
    if width is not None and width < MIN_DIMENSION:
        return 'rejected_too_small', f'declared_width:{width}'
    if height is not None and height < MIN_DIMENSION:
        return 'rejected_too_small', f'declared_height:{height}'
    return 'article_media', 'declared_in_article_body'


def media_id(item_id, url):
    return hashlib.sha256((item_id + '|' + url).encode('utf-8')).hexdigest()


def extract(raw_html, *, item_id, base_url, summary_source):
    """Split one feed content payload into body text, images and document links.

    `raw_html` is the feed's own markup. No request is made for anything it
    references; media rows describe what the feed declared, not what was
    downloaded.
    """
    parser = _Extract()
    try:
        parser.feed(html.unescape(raw_html or ''))
        parser.close()
    except Exception:
        return {'text': None, 'media': [], 'status': 'error', 'error': 'html_parse_failed'}

    text = normalize_text(''.join(parser.parts))
    media, seen = [], set()

    for image in parser.images:
        url, srcset_width = None, None
        if image['srcset']:
            url, srcset_width = _best_from_srcset(image['srcset'], base_url)
        url = url or safe_url(image['src'], base_url)
        if not url:
            continue
        key = media_id(item_id, url)
        if key in seen:
            continue
        seen.add(key)
        meta = dict(image)
        if meta.get('width') is None and srcset_width:
            meta['width'] = srcset_width
        relevance, reason = classify_image(url, meta)
        media.append({'media_id': key, 'item_id': item_id, 'kind': 'image', 'url': url,
            'mime_type': IMAGE_EXTENSIONS.get(_extension(url)), 'declared_width': meta.get('width'),
            'declared_height': meta.get('height'), 'alt_text': (image['alt'] or image['title'] or None),
            'position': image['order'], 'relevance': relevance, 'rejection_reason':
            None if relevance.startswith('article') else reason, 'discovery_method': 'feed_content_html',
            'verification_status': 'unverified'})

    for link in parser.links:
        url = safe_url(link['href'], base_url)
        if not url:
            continue
        extension = _extension(url)
        if extension not in DOCUMENT_EXTENSIONS:
            continue
        key = media_id(item_id, url)
        if key in seen:
            continue
        seen.add(key)
        media.append({'media_id': key, 'item_id': item_id, 'kind': 'document', 'url': url,
            'mime_type': DOCUMENT_EXTENSIONS[extension], 'declared_width': None, 'declared_height': None,
            'alt_text': link['title'] or None, 'position': None, 'relevance': 'linked_document',
            'rejection_reason': None, 'discovery_method': 'feed_content_html',
            'verification_status': 'unverified'})

    # The lead image is the first one that survived filtering, not the first in
    # document order: feeds routinely open with a masthead or a tracking pixel.
    lead = next((m for m in media if m['kind'] == 'image' and m['relevance'] == 'article_media'), None)
    if lead:
        lead['relevance'] = 'article_image'

    media = media[:MAX_MEDIA_PER_ITEM]
    if text:
        status = 'available' if summary_source in FULL_TEXT_SOURCES else 'summary_only'
    else:
        status = 'unavailable'
    return {'text': text, 'media': media, 'status': status, 'error': None}


def display_policy(summary_source, text):
    """What the platform may render for this item.

    `full_syndicated` means the publisher put the article body in its own feed.
    Anything else gets a summary plus a link to the original.
    """
    if not text:
        return 'link_only'
    if summary_source in FULL_TEXT_SOURCES and len(text) >= 400:
        return 'full_syndicated'
    return 'summary_only'

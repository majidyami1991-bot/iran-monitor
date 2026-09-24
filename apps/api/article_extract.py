"""Public article page extraction: fetched only when the feed itself carried
no usable body (policy order: RSS content, then enclosures, then page
metadata, then the public page — see content.py for the RSS-side extractor,
which this module does not replace).

Structure-preserving: returns typed blocks (heading/paragraph/list_item/
quote/table_row) rather than flat text, and strips chrome — nav, footer,
cookie banners, ads, related-stories, newsletter boxes, social widgets — by
tag and by a curated class/id keyword list. Never fetches more than one page
per item; the caller enforces that budget, this module just does the one
fetch it's given.
"""
import hashlib, html, re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode

import net_guard as ng
from image_verify import verify_image, meets_minimum_size

MAX_PAGE_BYTES = 3 * 1024 * 1024
MAX_BLOCKS = 400
MAX_BLOCK_CHARS = 4000

# Whole elements to discard outright — chrome that never contains article body.
CHROME_TAGS = {'nav', 'footer', 'script', 'style', 'iframe', 'noscript', 'svg',
               'form', 'button', 'aside', 'header'}
# Individual class/id word tokens (after splitting on whitespace and -/_)
# that mark a container as chrome even when its tag is generic (div/section).
# Matched against exact tokens only — never a substring of a longer compound
# class name — so a theme's own unrelated config flags (e.g. Divi/Extra's
# body class "et_fullwidth_nav", which is a layout-width setting, not a
# navigation element) can't false-positive a whole page into looking empty.
CHROME_HINTS = frozenset((
    'nav', 'navbar', 'navigation', 'menu', 'footer', 'header', 'cookie', 'cookies',
    'consent', 'gdpr', 'ad', 'ads', 'advert', 'adverts', 'advertisement', 'sponsor', 'sponsored',
    'promo', 'promoted', 'newsletter', 'subscribe', 'subscription', 'signup',
    'social', 'share', 'sharing', 'related', 'recommend', 'recommended', 'outbrain',
    'taboola', 'comment', 'comments', 'sidebar', 'breadcrumb',
    'breadcrumbs', 'pagination', 'popup', 'modal', 'overlay', 'masthead',
    # Deliberately NOT included, despite looking like obvious chrome words:
    # - 'widget'/'widgets': traditional WordPress sidebar boxes, but the
    #   Elementor page builder wraps every content block on the page —
    #   including the post title and body — in a class containing "widget"
    #   (e.g. "elementor-widget-container").
    # - 'banner': as often means the article's own hero/featured image
    #   ("banner-wrapper", "post-with-banner") as it means an ad slot. Actual
    #   ad slots are still caught by the 'ad'/'ads'/'advert' family above.
))
CONTENT_HINTS = frozenset((
    'article', 'content', 'entry', 'story', 'post', 'main', 'body',
))

HEADING_TAGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
# HTML5 void elements never get a matching handle_endtag call from
# html.parser unless the source writes an explicit self-closing slash — real
# pages rarely do for <br>, <img>, <meta>, <hr> etc. Pushing these onto a
# stack that only pops in handle_endtag desyncs the stack after the first one
# appears inside any chrome container, which silently blanks the whole page.
VOID_ELEMENTS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
                  'link', 'meta', 'param', 'source', 'track', 'wbr'}
LIST_ITEM_TAGS = {'li'}
QUOTE_TAGS = {'blockquote', 'q'}
PARA_BREAK_TAGS = {'p', 'div', 'br', 'section', 'article', 'tr'}


# Root document-skeleton tags routinely carry theme/global-state flags in
# their own class attribute (WordPress themes in particular dump dozens of
# config tokens onto <body>, e.g. Divi/Extra's "et_fullwidth_nav") that have
# nothing to do with the element itself being a chrome *region*. Only
# discrete regions can meaningfully be "navigation" or "an ad slot".
_NEVER_HINT_MATCHED = {'html', 'body'}


def _class_tokens(attrs):
    """Real class/id words, not a substring-searchable blob: split each
    class/id value on whitespace, then each of those on '-'/'_' so a
    substring match can never fire on an unrelated compound token."""
    tokens = set()
    for k, v in attrs:
        if k not in ('class', 'id') or not v:
            continue
        for word in v.lower().split():
            tokens.add(word)
            tokens.update(part for part in re.split(r'[-_]', word) if part)
    return tokens


def _is_chrome_by_attrs(tag, attrs):
    if tag in _NEVER_HINT_MATCHED:
        return False
    tokens = _class_tokens(attrs)
    return any(hint in tokens for hint in CHROME_HINTS)


def _is_content_by_attrs(tag, attrs):
    if tag in _NEVER_HINT_MATCHED:
        return False
    tokens = _class_tokens(attrs)
    return any(hint in tokens for hint in CONTENT_HINTS)


class _ArticleParser(HTMLParser):
    """Two passes in one walk: find the best content container (by scoring
    text density under `article`/content-hinted elements as we go), and
    collect typed blocks only for text emitted inside a non-chrome context."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        # One stack of frames — never two parallel structures. Python's
        # html.parser is a bare tokenizer with no HTML5 tag-omission repair
        # (a second <p> does not implicitly close an unclosed first one the
        # way a browser DOM would), so real pages routinely hand back
        # unbalanced start/end events; a matching pop-by-search below is what
        # keeps this safe instead of silently desyncing on real content.
        self.stack = []  # each: {'tag':, 'chrome':, 'is_content':}
        self.blocks = []
        self.buf = []
        self.current_type = 'paragraph'
        self.images = []
        self.doc_links = []
        self.meta_image = None
        self.in_content_container = 0  # >0 once inside an <article>/content-hinted element
        self.image_order = 0

    def _skipping(self):
        return any(f['chrome'] for f in self.stack)

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs = [(k.lower(), v or '') for k, v in attrs]
        attrd = dict(attrs)

        if tag == 'meta':
            prop = (attrd.get('property') or attrd.get('name') or '').lower()
            if prop in ('og:image', 'twitter:image', 'twitter:image:src') and attrd.get('content') and not self.meta_image:
                self.meta_image = attrd['content']
            return

        chrome = tag in CHROME_TAGS or _is_chrome_by_attrs(tag, attrs)
        is_void = tag in VOID_ELEMENTS
        if not is_void:
            is_content = tag == 'article' or _is_content_by_attrs(tag, attrs)
            self.stack.append({'tag': tag, 'chrome': chrome, 'is_content': is_content})
            if is_content:
                self.in_content_container += 1
        elif chrome:
            # A void chrome element (e.g. a tracking <img> or <br> inside an
            # ad slot) must not emit data, but it has no children and no end
            # tag, so nothing needs pushing — just skip its own handling below.
            return

        if self._skipping():
            return

        if tag == 'img' and not chrome:
            self.image_order += 1
            self.images.append({'src': attrd.get('src') or attrd.get('data-src') or attrd.get('data-lazy-src') or '',
                                 'alt': attrd.get('alt', ''), 'width': attrd.get('width'),
                                 'height': attrd.get('height'), 'order': self.image_order})
        elif tag == 'a' and attrd.get('href'):
            href = attrd['href']
            if re.search(r'\.pdf(\?|$)', href, re.I):
                self.doc_links.append({'href': href, 'title': attrd.get('title', '')})
        elif tag in HEADING_TAGS:
            self._flush()
            self.current_type = 'heading'
        elif tag in QUOTE_TAGS:
            self._flush()
            self.current_type = 'quote'
        elif tag in LIST_ITEM_TAGS:
            self._flush()
            self.current_type = 'list_item'
        elif tag in PARA_BREAK_TAGS:
            self._flush()
            self.current_type = 'paragraph'

    def handle_startendtag(self, tag, attrs):
        # Self-closing form (<tag/>): handle_starttag already skips the stack
        # push for void elements, and a non-void element written as
        # self-closing (rare, XHTML-style) still needs its end processed so
        # the stack doesn't leak.
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID_ELEMENTS and tag.lower() not in ('meta',):
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in VOID_ELEMENTS:
            return  # never pushed; an explicit closing tag for a void element is invalid HTML
        # Search from the top for the matching open frame rather than
        # trusting strict LIFO order, and discard every unclosed frame above
        # it (the HTML5-omission case: e.g. a second <li> ending the first).
        # An end tag with no matching open frame anywhere (malformed markup)
        # changes nothing — never pop the wrong element to "stay balanced".
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]['tag'] == tag:
                closed = self.stack[i:]
                del self.stack[i:]
                for frame in closed:
                    if frame['is_content']:
                        self.in_content_container = max(0, self.in_content_container - 1)
                break
        if tag in HEADING_TAGS | QUOTE_TAGS | LIST_ITEM_TAGS | PARA_BREAK_TAGS:
            self._flush()
            self.current_type = 'paragraph'

    def handle_data(self, data):
        if not self._skipping():
            self.buf.append(data)

    def _flush(self):
        text = ' '.join(''.join(self.buf).split())
        self.buf = []
        if not text:
            return
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)[:MAX_BLOCK_CHARS]
        if len(self.blocks) < MAX_BLOCKS and len(text) >= 2:
            self.blocks.append({'type': self.current_type, 'text': text,
                                 'in_content_container': self.in_content_container > 0})

    def close(self):
        self._flush()
        super().close()


def _dedupe_blocks(blocks):
    """Drop consecutive duplicate blocks (a common source of "متن تکراری"
    when the same teaser appears both above and inside the article body)."""
    out, seen_recent = [], []
    for b in blocks:
        if b['text'] in seen_recent[-3:]:
            continue
        out.append(b)
        seen_recent.append(b['text'])
    return out


def safe_url(value, base=None):
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
                       if not k.lower().startswith(('utm_', 'fbclid', 'gclid'))])
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, query, ''))


def extract_structured(raw_html, base_url):
    """Parse a full article page into typed blocks plus image/document
    candidates. Prefers blocks found inside an <article>/content-hinted
    container when any exist, so a sidebar "related stories" list that
    survived the chrome filter still doesn't pollute the body."""
    parser = _ArticleParser()
    try:
        parser.feed(html.unescape(raw_html or ''))
        parser.close()
    except Exception:
        return {'blocks': [], 'images': [], 'documents': [], 'meta_image': None, 'status': 'parse_error'}

    blocks = parser.blocks
    in_container = [b for b in blocks if b['in_content_container']]
    chosen = in_container if len(in_container) >= 3 else blocks
    chosen = _dedupe_blocks(chosen)
    for b in chosen:
        b.pop('in_content_container', None)

    images = []
    seen = set()
    if parser.meta_image:
        u = safe_url(parser.meta_image, base_url)
        if u:
            images.append({'url': u, 'alt_text': None, 'declared_width': None,
                            'declared_height': None, 'source': 'meta_og_twitter', 'order': 0})
            seen.add(u)
    for img in parser.images:
        u = safe_url(img['src'], base_url)
        if not u or u in seen:
            continue
        seen.add(u)
        images.append({'url': u, 'alt_text': img['alt'] or None,
                        'declared_width': _to_int(img['width']), 'declared_height': _to_int(img['height']),
                        'source': 'article_body', 'order': img['order']})

    documents = []
    dseen = set()
    for d in parser.doc_links:
        u = safe_url(d['href'], base_url)
        if not u or u in dseen:
            continue
        dseen.add(u)
        documents.append({'url': u, 'title': d['title'] or None})

    return {'blocks': chosen, 'images': images[:25], 'documents': documents[:10],
            'meta_image': images[0]['url'] if images and images[0]['source'] == 'meta_og_twitter' else None,
            'status': 'available' if chosen else 'empty'}


def _to_int(v):
    try:
        n = int(str(v).strip().rstrip('px'))
        return n if 0 < n < 20000 else None
    except (TypeError, ValueError):
        return None


def fetch_article(url):
    """The one bounded request per item this stage is allowed. Returns a dict
    with `status` always set; never raises for a network-level failure — the
    caller records the reason and moves on to the next item."""
    try:
        r = ng.guarded_get(url, max_bytes=MAX_PAGE_BYTES)
    except ng.GuardError as exc:
        return {'status': 'fetch_failed', 'reason': str(exc), 'blocks': [], 'images': [], 'documents': []}
    if r.status != 200:
        return {'status': 'fetch_failed', 'reason': f'http_{r.status}', 'blocks': [], 'images': [], 'documents': []}
    content_type = (r.headers.get('content-type') or '').split(';')[0].strip().lower()
    if content_type and 'html' not in content_type:
        return {'status': 'fetch_failed', 'reason': f'unexpected_content_type:{content_type}', 'blocks': [], 'images': [], 'documents': []}
    try:
        text = r.body.decode('utf-8', 'replace')
    except Exception:
        return {'status': 'fetch_failed', 'reason': 'decode_error', 'blocks': [], 'images': [], 'documents': []}
    result = extract_structured(text, r.final_url)
    result['fetched_bytes'] = len(r.body)
    result['final_url'] = r.final_url
    result['content_sha256'] = hashlib.sha256(r.body).hexdigest()
    return result

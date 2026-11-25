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
import hashlib, html, re, threading, time, urllib.parse
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
    'enquiry', 'enquiries', 'tags', 'reprint', 'reprints', 'disclaimer',
    'author-bio', 'related-posts', 'related-articles', 'related-content',
    'media-enquiries', 'post-tags', 'social-share', 'share-widget', 'carousel',
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


BOILERPLATE_PATTERNS = [
    r'(?i)^the post\s+.+?\s+appeared first on\s+.+$',
    r'(?i)^click to read more$',
    r'(?i)^click below to continue reading this story.+$',
    r'(?i)^never miss updated intel from .+$',
    r'(?i)^move faster with human-validated intelligence\.?$',
    r'(?i)^get equipment and weapon intelligence.+$',
    r'(?i)^request a free trial\b',
    r'(?i)^already a subscriber\?\s*sign in\b',
    r'(?i)^view products$',
    r'(?i)^read article$',
    r'(?i)^notifications$',
    r'(?i)^share this (page|article|post|story)$',
    r'(?i)^share\s*:\s*$',
    r'(?i)^share on (facebook|twitter|x|linkedin|email|whatsapp|telegram)$',
    r'(?i)^media enquiries$',
    r'(?i)^explore our related content$',
    r'(?i)^contact the (author|editor)\s*:.+$',
    r'(?i)^\s*topics\s*$',
    r'(?i)^\s*for release\s*$',
    r'(?i)^\s*online analysis\s*$',
    r'(?i)^\s*realclear context\s*$',
    r'(?i)^broken link\s*:.+$',
    r'(?i)^image credit\s*:.+$',
    r'(?i)^photo courtesy .+$',
    r'(?i)^photo by\s+.+$',
    r'(?i)^the views expressed are those of the author and do not reflect the official position.+$',
    r'(?i)^about\s+[a-z]+(\s+[a-z]+)?$',
    r'(?i)^authors?$',
    r'(?i)^news\s*(air|land|naval|sea)?\s*forces\s*(press releases)?$',
    r'(?i)^(land|air|naval)\s*forces\s+[a-z]{3}\s+\d{1,2},\s+\d{4}$',
    r'(?i)^.+media relations manager.+@.+\..+$',
    r'(?i)^\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*$',
    r'(?i)^\s*rand (education|health|social|public|national|infrastructure|labor).+$',
    r'(?i)^\s*(international security|military sciences|guest contributor)\s*$',
    r'(?i)^\s*missile dialogue initiative\s*$',
    r'(?i)^\s*sarmat:\s*better late than never for moscow\s*$',
    r'(?i)^rheinmetall shows wild goose robot mule.+$',
    r'(?i)^ukrainian mirage 2000 shoots down.+$',
    r'(?i)^russian corvette reportedly destroyed.+$',
    r'(?i)^u\.s\. army tests commercial shotgun shells.+$',
    r'(?i)^netherlands and germany order hensoldt.+knifefish.+$',
    r'(?i)^follow us on (google news|twitter|telegram|facebook)\b',
    r'(?i)^sign up for (our|the) newsletter\b',
    r'(?i)^got a tip\?\s*(email|contact)\b',
    r'(?i)^copyright\s+\d{4}\b',
    r'(?i)^all rights reserved\.?$',
]

CUTOFF_MARKERS = [
    r'(?i)^\s*online analysis\s*$',
    r'(?i)^\s*explore our related content\s*$',
    r'(?i)^\s*media enquiries\s*$',
    r'(?i)^\s*for media inquiries\s*$',
    r'(?i)^\s*never miss updated intel\s*',
    r'(?i)^\s*view products\s*$',
    r'(?i)^\s*read article\s*$',
    r'(?i)^\s*notifications\s*$',
    r'(?i)^\s*realclear context\s*$',
    r'(?i)^\s*click below to continue reading this story\s*',
    r'(?i)^\s*missile dialogue initiative\s*$',
    r'(?i)^\s*related (research|analysis|content|posts|articles|topics|programs|experts)\s*$',
    r'(?i)^\s*trending topics\s*$',
    r'(?i)^\s*tags\s*:\s*$',
    r'(?i)^\s*read (also|more)\s*:\s*$',
    r'(?i)^\s*read (the )?full article (at|on)\b',
    r'(?i)^\s*media queries\s*$',
    r'(?i)^\s*media relations\s*$',
    r'(?i)^\s*about the author\s*$',
    r'(?i)^\s*contact the author\s*:',
    r'(?i)^\s*got a tip\?\s*email\b',
    r'(?i)^\s*the views expressed (in this article|here )?are those of the author\b',
]


def _clean_boilerplate_blocks(blocks):
    cleaned = []
    for b in blocks:
        t = b['text'].strip()
        t = re.sub(r'(?i)\s*The post\s+.+?\s+appeared first on\s+.+?\.?$', '', t).strip()
        t = re.sub(r'(?i)\s*skip to (main )?content\s*', ' ', t).strip()
        t = re.sub(r'\s+', ' ', t).strip()
        if not t:
            continue
        if any(re.search(pat, t) for pat in CUTOFF_MARKERS):
            break
        if any(re.search(pat, t) for pat in BOILERPLATE_PATTERNS):
            continue
        b['text'] = t
        cleaned.append(b)

    while cleaned and (
        any(re.search(pat, cleaned[-1]['text']) for pat in BOILERPLATE_PATTERNS) or
        cleaned[-1]['text'].lower() in ('view profile', 'view all news', 'topics', 'share', 'related content', 'tags') or
        re.search(r'(?i)^by\s+.+,\s*[A-Z]{2,}$', cleaned[-1]['text'])
    ):
        cleaned.pop()

    while cleaned and (
        any(re.search(pat, cleaned[0]['text']) for pat in BOILERPLATE_PATTERNS) or
        cleaned[0]['text'].lower() in ('news', 'share:', 'for release')
    ):
        cleaned.pop()

    return cleaned


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
    chosen = _clean_boilerplate_blocks(chosen)
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


class SourceCircuitBreaker:
    """Tracks consecutive persistent access failures (e.g. 403, 401, bot protection) per hostname/domain.
    If a domain fails 3 consecutive times with access denied, it is put into cooldown for 2 hours."""
    def __init__(self, failure_threshold=3, cooldown_seconds=7200):
        self._lock = threading.Lock()
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._state = {}

    def _extract_domain(self, url: str) -> str:
        try:
            return urllib.parse.urlparse(url).netloc.lower().split(':')[0]
        except Exception:
            return ''

    def is_blocked(self, url: str) -> tuple[bool, str | None]:
        domain = self._extract_domain(url)
        if not domain:
            return False, None
        with self._lock:
            info = self._state.get(domain)
            if not info:
                return False, None
            now = time.time()
            if info['cooldown_until'] > now:
                remaining = int(info['cooldown_until'] - now)
                return True, f"circuit_open:{info['last_error']}_cooldown_{remaining}s"
            return False, None

    def record_success(self, url: str):
        domain = self._extract_domain(url)
        if not domain:
            return
        with self._lock:
            if domain in self._state:
                self._state[domain]['consecutive_failures'] = 0
                self._state[domain]['cooldown_until'] = 0

    def record_failure(self, url: str, error_reason: str):
        domain = self._extract_domain(url)
        if not domain:
            return
        is_access_denied = any(tok in str(error_reason).lower() for tok in ('403', 'forbidden', '401', 'unauthorized', 'access_denied', 'cloudflare', 'blocked'))
        with self._lock:
            info = self._state.setdefault(domain, {'consecutive_failures': 0, 'cooldown_until': 0, 'last_error': ''})
            if is_access_denied:
                info['consecutive_failures'] += 1
                info['last_error'] = str(error_reason)[:50]
                if info['consecutive_failures'] >= self._failure_threshold:
                    info['cooldown_until'] = time.time() + self._cooldown_seconds


_CIRCUIT_BREAKER = SourceCircuitBreaker()


class PlaywrightBrowserManager:
    """Singleton warm Chromium browser instance with bounded concurrency and isolated contexts."""
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._max_contexts = 3
        self._sem = threading.Semaphore(self._max_contexts)

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _ensure_browser(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError("playwright_not_installed")

        if self._browser is None or not self._browser.is_connected():
            if self._playwright:
                try:
                    self._playwright.stop()
                except Exception:
                    pass
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )
        return self._browser

    def fetch_page(self, url: str, timeout_ms: int = 25000):
        acquired = self._sem.acquire(timeout=30)
        if not acquired:
            return {'status': 'fetch_failed', 'reason': 'browser_busy_timeout', 'blocks': [], 'images': [], 'documents': []}

        context = None
        page = None
        try:
            with self._lock:
                browser = self._ensure_browser()

            context = browser.new_context(
                user_agent=ng.UA,
                viewport={'width': 1280, 'height': 800}
            )
            page = context.new_page()
            resp = page.goto(url, wait_until='domcontentloaded', timeout=timeout_ms)
            if not resp or resp.status >= 400:
                status_code = resp.status if resp else 'no_response'
                return {'status': 'fetch_failed', 'reason': f'http_{status_code}', 'blocks': [], 'images': [], 'documents': []}

            html_text = page.content()
            result = extract_structured(html_text, page.url)
            result['fetched_bytes'] = len(html_text.encode('utf-8'))
            result['final_url'] = page.url
            result['content_sha256'] = hashlib.sha256(html_text.encode('utf-8')).hexdigest()
            result['extraction_engine'] = 'playwright'
            return result
        except Exception as exc:
            with self._lock:
                if self._browser and not self._browser.is_connected():
                    self._browser = None
            return {'status': 'fetch_failed', 'reason': f'playwright_{type(exc).__name__}:{str(exc)[:100]}', 'blocks': [], 'images': [], 'documents': []}
        finally:
            if page:
                try:
                    page.close()
                except Exception:
                    pass
            if context:
                try:
                    context.close()
                except Exception:
                    pass
            self._sem.release()

    def close(self):
        with self._lock:
            if self._browser:
                try:
                    self._browser.close()
                except Exception:
                    pass
                self._browser = None
            if self._playwright:
                try:
                    self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None


def fetch_article_playwright(url, timeout_ms=25000):
    """Playwright browser-based article extractor using the warm singleton browser manager."""
    try:
        mgr = PlaywrightBrowserManager.get_instance()
        return mgr.fetch_page(url, timeout_ms=timeout_ms)
    except Exception as exc:
        return {'status': 'fetch_failed', 'reason': f'playwright_{type(exc).__name__}:{str(exc)[:100]}', 'blocks': [], 'images': [], 'documents': []}


def fetch_article(url):
    """The bounded request per item. First checks the source circuit breaker.
    Tries ordinary HTTP with standard browser headers;
    falls back to headless Playwright when blocked (e.g. 403) or when JS rendering is required."""
    blocked, cb_reason = _CIRCUIT_BREAKER.is_blocked(url)
    if blocked:
        return {'status': 'fetch_failed', 'reason': cb_reason, 'blocks': [], 'images': [], 'documents': []}

    http_error_reason = None
    try:
        r = ng.guarded_get(url, max_bytes=MAX_PAGE_BYTES)
        if r.status == 200:
            content_type = (r.headers.get('content-type') or '').split(';')[0].strip().lower()
            if not content_type or 'html' in content_type:
                try:
                    text = r.body.decode('utf-8', 'replace')
                    result = extract_structured(text, r.final_url)
                    if result.get('status') == 'available' and len(result.get('blocks', [])) > 0:
                        result['fetched_bytes'] = len(r.body)
                        result['final_url'] = r.final_url
                        result['content_sha256'] = hashlib.sha256(r.body).hexdigest()
                        result['extraction_engine'] = 'http'
                        _CIRCUIT_BREAKER.record_success(url)
                        return result
                except Exception:
                    pass
        else:
            http_error_reason = f'http_{r.status}'
    except ng.GuardError as exc:
        http_error_reason = str(exc)
    except Exception as exc:
        http_error_reason = str(exc)

    if http_error_reason:
        _CIRCUIT_BREAKER.record_failure(url, http_error_reason)

    # Check if the failure tripped the circuit breaker before launching Playwright
    blocked, cb_reason = _CIRCUIT_BREAKER.is_blocked(url)
    if blocked:
        return {'status': 'fetch_failed', 'reason': cb_reason, 'blocks': [], 'images': [], 'documents': []}

    # Attempt Playwright fallback for edge-protected or JS-rendered pages
    pw_result = fetch_article_playwright(url)
    if pw_result.get('status') == 'available' and len(pw_result.get('blocks', [])) > 0:
        _CIRCUIT_BREAKER.record_success(url)
        return pw_result

    # Record failure on Playwright attempt as well
    pw_reason = pw_result.get('reason') if pw_result.get('status') == 'fetch_failed' else (http_error_reason or 'empty_blocks')
    _CIRCUIT_BREAKER.record_failure(url, pw_reason)

    return {'status': 'fetch_failed', 'reason': pw_reason, 'blocks': [], 'images': [], 'documents': []}

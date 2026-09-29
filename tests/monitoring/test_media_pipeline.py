"""Offline tests for the news media pipeline v2. Fixtures are minimal
reproductions of structures seen in the real feeds on 2026-09-29 (JFeed
enclosure, Air & Space Forces media:content/thumbnail, TWZ content:encoded,
Breaking Defense description img) with synthetic URLs. No network."""
import email.message

import pytest
from defusedxml import ElementTree as ET

import media_pipeline as mp

RSS = '''<rss xmlns:media="http://search.yahoo.com/mrss/" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
<item><title>A</title><link>https://www.jfeed.com/news/a</link>
  <enclosure url="https://images.jfeed.com/p/a.jpg" type="image/jpeg" length="45000"/></item>
<item><title>B</title><link>https://www.airandspaceforces.com/b/</link>
  <media:content url="https://www.airandspaceforces.com/wp/b-1200.jpg" medium="image" width="1200" height="675">
    <media:description>Airmen on the flight line.</media:description><media:credit>USAF photo</media:credit></media:content>
  <media:thumbnail url="https://www.airandspaceforces.com/wp/b-150.jpg" width="150" height="150"/></item>
<item><title>C</title><link>https://www.twz.com/c</link>
  <content:encoded><![CDATA[<p><img src="https://s.w.org/images/core/emoji/17/72x72/1f535.png" width="72" height="72">
  <img src="/uploads/c-5-c-17-share-ramp.jpg?strip=all&amp;utm_source=rss" width="1024" height="576" alt="C-5 ramp"></p>
  <script>alert(1)</script><iframe src="https://evil.example/x"></iframe>]]></content:encoded></item>
<item><title>D</title><link>https://breakingdefense.com/d</link>
  <description><![CDATA[<img src="https://breakingdefense.com/wp/d.jpg" width="1200" height="800"> text]]></description></item>
</channel></rss>'''


def items():
    return ET.fromstring(RSS).findall('.//item')


def test_enclosure_image_extracted_and_trusted():
    [c] = mp.rss_candidates(items()[0], 'https://www.jfeed.com/news/a')
    assert c.source_method == 'rss_enclosure' and c.mime_type == 'image/jpeg' and c.file_size_bytes == 45000
    assert mp.select_primary([c]) is c


def test_media_content_wins_over_thumbnail_and_keeps_caption_credit():
    cs = mp.rss_candidates(items()[1], 'https://www.airandspaceforces.com/b/')
    methods = [c.source_method for c in cs]
    assert methods == ['rss_media_content', 'rss_media_thumbnail']
    thumb = cs[1]
    assert thumb.rejection_reason == 'too_small'
    p = mp.select_primary(cs)
    assert p.source_method == 'rss_media_content' and p.width == 1200
    assert p.caption == 'Airmen on the flight line.' and p.credit == 'USAF photo'


def test_content_html_relative_url_emoji_rejected_and_share_false_positive_fixed():
    cs = mp.rss_candidates(items()[2], 'https://www.twz.com/c')
    by = {c.url: c for c in cs}
    emoji = next(c for c in cs if 'emoji' in c.url)
    assert emoji.rejection_reason in ('ad_or_tracking_host', 'chrome_path', 'icon', 'too_small')
    ramp = by['https://www.twz.com/uploads/c-5-c-17-share-ramp.jpg?strip=all']
    assert ramp.rejection_reason is None, 'whole-token matching: "share-ramp" is not a share icon'
    assert 'utm_source' not in ramp.url and 'strip=all' in ramp.url
    assert mp.select_primary(cs) is ramp  # declared dims prove the size rule
    assert not any('evil.example' in c.url for c in cs), 'iframes/scripts are never mined for images'


def test_description_html_image():
    [c] = mp.rss_candidates(items()[3], 'https://breakingdefense.com/d')
    assert c.source_method == 'rss_description_html' and c.width == 1200


@pytest.mark.parametrize('url,reason', [
    ('https://example.com/img/site-logo.png', 'logo'),
    ('https://example.com/u/avatar_42.jpg', 'avatar'),
    ('https://example.com/i/favicon.png', 'icon'),
    ('https://example.com/banner-top.jpg', 'banner_ad'),
    ('https://ad.doubleclick.net/x.jpg', 'ad_or_tracking_host'),
    ('https://example.com/track/pixel.gif', 'tracking_pixel'),
    ('https://example.com/spacer.jpg', 'tracking_pixel'),
    ('https://example.com/default-image.jpg', 'placeholder'),
    ('https://example.com/newsletter-signup.jpg', 'newsletter'),
    ('https://example.com/wp-content/themes/x/header.jpg', 'chrome_path'),
    ('https://example.com/diagram.svg', 'svg_not_allowed'),
    ('https://example.com/anim.gif', 'unsupported_mime'),
])
def test_chrome_ad_and_placeholder_rejected(url, reason):
    c = mp.Candidate(url, url, 'rss_media_content', 'media:content')
    assert mp.reject_reason(c) == reason


def test_dimension_rules():
    mk = lambda w, h: mp.Candidate('https://e.com/p.jpg', '', 'rss_media_content', 'x', w, h)
    assert mp.reject_reason(mk(1, 1)) == 'tracking_pixel'
    assert mp.reject_reason(mk(300, 200)) == 'too_small'
    assert mp.reject_reason(mk(3000, 500)) == 'aspect_ratio'
    assert mp.reject_reason(mk(1200, 675)) is None
    assert mp.reject_reason(mk(None, None)) is None  # unknown, not rejected


def test_unknown_dimensions_from_html_not_primary_but_trusted_declaration_is():
    html_img = mp.Candidate('https://e.com/a.jpg', '', 'rss_content_html', 'content:encoded')
    og = mp.Candidate('https://e.com/b.jpg', '', 'article_open_graph', 'og:image')
    assert mp.select_primary(mp.evaluate([html_img])) is None
    assert mp.select_primary(mp.evaluate([html_img, og])).url == 'https://e.com/b.jpg'
    assert mp.select_primary([html_img], {html_img.url: 'valid'}) is html_img


def test_blocked_or_unreachable_never_primary():
    c = mp.Candidate('https://e.com/a.jpg', '', 'rss_media_content', 'media:content', 1200, 675)
    assert mp.select_primary([c], {c.url: 'blocked'}) is None
    assert mp.select_primary([c], {c.url: 'unreachable'}) is None


def test_duplicate_canonical_url_kept_once():
    a = mp.Candidate('https://e.com/a.jpg', '', 'rss_media_content', 'media:content')
    b = mp.Candidate('https://e.com/a.jpg', '', 'rss_content_html', 'content:encoded')
    assert len(mp.evaluate([a, b])) == 1 and mp.evaluate([a, b])[0].source_method == 'rss_media_content'


@pytest.mark.parametrize('value,base,expect', [
    ('/img/a.jpg', 'https://site.com/news/1', 'https://site.com/img/a.jpg'),
    ('//cdn.site.com/a.jpg', None, 'https://cdn.site.com/a.jpg'),
    ('https://Site.com/a.jpg?utm_source=x&w=800&sig=abc', None, 'https://site.com/a.jpg?w=800&sig=abc'),
])
def test_canonical_url(value, base, expect):
    assert mp.canonical_media_url(value, base)[0] == expect


@pytest.mark.parametrize('value,base', [
    ('data:image/png;base64,AAAA', None), ('javascript:alert(1)', None), ('file:///etc/passwd', None),
    ('/a.jpg', None), ('https://127.0.0.1/a.jpg', None), ('https://10.0.0.5/a.jpg', None),
    ('https://169.254.169.254/latest/meta-data', None), ('https://localhost/a.jpg', None), ('https://[::1]/a.jpg', None),
])
def test_unsafe_urls_refused(value, base):
    assert mp.canonical_media_url(value, base)[0] is None


def test_http_url_is_pending_and_never_primary_until_https_is_proven():
    url, insecure = mp.canonical_media_url('http://site.com/a.jpg')
    c = mp.evaluate([mp.Candidate(url, url, 'rss_media_content', 'media:content', 1200, 675, insecure_http=insecure)])[0]
    assert insecure and mp.select_primary([c]) is None


ARTICLE = '''<html><head>
<meta property="og:image" content="https://rusi.org/media/hero.jpg"><meta property="og:image:width" content="1600">
<meta property="og:image:height" content="900"><meta property="og:image:alt" content="Panel discussion">
<meta name="twitter:image" content="https://rusi.org/media/hero-tw.jpg">
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"NewsArticle",
 "image":{"@type":"ImageObject","url":"https://rusi.org/media/ld.jpg","width":1200,"height":675,"caption":"Caption"}}]}</script>
<script>document.write('<img src=https://evil.example/x.jpg>')</script>
</head><body><img src="/logo.png"></body></html>'''


def test_open_graph_and_json_ld():
    cs = mp.article_candidates(ARTICLE, 'https://rusi.org/explore/a')
    methods = [(c.source_method, c.source_field) for c in cs]
    assert ('article_open_graph', 'og:image') in methods and ('article_json_ld', 'json-ld:image') in methods
    og = cs[0]
    assert og.width == 1600 and og.alt_text == 'Panel discussion'
    ld = next(c for c in cs if c.source_method == 'article_json_ld')
    assert ld.caption == 'Caption' and ld.width == 1200
    assert mp.select_primary(cs).url == 'https://rusi.org/media/hero.jpg'
    assert not any('evil' in c.url or 'logo' in c.url for c in cs), 'body images and scripts are ignored'


class _Resp:
    def __init__(self, status, ctype, body, final='https://site.com/a.jpg'):
        self.status, self.headers, self.body, self.final_url, self.redirect_chain = status, {'content-type': ctype}, body, final, [final]


PNG_1200x675 = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + (1200).to_bytes(4, 'big') + (675).to_bytes(4, 'big') + b'\x08\x02\x00\x00\x00'
PNG_1x1 = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + (1).to_bytes(4, 'big') + (1).to_bytes(4, 'big') + b'\x08\x02\x00\x00\x00'


def test_article_fallback_is_off_by_default(monkeypatch):
    monkeypatch.delenv('NEWS_ARTICLE_MEDIA_FALLBACK_ENABLED', raising=False)
    called = []
    cs, audit = mp.fetch_article_meta('https://rusi.org/a', fetch=lambda u: called.append(u))
    assert cs == [] and audit == {'status': 'disabled'} and called == []


def test_article_fallback_only_html_and_blocked_is_recorded(monkeypatch):
    monkeypatch.setenv('NEWS_ARTICLE_MEDIA_FALLBACK_ENABLED', 'true')
    cs, audit = mp.fetch_article_meta('https://rusi.org/a', fetch=lambda u: _Resp(200, 'application/json', b'{}'))
    assert cs == [] and audit['status_class'] == 'not_html'
    cs, audit = mp.fetch_article_meta('https://rusi.org/a', fetch=lambda u: _Resp(403, 'text/html', b''))
    assert cs == [] and audit['status_class'] == 'blocked'
    cs, audit = mp.fetch_article_meta('https://rusi.org/a', fetch=lambda u: _Resp(200, 'text/html; charset=utf-8', ARTICLE.encode()))
    assert cs and audit['requests'] == 1

    def timeout(u):
        raise TimeoutError('read timed out')
    cs, audit = mp.fetch_article_meta('https://rusi.org/a', fetch=timeout)
    assert cs == [] and audit['status'] == 'error' and audit['requests'] == 1


def test_validation_statuses():
    v = lambda s, ct, b, **k: mp.validate_image('https://site.com/a.jpg', fetch=lambda u: _Resp(s, ct, b, **k))
    assert v(200, 'image/png', PNG_1200x675)['validation_status'] == 'valid'
    assert v(206, 'image/png', PNG_1200x675)['width'] == 1200
    assert v(403, 'text/html', b'')['validation_status'] == 'blocked'
    assert v(404, 'text/html', b'')['validation_status'] == 'unreachable'
    assert v(429, 'text/html', b'')['validation_status'] == 'blocked'
    assert v(503, 'text/html', b'')['validation_status'] == 'unreachable'
    assert v(200, 'image/jpeg', b'<!doctype html><html>')['reason'] == 'html_or_svg_disguised_as_image'
    assert v(200, 'image/jpeg', PNG_1200x675)['reason'].startswith('mime_mismatch')
    assert v(200, 'image/png', PNG_1x1)['reason'] == 'tracking_pixel'
    assert v(200, 'image/png', PNG_1200x675, final='http://site.com/a.jpg')['reason'] == 'final_url_not_https'


def test_validation_guard_errors_become_statuses():
    import net_guard as ng

    def ssrf(u):
        raise ng.GuardError('resolved_address_blocked')

    def big(u):
        raise ng.GuardError('response_too_large')
    assert mp.validate_image('https://x.com/a.jpg', fetch=ssrf)['validation_status'] == 'blocked'
    assert mp.validate_image('https://x.com/a.jpg', fetch=big)['validation_status'] == 'rejected'


def test_head_405_falls_back_to_get():
    heads = []

    def head(u):
        heads.append(u)
        return _Resp(405, 'text/plain', b'')
    r = mp.validate_image('https://site.com/a.jpg', mode='head_then_get', head=head,
                          fetch=lambda u: _Resp(200, 'image/png', PNG_1200x675))
    assert heads and r['validation_status'] == 'valid' and r['requests'] == 2


def test_net_guard_refuses_redirect_to_private_ip(monkeypatch):
    import net_guard as ng
    calls = []

    def single(method, url, **kw):
        calls.append(url)
        if len(calls) == 1:
            return 302, {'location': 'https://169.254.169.254/latest/meta-data'}, b''
        return ng.resolve_safe('169.254.169.254', 443)
    monkeypatch.setattr(ng, '_single_request', single)
    with pytest.raises(ng.GuardError):
        ng.guarded_fetch('https://site.com/a.jpg')


def test_collector_parse_carries_rss_media_without_changing_the_content_hash():
    import collector
    items, total, rejected, meta = collector.parse(RSS.encode('utf-8'), 'sid-test', '2026-09-29T00:00:00+00:00')
    jfeed = next(i for i in items if 'jfeed' in i['canonical_url'])
    assert [m['source_method'] for m in jfeed['rss_media']] == ['rss_enclosure']
    without = {k: v for k, v in jfeed.items() if k != 'rss_media'}
    assert collector.content_hash(jfeed) == collector.content_hash(without)

"""Offline article-extraction tests. Fixtures reproduce the exact real-world
failure patterns found while building this against live pilot pages — an
Elementor page builder (WordPress) and a hero-image "banner" class — so those
specific regressions can never come back silently."""
import article_extract as ae


def extract(html, base='https://publisher.example/story'):
    return ae.extract_structured(html, base)


def test_real_paragraphs_survive_alongside_nav_and_footer():
    html = '''
    <body class="site">
      <header class="site-header"><nav class="main-navigation"><ul><li>Home</li><li>World</li></ul></nav></header>
      <article>
        <h1>A real headline</h1>
        <p>The first real paragraph of the story, naming General Smith on 12 March.</p>
        <p>The second real paragraph continues the story with more detail.</p>
      </article>
      <footer class="site-footer"><p>Copyright 2026 Example Corp. All rights reserved.</p></footer>
    </body>'''
    result = extract(html)
    text = ' '.join(b['text'] for b in result['blocks'])
    assert 'General Smith' in text
    assert 'second real paragraph' in text
    assert 'Home' not in text
    assert 'Copyright 2026' not in text


def test_void_elements_without_self_closing_slashes_do_not_blank_the_page():
    # The historical bug: <br>, <img>, <meta> written without a trailing "/"
    # never fire handle_endtag, which desynced a naive push/pop stack and
    # caused everything after the first chrome element to read as chrome.
    html = '''
    <body>
      <header class="site-header">
        <img src="/logo.png" width="40" height="40">
        <br>
        <input type="text" placeholder="Search">
      </header>
      <article>
        <p>Real article text that must survive the void elements above.</p>
      </article>
    </body>'''
    result = extract(html)
    text = ' '.join(b['text'] for b in result['blocks'])
    assert 'Real article text' in text


def test_elementor_style_widget_wrapper_is_not_treated_as_chrome():
    # Real defect found against a live page: the Elementor WordPress page
    # builder wraps every content block — including the post title and body,
    # not just sidebar widgets — in a class containing "widget"
    # (elementor-widget-container). Treating "widget" as a chrome signal blanked
    # the entire article on every Elementor-built site.
    html = '''
    <body>
      <div class="elementor-element elementor-widget elementor-widget-theme-post-title">
        <div class="elementor-widget-container"><h1>Elementor Post Title</h1></div>
      </div>
      <div class="elementor-element elementor-widget elementor-widget-text-editor">
        <div class="elementor-widget-container">
          <p>The real article body lives inside an Elementor widget wrapper.</p>
        </div>
      </div>
    </body>'''
    result = extract(html)
    text = ' '.join(b['text'] for b in result['blocks'])
    assert 'Elementor Post Title' in text
    assert 'real article body' in text


def test_hero_image_banner_class_is_not_treated_as_an_ad():
    # Real defect: "banner-wrapper" / "post-with-banner" are common WordPress
    # theme classes for the article's own featured/hero image, not an ad slot.
    html = '''
    <body>
      <div class="banner-wrapper">
        <div class="container banner-content post-caption">
          <img src="/hero.jpg" width="1200" height="700" alt="Hero photo">
        </div>
      </div>
      <div class="col-body body-wrapper post-with-banner">
        <p>The real story text sits in a container whose class also says "banner".</p>
      </div>
    </body>'''
    result = extract(html)
    text = ' '.join(b['text'] for b in result['blocks'])
    assert 'real story text' in text


def test_actual_ad_slot_is_still_rejected_as_chrome():
    html = '''
    <body>
      <div class="top-ad"><p>Buy our sponsored widget now, 50% off!</p></div>
      <article><p>The real news paragraph about the actual event.</p></article>
    </body>'''
    result = extract(html)
    text = ' '.join(b['text'] for b in result['blocks'])
    assert 'sponsored widget' not in text
    assert 'real news paragraph' in text


def test_cookie_banner_and_newsletter_box_are_removed():
    html = '''
    <body>
      <div class="cookie-consent-banner"><p>We use cookies to improve your experience.</p></div>
      <div class="newsletter-signup"><p>Subscribe to our newsletter for daily updates.</p></div>
      <article><p>The one paragraph of real reporting in this story.</p></article>
    </body>'''
    result = extract(html)
    text = ' '.join(b['text'] for b in result['blocks'])
    assert 'cookies' not in text.lower()
    assert 'newsletter' not in text.lower()
    assert 'real reporting' in text


def test_heading_and_list_and_quote_types_are_preserved_distinctly():
    html = '''
    <article>
      <h2>A subheading</h2>
      <p>Intro paragraph.</p>
      <ul><li>First point</li><li>Second point</li></ul>
      <blockquote>A direct quotation from an official.</blockquote>
    </article>'''
    result = extract(html)
    types = [b['type'] for b in result['blocks']]
    assert 'heading' in types
    assert 'list_item' in types
    assert 'quote' in types


def test_og_image_meta_tag_is_captured_as_a_candidate():
    html = '''
    <head><meta property="og:image" content="/social-share.jpg"></head>
    <body><article><p>Story text.</p></article></body>'''
    result = extract(html)
    urls = [i['url'] for i in result['images']]
    assert 'https://publisher.example/social-share.jpg' in urls
    assert result['images'][0]['source'] == 'meta_og_twitter'


def test_pdf_link_inside_article_is_captured_as_a_document():
    html = '''<article><p>See the <a href="/reports/annual.pdf">annual report</a>.</p></article>'''
    result = extract(html)
    assert any(d['url'].endswith('annual.pdf') for d in result['documents'])


def test_duplicate_consecutive_teaser_paragraph_is_not_repeated():
    html = '''
    <article>
      <p>A teaser sentence that also appears again below.</p>
      <p>A teaser sentence that also appears again below.</p>
      <p>The real unique body continues from here.</p>
    </article>'''
    result = extract(html)
    count = sum(1 for b in result['blocks'] if b['text'] == 'A teaser sentence that also appears again below.')
    assert count == 1


def test_script_and_style_content_never_leaks_into_blocks():
    html = '''
    <head><style>.foo{color:red}nav.related{display:none}</style></head>
    <body>
      <script>var config = {nav: true, ad: "banner-slot"};</script>
      <article><p>The only real sentence on this page.</p></article>
    </body>'''
    result = extract(html)
    text = ' '.join(b['text'] for b in result['blocks'])
    assert 'color:red' not in text
    assert 'config' not in text
    assert 'The only real sentence' in text


def test_malformed_unclosed_paragraph_does_not_corrupt_later_content():
    # HTML5 allows <p> to be implicitly closed by the next block element;
    # Python's stdlib tokenizer does not perform that repair itself, so the
    # extractor's own recovery is what's under test here.
    html = '''<article><p>First unclosed paragraph<p>Second paragraph<div>Real trailing content</div></article>'''
    result = extract(html)
    text = ' '.join(b['text'] for b in result['blocks'])
    assert 'Real trailing content' in text


def test_empty_page_returns_empty_not_an_error():
    result = extract('')
    assert result['blocks'] == []
    assert result['status'] in ('empty', 'parse_error')


def test_unparseable_bytes_do_not_raise():
    result = extract('<<<not really html>>>')
    assert isinstance(result['blocks'], list)

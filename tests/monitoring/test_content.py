"""Extraction, media filtering and translation-status tests. No network access."""
import datetime

import collector
import content
import translate

RECEIVED = datetime.datetime(2026, 9, 22, 12, 0, tzinfo=datetime.timezone.utc)


def test_rss_channel_title_is_captured_as_the_publisher_name():
    xml = b'''<rss version="2.0"><channel><title>The War Zone</title><language>en-US</language>
    <item><title>Story</title><link>https://www.twz.com/a</link></item></channel></rss>'''
    _items, _observed, _rejected, meta = collector.parse(xml, 's1', RECEIVED)
    assert meta['feed_title'] == 'The War Zone'
    assert meta['feed_language'] == 'en-US'


def test_atom_feed_title_is_captured():
    xml = b'''<feed xmlns="http://www.w3.org/2005/Atom"><title>Modern War Institute</title>
    <entry><title>Story</title><link rel="alternate" href="https://mwi.westpoint.edu/a"/></entry></feed>'''
    _items, _observed, _rejected, meta = collector.parse(xml, 's2', RECEIVED)
    assert meta['feed_title'] == 'Modern War Institute'


def test_feed_without_a_title_reports_none_rather_than_a_guess():
    xml = b'''<rss version="2.0"><channel>
    <item><title>Story</title><link>https://e.com/a</link></item></channel></rss>'''
    _items, _observed, _rejected, meta = collector.parse(xml, 's3', RECEIVED)
    assert meta['feed_title'] is None


def test_full_content_block_is_preferred_over_a_short_description_for_extraction():
    xml = b'''<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
    <channel><title>T</title><item><title>Story</title><link>https://e.com/a</link>
    <description>Short teaser.</description>
    <content:encoded><![CDATA[<p>The full body runs much longer than the teaser does.</p>]]></content:encoded>
    </item></channel></rss>'''
    items, _observed, _rejected, _meta = collector.parse(xml, 's4', RECEIVED)
    assert 'full body' in items[0]['content_html']


def extract(html, *, item_id='item-1', base='https://publisher.example/story', source='content_encoded'):
    return content.extract(html, item_id=item_id, base_url=base, summary_source=source)


def test_body_text_keeps_names_numbers_and_dates():
    result = extract('<p>The Air Force said on 12 March 2026 that 3 units deploy to Al Udeid.</p>')
    assert 'Air Force' in result['text']
    assert '12 March 2026' in result['text']
    assert '3 units' in result['text']
    assert 'Al Udeid' in result['text']


def test_script_and_style_content_is_not_treated_as_article_text():
    result = extract('<p>Real body.</p><script>var secret=1;</script><style>.a{color:red}</style>')
    assert 'Real body.' in result['text']
    assert 'secret' not in result['text']
    assert 'color:red' not in result['text']


def test_logo_and_tracking_pixel_are_rejected_with_a_reason():
    result = extract('<img src="https://cdn.example/logo-header.png" width="120" height="40"/>'
                     '<img src="https://t.example/p.gif" width="1" height="1"/>')
    kinds = {m['url']: (m['relevance'], m['rejection_reason']) for m in result['media']}
    assert kinds['https://cdn.example/logo-header.png'][0] == 'rejected_chrome'
    assert kinds['https://t.example/p.gif'][0] == 'rejected_tracking_pixel'
    assert all(v[1] for v in kinds.values())


def test_small_declared_images_are_rejected():
    result = extract('<img src="https://cdn.example/thumb.jpg" width="80" height="80"/>')
    assert result['media'][0]['relevance'] == 'rejected_too_small'


def test_lead_image_is_the_first_surviving_image_not_the_first_in_markup():
    result = extract('<img src="https://cdn.example/site-logo.png" width="300" height="300"/>'
                     '<img src="https://cdn.example/scene.jpg" width="1200" height="800"/>')
    lead = [m for m in result['media'] if m['relevance'] == 'article_image']
    assert len(lead) == 1
    assert lead[0]['url'] == 'https://cdn.example/scene.jpg'


def test_srcset_prefers_the_widest_candidate():
    result = extract('<img srcset="https://cdn.example/a-400.jpg 400w, https://cdn.example/a-1600.jpg 1600w"/>')
    assert result['media'][0]['url'] == 'https://cdn.example/a-1600.jpg'
    assert result['media'][0]['declared_width'] == 1600


def test_data_and_javascript_urls_are_dropped():
    result = extract('<img src="data:image/gif;base64,R0lGOD"/><img src="javascript:alert(1)"/>')
    assert result['media'] == []


def test_relative_urls_resolve_and_tracking_parameters_are_stripped():
    result = extract('<img src="/img/a.jpg?utm_source=feed&id=7" width="900"/>')
    assert result['media'][0]['url'] == 'https://publisher.example/img/a.jpg?id=7'


def test_credentialed_urls_are_refused():
    assert content.safe_url('https://user:pass@example.com/a.jpg') is None


def test_documents_are_captured_with_mime_type():
    result = extract('<a href="https://example.com/report.pdf">Annual report</a>')
    doc = result['media'][0]
    assert doc['kind'] == 'document'
    assert doc['mime_type'] == 'application/pdf'
    assert doc['relevance'] == 'linked_document'


def test_duplicate_urls_appear_once():
    result = extract('<img src="https://cdn.example/a.jpg" width="900"/>'
                     '<img src="https://cdn.example/a.jpg" width="900"/>')
    assert len(result['media']) == 1


def test_media_rows_start_unverified_because_nothing_is_downloaded():
    result = extract('<img src="https://cdn.example/a.jpg" width="900"/>')
    assert result['media'][0]['verification_status'] == 'unverified'
    assert result['media'][0]['discovery_method'] == 'feed_content_html'


def test_display_policy_separates_syndicated_body_from_short_description():
    assert content.display_policy('content_encoded', 'x' * 500) == 'full_syndicated'
    assert content.display_policy('description', 'x' * 500) == 'summary_only'
    assert content.display_policy('content_encoded', None) == 'link_only'


def test_empty_payload_is_unavailable_not_an_error():
    result = extract('')
    assert result['status'] == 'unavailable'
    assert result['media'] == []
    assert result['error'] is None


def test_media_count_is_bounded():
    html = ''.join(f'<img src="https://cdn.example/{i}.jpg" width="900"/>' for i in range(60))
    assert len(extract(html)['media']) <= content.MAX_MEDIA_PER_ITEM


def test_no_provider_configured_yields_pending_and_never_invented_text(monkeypatch):
    monkeypatch.delenv('NEWS_TRANSLATION_PROVIDER', raising=False)
    provider = translate.build_provider()
    result = translate.run_task(provider, 'translation', 'Some English text.')
    assert result['status'] == 'pending'
    assert result['text'] is None


def test_missing_source_text_is_unavailable():
    result = translate.run_task(translate.NullProvider(), 'translation', '')
    assert result['status'] == 'unavailable'
    assert result['error'] == 'no_source_text'


def test_unknown_provider_name_falls_back_to_null(monkeypatch):
    monkeypatch.setenv('NEWS_TRANSLATION_PROVIDER', 'not-a-provider')
    assert isinstance(translate.build_provider(), translate.NullProvider)


def test_provider_named_without_a_key_falls_back_to_null(monkeypatch):
    monkeypatch.setenv('NEWS_TRANSLATION_PROVIDER', 'openai')
    monkeypatch.delenv('NEWS_TRANSLATION_API_KEY', raising=False)
    assert isinstance(translate.build_provider(), translate.NullProvider)


def test_english_output_is_rejected_so_an_untranslated_echo_never_ships():
    class Echo(translate.Provider):
        name = 'echo'
        model = 'echo-1'

        def complete(self, system, user):
            return user

    result = translate.run_task(Echo(), 'translation', 'The Air Force said on 12 March.')
    assert result['status'] == 'error'
    assert result['error'] == 'output_not_persian'


def test_persian_output_is_accepted():
    class Fa(translate.Provider):
        name = 'fa'
        model = 'fa-1'

        def complete(self, system, user):
            return 'نیروی هوایی در ۱۲ مارس ۲۰۲۶ اعلام کرد.'

    result = translate.run_task(Fa(), 'translation', 'The Air Force said on 12 March 2026.')
    assert result['status'] == 'available'
    assert 'نیروی هوایی' in result['text']


def test_provider_errors_are_sanitized_of_key_material():
    class Boom(translate.Provider):
        name = 'boom'
        model = 'b'

        def complete(self, system, user):
            raise translate.ProviderError('bad key sk-abcdef0123456789 rejected')

    result = translate.run_task(Boom(), 'translation', 'text')
    assert result['status'] == 'error'
    assert 'sk-abcdef0123456789' not in result['error']
    assert '[REDACTED]' in result['error']

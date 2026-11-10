"""Offline tests for X-FREE (manual X monitoring). No network, no database:
the manifest is the real shipped file, everything else is pure logic."""
import time

import pytest

import social as s

MANIFEST = s.load_manifest()
KEYS = {a['handle_key'] for a in MANIFEST['accounts']}


# ------------------------------------------------------------------ registry
def test_manifest_has_36_unique_accounts_from_38_raw_occurrences():
    assert MANIFEST['summary']['raw_occurrences'] == 38
    assert MANIFEST['summary']['unique_accounts'] == 36
    assert len(MANIFEST['accounts']) == 36 and len(KEYS) == 36


def test_duplicate_occurrences_are_the_two_known_handles():
    assert MANIFEST['summary']['duplicate_handles'] == ['@ThetiMapping', '@manniefabian']
    dup = [a for a in MANIFEST['accounts'] if a['occurrence_count'] == 2]
    assert sorted(a['handle'] for a in dup) == ['@ThetiMapping', '@manniefabian']
    for a in dup:
        assert len(a['provenance']) == 2, 'both raw occurrences keep their provenance'


def test_every_account_is_manual_only_and_keeps_its_source_id():
    for a in MANIFEST['accounts']:
        assert a['enabled'] is False and a['official_api_enabled'] is False
        assert a['collection_mode'] == 'manual' and a['collection_status'] == 'manual_monitoring'
        assert a['source_id'] and a['provenance']
        assert a['canonical_profile_url'] == 'https://x.com/' + a['handle'][1:]
    assert MANIFEST['policy'] == {'official_api': False, 'scraping': False, 'scheduler': False,
                                  'collection': MANIFEST['policy']['collection']}


# ------------------------------------------------------------------ URL validation
HANDLE = MANIFEST['accounts'][0]['handle'][1:]


@pytest.mark.parametrize('url', [
    f'https://x.com/{HANDLE}/status/1839001234567890123',
    f'https://twitter.com/{HANDLE}/status/1839001234567890123',
    f'https://www.x.com/{HANDLE.upper()}/status/1839001234567890123/?s=20',
    f'https://mobile.twitter.com/{HANDLE}/status/1839001234567890123#frag',
])
def test_valid_x_and_twitter_urls_canonicalise_deterministically(url):
    canon, key, pid = s.validate_x_url(url, KEYS)
    assert pid == '1839001234567890123'
    assert key == '@' + HANDLE.lower()
    assert canon.startswith('https://x.com/') and canon.endswith('/status/1839001234567890123')


@pytest.mark.parametrize('url,code', [
    ('http://x.com/{h}/status/1839001234567890123', 'url_not_https'),
    ('https://x.com.evil.io/{h}/status/1839001234567890123', 'url_host_not_x'),
    ('https://xcom.io/{h}/status/1839001234567890123', 'url_host_not_x'),
    ('https://twitter.co/{h}/status/1839001234567890123', 'url_host_not_x'),
    ('https://t.co/AbCdEf123', 'url_host_not_x'),
    ('https://evil.com/?u=https://x.com/{h}/status/1839001234567890123', 'url_host_not_x'),
    ('https://user:pw@x.com/{h}/status/1839001234567890123', 'url_has_credentials_or_port'),
    ('https://x.com:8443/{h}/status/1839001234567890123', 'url_has_credentials_or_port'),
    ('https://x.com/{h}', 'url_not_a_status_link'),
    ('https://x.com/{h}/status/', 'url_not_a_status_link'),
    ('https://x.com/{h}/status/abc', 'url_not_a_status_link'),
    ('https://x.com/i/web/status/1839001234567890123', 'url_not_a_status_link'),  # no author handle to verify
    ('https://x.com/elonmusk/status/1839001234567890123', 'handle_not_in_registry'),
    ('javascript:alert(1)', 'url_not_https'),
])
def test_invalid_urls_are_rejected_with_a_stable_code(url, code):
    with pytest.raises(s.SocialError) as e:
        s.validate_x_url(url.format(h=HANDLE), KEYS)
    assert str(e.value) == code


# ------------------------------------------------------------------ text, xss, provenance
def test_html_and_script_are_kept_as_inert_text_not_stripped_or_executed():
    payload = '<script>alert(1)</script><img src=x onerror=alert(2)>'
    assert s.clean_text(payload, 4000, 'original_text') == payload  # stored verbatim, rendered as text by React


def test_control_characters_and_oversize_text_rejected():
    with pytest.raises(s.SocialError):
        s.clean_text('bad\x00text', 4000, 'original_text')
    with pytest.raises(s.SocialError):
        s.clean_text('x' * 4001, 4000, 'original_text')
    assert s.clean_text('   ', 4000, 'original_text') is None


def test_provenance_says_who_entered_the_text_and_that_x_was_not_called():
    p = s.build_provenance('analyst one', True)
    assert p['text_source'] == 'analyst_entered' and p['fetched_from_x'] is False and p['text_is_x_api_output'] is False
    q = s.build_provenance('analyst one', False)
    assert q['text_source'] == 'not_recorded' and 'متن محلی ثبت نشده' in q['note_fa']


def test_published_at_bounds():
    assert s.parse_published('') is None
    assert s.parse_published('2026-09-28T10:00:00Z').year == 2026
    with pytest.raises(s.SocialError):
        s.parse_published('2099-01-01')
    with pytest.raises(s.SocialError):
        s.parse_published('not a date')


def test_media_only_from_x_cdn():
    ok = s.validate_media([{'media_type': 'image', 'external_url': 'https://pbs.twimg.com/media/abc.jpg'}])
    assert ok[0]['media_type'] == 'image'
    with pytest.raises(s.SocialError):
        s.validate_media([{'media_type': 'image', 'external_url': 'https://evil.example/a.jpg'}])


# ------------------------------------------------------------------ csrf and switch
def test_csrf_token_roundtrip_expiry_and_tamper():
    t = s.make_csrf_token()
    assert s.verify_csrf_token(t)
    ts, sig = t.split('.')
    assert not s.verify_csrf_token(ts + '.' + ('0' * len(sig)))
    assert not s.verify_csrf_token(t, now=time.time() + s.CSRF_TTL_SECONDS + 5)
    assert not s.verify_csrf_token('')
    assert not s.verify_csrf_token('abc.def')


def test_ingest_disabled_by_default(monkeypatch):
    monkeypatch.delenv('SOCIAL_MANUAL_INGEST_ENABLED', raising=False)
    assert s.ingest_enabled() is False
    monkeypatch.setenv('SOCIAL_MANUAL_INGEST_ENABLED', 'true')
    assert s.ingest_enabled() is True


def test_write_guard_refuses_disabled_bad_origin_and_bad_token(monkeypatch):
    from fastapi import HTTPException
    monkeypatch.delenv('SOCIAL_MANUAL_INGEST_ENABLED', raising=False)
    with pytest.raises(HTTPException) as e:
        s._require_write(s.make_csrf_token(), 'http://127.0.0.1:3002')
    assert e.value.detail == 'manual_ingest_disabled'
    monkeypatch.setenv('SOCIAL_MANUAL_INGEST_ENABLED', 'true')
    for origin in ('https://evil.example', 'absent', None):
        with pytest.raises(HTTPException) as e:
            s._require_write(s.make_csrf_token(), origin)
        assert e.value.detail == 'origin_not_allowed'
    with pytest.raises(HTTPException) as e:
        s._require_write('forged.token', 'http://127.0.0.1:3002')
    assert e.value.detail == 'csrf_token_invalid'
    s._require_write(s.make_csrf_token(), 'http://127.0.0.1:3002')  # passes


def test_request_models_forbid_unknown_fields():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        s.ManualPostIn(url='https://x.com/a/status/12345', analyst='a b', injected_field='x')


def test_ai_actions_are_a_closed_list():
    assert s.AI_ACTIONS == ('translate', 'summarize', 'classify', 'entities', 'suggest_event')

"""Offline tests for content_intelligence.py — the orchestration layer over
the AI Gateway. Uses a fake adapter; no network access."""
import ai_gateway as gw
import content_intelligence as ci


class FakeAdapter(gw.Adapter):
    name = 'fake'
    model = 'fake-model'

    def __init__(self, response_text):
        self._response_text = response_text
        self.calls = 0

    def complete(self, system, user):
        self.calls += 1
        return gw.AdapterResponse(self._response_text, tokens_in=10, tokens_out=5)


def make_gateway(mode, adapter):
    config = gw.GatewayConfig(mode=mode, provider='fake', base_url='', api_key='x',
                               models={'translation': 'fake-model', 'summary': 'fake-model',
                                       'classification': 'fake-model', 'signal_analysis': 'fake-model',
                                       'scenario': 'fake-model', 'key_point_extraction': 'fake-model'},
                               timeout_seconds=5, max_concurrency=3, daily_budget_usd=None)
    g = gw.AIGateway(config=config)
    g.adapter = adapter
    g.breaker = gw.CircuitBreaker()
    return g


# --------------------------------------------------------------------------- language detection

def test_detect_language_persian_text():
    r = ci.detect_language('این یک متن فارسی است')
    assert r['language'] == 'fa'
    assert r['method'] == 'deterministic_unicode_range'


def test_detect_language_english_text():
    r = ci.detect_language('This is an English sentence about defence policy.')
    assert r['language'] == 'en'


def test_detect_language_empty_text_is_unknown():
    r = ci.detect_language('')
    assert r['language'] == 'unknown'
    assert r['confidence'] == 0.0


def test_detect_language_never_calls_the_gateway():
    # No gateway argument exists on detect_language at all — this test
    # documents that fact: the function signature itself proves it never
    # makes a network-dependent call.
    import inspect
    assert 'gateway' not in inspect.signature(ci.detect_language).parameters


# --------------------------------------------------------------------------- translation

def test_translate_to_persian_available_and_validated():
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, FakeAdapter('{"text": "سلام دنیا"}'))
    result = ci.translate_to_persian('Hello world', gateway=g)
    assert result['status'] == 'available'
    assert result['text'] == 'سلام دنیا'
    assert result['validation']['passed'] is True


def test_translate_to_persian_disabled_provider_is_clearly_reported():
    g = make_gateway(gw.Mode.DISABLED, FakeAdapter('{"text": "x"}'))
    result = ci.translate_to_persian('Hello world', gateway=g)
    assert result['status'] == 'provider_not_configured'
    assert result['text'] is None
    assert result['validation'] is None


def test_translate_to_persian_flags_a_bad_translation_even_though_gateway_says_available():
    # Gateway-valid JSON shape does not mean validator-valid content —
    # both facts must survive into the result, not just the Gateway's.
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, FakeAdapter('{"text": ""}'))
    result = ci.translate_to_persian('Hello world', gateway=g)
    assert result['status'] == 'available'
    assert result['validation']['passed'] is False
    assert 'empty_output' in result['validation']['flags']


# --------------------------------------------------------------------------- summaries

def test_summarize_news_uses_the_default_summary_prompt():
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, FakeAdapter('{"text": "خلاصه خبر"}'))
    result = ci.summarize_news('Some English source text about a topic.', gateway=g)
    assert result['prompt_version'] == gw.LATEST_PROMPT_VERSION['summary']
    assert result['status'] == 'available'


def test_generate_executive_summary_uses_the_executive_prompt_version():
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, FakeAdapter('{"text": "یک جمله"}'))
    result = ci.generate_executive_summary('Some English source text.', gateway=g)
    assert result['prompt_version'] == gw.EXECUTIVE_SUMMARY_PROMPT_VERSION


def test_news_summary_and_executive_summary_are_independent_cache_entries():
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, FakeAdapter('{"text": "x"}'))
    ci.summarize_news('Same text', gateway=g)
    ci.generate_executive_summary('Same text', gateway=g)
    assert g.adapter.calls == 2  # distinct prompt versions -> distinct content hashes, no false cache reuse


# --------------------------------------------------------------------------- key points

def test_extract_key_points_with_real_evidence():
    source = 'The Israeli Air Force conducted a strike near the border on Tuesday.'
    payload = '{"points": [{"text": "نیروی هوایی حمله کرد", "evidence_span": "The Israeli Air Force conducted a strike"}]}'
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, FakeAdapter(payload))
    result = ci.extract_key_points(source, gateway=g)
    assert result['status'] == 'available'
    assert len(result['points']) == 1
    assert result['points'][0]['evidence_verified'] is True


def test_extract_key_points_rejects_fabricated_evidence():
    source = 'The Israeli Air Force conducted a strike near the border on Tuesday.'
    payload = '{"points": [{"text": "روسیه دخالت کرد", "evidence_span": "Russia was directly involved"}]}'
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, FakeAdapter(payload))
    result = ci.extract_key_points(source, gateway=g)
    assert result['status'] == 'available'  # Gateway-valid shape
    assert result['points'][0]['evidence_verified'] is False  # but validator caught the fabrication
    assert 'evidence_not_found_in_source' in result['points'][0]['validation']['flags']


def test_extract_key_points_caps_at_max_points():
    source = 'A B C D E F G H.'
    many_points = ', '.join(f'{{"text": "p{i}", "evidence_span": "{c}"}}' for i, c in enumerate('ABCDEFGH'))
    payload = '{"points": [' + many_points + ']}'
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, FakeAdapter(payload))
    result = ci.extract_key_points(source, gateway=g, max_points=5)
    assert len(result['points']) == 5


def test_extract_key_points_disabled_provider_returns_no_points_not_fake_ones():
    g = make_gateway(gw.Mode.DISABLED, FakeAdapter('{"points": []}'))
    result = ci.extract_key_points('Some text', gateway=g)
    assert result['status'] == 'provider_not_configured'
    assert result['points'] == []

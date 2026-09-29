"""Offline tests for the OpenRouter free-tier-only mode (2026-09-29).

No network: ai_gateway.build_opener is patched with a scripted opener, so the
adapter's real request construction and the gateway's real guards run.
"""
import json
from unittest.mock import patch

import pytest

import ai_gateway as gw

FAKE_KEY = 'test-openrouter-key-not-a-secret'
FREE = 'openrouter/free'


class _Opener:
    def __init__(self, body):
        self.body = body
        self.requests = []

    def open(self, request, timeout=None):
        self.requests.append(json.loads(request.data.decode('utf-8')))
        return _Resp(self.body)


class _Resp:
    def __init__(self, body):
        self._b = body

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _body(cost=0, model='meta-llama/llama-3.3-70b-instruct:free', text='سلام'):
    usage = {'prompt_tokens': 10, 'completion_tokens': 5}
    if cost is not None:
        usage['cost'] = cost
    return json.dumps({'model': model, 'choices': [{'message': {'content': json.dumps({'text': text})}}],
                       'usage': usage}).encode('utf-8')


def _config(translation=FREE, summary=FREE):
    return gw.GatewayConfig(mode=gw.Mode.EXTERNAL_PROVIDER, provider='openrouter', base_url='https://openrouter.ai/api/v1',
                            api_key=FAKE_KEY, models={'translation': translation, 'summary': summary, 'classification': '',
                                                      'signal_analysis': '', 'scenario': ''},
                            timeout_seconds=5, max_concurrency=1, daily_budget_usd=None)


@pytest.fixture(autouse=True)
def _fresh_breakers(monkeypatch):
    monkeypatch.delenv('AI_FREE_ONLY', raising=False)
    gw._BREAKERS.clear()
    yield
    gw._BREAKERS.clear()


def _run(gateway, text='Hello world'):
    return gateway.run(gw.GatewayRequest('translation', text))


def test_openrouter_free_is_allowlisted_and_free():
    assert gw.model_is_approved('openrouter', FREE)
    assert gw.model_is_free('openrouter', FREE)
    assert not gw.model_is_free('openrouter', 'anthropic/claude-haiku-4.5')


def test_free_mode_is_on_whenever_a_free_model_is_configured():
    assert gw.free_only_enabled(_config())
    assert not gw.free_only_enabled(_config('anthropic/claude-haiku-4.5', 'anthropic/claude-haiku-4.5'))


def test_env_flag_forces_free_mode(monkeypatch):
    monkeypatch.setenv('AI_FREE_ONLY', 'true')
    assert gw.free_only_enabled(_config('anthropic/claude-haiku-4.5', 'anthropic/claude-haiku-4.5'))


def test_request_always_carries_exactly_the_free_model_and_no_fallbacks():
    opener = _Opener(_body())
    g = gw.AIGateway(_config())
    with patch('ai_gateway.build_opener', return_value=opener):
        r = _run(g)
    assert r.status == 'available'
    sent = opener.requests[0]
    assert sent['model'] == FREE
    assert 'models' not in sent and 'route' not in sent and 'provider' not in sent
    assert sent['usage'] == {'include': True}


def test_actual_model_and_reported_cost_are_recorded():
    g = gw.AIGateway(_config())
    with patch('ai_gateway.build_opener', return_value=_Opener(_body(cost=0, model='google/gemma-3-27b-it:free'))):
        r = _run(g)
    assert r.model == FREE
    assert r.response_model == 'google/gemma-3-27b-it:free'
    assert r.reported_cost_usd == 0.0
    assert r.estimated_cost_usd == 0.0


def test_nonzero_cost_opens_breaker_and_blocks_further_calls():
    g = gw.AIGateway(_config())
    with patch('ai_gateway.build_opener', return_value=_Opener(_body(cost=0.0004))):
        r = _run(g)
    assert r.status == 'error' and r.error.startswith('nonzero_cost_reported')
    assert r.payload is None, 'a paid response is never used'
    assert g.breaker.is_open
    opener = _Opener(_body())
    with patch('ai_gateway.build_opener', return_value=opener):
        r2 = _run(g, 'Another text')
    assert r2.status == 'circuit_open' and opener.requests == []


def test_missing_cost_report_fails_closed():
    g = gw.AIGateway(_config())
    with patch('ai_gateway.build_opener', return_value=_Opener(_body(cost=None))):
        r = _run(g)
    assert r.status == 'error' and r.error.startswith('cost_not_reported')
    assert g.breaker.is_open


def test_paid_model_refused_before_any_network_call_in_free_mode(monkeypatch):
    monkeypatch.setenv('AI_FREE_ONLY', 'true')
    opener = _Opener(_body())
    g = gw.AIGateway(_config('anthropic/claude-haiku-4.5', 'anthropic/claude-haiku-4.5'))
    with patch('ai_gateway.build_opener', return_value=opener):
        r = _run(g)
    assert r.status == 'error' and r.error == 'free_only_guard:model_not_free'
    assert opener.requests == []


def test_retry_disabled_in_free_mode():
    g = gw.AIGateway(_config())
    assert isinstance(g.adapter, gw.OpenRouterAdapter)
    assert g.adapter.retry_enabled is False
    paid = gw.AIGateway(_config('anthropic/claude-haiku-4.5', 'anthropic/claude-haiku-4.5'))
    assert paid.adapter.retry_enabled is True


def test_rate_limit_is_not_retried_in_free_mode():
    import email.message
    import io
    from urllib.error import HTTPError

    calls = []

    class _RateLimited:
        def open(self, request, timeout=None):
            calls.append(1)
            raise HTTPError('https://openrouter.ai/api/v1/chat/completions', 429, 'rate', email.message.Message(), io.BytesIO(b'{}'))

    g = gw.AIGateway(_config())
    with patch('ai_gateway.build_opener', return_value=_RateLimited()):
        r = _run(g)
    assert r.status == 'error' and r.error.startswith('rate_limited')
    assert len(calls) == 1


def test_parse_response_ignores_non_numeric_cost():
    resp = gw.parse_openrouter_response({'model': 'x:free', 'choices': [{'message': {'content': '{"text":"a"}'}}],
                                         'usage': {'cost': 'n/a'}})
    assert resp.reported_cost_usd is None and resp.response_model == 'x:free'


def test_validator_rejects_persian_output_with_untranslated_english_prose():
    import content_validator as cv
    src = 'U.S. Northern Command plans to sign an agreement with its European counterparts, officials said.'
    mixed = ('فرماندهی شمالی آمریکا قرار است توافق‌نامه‌ای امضا کند. «Over the last couple of years, '
             'we have received a few new missions»، گفت Guillot.')
    clean = 'مقامات گفتند فرماندهی شمالی ایالات متحده (NORTHCOM) قصد دارد با همتایان اروپایی خود توافق‌نامه‌ای امضا کند.'
    bad = cv.validate_translation(src, mixed)
    assert not bad.passed and 'untranslated_english' in bad.flags
    good = cv.validate_translation(src, clean)
    assert 'untranslated_english' not in good.flags

"""Offline tests for OpenRouter free-tier-only mode.

2026-09-29: the Free Router (openrouter/free) was replaced by one pinned
model, google/gemma-4-31b-it:free, after the router picked a model that left
English untranslated. No network: ai_gateway.build_opener is patched with a
scripted opener, so the adapter's real request construction and the
gateway's real guards run.
"""
import email.message
import io
import json
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

import ai_gateway as gw
import content_validator as cv
import enrichment_worker as ew

FAKE_KEY = 'test-openrouter-key-not-a-secret'
PINNED = 'google/gemma-4-31b-it:free'
ROUTER = 'openrouter/free'


class _Opener:
    def __init__(self, body):
        self.body = body
        self.requests = []

    def open(self, request, timeout=None):
        self.requests.append(json.loads(request.data.decode('utf-8')))
        return _Resp(self.body)


class _Resp:
    def __init__(self, b):
        self._b = b

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _body(cost=0, model=PINNED, payload=None):
    usage = {'prompt_tokens': 10, 'completion_tokens': 5}
    if cost is not None:
        usage['cost'] = cost
    content = json.dumps(payload if payload is not None else {'text': 'سلام'})
    return json.dumps({'model': model, 'choices': [{'message': {'content': content}}], 'usage': usage}).encode('utf-8')


def _config(translation=PINNED, summary=PINNED):
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


# ------------------------------------------------------------------ guard
def test_pinned_model_is_allowlisted_and_free_router_is_not_a_pinned_model():
    assert gw.model_is_approved('openrouter', PINNED)
    assert gw.model_is_free('openrouter', PINNED)
    assert not gw.model_is_free('openrouter', ROUTER)
    assert gw.model_is_router('openrouter', ROUTER)
    assert not gw.model_is_free('openrouter', 'anthropic/claude-haiku-4.5')
    assert not gw.model_is_free('openrouter', 'someone/unlisted-model:free'), 'must also be on the allowlist'


def test_free_mode_turns_on_for_any_free_model_or_env(monkeypatch):
    assert gw.free_only_enabled(_config())
    assert gw.free_only_enabled(_config(ROUTER, ROUTER))
    assert not gw.free_only_enabled(_config('anthropic/claude-haiku-4.5', 'anthropic/claude-haiku-4.5'))
    monkeypatch.setenv('AI_FREE_ONLY', 'true')
    assert gw.free_only_enabled(_config('anthropic/claude-haiku-4.5', 'anthropic/claude-haiku-4.5'))


def test_request_carries_exactly_the_pinned_model_and_no_fallbacks():
    opener = _Opener(_body())
    g = gw.AIGateway(_config())
    with patch('ai_gateway.build_opener', return_value=opener):
        r = _run(g)
    assert r.status == 'available'
    sent = opener.requests[0]
    assert sent['model'] == PINNED
    assert 'models' not in sent and 'route' not in sent and 'provider' not in sent
    assert sent['usage'] == {'include': True}
    assert r.response_model == PINNED and r.reported_cost_usd == 0.0


def test_router_refused_before_any_network_call():
    opener = _Opener(_body())
    g = gw.AIGateway(_config(ROUTER, ROUTER))
    with patch('ai_gateway.build_opener', return_value=opener):
        r = _run(g)
    assert r.error == 'free_only_guard:router_not_allowed' and opener.requests == []


def test_paid_model_refused_before_any_network_call(monkeypatch):
    monkeypatch.setenv('AI_FREE_ONLY', 'true')
    opener = _Opener(_body())
    g = gw.AIGateway(_config('anthropic/claude-haiku-4.5', 'anthropic/claude-haiku-4.5'))
    with patch('ai_gateway.build_opener', return_value=opener):
        r = _run(g)
    assert r.error == 'free_only_guard:model_not_free' and opener.requests == []


def test_response_from_a_different_model_stops_everything():
    g = gw.AIGateway(_config())
    with patch('ai_gateway.build_opener', return_value=_Opener(_body(model='meta-llama/llama-3.3-70b-instruct:free'))):
        r = _run(g)
    assert r.status == 'error' and r.error.startswith('model_identity_mismatch')
    assert r.payload is None and g.breaker.is_open


@pytest.mark.parametrize('cost', [0.0004, -0.1])
def test_any_nonzero_cost_opens_breaker(cost):
    g = gw.AIGateway(_config())
    with patch('ai_gateway.build_opener', return_value=_Opener(_body(cost=cost))):
        r = _run(g)
    assert r.error.startswith('nonzero_cost_reported') and g.breaker.is_open
    opener = _Opener(_body())
    with patch('ai_gateway.build_opener', return_value=opener):
        assert _run(g, 'Another').status == 'circuit_open'
    assert opener.requests == []


def test_missing_cost_report_fails_closed():
    g = gw.AIGateway(_config())
    with patch('ai_gateway.build_opener', return_value=_Opener(_body(cost=None))):
        r = _run(g)
    assert r.error.startswith('cost_not_reported') and g.breaker.is_open


def test_retry_disabled_in_free_mode_and_429_not_retried():
    calls = []

    class _RateLimited:
        def open(self, request, timeout=None):
            calls.append(1)
            raise HTTPError('https://openrouter.ai/api/v1/chat/completions', 429, 'rate', email.message.Message(), io.BytesIO(b'{}'))

    g = gw.AIGateway(_config())
    assert g.adapter.retry_enabled is False
    with patch('ai_gateway.build_opener', return_value=_RateLimited()):
        r = _run(g)
    assert r.error.startswith('rate_limited') and len(calls) == 1
    assert gw.AIGateway(_config('anthropic/claude-haiku-4.5', 'anthropic/claude-haiku-4.5')).adapter.retry_enabled is True


def test_translation_schema_is_exact():
    g = gw.AIGateway(_config())
    with patch('ai_gateway.build_opener', return_value=_Opener(_body(payload={'text': 'سلام', 'note': 'I translated it'}))):
        r = _run(g)
    assert r.status == 'invalid_response' and r.error.startswith('unexpected_key:note')


def test_parse_response_ignores_non_numeric_cost():
    resp = gw.parse_openrouter_response({'model': 'x:free', 'choices': [{'message': {'content': '{"text":"a"}'}}],
                                         'usage': {'cost': 'n/a'}})
    assert resp.reported_cost_usd is None and resp.response_model == 'x:free'


# ------------------------------------------------------------------ validator
SRC = ('U.S. Northern Command plans to sign an agreement with its European and Pacific counterparts, '
       'NORTHCOM’s Gen. Gregory M. Guillot told Air & Space Forces Magazine on Sept. 22, 2026.')


def test_entities_and_acronyms_in_latin_are_not_untranslated_english():
    out = ('ژنرال Gregory M. Guillot، فرمانده NORTHCOM، روز ۲۲ سپتامبر ۲۰۲۶ به Air & Space Forces Magazine گفت '
           'فرماندهی شمالی ایالات متحده (U.S. Northern Command) قصد دارد با همتایان اروپایی و آرام خود توافق‌نامه‌ای امضا کند.')
    v = cv.validate_translation(SRC, out)
    assert 'untranslated_english' not in v.flags, v.reasons
    assert v.passed, v.reasons


def test_english_sentence_or_quote_left_untranslated_fails():
    out = ('فرماندهی شمالی قرار است توافق‌نامه‌ای امضا کند. «Over the last couple of years, we have received a few new missions»، '
           'گفت Guillot در ۲۲ سپتامبر ۲۰۲۶.')
    v = cv.validate_translation(SRC + ' "Over the last couple of years, we have received a few new missions."', out)
    assert not v.passed and 'untranslated_english' in v.flags


def test_numbers_with_persian_separators_and_percent_match():
    v = cv.validate_translation('Prices will rise 40% after 13,500 targets and 5,000 sorties.',
                                'قیمت‌ها پس از ۱۳٬۵۰۰ هدف و ۵۰۰۰ سورتی پرواز ۴۰ درصد افزایش می‌یابد.')
    assert 'number_mismatch' not in v.flags and 'number_added' not in v.flags, v.reasons


def test_added_number_and_missing_code_fail():
    v = cv.validate_translation('Latvia orders F-35 jets.', 'لتونی ۱۲ فروند جنگنده سفارش داد.')
    assert not v.passed
    assert 'number_added' in v.flags and 'distinctive_code_missing' in v.flags


def test_markdown_or_model_commentary_fails():
    v = cv.validate_translation('Latvia orders missiles.', '**ترجمه:** لتونی موشک سفارش داد.')
    assert not v.passed and 'model_commentary_or_markdown' in v.flags


def test_output_identical_to_source_fails():
    v = cv.validate_translation('Latvia orders missiles.', 'Latvia orders missiles.')
    assert not v.passed


# ------------------------------------------------------------------ status semantics (regression)
def test_failed_validation_is_never_stored_as_available():
    ok = {'status': 'available', 'validation': {'passed': True, 'flags': []}}
    bad = {'status': 'available', 'validation': {'passed': False, 'flags': ['untranslated_english']}}
    assert ew.current_translation_status(ok) == 'available'
    assert ew.current_translation_status(bad) == 'needs_review'
    assert ew.current_translation_status({'status': 'error', 'validation': None}) == 'error'

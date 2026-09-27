"""Offline tests for OpenRouterAdapter — no network access. HTTP failures are
simulated by monkeypatching ai_gateway.build_opener so the adapter's real
request/error-handling code runs against a scripted response, not a fake
short-circuit like the other adapters' tests use.

Security regression coverage (added after a real incident where a broken
redaction command printed a live key to a session transcript — see
docs/INCIDENT - API KEY EXPOSURE IN SESSION OUTPUT.md): every test here that
touches an "Authorization"-bearing request or an error body containing
key-shaped text asserts the key material never survives into the resulting
GatewayError/GatewayResult — this is the actual data path a real logger or
status endpoint would see, not just a check on _redact() in isolation.
"""
import email.message
import io
from unittest.mock import patch
from urllib.error import HTTPError

import ai_gateway as gw

# A synthetic, obviously-fake fixture value — never derived from, or
# resembling, any real credential this project has ever used.
REAL_LOOKING_KEY = 'test-openrouter-key-not-a-secret'


class _FakeOpener:
    def __init__(self, exc=None, response_body=None):
        self._exc = exc
        self._response_body = response_body
        self.last_request = None

    def open(self, request, timeout=None):
        self.last_request = request
        if self._exc is not None:
            raise self._exc
        return _FakeResponse(self._response_body)


class _FakeResponse:
    def __init__(self, body):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _http_error(code, body=b'{}', headers=None):
    hdrs = email.message.Message()
    for k, v in (headers or {}).items():
        hdrs[k] = v
    return HTTPError('https://openrouter.ai/api/v1/chat/completions', code, 'error', hdrs, io.BytesIO(body))


def _adapter():
    return gw.OpenRouterAdapter(REAL_LOOKING_KEY, 'https://openrouter.ai/api/v1', 'anthropic/claude-haiku-4.5', 5)


def test_default_name_and_base_url():
    a = _adapter()
    assert a.name == 'openrouter'
    assert a.base == 'https://openrouter.ai/api/v1'


def test_missing_key_raises_before_any_request():
    try:
        gw.OpenRouterAdapter('', 'https://openrouter.ai/api/v1', 'anthropic/claude-haiku-4.5', 5)
        assert False, 'expected GatewayError'
    except gw.GatewayError as exc:
        assert 'api_key_missing' in str(exc)


def test_sends_bearer_auth_and_title_header_never_a_fabricated_referer():
    a = _adapter()
    fake = _FakeOpener(response_body=b'{"choices":[{"message":{"content":"{\\"text\\":\\"ok\\"}"}}],"usage":{}}')
    with patch('ai_gateway.build_opener', return_value=fake):
        a.complete('system', 'user')
    headers = {k.lower(): v for k, v in fake.last_request.headers.items()}
    assert headers.get('Authorization'.lower()) == f'Bearer {REAL_LOOKING_KEY}'
    assert headers.get('x-title') == 'Iran Monitor'
    assert 'http-referer' not in headers  # never a fabricated referer for an unhosted deployment


def test_401_is_authentication_failed_and_never_retried():
    a = _adapter()
    fake = _FakeOpener(exc=_http_error(401, b'{"error":"invalid api key"}'))
    with patch('ai_gateway.build_opener', return_value=fake):
        try:
            a.complete('system', 'user')
            assert False, 'expected GatewayError'
        except gw.GatewayError as exc:
            assert str(exc).startswith('authentication_failed:')
    assert a.total_retries == 0  # auth failures are never retried


def test_402_is_insufficient_credits():
    a = _adapter()
    fake = _FakeOpener(exc=_http_error(402, b'{"error":"insufficient credits"}'))
    with patch('ai_gateway.build_opener', return_value=fake):
        try:
            a.complete('system', 'user')
            assert False, 'expected GatewayError'
        except gw.GatewayError as exc:
            assert str(exc).startswith('insufficient_credits:')


def test_403_is_provider_forbidden():
    a = _adapter()
    fake = _FakeOpener(exc=_http_error(403, b'{}'))
    with patch('ai_gateway.build_opener', return_value=fake):
        try:
            a.complete('system', 'user')
            assert False
        except gw.GatewayError as exc:
            assert str(exc).startswith('provider_forbidden:')


def test_400_is_request_invalid_and_never_retried():
    a = _adapter()
    fake = _FakeOpener(exc=_http_error(400, b'{"error":"model not found: bogus/model"}'))
    with patch('ai_gateway.build_opener', return_value=fake):
        try:
            a.complete('system', 'user')
            assert False
        except gw.GatewayError as exc:
            assert str(exc).startswith('request_invalid:')
    assert a.total_retries == 0


def test_429_is_rate_limited_and_retried_exactly_once_then_succeeds():
    a = _adapter()
    call_count = {'n': 0}
    real_open = _FakeOpener.open

    class _SequenceOpener(_FakeOpener):
        def open(self, request, timeout=None):
            call_count['n'] += 1
            if call_count['n'] == 1:
                raise _http_error(429, b'{}', {'Retry-After': '0'})
            return _FakeResponse(b'{"choices":[{"message":{"content":"{\\"text\\":\\"ok\\"}"}}],"usage":{}}')

    with patch('ai_gateway.build_opener', return_value=_SequenceOpener()):
        response = a.complete('system', 'user')
    assert response.raw_text == '{"text":"ok"}'
    assert call_count['n'] == 2
    assert a.total_retries == 1


def test_429_twice_in_a_row_propagates_after_one_retry():
    a = _adapter()
    fake = _FakeOpener(exc=_http_error(429, b'{}'))
    with patch('ai_gateway.build_opener', return_value=fake):
        try:
            a.complete('system', 'user')
            assert False
        except gw.GatewayError as exc:
            assert str(exc).startswith('rate_limited:')
    assert a.total_retries == 1  # exactly one retry attempt, not unbounded


def test_5xx_is_provider_unavailable():
    a = _adapter()
    fake = _FakeOpener(exc=_http_error(503, b'{}'))
    with patch('ai_gateway.build_opener', return_value=fake):
        try:
            a.complete('system', 'user')
            assert False
        except gw.GatewayError as exc:
            assert str(exc).startswith('provider_unavailable:')


# --------------------------------------------------------------------------- security regressions
def test_error_body_containing_key_shaped_text_is_redacted_not_leaked():
    a = _adapter()
    leaking_body = f'{{"error":"rejected token Bearer {REAL_LOOKING_KEY}"}}'.encode()
    fake = _FakeOpener(exc=_http_error(401, leaking_body))
    with patch('ai_gateway.build_opener', return_value=fake):
        try:
            a.complete('system', 'user')
            assert False
        except gw.GatewayError as exc:
            assert REAL_LOOKING_KEY not in str(exc)
            assert 'REDACTED' in str(exc)


def test_gateway_result_error_never_contains_the_key_end_to_end():
    """The exact value a real PostgresLogger row or /api/v1/ai/status caller
    would see is GatewayResult.error — this proves the full run() path,
    not just the adapter in isolation."""
    config = gw.GatewayConfig(mode=gw.Mode.EXTERNAL_PROVIDER, provider='openrouter',
                               base_url='https://openrouter.ai/api/v1', api_key=REAL_LOOKING_KEY,
                               models={'translation': 'anthropic/claude-haiku-4.5', 'summary': 'anthropic/claude-haiku-4.5',
                                       'classification': '', 'signal_analysis': '', 'scenario': ''},
                               timeout_seconds=5, max_concurrency=3, daily_budget_usd=None)
    gateway = gw.AIGateway(config=config)
    fake = _FakeOpener(exc=_http_error(401, f'Bearer {REAL_LOOKING_KEY} invalid'.encode()))
    with patch('ai_gateway.build_opener', return_value=fake):
        result = gateway.run(gw.GatewayRequest('translation', 'Iran test headline'))
    assert result.status == 'error'
    assert REAL_LOOKING_KEY not in (result.error or '')
    assert REAL_LOOKING_KEY not in repr(result)
    assert REAL_LOOKING_KEY not in repr(gateway.adapter)  # default repr — no custom leak added


def test_adapter_registered_and_default_base_url():
    assert gw.ADAPTER_REGISTRY['openrouter'] is gw.OpenRouterAdapter
    assert gw._default_base_url('openrouter') == 'https://openrouter.ai/api/v1'


def test_model_allowlist_accepts_approved_and_rejects_unknown():
    assert gw.model_is_approved('openrouter', 'anthropic/claude-haiku-4.5') is True
    assert gw.model_is_approved('openrouter', 'openrouter/free-something') is False
    assert gw.model_is_approved('openrouter', 'anthropic/claude-opus-5') is False


def test_gateway_uses_the_correct_per_task_model_for_openrouter():
    """Regression: run() only overrode adapter.model for OpenAICompatibleAdapter
    and AnthropicAdapter instances, so a Gateway configured with different
    translation/summary models would have silently kept using whichever one
    build_adapter() happened to initialize with, for every task, once
    OpenRouterAdapter was added — this proves the fix."""
    config = gw.GatewayConfig(mode=gw.Mode.EXTERNAL_PROVIDER, provider='openrouter',
                               base_url='https://openrouter.ai/api/v1', api_key=REAL_LOOKING_KEY,
                               models={'translation': 'model-a', 'summary': 'model-b',
                                       'classification': '', 'signal_analysis': '', 'scenario': ''},
                               timeout_seconds=5, max_concurrency=3, daily_budget_usd=None)
    gateway = gw.AIGateway(config=config)
    fake = _FakeOpener(response_body=b'{"choices":[{"message":{"content":"{\\"text\\":\\"ok\\"}"}}],"usage":{}}')
    with patch('ai_gateway.build_opener', return_value=fake):
        result = gateway.run(gw.GatewayRequest('summary', 'some text'))
    assert result.model == 'model-b'

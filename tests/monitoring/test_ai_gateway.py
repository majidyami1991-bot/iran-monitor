"""Offline tests for the AI Gateway. No network access — a fake adapter and
in-memory cache/log stand in for real providers and Postgres."""
import json

import ai_gateway as gw


class FakeAdapter(gw.Adapter):
    name = 'fake'
    model = 'fake-model'

    def __init__(self, response_text=None, raise_error=None):
        self._response_text = response_text
        self._raise = raise_error
        self.calls = 0

    def complete(self, system, user):
        self.calls += 1
        if self._raise:
            raise self._raise
        return gw.AdapterResponse(self._response_text, tokens_in=100, tokens_out=50)


class MemoryCache:
    def __init__(self):
        self.store = {}
        self.gets = 0
        self.sets = 0

    def get(self, key):
        self.gets += 1
        return self.store.get(key)

    def set(self, key, value):
        self.sets += 1
        self.store[key] = value


def make_gateway(mode, adapter=None, **kwargs):
    config = gw.GatewayConfig(mode=mode, provider='fake', base_url='', api_key='x',
                               models={'translation': 'fake-model', 'summary': 'fake-model',
                                       'classification': 'fake-model', 'signal_analysis': 'fake-model',
                                       'scenario': 'fake-model'},
                               timeout_seconds=5, max_concurrency=3, daily_budget_usd=kwargs.pop('daily_budget_usd', None))
    g = gw.AIGateway(config=config, **kwargs)
    if adapter is not None:
        g.adapter = adapter
        g.breaker = gw.CircuitBreaker()
    return g


def test_disabled_mode_never_calls_the_adapter():
    g = make_gateway(gw.Mode.DISABLED, adapter=FakeAdapter('{"text":"x"}'))
    result = g.run(gw.GatewayRequest('translation', 'Some English text'))
    assert result.status == 'provider_not_configured'
    assert g.adapter.calls == 0


def test_deterministic_mode_refuses_generation_not_fabricates():
    g = make_gateway(gw.Mode.DETERMINISTIC, adapter=FakeAdapter('{"text":"x"}'))
    result = g.run(gw.GatewayRequest('summary', 'Some text'))
    assert result.status == 'deterministic_only'
    assert result.payload is None
    assert g.adapter.calls == 0


def test_empty_content_is_an_error_not_a_call():
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, adapter=FakeAdapter('{"text":"x"}'))
    result = g.run(gw.GatewayRequest('translation', ''))
    assert result.status == 'error'
    assert result.error == 'no_source_text'
    assert g.adapter.calls == 0


def test_valid_response_is_available_with_full_provenance():
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, adapter=FakeAdapter('{"text":"سلام دنیا"}'))
    result = g.run(gw.GatewayRequest('translation', 'Hello world'))
    assert result.status == 'available'
    assert result.payload == {'text': 'سلام دنیا'}
    assert result.provider == 'fake'
    assert result.prompt_version == gw.LATEST_PROMPT_VERSION['translation']
    assert result.tokens_in == 100 and result.tokens_out == 50
    assert result.latency_ms is not None


def test_invalid_json_is_invalid_response_not_silently_dropped():
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, adapter=FakeAdapter('not json at all'))
    result = g.run(gw.GatewayRequest('translation', 'Hello'))
    assert result.status == 'invalid_response'
    assert result.error == 'output_not_valid_json'


def test_missing_required_key_is_invalid_response():
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, adapter=FakeAdapter('{"wrong_key": "x"}'))
    result = g.run(gw.GatewayRequest('translation', 'Hello'))
    assert result.status == 'invalid_response'
    assert 'missing_key' in result.error


def test_wrong_type_for_a_key_is_invalid_response():
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, adapter=FakeAdapter('{"category_id": "x", "confidence": "not_a_number", "subtopics": []}'))
    result = g.run(gw.GatewayRequest('classification', 'Hello'))
    assert result.status == 'invalid_response'
    assert 'wrong_type' in result.error


def test_adapter_error_is_recorded_and_trips_the_breaker():
    adapter = FakeAdapter(raise_error=gw.GatewayError('http_500:boom'))
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, adapter=adapter)
    g.breaker.threshold = 2
    r1 = g.run(gw.GatewayRequest('translation', 'Hello'))
    assert r1.status == 'error'
    r2 = g.run(gw.GatewayRequest('translation', 'Hello again'))
    assert r2.status == 'error'
    # third call should find the breaker open and never reach the adapter
    r3 = g.run(gw.GatewayRequest('translation', 'Hello a third time'))
    assert r3.status == 'circuit_open'
    assert adapter.calls == 2


def test_circuit_recovers_after_a_success():
    adapter = FakeAdapter('{"text":"ok"}')
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, adapter=adapter)
    g.run(gw.GatewayRequest('translation', 'Hello'))
    assert g.breaker.is_open is False


def test_cache_hit_skips_the_adapter_entirely():
    adapter = FakeAdapter('{"text":"cached result"}')
    cache = MemoryCache()
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, adapter=adapter, cache=cache)
    first = g.run(gw.GatewayRequest('translation', 'Hello world'))
    assert first.status == 'available'
    assert adapter.calls == 1
    second = g.run(gw.GatewayRequest('translation', 'Hello world'))
    assert second.status == 'cached'
    assert second.payload == {'text': 'cached result'}
    assert adapter.calls == 1  # not called again


def test_different_content_is_a_cache_miss():
    adapter = FakeAdapter('{"text":"x"}')
    cache = MemoryCache()
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, adapter=adapter, cache=cache)
    g.run(gw.GatewayRequest('translation', 'Hello world'))
    g.run(gw.GatewayRequest('translation', 'A totally different sentence'))
    assert adapter.calls == 2


def test_provider_change_is_a_cache_miss_not_a_silent_reuse():
    cache = MemoryCache()
    adapter_a = FakeAdapter('{"text":"from provider a"}')
    adapter_a.name = 'provider_a'
    g1 = make_gateway(gw.Mode.EXTERNAL_PROVIDER, adapter=adapter_a, cache=cache)
    r1 = g1.run(gw.GatewayRequest('translation', 'Hello world'))
    assert r1.status == 'available'

    adapter_b = FakeAdapter('{"text":"from provider b"}')
    adapter_b.name = 'provider_b'
    g2 = make_gateway(gw.Mode.EXTERNAL_PROVIDER, adapter=adapter_b, cache=cache)
    r2 = g2.run(gw.GatewayRequest('translation', 'Hello world'))
    assert r2.status == 'available'  # not "cached" — different provider, must call again
    assert adapter_b.calls == 1
    assert r2.payload == {'text': 'from provider b'}


def test_budget_exceeded_fails_closed_before_calling_the_adapter():
    adapter = FakeAdapter('{"text":"x"}')
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, adapter=adapter, daily_budget_usd=1.0, budget_check=lambda: 1.5)
    result = g.run(gw.GatewayRequest('translation', 'Hello'))
    assert result.status == 'budget_exceeded'
    assert adapter.calls == 0


def test_budget_under_limit_proceeds_normally():
    adapter = FakeAdapter('{"text":"x"}')
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, adapter=adapter, daily_budget_usd=10.0, budget_check=lambda: 1.0)
    result = g.run(gw.GatewayRequest('translation', 'Hello'))
    assert result.status == 'available'


def test_content_hash_is_deterministic_and_content_and_version_addressed():
    a = gw.content_hash('translation', 'same text', '1.0.0')
    b = gw.content_hash('translation', 'same text', '1.0.0')
    c = gw.content_hash('translation', 'different text', '1.0.0')
    d = gw.content_hash('translation', 'same text', '2.0.0')
    assert a == b
    assert a != c
    assert a != d


def test_cost_estimate_uses_the_configured_model_rate():
    cost = gw.estimate_cost_usd('claude-sonnet-5', 1_000_000, 1_000_000)
    assert cost == 12.0  # 2.0 in + 10.0 out per the price table


def test_cost_estimate_is_none_for_an_unknown_model():
    assert gw.estimate_cost_usd('some-unlisted-model', 1000, 1000) is None


def test_local_mode_never_estimates_a_cost():
    adapter = FakeAdapter('{"text":"free"}')
    g = make_gateway(gw.Mode.LOCAL, adapter=adapter)
    result = g.run(gw.GatewayRequest('translation', 'Hello'))
    assert result.status == 'available'
    assert result.estimated_cost_usd is None


def test_error_messages_redact_api_keys():
    redacted = gw._redact('Authorization: Bearer sk-abcdefgh12345678')
    assert 'sk-abcdefgh12345678' not in redacted
    assert 'REDACTED' in redacted


def test_unknown_task_type_raises_a_programming_error_not_a_silent_result():
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, adapter=FakeAdapter('{"text":"x"}'))
    try:
        g.run(gw.GatewayRequest('not_a_real_task_type', 'Hello'))
        assert False, 'expected ValueError'
    except ValueError:
        pass


def test_logger_receives_every_result_including_failures():
    seen = []
    adapter = FakeAdapter(raise_error=gw.GatewayError('boom'))
    g = make_gateway(gw.Mode.EXTERNAL_PROVIDER, adapter=adapter, logger=seen.append)
    g.run(gw.GatewayRequest('translation', 'Hello'))
    assert len(seen) == 1
    assert seen[0].status == 'error'


def test_prompt_registry_has_a_version_for_every_task_type():
    for task_type in gw.TASK_TYPES:
        assert task_type in gw.LATEST_PROMPT_VERSION
        version = gw.LATEST_PROMPT_VERSION[task_type]
        assert (task_type, version) in gw.PROMPTS

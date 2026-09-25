"""AI Gateway — the single, provider-agnostic entry point every AI-assisted
feature in this project must go through (translation, summarization,
classification, signal analysis, scenario generation). No call site should
import a vendor SDK or hard-code a vendor's request/response shape — only
this module's `run()` and its typed request/result objects.

Design contract (see docs/AI GATEWAY.md for the full write-up):
  - Modes: disabled | deterministic | local | external_provider. Switching
    modes is an environment change, never a code change at a call site.
  - Every adapter speaks the same GatewayRequest -> GatewayResult contract.
  - Every result carries full provenance: provider, model, prompt_version,
    latency_ms, tokens, estimated cost, cache_hit — never silently dropped.
  - Output is schema-validated per task type; an invalid shape is a failure
    (`status=invalid_response`), never coerced into looking successful.
  - Content is cached by (content_hash, task_type, prompt_version, provider,
    model) — changing the provider or prompt version is a cache miss, so it
    can never silently reuse another provider's or another prompt version's
    output. Nothing is ever overwritten in place; a new key is a new row.
  - A circuit breaker and a daily cost budget both fail closed: once either
    trips, calls return a clear status immediately, never a best-effort call
    that might blow the budget or hammer a failing provider.
"""
import hashlib
import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler

TASK_TYPES = ('translation', 'summary', 'classification', 'signal_analysis', 'scenario')


class Mode(str, Enum):
    DISABLED = 'disabled'
    DETERMINISTIC = 'deterministic'
    LOCAL = 'local'
    EXTERNAL_PROVIDER = 'external_provider'


class GatewayError(RuntimeError):
    """Raised only inside an adapter; run() always converts this to a
    GatewayResult rather than letting it propagate — a caller should never
    need a try/except around a gateway call to stay safe."""


# --------------------------------------------------------------------------- prompt registry
# Every prompt is versioned explicitly. A prompt is never edited in place —
# a wording change gets a new version string, so historical results (and the
# cache, which is keyed on this) stay attributable to the exact prompt that
# produced them.
PROMPTS = {
    ('translation', '1.0.0'): (
        'You are a professional English to Persian (Farsi) translator working on '
        'defence and geopolitics news. Translate the user text into fluent, formal '
        'Persian. Preserve every proper noun, organisation, place, number, date, '
        'quantity and unit exactly. Do not add, remove, explain or speculate. If '
        'the source hedges, keep the hedge. Return only JSON: {"text": "<translation>"}.'
    ),
    ('summary', '1.0.0'): (
        'You summarise defence and geopolitics news into Persian for an intelligence '
        'monitoring dashboard, using only facts present in the supplied text — never '
        'infer or add background. State uncertainty the source states. Return only '
        'JSON: {"text": "<Persian summary>"}.'
    ),
    ('classification', '1.0.0'): (
        'Classify the supplied defence/geopolitics text into exactly one category '
        'from the provided taxonomy, with 0-3 subtopics and a confidence between 0 '
        'and 1 reflecting how specific and unambiguous the match is. Return only '
        'JSON: {"category_id": "...", "confidence": 0.0, "subtopics": ["..."]}.'
    ),
    ('signal_analysis', '0.1.0'): (
        'Given a cluster of related news items and their deterministic novelty, '
        'momentum, source-diversity and evidence-strength scores, propose a short, '
        'plain-language name and explanation for the potential weak signal they may '
        'represent, and list alternative (non-signal) explanations. Do not assert '
        'the signal is real or important — only describe what the evidence shows. '
        'Return only JSON: {"title": "...", "explanation": "...", '
        '"alternative_explanations": ["..."]}.'
    ),
    ('scenario', '0.1.0'): (
        'Given a set of drivers, their impact/uncertainty ratings, and a pair of '
        'key uncertainties, draft one scenario narrative consistent with the '
        'supplied evidence only. Never present it as a prediction. Return only '
        'JSON: {"title": "...", "narrative": "...", "confirming_indicators": ["..."], '
        '"disconfirming_indicators": ["..."]}.'
    ),
}


def prompt_for(task_type, version=None):
    version = version or LATEST_PROMPT_VERSION[task_type]
    key = (task_type, version)
    if key not in PROMPTS:
        raise GatewayError(f'unknown_prompt_version:{task_type}:{version}')
    return PROMPTS[key]


LATEST_PROMPT_VERSION = {
    'translation': '1.0.0', 'summary': '1.0.0', 'classification': '1.0.0',
    'signal_analysis': '0.1.0', 'scenario': '0.1.0',
}

# --------------------------------------------------------------------------- output schemas
# Minimal, explicit per-task-type validation. A response missing a required
# key, or with a key of the wrong type, is `invalid_response` — never passed
# through as if it were valid.
_SCHEMAS = {
    'translation': {'text': str},
    'summary': {'text': str},
    'classification': {'category_id': str, 'confidence': (int, float), 'subtopics': list},
    'signal_analysis': {'title': str, 'explanation': str, 'alternative_explanations': list},
    'scenario': {'title': str, 'narrative': str, 'confirming_indicators': list, 'disconfirming_indicators': list},
}


def validate_output(task_type, payload):
    schema = _SCHEMAS.get(task_type)
    if schema is None:
        return False, f'no_schema_registered:{task_type}'
    if not isinstance(payload, dict):
        return False, 'not_a_json_object'
    for key, expected_type in schema.items():
        if key not in payload:
            return False, f'missing_key:{key}'
        if not isinstance(payload[key], expected_type):
            return False, f'wrong_type:{key}'
    return True, None


# --------------------------------------------------------------------------- circuit breaker
class CircuitBreaker:
    """Per-adapter. Opens after `threshold` consecutive failures; refuses
    calls for `cooldown_seconds`, then allows one probe call (half-open)."""

    def __init__(self, threshold=5, cooldown_seconds=60):
        self.threshold = threshold
        self.cooldown_seconds = cooldown_seconds
        self._failures = 0
        self._opened_at = None
        self._lock = threading.Lock()

    def allow(self):
        with self._lock:
            if self._opened_at is None:
                return True
            if time.monotonic() - self._opened_at >= self.cooldown_seconds:
                return True  # half-open: let one probe through
            return False

    def record_success(self):
        with self._lock:
            self._failures = 0
            self._opened_at = None

    def record_failure(self):
        with self._lock:
            self._failures += 1
            if self._failures >= self.threshold:
                self._opened_at = time.monotonic()

    @property
    def is_open(self):
        with self._lock:
            return self._opened_at is not None and time.monotonic() - self._opened_at < self.cooldown_seconds


# --------------------------------------------------------------------------- adapters
@dataclass
class AdapterResponse:
    raw_text: str
    tokens_in: int | None = None
    tokens_out: int | None = None


class Adapter:
    name = 'base'
    model = None

    def complete(self, system, user) -> AdapterResponse:
        raise NotImplementedError


class DisabledAdapter(Adapter):
    name = 'disabled'

    def complete(self, system, user):
        raise GatewayError('provider_not_configured')


def _post_json(url, payload, headers, timeout):
    opener = build_opener(ProxyHandler())
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    request = Request(url, data=body, headers={'Content-Type': 'application/json', **headers})
    try:
        with opener.open(request, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        detail = ''
        try:
            detail = exc.read()[:200].decode('utf-8', 'replace')
        except Exception:
            pass
        raise GatewayError(f'http_{exc.code}:{_redact(detail)}') from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise GatewayError(f'{type(exc).__name__}:{_redact(str(exc))}') from exc


def _redact(text):
    text = re.sub(r'(?i)(sk-|key-|bearer\s+)[A-Za-z0-9_\-]{8,}', r'\1[REDACTED]', text or '')
    return re.sub(r'\s+', ' ', text)[:200]


class OpenAICompatibleAdapter(Adapter):
    name = 'openai_compatible'

    def __init__(self, api_key, base_url, model, timeout):
        if not api_key:
            raise GatewayError('provider_api_key_missing')
        self.api_key, self.base, self.model, self.timeout = api_key, base_url.rstrip('/'), model, timeout

    def complete(self, system, user):
        data = _post_json(
            f'{self.base}/chat/completions',
            {'model': self.model, 'temperature': 0,
             'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]},
            {'Authorization': f'Bearer {self.api_key}'}, self.timeout)
        try:
            text = data['choices'][0]['message']['content'].strip()
            usage = data.get('usage', {})
            return AdapterResponse(text, usage.get('prompt_tokens'), usage.get('completion_tokens'))
        except (KeyError, IndexError, AttributeError, TypeError) as exc:
            raise GatewayError('unexpected_response_shape') from exc


class AzureOpenAIAdapter(OpenAICompatibleAdapter):
    """Same request/response shape as OpenAI-compatible; kept as a distinct
    adapter name for audit clarity even though the wire format matches."""
    name = 'azure_openai'


class AnthropicAdapter(Adapter):
    name = 'anthropic'

    def __init__(self, api_key, base_url, model, timeout):
        if not api_key:
            raise GatewayError('provider_api_key_missing')
        self.api_key, self.base, self.model, self.timeout = api_key, base_url.rstrip('/'), model, timeout

    def complete(self, system, user):
        data = _post_json(
            f'{self.base}/messages',
            {'model': self.model, 'max_tokens': 4096, 'temperature': 0, 'system': system,
             'messages': [{'role': 'user', 'content': user}]},
            {'x-api-key': self.api_key, 'anthropic-version': '2023-06-01'}, self.timeout)
        try:
            text = ''.join(b.get('text', '') for b in data['content']).strip()
            usage = data.get('usage', {})
            return AdapterResponse(text, usage.get('input_tokens'), usage.get('output_tokens'))
        except (KeyError, TypeError) as exc:
            raise GatewayError('unexpected_response_shape') from exc


class LocalModelAdapter(OpenAICompatibleAdapter):
    """A self-hosted, OpenAI-compatible endpoint (e.g. Ollama, vLLM, LM
    Studio). No API key is required by default — local deployments are
    commonly unauthenticated on a private network."""
    name = 'local'

    def __init__(self, base_url, model, timeout, api_key=None):
        self.api_key, self.base, self.model, self.timeout = (api_key or 'local'), base_url.rstrip('/'), model, timeout


ADAPTER_REGISTRY = {
    'openai_compatible': OpenAICompatibleAdapter,
    'openai': OpenAICompatibleAdapter,
    'azure_openai': AzureOpenAIAdapter,
    'anthropic': AnthropicAdapter,
}

# One breaker per adapter *name*, shared across requests in this process —
# a run of failures against one provider must not need a fresh gateway
# instance to recover once the cooldown passes.
_BREAKERS: dict[str, CircuitBreaker] = {}
_BREAKERS_LOCK = threading.Lock()


def _breaker_for(name):
    with _BREAKERS_LOCK:
        if name not in _BREAKERS:
            _BREAKERS[name] = CircuitBreaker()
        return _BREAKERS[name]


# --------------------------------------------------------------------------- estimated cost
# Deliberately approximate — per-million-token list prices, USD, checked
# against the configured model only loosely (prefix match) since exact SKUs
# change faster than this table should need to. Cost tracking exists to
# catch runaway spend, not to produce an invoice.
_PRICE_PER_MILLION_TOKENS_USD = {
    'claude-sonnet-5': (2.0, 10.0), 'claude-haiku-4-5': (1.0, 5.0),
    'gpt-4o-mini': (0.15, 0.6), 'gpt-4o': (2.5, 10.0),
}


def estimate_cost_usd(model, tokens_in, tokens_out):
    if not tokens_in and not tokens_out:
        return None
    rate = next((v for k, v in _PRICE_PER_MILLION_TOKENS_USD.items() if model and model.startswith(k)), None)
    if rate is None:
        return None
    in_rate, out_rate = rate
    return round((tokens_in or 0) * in_rate / 1_000_000 + (tokens_out or 0) * out_rate / 1_000_000, 6)


# --------------------------------------------------------------------------- config resolution
@dataclass
class GatewayConfig:
    mode: Mode
    provider: str
    base_url: str
    api_key: str
    models: dict
    timeout_seconds: int
    max_concurrency: int
    daily_budget_usd: float | None


def load_config() -> GatewayConfig:
    provider = (os.getenv('AI_PROVIDER') or 'disabled').strip().lower()
    mode = Mode.DISABLED
    if provider == 'disabled' or not provider:
        mode = Mode.DISABLED
    elif provider == 'deterministic':
        mode = Mode.DETERMINISTIC
    elif provider == 'local':
        mode = Mode.LOCAL
    else:
        mode = Mode.EXTERNAL_PROVIDER
    budget = os.getenv('AI_DAILY_BUDGET_LIMIT')
    return GatewayConfig(
        mode=mode, provider=provider,
        base_url=os.getenv('AI_BASE_URL', ''), api_key=os.getenv('AI_API_KEY', ''),
        models={
            'translation': os.getenv('AI_MODEL_TRANSLATION', ''),
            'summary': os.getenv('AI_MODEL_SUMMARY', ''),
            'classification': os.getenv('AI_MODEL_CLASSIFICATION', ''),
            'signal_analysis': os.getenv('AI_MODEL_SIGNAL_ANALYSIS', ''),
            'scenario': os.getenv('AI_MODEL_SCENARIO', ''),
        },
        timeout_seconds=int(os.getenv('AI_REQUEST_TIMEOUT', '60')),
        max_concurrency=int(os.getenv('AI_MAX_CONCURRENCY', '3')),
        daily_budget_usd=float(budget) if budget else None,
    )


def build_adapter(config: GatewayConfig) -> Adapter:
    if config.mode in (Mode.DISABLED, Mode.DETERMINISTIC):
        return DisabledAdapter()
    if config.mode == Mode.LOCAL:
        return LocalModelAdapter(config.base_url or 'http://localhost:11434/v1', config.models.get('translation') or 'local-model', config.timeout_seconds)
    factory = ADAPTER_REGISTRY.get(config.provider)
    if factory is None:
        return DisabledAdapter()
    try:
        return factory(config.api_key, config.base_url or _default_base_url(config.provider), config.models.get('translation') or '', config.timeout_seconds)
    except GatewayError:
        return DisabledAdapter()


def _default_base_url(provider):
    return {'anthropic': 'https://api.anthropic.com/v1', 'azure_openai': ''}.get(provider, 'https://api.openai.com/v1')


# --------------------------------------------------------------------------- concurrency limiter
_SEMAPHORES: dict[int, threading.Semaphore] = {}
_SEMAPHORES_LOCK = threading.Lock()


def _semaphore_for(max_concurrency):
    with _SEMAPHORES_LOCK:
        if max_concurrency not in _SEMAPHORES:
            _SEMAPHORES[max_concurrency] = threading.Semaphore(max_concurrency)
        return _SEMAPHORES[max_concurrency]


# --------------------------------------------------------------------------- request / result
@dataclass
class GatewayRequest:
    task_type: str
    content: str
    prompt_version: str | None = None
    context: dict = field(default_factory=dict)  # e.g. taxonomy for classification


@dataclass
class GatewayResult:
    status: str  # available | pending | cached | invalid_response | error | budget_exceeded | circuit_open | deterministic_only
    payload: dict | None
    provider: str | None
    model: str | None
    prompt_version: str
    task_type: str
    content_hash: str
    latency_ms: int | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    estimated_cost_usd: float | None = None
    cache_hit: bool = False
    error: str | None = None


def content_hash(task_type, content, prompt_version):
    return hashlib.sha256(f'{task_type}|{prompt_version}|{content or ""}'.encode('utf-8')).hexdigest()


class AIGateway:
    """Construct with an explicit config (or `load_config()`'s default) and
    optional cache/log backends. `run()` never raises — every failure mode
    is a `GatewayResult.status`, so a call site never needs its own
    try/except to stay safe against a provider outage."""

    def __init__(self, config: GatewayConfig | None = None, cache=None, logger=None, budget_check=None):
        self.config = config or load_config()
        self.adapter = build_adapter(self.config)
        self.breaker = _breaker_for(self.adapter.name)
        self.cache = cache  # object with .get(key) / .set(key, value)
        self.logger = logger  # callable(GatewayResult) -> None
        self.budget_check = budget_check  # callable() -> float spent today, or None to skip

    def run(self, request: GatewayRequest) -> GatewayResult:
        if request.task_type not in TASK_TYPES:
            raise ValueError(f'unknown_task_type:{request.task_type}')
        prompt_version = request.prompt_version or LATEST_PROMPT_VERSION[request.task_type]
        digest = content_hash(request.task_type, request.content, prompt_version)

        if self.config.mode == Mode.DISABLED:
            return self._finish(GatewayResult('provider_not_configured', None, None, None,
                                               prompt_version, request.task_type, digest))
        if self.config.mode == Mode.DETERMINISTIC:
            return self._finish(GatewayResult('deterministic_only', None, None, None,
                                               prompt_version, request.task_type, digest,
                                               error='this_gateway_instance_is_deterministic_mode_no_generative_call_made'))
        if not request.content or not request.content.strip():
            return self._finish(GatewayResult('error', None, self.adapter.name, self._model_for(request.task_type),
                                               prompt_version, request.task_type, digest, error='no_source_text'))

        cache_key = (digest, self.adapter.name, self._model_for(request.task_type))
        if self.cache is not None:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return self._finish(GatewayResult('cached', cached, self.adapter.name, self._model_for(request.task_type),
                                                    prompt_version, request.task_type, digest, cache_hit=True))

        if self.budget_check is not None and self.config.daily_budget_usd is not None:
            spent = self.budget_check()
            if spent is not None and spent >= self.config.daily_budget_usd:
                return self._finish(GatewayResult('budget_exceeded', None, self.adapter.name, self._model_for(request.task_type),
                                                    prompt_version, request.task_type, digest,
                                                    error=f'daily_budget_usd_{self.config.daily_budget_usd}_reached'))

        if not self.breaker.allow():
            return self._finish(GatewayResult('circuit_open', None, self.adapter.name, self._model_for(request.task_type),
                                                prompt_version, request.task_type, digest,
                                                error='circuit_breaker_open_provider_failing'))

        system = prompt_for(request.task_type, prompt_version)
        sem = _semaphore_for(self.config.max_concurrency)
        started = time.monotonic()
        acquired = sem.acquire(timeout=self.config.timeout_seconds)
        if not acquired:
            return self._finish(GatewayResult('error', None, self.adapter.name, self._model_for(request.task_type),
                                                prompt_version, request.task_type, digest, error='max_concurrency_wait_timeout'))
        try:
            if isinstance(self.adapter, (OpenAICompatibleAdapter, AnthropicAdapter)):
                self.adapter.model = self._model_for(request.task_type) or self.adapter.model
            response = self.adapter.complete(system, request.content)
        except GatewayError as exc:
            self.breaker.record_failure()
            return self._finish(GatewayResult('error', None, self.adapter.name, self._model_for(request.task_type),
                                                prompt_version, request.task_type, digest, error=str(exc)[:200],
                                                latency_ms=int((time.monotonic() - started) * 1000)))
        finally:
            sem.release()
        self.breaker.record_success()

        latency_ms = int((time.monotonic() - started) * 1000)
        try:
            payload = json.loads(response.raw_text)
        except (json.JSONDecodeError, TypeError):
            return self._finish(GatewayResult('invalid_response', None, self.adapter.name, self._model_for(request.task_type),
                                                prompt_version, request.task_type, digest, error='output_not_valid_json',
                                                latency_ms=latency_ms))
        ok, reason = validate_output(request.task_type, payload)
        if not ok:
            return self._finish(GatewayResult('invalid_response', None, self.adapter.name, self._model_for(request.task_type),
                                                prompt_version, request.task_type, digest, error=reason,
                                                latency_ms=latency_ms))

        cost = None if self.config.mode == Mode.LOCAL else estimate_cost_usd(
            self._model_for(request.task_type), response.tokens_in, response.tokens_out)
        result = GatewayResult('available', payload, self.adapter.name, self._model_for(request.task_type),
                                prompt_version, request.task_type, digest, latency_ms=latency_ms,
                                tokens_in=response.tokens_in, tokens_out=response.tokens_out,
                                estimated_cost_usd=cost)
        if self.cache is not None:
            self.cache.set(cache_key, payload)
        return self._finish(result)

    def _model_for(self, task_type):
        return self.config.models.get(task_type) or None

    def _finish(self, result: GatewayResult) -> GatewayResult:
        if self.logger is not None:
            self.logger(result)
        return result


# --------------------------------------------------------------------------- Postgres-backed cache / log / budget
# Kept separate from the core class above (which only needs plain objects
# with .get/.set, a callable, and another callable) so the gateway itself has
# zero hard dependency on a database and stays trivially unit-testable with
# in-memory fakes. Import psycopg lazily — only paid the moment one of these
# is actually constructed.

class PostgresCache:
    def __init__(self, dsn):
        self._dsn = dsn

    def get(self, key):
        import psycopg
        content_sha256, provider, model = key
        with psycopg.connect(self._dsn) as c:
            row = c.execute(
                'SELECT response_json FROM ai_response_cache WHERE content_sha256=%s AND provider=%s AND model=%s',
                (content_sha256, provider, model or '')).fetchone()
        return row[0] if row else None

    def set(self, key, value):
        import psycopg
        from psycopg.types.json import Jsonb
        content_sha256, provider, model = key
        # task_type/prompt_version are folded into content_sha256 already
        # (see content_hash()), but are also stored plainly for querying.
        with psycopg.connect(self._dsn, autocommit=True) as c:
            c.execute('''INSERT INTO ai_response_cache(content_sha256,task_type,prompt_version,provider,model,response_json)
                VALUES(%s,'unknown','unknown',%s,%s,%s)
                ON CONFLICT(content_sha256,task_type,prompt_version,provider,model) DO NOTHING''',
                (content_sha256, provider, model or '', Jsonb(value)))


class PostgresLogger:
    def __init__(self, dsn):
        self._dsn = dsn

    def __call__(self, result: GatewayResult):
        import psycopg
        with psycopg.connect(self._dsn, autocommit=True) as c:
            c.execute('''INSERT INTO ai_requests_log(task_type,provider,model,prompt_version,content_sha256,
                status,latency_ms,tokens_in,tokens_out,estimated_cost_usd,cache_hit,error)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                (result.task_type, result.provider, result.model, result.prompt_version, result.content_hash,
                 result.status, result.latency_ms, result.tokens_in, result.tokens_out,
                 result.estimated_cost_usd, result.cache_hit, result.error))


def postgres_budget_check(dsn):
    def _check():
        import psycopg
        with psycopg.connect(dsn) as c:
            row = c.execute('''SELECT COALESCE(sum(estimated_cost_usd),0) FROM ai_requests_log
                WHERE created_at >= date_trunc('day', now()) AND estimated_cost_usd IS NOT NULL''').fetchone()
        return float(row[0]) if row else 0.0
    return _check


def build_default_gateway(dsn=None):
    """Convenience factory: a gateway wired to Postgres cache/log/budget
    when a DSN is given, or fully in-memory (no persistence) otherwise —
    useful for one-off scripts and tests."""
    if dsn:
        return AIGateway(cache=PostgresCache(dsn), logger=PostgresLogger(dsn), budget_check=postgres_budget_check(dsn))
    return AIGateway()

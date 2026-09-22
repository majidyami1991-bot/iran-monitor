"""Configurable Persian translation and summarisation providers.

No provider is enabled by default. With `NEWS_TRANSLATION_PROVIDER` unset every
request resolves to `pending`, which is what the API and UI then display. The
system never invents a translation or a summary: an absent provider produces an
absent field, never generated text.
"""
import json, os, re, time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler

TIMEOUT = int(os.getenv('NEWS_TRANSLATION_TIMEOUT_SECONDS', '60'))
MAX_INPUT_CHARS = int(os.getenv('NEWS_TRANSLATION_MAX_INPUT_CHARS', '12000'))
SUMMARY_SENTENCES = 3

TRANSLATE_SYSTEM = (
    'You are a professional English to Persian (Farsi) translator working on defence and '
    'geopolitics news. Translate the user text into fluent, formal Persian. Preserve every '
    'proper noun, organisation, place, number, date, quantity and unit exactly. Do not add, '
    'remove, explain or speculate. If the source hedges, keep the hedge. Return only the '
    'Persian translation.')
SUMMARY_SYSTEM = (
    'You summarise defence and geopolitics news into Persian for an intelligence monitoring '
    f'dashboard. Write at most {SUMMARY_SENTENCES} short Persian sentences covering what '
    'happened, who is involved and when. Keep all names, numbers and dates exactly as given. '
    'State uncertainty that the source states. Use only facts present in the supplied text; '
    'never infer or add background. Return only the Persian summary.')


class ProviderError(RuntimeError):
    """Raised when a configured provider fails; the caller records `error`."""


class Provider:
    name = 'base'
    model = None

    def complete(self, system, user):
        raise NotImplementedError


class NullProvider(Provider):
    """Stands in when nothing is configured. Always reports work as pending."""
    name = 'none'

    def complete(self, system, user):
        raise ProviderError('translation_provider_not_configured')


def _post_json(url, payload, headers):
    opener = build_opener(ProxyHandler())
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    request = Request(url, data=body, headers={'Content-Type': 'application/json', **headers})
    try:
        with opener.open(request, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        detail = ''
        try:
            detail = exc.read()[:200].decode('utf-8', 'replace')
        except Exception:
            pass
        raise ProviderError(f'http_{exc.code}:{_redact(detail)}') from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise ProviderError(f'{type(exc).__name__}:{_redact(str(exc))}') from exc


def _redact(text):
    text = re.sub(r'(?i)(sk-|key-|bearer\s+)[A-Za-z0-9_\-]{8,}', r'\1[REDACTED]', text or '')
    return re.sub(r'\s+', ' ', text)[:160]


class OpenAICompatibleProvider(Provider):
    """Chat-completions API shape, as served by OpenAI, Azure OpenAI and gateways."""
    name = 'openai_compatible'

    def __init__(self):
        self.key = os.getenv('NEWS_TRANSLATION_API_KEY')
        self.base = os.getenv('NEWS_TRANSLATION_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
        self.model = os.getenv('NEWS_TRANSLATION_MODEL', 'gpt-4o-mini')
        if not self.key:
            raise ProviderError('translation_api_key_missing')

    def complete(self, system, user):
        data = _post_json(f'{self.base}/chat/completions',
            {'model': self.model, 'temperature': 0,
             'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]},
            {'Authorization': f'Bearer {self.key}'})
        try:
            return data['choices'][0]['message']['content'].strip()
        except (KeyError, IndexError, AttributeError, TypeError) as exc:
            raise ProviderError('unexpected_response_shape') from exc


class AnthropicProvider(Provider):
    name = 'anthropic'

    def __init__(self):
        self.key = os.getenv('NEWS_TRANSLATION_API_KEY')
        self.base = os.getenv('NEWS_TRANSLATION_BASE_URL', 'https://api.anthropic.com/v1').rstrip('/')
        self.model = os.getenv('NEWS_TRANSLATION_MODEL', 'claude-sonnet-5')
        if not self.key:
            raise ProviderError('translation_api_key_missing')

    def complete(self, system, user):
        data = _post_json(f'{self.base}/messages',
            {'model': self.model, 'max_tokens': 4096, 'temperature': 0, 'system': system,
             'messages': [{'role': 'user', 'content': user}]},
            {'x-api-key': self.key, 'anthropic-version': '2023-06-01'})
        try:
            return ''.join(b.get('text', '') for b in data['content']).strip()
        except (KeyError, TypeError) as exc:
            raise ProviderError('unexpected_response_shape') from exc


PROVIDERS = {'none': NullProvider, 'openai': OpenAICompatibleProvider,
             'openai_compatible': OpenAICompatibleProvider, 'azure_openai': OpenAICompatibleProvider,
             'anthropic': AnthropicProvider}


def build_provider():
    """Return the configured provider, or NullProvider when none is usable."""
    name = (os.getenv('NEWS_TRANSLATION_PROVIDER') or 'none').strip().lower()
    factory = PROVIDERS.get(name)
    if factory is None or factory is NullProvider:
        return NullProvider()
    try:
        return factory()
    except ProviderError:
        return NullProvider()


def _looks_persian(text):
    """Guard against a provider echoing the English input back."""
    if not text:
        return False
    persian = sum(1 for ch in text if '؀' <= ch <= 'ۿ')
    return persian >= max(8, len(text.strip()) * 0.2)


def run_task(provider, kind, text):
    """Execute one translation or summary. Returns a status dict, never raises.

    Statuses: `available` with text, `pending` when no provider is configured,
    `unavailable` when there is no source text, `error` with a sanitized reason.
    """
    if not text or not text.strip():
        return {'status': 'unavailable', 'text': None, 'error': 'no_source_text',
                'provider': provider.name, 'model': provider.model}
    if isinstance(provider, NullProvider):
        return {'status': 'pending', 'text': None, 'error': None,
                'provider': None, 'model': None}
    system = TRANSLATE_SYSTEM if kind == 'translation' else SUMMARY_SYSTEM
    started = time.monotonic()
    try:
        output = provider.complete(system, text[:MAX_INPUT_CHARS])
    except ProviderError as exc:
        return {'status': 'error', 'text': None, 'error': _redact(str(exc)),
                'provider': provider.name, 'model': provider.model}
    if not _looks_persian(output):
        return {'status': 'error', 'text': None, 'error': 'output_not_persian',
                'provider': provider.name, 'model': provider.model}
    return {'status': 'available', 'text': output.strip(), 'error': None,
            'provider': provider.name, 'model': provider.model,
            'latency_ms': int((time.monotonic() - started) * 1000),
            'source_chars': min(len(text), MAX_INPUT_CHARS)}

"""Offline tests for local (Ollama) X post translation: validator, adapter,
gateway wiring and the worker's decision logic. No database and no external
network: the "Ollama" here is a fake HTTP server on 127.0.0.1."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

import ai_gateway as gw
import x_translate_worker as xw
import x_translation_validator as xv

FIX = json.loads((Path(__file__).parent / 'fixtures' / 'x_translation_fixtures.json').read_text(encoding='utf-8'))
MODEL = 'gemma4:e2b'
DIGEST = '7fbdbf8f5e45' + '0' * 52


# ------------------------------------------------------------------ fake Ollama
class Fake:
    mode = 'ok'            # ok | invalid_json | fenced | wrong_model | slow | http500 | truncated | not_required
    reply = None           # dict for translation payload
    tags_models = [{'name': MODEL, 'digest': DIGEST}]
    chat_calls = 0
    last_body = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj=None, raw=None):
        body = raw if raw is not None else json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/api/tags':
            return self._send(200, {'models': Fake.tags_models})
        self._send(404, {'error': 'not found'})

    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        Fake.last_body = json.loads(self.rfile.read(n).decode('utf-8'))
        Fake.chat_calls += 1
        if Fake.mode == 'slow':
            time.sleep(1.5)
        if Fake.mode == 'http500':
            return self._send(500, {'error': 'boom'})
        payload = Fake.reply or {'detected_language': 'en', 'translation_fa': 'نیروی دریایی تأیید کرد که رزمایش به‌سلامت پایان یافت.',
                                 'translation_not_required': False, 'quality_notes': []}
        content = json.dumps(payload, ensure_ascii=False)
        if Fake.mode == 'invalid_json':
            content = 'Here is the translation: نیروی دریایی ...'
        if Fake.mode == 'fenced':
            content = '```json\n' + content + '\n```'
        out = {'model': 'gemma3:1b' if Fake.mode == 'wrong_model' else MODEL, 'message': {'role': 'assistant', 'content': content},
               'done': True, 'done_reason': 'length' if Fake.mode == 'truncated' else 'stop',
               'prompt_eval_count': 300, 'eval_count': 90}
        try:
            self._send(200, out)
        except (BrokenPipeError, ConnectionResetError):
            pass


@pytest.fixture(scope='module')
def server():
    srv = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f'http://127.0.0.1:{srv.server_address[1]}'
    srv.shutdown()


@pytest.fixture(autouse=True)
def reset():
    Fake.mode, Fake.reply, Fake.chat_calls, Fake.last_body = 'ok', None, 0, None
    Fake.tags_models = [{'name': MODEL, 'digest': DIGEST}]
    gw._BREAKERS.clear()
    yield


def gateway(base, timeout=5, cache=None, digest='7fbdbf8f5e45', model=MODEL):
    cfg = gw.GatewayConfig(gw.Mode.LOCAL, 'ollama', base, '', {'x_post_translation': model}, timeout, 1, None,
                           {'expected_digest': digest, 'num_thread': 8})
    return gw.AIGateway(cfg, cache=cache)


def req(text='The navy confirmed that the exercise ended safely.'):
    return gw.GatewayRequest('x_post_translation', xw.model_input(text))


class MemCache:
    def __init__(self):
        self.d = {}

    def get(self, k):
        return self.d.get(k)

    def set(self, k, v):
        self.d[k] = v


# ------------------------------------------------------------------ validator (fixtures 1-10, 12-15)
@pytest.mark.parametrize('f', FIX['good'], ids=[f['case'] for f in FIX['good']])
def test_good_translations_pass(f):
    r = xv.validate(f['source'], f['translation'])
    assert r.passed, (f['case'], r.flags, r.reasons)


def test_persian_source_is_not_required():
    assert xv.is_persian_source(FIX['persian_source']['source'])
    assert not xv.is_persian_source('CENTCOM says an MQ-9 was lost. #OSINT')
    assert not xv.is_persian_source('https://x.com/a/status/1 @user')


@pytest.mark.parametrize('f', FIX['bad'], ids=[f['case'] for f in FIX['bad']])
def test_bad_translations_need_review(f):
    r = xv.validate(f['source'], f['translation'])
    assert not r.passed, f['case']
    assert f['expect_flag'] in r.flags, (f['case'], r.flags)


def test_acronyms_and_names_are_not_untranslated_prose():
    src = 'OSINT, IMINT and ELINT teams at CENTCOM and NORTHCOM tracked the F-35 and J-20 flights.'
    out = 'تیم‌های OSINT، IMINT و ELINT در CENTCOM و NORTHCOM پروازهای F-35 و J-20 را ردیابی کردند.'
    r = xv.validate(src, out)
    assert r.passed, r.flags


def test_status_url_digits_do_not_count_as_numbers():
    src = 'See https://x.com/someone/status/1876543210987654321 for the clip.'
    out = 'ویدیو را در https://x.com/someone/status/1876543210987654321 ببینید.'
    assert xv.validate(src, out).passed


def test_empty_output_fails():
    assert xv.validate('Anything at all here.', '   ').flags == ['empty_output']


# ------------------------------------------------------------------ adapter + gateway
def test_adapter_refuses_non_local_hosts():
    for base in ('http://example.com:11434', 'https://127.0.0.1:11434', 'http://10.0.0.5:11434', 'http://openrouter.ai'):
        with pytest.raises(gw.GatewayError):
            gw.OllamaAdapter(base, MODEL, 5)
    cfg = gw.GatewayConfig(gw.Mode.LOCAL, 'ollama', 'http://api.openai.com', '', {'x_post_translation': MODEL}, 5, 1, None)
    assert isinstance(gw.build_adapter(cfg), gw.DisabledAdapter)


def test_request_body_is_cpu_bounded_and_structured(server):
    a = gw.OllamaAdapter(server, MODEL, 5, num_thread=8)
    a.json_schema = gw.OUTPUT_JSON_SCHEMAS['x_post_translation']
    b = a.request_body('sys', 'x' * 100)
    assert b['think'] is False and b['stream'] is False
    assert b['options']['temperature'] == 0.1 and b['options']['num_ctx'] <= 4096 and b['options']['num_thread'] == 8
    assert 192 <= b['options']['num_predict'] <= 1536
    assert a.request_body('sys', 'x' * 100000)['options']['num_predict'] == 1536
    assert b['format']['required'] == ['detected_language', 'translation_fa', 'translation_not_required', 'quality_notes']


def test_gateway_success_records_provenance_and_zero_cost(server):
    r = gateway(server).run(req())
    assert r.status == 'available'
    assert r.provider == 'ollama/local' and r.model == MODEL and r.response_model == MODEL
    assert r.prompt_version == 'x-post-translation-fa-v1.0.0'
    assert r.estimated_cost_usd == 0 and r.reported_cost_usd == 0
    assert r.latency_ms is not None and r.tokens_out == 90
    assert Fake.last_body['options']['num_thread'] == 8


def test_invalid_json_is_invalid_response(server):
    Fake.mode = 'invalid_json'
    r = gateway(server).run(req())
    assert r.status == 'invalid_response' and r.error == 'output_not_valid_json'
    assert xw.decide('x', r)['status'] == 'failed'


def test_single_fenced_block_is_unwrapped(server):
    Fake.mode = 'fenced'
    assert gateway(server).run(req()).status == 'available'
    assert gw.strip_json_fence('noise ```json\n{"a":1}\n```') == 'noise ```json\n{"a":1}\n```'


def test_extra_keys_are_rejected(server):
    Fake.reply = {'detected_language': 'en', 'translation_fa': 'متن', 'translation_not_required': False,
                  'quality_notes': [], 'explanation': 'added'}
    r = gateway(server).run(req())
    assert r.status == 'invalid_response' and r.error.startswith('unexpected_key')


def test_timeout_is_transient_and_retryable(server):
    Fake.mode = 'slow'
    r = gateway(server, timeout=1).run(req())
    assert r.status == 'error' and xw.error_class(r.error) == 'transient_timeout'
    d = xw.decide('x', r)
    assert d['status'] == 'failed' and d['retryable'] is True and d['stop_batch'] is False


def test_http_500_is_transient(server):
    Fake.mode = 'http500'
    d = xw.decide('x', gateway(server).run(req()))
    assert d['retryable'] is True


def test_ollama_unavailable_stops_batch():
    r = gateway('http://127.0.0.1:9', timeout=2).run(req())  # port 9 (discard): nothing listens
    assert r.status == 'error' and xw.error_class(r.error) == 'provider_unreachable'
    d = xw.decide('x', r)
    assert d['stop_batch'] is True and d['status'] == 'pending'


def test_model_missing_or_mismatched_fails_closed(server):
    Fake.tags_models = [{'name': 'gemma3:1b', 'digest': 'abc'}]
    r = gateway(server).run(req())
    assert xw.error_class(r.error) == 'model_not_found' and xw.decide('x', r)['stop_batch']
    Fake.tags_models = [{'name': MODEL, 'digest': 'ffff' * 16}]
    gw._BREAKERS.clear()
    r = gateway(server).run(req())
    assert xw.error_class(r.error) == 'model_digest_mismatch'
    Fake.tags_models = [{'name': MODEL, 'digest': DIGEST}]
    Fake.mode = 'wrong_model'
    gw._BREAKERS.clear()
    r = gateway(server).run(req())
    assert xw.error_class(r.error) == 'model_identity_mismatch' and xw.decide('x', r)['stop_batch']


def test_unapproved_model_never_called(server):
    r = gateway(server, model='llama3:70b').run(req())
    assert r.error == 'model_not_approved' and Fake.chat_calls == 0


def test_truncated_output_is_failed_not_available(server):
    Fake.mode = 'truncated'
    r = gateway(server).run(req())
    assert xw.error_class(r.error) == 'output_truncated_num_predict'
    assert xw.decide('x', r)['status'] == 'failed'


def test_cache_hit_makes_no_provider_call(server):
    cache = MemCache()
    g = gateway(server, cache=cache)
    assert g.run(req()).status == 'available' and Fake.chat_calls == 1
    r = g.run(req())
    assert r.cache_hit and r.status == 'cached' and Fake.chat_calls == 1


def test_free_only_guard_does_not_block_local(server, monkeypatch):
    monkeypatch.setenv('AI_FREE_ONLY', 'true')
    assert gateway(server).run(req()).status == 'available'


# ------------------------------------------------------------------ worker decisions and settings
class R:
    def __init__(self, status, payload=None, error=None):
        self.status, self.payload, self.error = status, payload, error


def test_decide_available_and_review():
    src = FIX['good'][4]['source']
    ok = xw.decide(src, R('available', {'detected_language': 'en', 'translation_fa': FIX['good'][4]['translation'],
                                        'translation_not_required': False, 'quality_notes': []}))
    assert ok['status'] == 'available' and ok['translated_text'] and ok['source_language'] == 'en'
    bad = xw.decide(src, R('available', {'detected_language': 'en', 'translation_fa': FIX['bad'][2]['translation'],
                                         'translation_not_required': False, 'quality_notes': []}))
    assert bad['status'] == 'needs_review' and 'number_added' in bad['flags']


def test_decide_not_required_only_for_persian_source():
    p = {'detected_language': 'fa', 'translation_fa': '', 'translation_not_required': True, 'quality_notes': []}
    assert xw.decide(FIX['persian_source']['source'], R('available', p))['status'] == 'not_required'
    d = xw.decide('The navy confirmed that the exercise ended safely.', R('available', p))
    assert d['status'] == 'needs_review' and d['flags'] == ['model_claimed_not_required']


def test_settings_enforce_single_worker(monkeypatch):
    monkeypatch.setenv('OLLAMA_MODEL_TRANSLATION', MODEL)
    monkeypatch.setenv('X_TRANSLATION_CONCURRENCY', '2')
    monkeypatch.setenv('X_TRANSLATION_MAX_ATTEMPTS', '5')
    monkeypatch.setenv('X_TRANSLATION_TIMEOUT_SECONDS', '3600')
    monkeypatch.setenv('OLLAMA_NUM_CTX', '32768')
    s = xw.load_settings()
    assert 'X_TRANSLATION_CONCURRENCY must be 1' in s.errors
    assert s.max_attempts == 2 and s.timeout_seconds == 600 and s.num_ctx == 4096
    assert s.enabled is False  # off unless explicitly enabled
    monkeypatch.setenv('OLLAMA_MODEL_TRANSLATION', 'llama3:70b')
    monkeypatch.setenv('X_TRANSLATION_CONCURRENCY', '1')
    assert 'OLLAMA_MODEL_TRANSLATION is not an approved model' in xw.load_settings().errors


def test_run_batch_refuses_misconfiguration_and_disabled(monkeypatch):
    monkeypatch.setenv('OLLAMA_MODEL_TRANSLATION', MODEL)
    s = xw.load_settings()
    assert xw.run_batch('postgresql://unused', s).stopped_reason == 'x_translation_disabled'
    s.errors = ['X_TRANSLATION_CONCURRENCY must be 1']
    with pytest.raises(RuntimeError):
        xw.run_batch('postgresql://unused', s)


def test_source_hash_and_model_input():
    assert xw.source_hash('a') != xw.source_hash('a ')
    mi = json.loads(xw.model_input('Hello @x https://e.org'))
    assert mi == {'task': 'translate_x_post_to_persian', 'source_language': 'auto', 'target_language': 'fa',
                  'post_text': 'Hello @x https://e.org'}

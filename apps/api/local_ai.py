"""Shared plumbing for the local (Ollama, CPU-only) AI features: settings,
the gateway wired to gemma4:e2b, and the two PostgreSQL advisory locks.

    BATCH_LOCK      one translation batch per database (shared with
                    x_translate_worker, which uses the same key)
    INFERENCE_LOCK  one model inference at a time across translation AND the
                    assistant, in every process — the CPU runs one generation,
                    and anyone else waits or is told the model is busy

No cloud provider is reachable from here: OllamaAdapter accepts local hosts
only and the model must match the approved name and digest.
"""
import contextlib
import os
import time
from dataclasses import dataclass, field

import psycopg
from psycopg.rows import dict_row

import ai_gateway as gw
import model_identity as mi

BATCH_LOCK = 7_270_061
INFERENCE_LOCK = 7_270_062
ASSISTANT_WAITING = 7_270_063   # shared lock held by interactive assistant requests while they wait for the model


@dataclass
class LocalAISettings:
    provider: str
    base_url: str
    model: str
    expected_digest: str | None
    num_ctx: int
    temperature: float
    max_output_tokens: int
    concurrency: int
    timeout_seconds: int
    num_thread: int | None
    keep_alive: str
    errors: list = field(default_factory=list)
    approval: dict | None = None
    seed: int | None = None
    translation_max_output_tokens: int = 1536


def _int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def load_settings(allow_proposed=None, role=None):
    """allow_proposed: an approval id admitted for an offline evaluation run
    only (quality gate). Stored content is never produced in that mode."""
    s = LocalAISettings(
        provider=(os.getenv('LOCAL_AI_PROVIDER') or 'ollama').strip().lower(),
        base_url=(os.getenv('OLLAMA_BASE_URL') or 'http://host.docker.internal:11434').strip(),
        model=(os.getenv('OLLAMA_MODEL') or '').strip(),
        expected_digest=(os.getenv('OLLAMA_MODEL_DIGEST') or '').strip() or None,
        num_ctx=max(1024, min(_int('LOCAL_AI_NUM_CTX', 4096), 4096)),
        temperature=float(os.getenv('LOCAL_AI_TEMPERATURE', '0.1') or 0.1),
        max_output_tokens=max(64, min(_int('LOCAL_AI_MAX_OUTPUT_TOKENS', 512), 512)),
        concurrency=_int('LOCAL_AI_CONCURRENCY', 1),
        timeout_seconds=max(30, min(_int('LOCAL_AI_TIMEOUT_SECONDS', 900), 900)),
        num_thread=_int('LOCAL_AI_NUM_THREAD', 8) or None,
        keep_alive=(os.getenv('OLLAMA_KEEP_ALIVE') or '5m').strip(),
    )
    try:
        contract = mi.load_contract()
        s.approval = mi.active_approval(contract, allow_proposed=allow_proposed, role=role)
    except (OSError, ValueError, KeyError):
        s.approval = None
    if s.approval is None:
        s.errors.append('no_approved_model_artifact')
    else:
        rt = s.approval.get('runtime') or {}
        s.seed = rt.get('seed')
        s.translation_max_output_tokens = rt.get('translation_max_output_tokens', 1536)
        if role is None and mi.role_of(s.approval) != 'both':
            s.errors.append('role_required_for_role_scoped_approval')  # never serve a role-scoped model to an unspecified caller
        if s.model and s.model != s.approval['tag'] and role is None:
            s.errors.append('OLLAMA_MODEL is not the approved immutable tag')
        if s.expected_digest and not s.approval['manifest_digest'].startswith(s.expected_digest):
            s.errors.append('OLLAMA_MODEL_DIGEST does not match the approved manifest digest')
        s.expected_digest = s.approval['manifest_digest']
        s.model = s.approval['tag']  # the contract names the exact tag; env may not redirect it
        s.max_output_tokens = min(s.max_output_tokens, rt.get('assistant_max_output_tokens') or s.max_output_tokens)
        s.temperature = rt.get('temperature', s.temperature)
    if s.provider != 'ollama':
        s.errors.append('LOCAL_AI_PROVIDER must be ollama')
    if s.concurrency != 1:
        s.errors.append('LOCAL_AI_CONCURRENCY must be 1')
    if not s.model:
        s.errors.append('OLLAMA_MODEL is not set')
    elif not gw.model_is_approved('ollama', s.model):
        s.errors.append('OLLAMA_MODEL is not an approved model')
    return s


def gateway_config(s, task_type):
    return gw.GatewayConfig(
        mode=gw.Mode.LOCAL, provider='ollama', base_url=s.base_url, api_key='', models={task_type: s.model},
        timeout_seconds=s.timeout_seconds, max_concurrency=1, daily_budget_usd=None,
        options={'expected_digest': s.expected_digest, 'num_ctx': s.num_ctx, 'num_thread': s.num_thread,
                 'temperature': s.temperature, 'keep_alive': s.keep_alive, 'max_predict': s.max_output_tokens,
                 'seed': s.seed})


class ContractCache(gw.PostgresCache):
    """Response cache keyed additionally by the identity fingerprint, so any
    change of weights, runner, Ollama version, digests, parameters or prompt
    versions is a cache miss."""

    def __init__(self, dsn, fp):
        super().__init__(dsn)
        self.fp = fp

    def _k(self, key):
        content_sha256, provider, model = key
        return (content_sha256, provider, f'{model or ""}|{self.fp[:32]}')

    def get(self, key):
        return super().get(self._k(key))

    def set(self, key, value):
        return super().set(self._k(key), value)


def runtime_params(s, kind):
    p = {'temperature': s.temperature, 'num_ctx': s.num_ctx, 'num_thread': s.num_thread, 'seed': s.seed}
    if kind == 'translation':
        p['translation_max'] = s.max_output_tokens
    elif kind == 'assistant':
        p['assistant_max'] = s.max_output_tokens
    return p


def preflight(s, kind, timeout=5):
    """Full identity check (version, tag digests, attestation, params).
    Raises mi.IdentityError; returns facts."""
    if s.approval is None:
        raise mi.IdentityError('no_approved_model_artifact')
    return mi.verify(s.approval, s.base_url, runtime_params(s, kind), timeout=timeout)


def build_gateway(s, dsn, task_type, use_cache=True):
    fp = mi.fingerprint(s.approval) if s.approval else 'none'
    g = gw.AIGateway(gateway_config(s, task_type), cache=ContractCache(dsn, fp) if use_cache and dsn else None,
                     logger=gw.PostgresLogger(dsn) if dsn else None)
    if isinstance(g.adapter, gw.OllamaAdapter) and s.approval:
        approval, base = s.approval, s.base_url
        g.adapter.post_check = lambda: mi.check_loaded(approval, base)
    return g


_PROBE = {'at': 0.0, 'value': (False, False, None)}


def probe(s, timeout=2, ttl=30.0):
    """(reachable, model_found, digest12) via /api/tags only; cached ttl s."""
    if gw.local_ai_disabled_reason():
        return (False, False, None)                     # operator switch: no request to Ollama
    now = time.monotonic()
    if now - _PROBE['at'] <= ttl:
        return _PROBE['value']
    try:
        a = gw.OllamaAdapter(s.base_url, s.model or 'unset', timeout, expected_digest=s.expected_digest)
        digest = a.verify_model(timeout=timeout)[:12]
        preflight(s, 'probe', timeout=timeout)  # version, tag digests, attestation, params
        value = (True, True, digest)
    except gw.GatewayError as exc:
        value = (not str(exc).startswith(('provider_unreachable', 'transient_timeout', 'ollama_host_not_local')), False, None)
    except mi.IdentityError as exc:
        value = (not str(exc).startswith('identity_provider_unreachable'), False, None)
        _PROBE['reason'] = str(exc)
    _PROBE['at'], _PROBE['value'] = now, value
    return value


# ------------------------------------------------------------------ locks
def connect(dsn):
    return psycopg.connect(dsn, row_factory=dict_row, autocommit=True)


def lock_held(conn, key):
    r = conn.cursor(row_factory=dict_row).execute(
        "SELECT count(*) AS n FROM pg_locks WHERE locktype='advisory' AND granted AND classid=0 AND objid=%s",
        (key,)).fetchone()
    return r['n'] > 0


def disabled_state():
    """None, or {'state', 'message_fa'} while the operator switch is set."""
    r = gw.local_ai_disabled_reason()
    return {'state': r, 'message_fa': gw.LOCAL_AI_DISABLED_FA} if r else None


def make_room_for(tag, base_url, timeout=60):
    """Unload every OTHER model resident in Ollama before `tag` is used. Called while
    holding INFERENCE_LOCK, so no other call is running. Keeps the 27B translator and
    the qwen3 assistant from being resident together (host commit memory is limited:
    co-residency evicted/reloaded models and once ended in provider_unreachable)."""
    if gw.local_ai_disabled_reason():
        return []
    import json as _json
    from urllib.request import ProxyHandler as _P, Request as _R, build_opener as _b
    op = _b(_P({}))
    try:
        with op.open(_R(base_url.rstrip('/') + '/api/ps'), timeout=5) as r:
            loaded = [m.get('name') for m in _json.loads(r.read()).get('models', [])]
    except OSError:
        return []
    others = [m for m in loaded if m and m != tag]
    for m in others:
        try:
            op.open(_R(base_url.rstrip('/') + '/api/generate', _json.dumps({'model': m, 'keep_alive': 0}).encode(),
                       {'Content-Type': 'application/json'}), timeout=30).read()
        except OSError:
            pass
    deadline = time.monotonic() + timeout
    while others and time.monotonic() < deadline:
        try:
            with op.open(_R(base_url.rstrip('/') + '/api/ps'), timeout=5) as r:
                if not [m.get('name') for m in _json.loads(r.read()).get('models', []) if m.get('name') in others]:
                    break
        except OSError:
            break
        time.sleep(1)
    return others


class Busy(RuntimeError):
    """The inference lock could not be taken in time (or the wait was cancelled)."""


@contextlib.contextmanager
def inference_lock(dsn, wait_seconds=0.0, should_cancel=lambda: False, poll=0.5, priority=False, yield_to_priority=False,
                   yield_grace_seconds=0):
    """Hold INFERENCE_LOCK for one model call. Waits up to wait_seconds,
    polling should_cancel(); raises Busy if the lock is not obtained.
    priority=True (interactive assistant): announces itself with a SHARED
    ASSISTANT_WAITING lock while it waits. yield_to_priority=True (background
    translator): does not start a call while anyone holds ASSISTANT_WAITING."""
    conn = psycopg.connect(dsn, autocommit=True)
    try:
        if priority:
            conn.execute('SELECT pg_advisory_lock_shared(%s)', (ASSISTANT_WAITING,))
        deadline = time.monotonic() + wait_seconds
        while True:
            waiting = yield_to_priority and conn.execute(
                "SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND granted AND classid=0 AND objid=%s",
                (ASSISTANT_WAITING,)).fetchone()[0] > 0
            if yield_to_priority and not waiting and yield_grace_seconds:
                # a conversation in progress keeps its model: no background call within the grace window
                waiting = conn.execute("SELECT EXISTS (SELECT 1 FROM assistant_messages WHERE created_at > now() - make_interval(secs => %s))",
                                       (yield_grace_seconds,)).fetchone()[0]
            if not waiting and conn.execute('SELECT pg_try_advisory_lock(%s)', (INFERENCE_LOCK,)).fetchone()[0]:
                if priority:
                    conn.execute('SELECT pg_advisory_unlock_shared(%s)', (ASSISTANT_WAITING,))
                break
            if should_cancel():
                raise Busy('cancelled')
            if time.monotonic() >= deadline:
                raise Busy('model_busy')
            time.sleep(poll)
        try:
            yield
        finally:
            conn.execute('SELECT pg_advisory_unlock(%s)', (INFERENCE_LOCK,))
    finally:
        conn.close()

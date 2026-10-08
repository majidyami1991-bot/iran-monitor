"""Offline tests for the model identity guard (contract + attestation +
live API checks against a fake Ollama on 127.0.0.1)."""
import copy
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import ai_gateway as gw
import local_ai
import model_identity as mi

CONTRACT = mi.load_contract()
NEW = 'gemma4-e2b-ollama0401-llamacpp-d1e84c607e13'
APPROVAL = next(a for a in CONTRACT['approvals'] if a['id'] == NEW)


class Fake:
    version = '0.40.1'
    tags = [{'name': APPROVAL['tag'], 'digest': d} for d in APPROVAL['tag_entry_digests']]
    ps = [{'name': APPROVAL['tag'], 'digest': APPROVAL['manifest_digest'], 'size_vram': 0}]


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        body = {'/api/version': {'version': Fake.version}, '/api/tags': {'models': Fake.tags},
                '/api/ps': {'models': Fake.ps}}.get(self.path)
        raw = json.dumps(body or {}).encode()
        self.send_response(200 if body is not None else 404)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


@pytest.fixture(scope='module')
def base():
    srv = ThreadingHTTPServer(('127.0.0.1', 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{srv.server_address[1]}'
    srv.shutdown()


@pytest.fixture(autouse=True)
def reset():
    Fake.version = '0.40.1'
    Fake.tags = [{'name': APPROVAL['tag'], 'digest': d} for d in APPROVAL['tag_entry_digests']]
    Fake.ps = [{'name': APPROVAL['tag'], 'digest': APPROVAL['manifest_digest'], 'size_vram': 0}]


def attestation(tmp_path, **over):
    a = {'approval_id': NEW, 'passed': True, 'ollama_version': '0.40.1', 'runner': 'llamacpp',
         'manifest_digest': APPROVAL['manifest_digest'], 'model_blob_sha256': APPROVAL['model_blob_sha256'],
         'mmproj_blob_sha256': APPROVAL['mmproj_blob_sha256'], 'size_vram': 0}
    a.update(over)
    p = tmp_path / 'att.json'
    p.write_text(json.dumps(a))
    return p


PARAMS = {'temperature': 0.1, 'num_ctx': 4096, 'num_thread': 8, 'seed': 42}


# ------------------------------------------------------------------ contract / history
def test_history_is_append_only_and_state_derived():
    state = mi.approval_state(CONTRACT)
    assert state['gemma4-e2b-archive-7fbdbf8f5e45'] == 'superseded'
    assert state[NEW] in ('proposed', 'approved', 'rejected_quality_gate')
    ev = [e['event'] for e in CONTRACT['events'] if e['approval'] == 'gemma4-e2b-archive-7fbdbf8f5e45']
    assert ev[:2] == ['approved', 'superseded']  # history kept, not rewritten


def test_proposed_artifact_only_for_explicit_evaluation():
    c = copy.deepcopy(CONTRACT)
    c['events'] = [e for e in c['events'] if not (e['approval'] == NEW and e['event'] != 'proposed')]
    assert mi.active_approval(c) is None
    assert mi.active_approval(c, allow_proposed=NEW)['id'] == NEW
    c['events'].append({'approval': NEW, 'event': 'approved'})
    assert mi.active_approval(c)['id'] == NEW
    c['events'].append({'approval': NEW, 'event': 'revoked'})
    assert mi.active_approval(c) is None


def test_fingerprint_changes_with_any_identity_input():
    fp = mi.fingerprint(APPROVAL)
    for key, val in (('model_blob_sha256', 'f' * 64), ('mmproj_blob_sha256', 'e' * 64), ('runner', 'ggml'),
                     ('ollama_version', '0.41.0'), ('manifest_digest', 'a' * 64), ('prompt_versions', ['x'])):
        changed = dict(APPROVAL, **{key: val})
        assert mi.fingerprint(changed) != fp, key
    rt = dict(APPROVAL, runtime=dict(APPROVAL['runtime'], temperature=0.2))
    assert mi.fingerprint(rt) != fp
    assert mi.fingerprint(dict(APPROVAL, manifest_list_digest='0' * 64)) == fp  # metadata-only change


# ------------------------------------------------------------------ checks
def test_full_verify_passes(base, tmp_path):
    f = mi.verify(APPROVAL, base, PARAMS, attestation_path=attestation(tmp_path))
    assert f['ollama_version'] == '0.40.1' and len(f['fingerprint']) == 64


def test_version_change_fails_closed(base, tmp_path):
    Fake.version = '0.41.0'
    with pytest.raises(mi.IdentityError, match='identity_ollama_version_mismatch'):
        mi.verify(APPROVAL, base, PARAMS, attestation_path=attestation(tmp_path))


def test_manifest_digest_change_fails_closed(base, tmp_path):
    Fake.tags = [{'name': APPROVAL['tag'], 'digest': 'b' * 64}, {'name': APPROVAL['tag'], 'digest': APPROVAL['tag_entry_digests'][1]}]
    with pytest.raises(mi.IdentityError, match='identity_manifest_digest_mismatch'):
        mi.verify(APPROVAL, base, PARAMS, attestation_path=attestation(tmp_path))


def test_attestation_blob_or_runner_change_fails_closed(base, tmp_path):
    for over in ({'model_blob_sha256': 'c' * 64}, {'mmproj_blob_sha256': 'c' * 64}, {'runner': 'ggml'},
                 {'size_vram': 1024}, {'passed': False}, {'approval_id': 'other'}):
        with pytest.raises(mi.IdentityError, match='identity_attestation_mismatch'):
            mi.verify(APPROVAL, base, PARAMS, attestation_path=attestation(tmp_path, **over))
    with pytest.raises(mi.IdentityError, match='identity_attestation_missing'):
        mi.verify(APPROVAL, base, PARAMS, attestation_path=tmp_path / 'absent.json')


def test_runtime_param_change_fails_closed(base, tmp_path):
    with pytest.raises(mi.IdentityError, match='identity_runtime_params_mismatch:num_ctx'):
        mi.verify(APPROVAL, base, dict(PARAMS, num_ctx=8192), attestation_path=attestation(tmp_path))
    with pytest.raises(mi.IdentityError, match='translation_max_output_tokens'):
        mi.check_runtime_params(APPROVAL, **PARAMS, translation_max=2048)


def test_loaded_model_checks(base):
    assert mi.check_loaded(APPROVAL, base)['digest'] == APPROVAL['manifest_digest']
    Fake.ps = [{'name': APPROVAL['tag'], 'digest': APPROVAL['tag_entry_digests'][1], 'size_vram': 0}]
    with pytest.raises(mi.IdentityError, match='identity_loaded_digest_mismatch'):
        mi.check_loaded(APPROVAL, base)
    Fake.ps = [{'name': APPROVAL['tag'], 'digest': APPROVAL['manifest_digest'], 'size_vram': 5}]
    with pytest.raises(mi.IdentityError, match='identity_gpu_in_use'):
        mi.check_loaded(APPROVAL, base)
    Fake.ps = [{'name': APPROVAL['tag'], 'digest': APPROVAL['manifest_digest'], 'size_vram': 0},
               {'name': 'gemma4:e2b', 'digest': 'x', 'size_vram': 0}]
    with pytest.raises(mi.IdentityError, match='identity_other_model_loaded'):
        mi.check_loaded(APPROVAL, base)
    Fake.ps = []
    with pytest.raises(mi.IdentityError, match='identity_loaded_model_missing'):
        mi.check_loaded(APPROVAL, base)


def test_post_check_failure_becomes_gateway_error():
    a = gw.OllamaAdapter('http://127.0.0.1:9', APPROVAL['tag'], 5)
    a.post_check = lambda: (_ for _ in ()).throw(mi.IdentityError('identity_loaded_digest_mismatch:abc'))
    with pytest.raises(gw.GatewayError, match='identity_loaded_digest_mismatch'):
        a._post_check()


def test_settings_require_approved_tag(monkeypatch, tmp_path):
    proposed_contract(tmp_path, monkeypatch)
    monkeypatch.setenv('OLLAMA_MODEL', 'gemma4:e2b')
    s = local_ai.load_settings(allow_proposed=NEW)
    assert 'OLLAMA_MODEL is not the approved immutable tag' in s.errors
    monkeypatch.setenv('OLLAMA_MODEL', APPROVAL['tag'])
    s = local_ai.load_settings(allow_proposed=NEW)
    assert not s.errors and s.expected_digest == APPROVAL['manifest_digest'] and s.seed == 42


def test_contract_cache_key_includes_fingerprint():
    c = local_ai.ContractCache('postgresql://unused', mi.fingerprint(APPROVAL))
    k = c._k(('abc', 'ollama/local', APPROVAL['tag']))
    assert k[0] == 'abc' and k[2].startswith(APPROVAL['tag'] + '|') and len(k[2].split('|')[1]) == 32


def test_verify_model_accepts_any_entry_with_pinned_digest(base):
    a = gw.OllamaAdapter(base, APPROVAL['tag'], 5, expected_digest=APPROVAL['manifest_digest'])
    assert a.verify_model() == APPROVAL['manifest_digest']
    a2 = gw.OllamaAdapter(base, APPROVAL['tag'], 5, expected_digest='f' * 64)
    with pytest.raises(gw.GatewayError, match='model_digest_mismatch'):
        a2.verify_model()


def test_rejected_artifact_is_never_active_or_evaluable():
    assert mi.approval_state(CONTRACT)[NEW] == 'rejected_quality_gate'
    assert mi.active_approval(CONTRACT) is None
    assert mi.active_approval(CONTRACT, allow_proposed=NEW) is None


def proposed_contract(tmp_path, monkeypatch):
    """A copy of the contract with the artifact still 'proposed' (pre-gate state)."""
    import json as _j
    import model_identity as _mi
    c = _mi.load_contract()
    c['events'] = [e for e in c['events'] if e['event'] != 'rejected_quality_gate']
    p = tmp_path / 'contract.json'
    p.write_text(_j.dumps(c))
    monkeypatch.setattr(_mi, 'CONTRACT_PATH', p)

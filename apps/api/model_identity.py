"""Model identity guard for the local AI stack (versioned contract).

A model is accepted only when ALL of these hold for the active approval in
model_approvals.json:

  1. Ollama /api/version equals the approved version;
  2. the tag's /api/tags entries are exactly the approved manifest digests
     (manifest-level metadata may be re-serialised, but the digests of the
     runner manifests may not change);
  3. a host attestation (written by scripts/attest_local_model.py, mounted
     read-only) reports the approved runner process, the full SHA-256 of the
     model and mmproj blobs that runner actually loaded, and size_vram == 0;
  4. the runtime parameters in use equal the approved ones;
  5. after every inference, /api/ps shows the approved manifest digest loaded
     on CPU (size_vram == 0).

Anything else fails closed. A short ID alone is never sufficient. Approvals and
events are append-only; the active approval is derived from the events.
"""
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, ProxyHandler, build_opener

CONTRACT_PATH = Path(os.getenv('LOCAL_AI_MODEL_CONTRACT') or Path(__file__).with_name('model_approvals.json'))
ATTESTATION_PATH = Path(os.getenv('LOCAL_AI_ATTESTATION') or '/attest/attestation.json')


class IdentityError(RuntimeError):
    """Stable reason string, e.g. 'identity_ollama_version_mismatch'."""


def load_contract(path=None):
    return json.loads(Path(path or CONTRACT_PATH).read_text(encoding='utf-8'))


def approval_state(contract):
    """{approval_id: last_event} following the append-only event log."""
    state = {}
    for e in contract['events']:
        state[e['approval']] = e['event']
    return state


def active_approval(contract, allow_proposed=None):
    """The newest approval whose last event is 'approved'. allow_proposed
    (an approval id) admits that one proposed artifact for an offline
    evaluation run only — never for stored content."""
    state = approval_state(contract)
    by_id = {a['id']: a for a in contract['approvals']}
    if allow_proposed and state.get(allow_proposed) == 'proposed':
        return by_id[allow_proposed]
    approved = [e['approval'] for e in contract['events'] if e['event'] == 'approved' and state.get(e['approval']) == 'approved']
    return by_id[approved[-1]] if approved else None


def fingerprint(approval):
    """Cache/identity fingerprint: weights, runner, version, digests, params, prompts."""
    core = {k: approval.get(k) for k in ('id', 'tag', 'ollama_version', 'runner', 'manifest_digest',
                                          'model_blob_sha256', 'mmproj_blob_sha256', 'runtime', 'prompt_versions')}
    return hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()


def _get(base, path, timeout):
    with build_opener(ProxyHandler({})).open(Request(base.rstrip('/') + path), timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def check_runtime_params(approval, *, temperature, num_ctx, num_thread, seed, translation_max=None, assistant_max=None):
    rt = approval.get('runtime') or {}
    want = {'temperature': temperature, 'num_ctx': num_ctx, 'num_thread': num_thread, 'seed': seed}
    if translation_max is not None:
        want['translation_max_output_tokens'] = translation_max
    if assistant_max is not None:
        want['assistant_max_output_tokens'] = assistant_max
    bad = sorted(k for k, v in want.items() if k in rt and rt[k] != v)
    if bad:
        raise IdentityError('identity_runtime_params_mismatch:' + ','.join(bad))


def check_attestation(approval, path=None):
    p = Path(path or ATTESTATION_PATH)
    try:
        a = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise IdentityError('identity_attestation_missing')
    expect = {'approval_id': approval['id'], 'ollama_version': approval['ollama_version'],
              'runner': approval['runner'], 'manifest_digest': approval['manifest_digest'],
              'model_blob_sha256': approval['model_blob_sha256'], 'mmproj_blob_sha256': approval['mmproj_blob_sha256']}
    bad = sorted(k for k, v in expect.items() if a.get(k) != v)
    if bad or a.get('size_vram') != 0 or not a.get('passed'):
        raise IdentityError('identity_attestation_mismatch:' + ','.join(bad or ['size_vram_or_passed']))
    return a


def check_api(approval, base_url, timeout=5):
    """Checks 1 and 2 (live API). Returns the facts seen."""
    try:
        ver = _get(base_url, '/api/version', timeout).get('version')
        tags = _get(base_url, '/api/tags', timeout).get('models', [])
    except Exception as exc:
        raise IdentityError('identity_provider_unreachable') from exc
    if ver != approval['ollama_version']:
        raise IdentityError(f'identity_ollama_version_mismatch:{ver}')
    entries = sorted(m.get('digest') for m in tags if m.get('name') == approval['tag'])
    if not entries:
        raise IdentityError('identity_tag_not_found')
    if entries != sorted(approval['tag_entry_digests']):
        raise IdentityError('identity_manifest_digest_mismatch:' + ','.join(d[:12] for d in entries))
    return {'ollama_version': ver, 'tag_entries': entries}


def check_loaded(approval, base_url, timeout=5):
    """Check 5: the model actually loaded is the approved runner manifest, on CPU."""
    try:
        loaded = _get(base_url, '/api/ps', timeout).get('models', [])
    except Exception as exc:
        raise IdentityError('identity_provider_unreachable') from exc
    m = next((x for x in loaded if x.get('name') == approval['tag']), None)
    if m is None:
        raise IdentityError('identity_loaded_model_missing')
    if m.get('digest') != approval['manifest_digest']:
        raise IdentityError(f'identity_loaded_digest_mismatch:{str(m.get("digest"))[:12]}')
    if m.get('size_vram') not in (0, None):
        raise IdentityError('identity_gpu_in_use')
    others = [x.get('name') for x in loaded if x.get('name') != approval['tag']]
    if others:
        raise IdentityError('identity_other_model_loaded')
    return m


def verify(approval, base_url, settings_params, attestation_path=None, timeout=5):
    """Full pre-flight (checks 1-4). Raises IdentityError; returns facts."""
    check_runtime_params(approval, **settings_params)
    facts = check_api(approval, base_url, timeout)
    facts['attestation'] = check_attestation(approval, attestation_path)
    facts['fingerprint'] = fingerprint(approval)
    return facts

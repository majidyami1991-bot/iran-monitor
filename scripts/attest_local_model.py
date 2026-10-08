"""Host-side attestation of the local model artifact (run on the Windows host).

The local-AI containers cannot see host processes or Ollama's blob store, so
this script proves, on the host, what Ollama really executes for the approved
tag and writes the evidence to runtime/local-ai-attestation/attestation.json
(gitignored, mounted read-only into the containers as /attest).

It sends one synthetic prompt (no collected content) to load the model, then:
  - reads the runner process command line (llama-server.exe for llamacpp),
  - computes the full SHA-256 of the --model and --mmproj files it loaded,
  - checks /api/version, the tag's /api/tags entries and /api/ps,
  - compares everything with the approval in apps/api/model_approvals.json.
With --reload it unloads the model and loads it again, and requires the
same runner artifacts both times.

    python scripts/attest_local_model.py --approval gemma4-e2b-ollama0401-llamacpp-d1e84c607e13 [--reload]
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'apps' / 'api' / 'model_approvals.json'
OUT = ROOT / 'runtime' / 'local-ai-attestation' / 'attestation.json'
BASE = 'http://127.0.0.1:11434'


def api(path, body=None, timeout=600):
    data = json.dumps(body).encode() if body is not None else None
    req = Request(BASE + path, data=data, headers={'Content-Type': 'application/json'} if data else {})
    with build_opener(ProxyHandler({})).open(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def runner_processes():
    ps = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(llama-server|ollama)' } | "
          "Select-Object Name,ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress")
    out = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True, timeout=60).stdout
    rows = json.loads(out) if out.strip() else []
    return rows if isinstance(rows, list) else [rows]


def load(tag, seed, think=None):
    body = {'model': tag, 'stream': False, 'keep_alive': '10m',
            'options': {'temperature': 0.1, 'seed': seed, 'num_ctx': 4096, 'num_predict': 8, 'num_thread': 8},
                          'messages': [{'role': 'user', 'content': '[SYNTHETIC ATTESTATION] Reply with: ok'}]}
    if think is not None:
        body['think'] = think
    return api('/api/chat', body).get('model')


def observe(approval):
    rt = approval.get('runtime') or {}
    served = load(approval['tag'], rt.get('seed', 42), think=(False if rt.get('think') is False else None))
    procs = runner_processes()
    servers = [p for p in procs if (p.get('Name') or '').lower().startswith('llama-server')]
    facts = {'served_model': served, 'runner_processes': len(servers)}
    if len(servers) != 1:
        facts['error'] = f'expected exactly one llama-server process, found {len(servers)}'
        return facts
    cmd = servers[0]['CommandLine'] or ''
    model = re.search(r'--model\s+(\S+)', cmd)
    mmproj = re.search(r'--mmproj\s+(\S+)', cmd)
    facts['runner'] = 'llamacpp'
    facts['runner_process'] = servers[0]['Name']
    facts['runner_args'] = {k: v for k, v in (('-c', re.search(r'\s-c\s+(\d+)', cmd)), ('-np', re.search(r'\s-np\s+(\d+)', cmd))) if v
                            for v in [v.group(1)]}
    facts['model_path_name'] = Path(model.group(1)).name if model else None
    facts['mmproj_path_name'] = Path(mmproj.group(1)).name if mmproj else None
    facts['model_blob_sha256'] = sha256(model.group(1)) if model else None
    facts['mmproj_blob_sha256'] = sha256(mmproj.group(1)) if mmproj else None
    ps = api('/api/ps', timeout=30).get('models', [])
    loaded = [m for m in ps if m.get('name') == approval['tag']]
    facts['loaded_count'] = len(ps)
    facts['manifest_digest'] = loaded[0].get('digest') if loaded else None
    facts['size_vram'] = loaded[0].get('size_vram') if loaded else None
    return facts


def unload(tag):
    api('/api/generate', {'model': tag, 'keep_alive': 0}, timeout=120)
    for _ in range(60):
        if not any(m.get('name') == tag for m in api('/api/ps', timeout=30).get('models', [])):
            return True
        time.sleep(1)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--approval', required=True)
    ap.add_argument('--reload', action='store_true')
    a = ap.parse_args()
    contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
    approval = next(x for x in contract['approvals'] if x['id'] == a.approval)
    version = api('/api/version', timeout=10).get('version')
    entries = sorted(m['digest'] for m in api('/api/tags', timeout=30)['models'] if m['name'] == approval['tag'])
    # Clean start: unload every loaded model (MAX_LOADED_MODELS=1; another tag
    # sharing the digest would otherwise be reported under its own name).
    for m in api('/api/ps', timeout=30).get('models', []):
        unload(m['name'])
    first = observe(approval)
    second = None
    if a.reload:
        unloaded = unload(approval['tag'])
        second = observe(approval)
        second['unloaded_between'] = unloaded
    checks = {
        'ollama_version': version == approval['ollama_version'],
        'tag_entries': entries == sorted(approval['tag_entry_digests']),
        'served_model': first.get('served_model') == approval['tag'],
        'runner': first.get('runner') == approval['runner'],
        'model_blob': first.get('model_blob_sha256') == approval['model_blob_sha256']
                      and first.get('model_path_name') == 'sha256-' + approval['model_blob_sha256'],
        'mmproj_blob': (first.get('mmproj_blob_sha256') is None and approval.get('mmproj_blob_sha256') is None) or (
                       first.get('mmproj_blob_sha256') == approval.get('mmproj_blob_sha256')
                       and first.get('mmproj_path_name') == 'sha256-' + str(approval.get('mmproj_blob_sha256'))),
        'manifest_digest': first.get('manifest_digest') == approval['manifest_digest'],
        'cpu_only': first.get('size_vram') == 0,
        'single_model_loaded': first.get('loaded_count') == 1,
    }
    if second is not None:
        checks['stable_after_reload'] = all(second.get(k) == first.get(k) for k in
                                            ('runner', 'model_blob_sha256', 'mmproj_blob_sha256', 'manifest_digest', 'size_vram'))
        checks['unloaded_between'] = bool(second.get('unloaded_between'))
    passed = all(checks.values())
    att = {'approval_id': approval['id'], 'verified_at': datetime.now(timezone.utc).isoformat(), 'passed': passed,
           'checks': checks, 'ollama_version': version, 'runner': first.get('runner'),
           'manifest_digest': first.get('manifest_digest'), 'model_blob_sha256': first.get('model_blob_sha256'),
           'mmproj_blob_sha256': first.get('mmproj_blob_sha256'), 'size_vram': first.get('size_vram'),
           'tag_entries': entries, 'first': first, 'second': second}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    target = OUT if approval.get('role') is None else OUT.with_name(f"{approval['id']}.json")
    target.write_text(json.dumps(att, indent=2), encoding='utf-8')
    print(json.dumps({'passed': passed, 'checks': checks}, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())

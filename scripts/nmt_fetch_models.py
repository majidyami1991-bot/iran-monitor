"""One-time, owner-authorised fetch of the two NMT models at pinned commits,
then SHA-256 verification against the publisher's LFS hashes. Fails closed:
a mismatch deletes nothing but exits non-zero and the gate must not run.

  runtime/nmt-venv/Scripts/python.exe scripts/nmt_fetch_models.py
"""
import hashlib
import json
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[1] / 'runtime' / 'nmt-models' / 'src'
PINNED = {
    'google/madlad400-3b-mt': {
        'revision': 'fa184c675da0b5c9e1c8694fccd4e12e2d422094',
        'files': {'model.safetensors': '66ff5f8fcaf92291da486fdfbd4d5233cec90e1359348a56e3172c978b3a76d4',
                  'spiece.model': 'ef11ac9a22c7503492f56d48dce53be20e339b63605983e9f27d2cd0e0f3922c',
                  'tokenizer.json': 'a2799ccc696b752ba00c34f58726bfe253a04921ceb6cfc620400f560474790b',
                  'config.json': None, 'generation_config.json': None, 'tokenizer_config.json': None,
                  'special_tokens_map.json': None, 'added_tokens.json': None}},
    'facebook/nllb-200-distilled-600M': {
        'revision': 'f8d333a098d19b4fd9a8b18f94170487ad3f821d',
        'files': {'pytorch_model.bin': 'c266c2cfd19758b6d09c1fc31ecdf1e485509035f6b51dfe84f1ada83eefcc42',
                  'sentencepiece.bpe.model': '14bb8dfb35c0ffdea7bc01e56cea38b9e3d5efcdcb9c251d6b40538e1aab555a',
                  'tokenizer.json': 'e316b82de11d0f951f370943b3c438311629547285129b0b81dadabd01bca665',
                  'config.json': None, 'generation_config.json': None, 'tokenizer_config.json': None,
                  'special_tokens_map.json': None}},
}


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b''):
            h.update(chunk)
    return h.hexdigest()


report, ok = {}, True
for repo, spec in PINNED.items():
    d = ROOT / repo.split('/')[1]
    report[repo] = {'revision': spec['revision'], 'files': {}}
    for fn, want in spec['files'].items():
        p = Path(hf_hub_download(repo, fn, revision=spec['revision'], local_dir=d))
        got = sha256(p)
        match = (want is None) or got == want
        ok &= match
        report[repo]['files'][fn] = {'bytes': p.stat().st_size, 'sha256': got, 'pinned': want, 'match': match}
        print(repo, fn, p.stat().st_size, 'OK' if match else 'MISMATCH', flush=True)
out = Path(__file__).resolve().parents[1] / 'runtime' / 'local-ai-evidence' / 'phase6' / 'nmt-fetch.json'
out.write_text(json.dumps(report, indent=2))
sys.exit(0 if ok else 1)

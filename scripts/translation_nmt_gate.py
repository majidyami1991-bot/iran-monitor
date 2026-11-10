"""Translation quality gate for dedicated NMT models (MADLAD-400, NLLB-200)
run with CTranslate2 on the CPU — the SAME fixtures, placeholder protection,
validator (translation-validator-v2.1.0) and glossary (defence-glossary-fa
-v1.1.0) as the TranslateGemma gate, so results are directly comparable.

Isolation: synthetic fixtures only; no database connection is opened (no
DSN is read); Hugging Face / Transformers offline flags are forced; models
are read from a local directory; output is one JSON file under the evidence
folder. Nothing is approved or activated by this script.

  python scripts/translation_nmt_gate.py --engine madlad --model-dir <ct2 dir> --out <json>
  python scripts/translation_nmt_gate.py --engine fake --out <json>        # harness self-test
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_DATASETS_OFFLINE='1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'apps' / 'api'), str(ROOT / 'scripts')]
os.environ.setdefault('DATABASE_URL', 'postgresql://offline:offline@127.0.0.1:1/none')  # imported modules need the name; never used

# No database, by construction: the fixture modules import the API stack,
# which imports psycopg; a stub whose connect() raises replaces it here.
import types  # noqa: E402

def _no_db(*a, **k):
    raise RuntimeError('database access is forbidden in the NMT gate')

_pg = types.ModuleType('psycopg')
_pg.connect = _no_db
_pg.Connection = object
_pg.rows = types.SimpleNamespace(dict_row=None)
_pg.types = types.SimpleNamespace(json=types.SimpleNamespace(Jsonb=lambda x: x))
for _n, _m in {'psycopg': _pg, 'psycopg.rows': _pg.rows, 'psycopg.types': _pg.types, 'psycopg.types.json': _pg.types.json}.items():
    sys.modules.setdefault(_n, _m)

import translation_tg as tg  # noqa: E402
from local_ai_quality_gate import FIXTURES as BASE_FIXTURES, NEGATIVES as BASE_NEG, SRC as NSRC, GOOD as NGOOD  # noqa: E402
from translation_quality_gate_tg import TERMS, EXTRA_NEG, REGRESSION  # noqa: E402

# Sentence split for sentence-level NMT models (both were trained on
# sentence pairs). Splits after . ! ? when followed by space + capital/quote/
# digit; placeholders (ZQ…) and decimals are not split points.
_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9"“\'(])')


def split_sentences(text):
    parts = [p.strip() for p in _SPLIT.split(text.strip()) if p.strip()]
    return parts or [text]


class FakeEngine:
    """Harness self-test: returns the source unchanged (must fail validation)."""
    name, version = 'fake', 'fake-echo'

    def translate(self, sentences):
        return list(sentences), sum(len(s.split()) for s in sentences), sum(len(s.split()) for s in sentences)


class CT2Engine:
    def __init__(self, kind, model_dir, threads, compute_type, beam):
        import ctranslate2
        from tokenizers import Tokenizer
        self.kind, self.model_dir, self.beam = kind, Path(model_dir), beam
        self.translator = ctranslate2.Translator(str(self.model_dir), device='cpu', compute_type=compute_type,
                                                 intra_threads=threads, inter_threads=1)
        self.tok = Tokenizer.from_file(str(self.model_dir / 'tokenizer.json'))
        self.name = {'madlad': 'google/madlad400-3b-mt', 'nllb': 'facebook/nllb-200-distilled-600M'}[kind]
        self.version = f'ctranslate2-{ctranslate2.__version__}/{compute_type}/beam{beam}'

    def _src_tokens(self, s):
        if self.kind == 'madlad':
            return self.tok.encode('<2fa> ' + s).tokens          # post-processor appends </s>
        toks = self.tok.encode(s, add_special_tokens=False).tokens
        return ['eng_Latn'] + toks + ['</s>']                     # NLLB source: src lang code + tokens + </s>

    def translate(self, sentences):
        src = [self._src_tokens(s) for s in sentences]
        kw = dict(beam_size=self.beam, max_decoding_length=512, repetition_penalty=1.0, no_repeat_ngram_size=0)
        if self.kind == 'nllb':
            kw['target_prefix'] = [['pes_Arab']] * len(src)
        res = self.translator.translate_batch(src, **kw)
        outs, n_out = [], 0
        for r in res:
            toks = r.hypotheses[0]
            if self.kind == 'nllb' and toks and toks[0] == 'pes_Arab':
                toks = toks[1:]
            n_out += len(toks)
            ids = [self.tok.token_to_id(t) for t in toks]
            outs.append(self.tok.decode([i for i in ids if i is not None], skip_special_tokens=True).strip())
        return outs, sum(len(x) for x in src), n_out


def model_identity(model_dir):
    """SHA-256 of every file of the converted model actually executed."""
    if not model_dir:
        return None
    files = {}
    for p in sorted(Path(model_dir).rglob('*')):
        if p.is_file():
            h = hashlib.sha256()
            with open(p, 'rb') as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b''):
                    h.update(chunk)
            files[p.relative_to(model_dir).as_posix()] = {'bytes': p.stat().st_size, 'sha256': h.hexdigest()}
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--engine', choices=['madlad', 'nllb', 'fake'], required=True)
    ap.add_argument('--model-dir')
    ap.add_argument('--out', required=True)
    ap.add_argument('--threads', type=int, default=8)
    ap.add_argument('--compute-type', default='int8')
    ap.add_argument('--beam', type=int, default=4)
    a = ap.parse_args()
    eng = FakeEngine() if a.engine == 'fake' else CT2Engine(a.engine, a.model_dir, a.threads, a.compute_type, a.beam)
    calls = {'n': 0}

    def call(protected_text, num_predict):
        sents = split_sentences(protected_text)
        outs, tin, tout = eng.translate(sents)
        calls['n'] += 1
        return ' '.join(outs), tin, tout

    rep = {'engine': eng.name, 'runtime': eng.version, 'threads': a.threads, 'model_files': model_identity(a.model_dir),
           'glossary_version': tg.GLOSSARY_VERSION, 'validator_version': tg.VALIDATOR_VERSION,
           'fixture_source': 'scripts/local_ai_quality_gate.py FIXTURES + scripts/translation_quality_gate_tg.py TERMS (unchanged)',
           'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'fixtures': [], 'negatives': []}
    for case, kind, payload, exp in list(BASE_FIXTURES) + TERMS:
        row = {'case': case, 'kind': kind, 'regression': case in REGRESSION, 'fields': []}
        if kind == 'rule':
            r = tg.translate_field(call, payload['text'])
            row['fields'].append({'field': 'text', 'status': r['status'], 'inference': r['inference']})
        else:
            for f in (('title', 'summary') if kind == 'news' else ('text',)):
                src = payload.get(f, '')
                r = tg.translate_field(call, src)
                kept = [k for k in exp.get('keep', []) if k in src]
                row['fields'].append({'field': f, 'source': src, 'status': r['status'], 'inference': r['inference'], 'flags': r['flags'],
                                      'reasons': r['reasons'], 'output': r.get('text'), 'latency_ms': r.get('latency_ms'),
                                      'tokens_in': r.get('tokens_in'), 'tokens_out': r.get('tokens_out'),
                                      'kept_missing': [k for k in kept if not r.get('text') or k not in r['text']]})
        rep['fixtures'].append(row)
        print(case, [f['status'] for f in row['fields']], flush=True)

    # the validator's own negatives (model-independent): must still be 16/16
    for case, src, bad, flag in BASE_NEG:
        v = tg.validate(src, bad, {})
        rep['negatives'].append({'case': case, 'rejected': not v.passed, 'flags': v.flags})
    for case, src, bad, mode, flag in EXTRA_NEG:
        if mode == 'final':
            v = tg.validate(src, bad, {})
            rep['negatives'].append({'case': case, 'rejected': not v.passed, 'flag_present': flag in v.flags, 'flags': v.flags})
            continue
        protected, mapping, salt = tg.protect(src)
        tok = next(iter(mapping))
        fake = 'هزینه‌ها امسال ' + tok + ' افزایش یافت.'
        fake = {'drop_token': fake.replace(tok, ''), 'dup_token': fake.replace(tok, tok + ' ' + tok),
                'mangle_token': fake.replace(tok, tok[:-1] + 'Q' if tok[-1] != 'Q' else tok[:-1] + 'R')}[mode]
        restored, pflags = tg.restore(fake, mapping, salt)
        rep['negatives'].append({'case': case, 'rejected': bool(pflags), 'flag_present': flag in pflags, 'flags': pflags})
    ctrl = tg.validate(NSRC, NGOOD, {})

    flds = [f for r in rep['fixtures'] for f in r['fields'] if f['inference']]
    lat = [f['latency_ms'] for f in flds if f.get('latency_ms') is not None]
    rep['summary'] = {
        'fixtures': len(rep['fixtures']), 'inference_fields': len(flds), 'inferences': calls['n'],
        'available': sum(f['status'] == 'available' for f in flds),
        'needs_review': [f"{r['case']}:{f['field']}:{','.join(f['flags'])}" for r in rep['fixtures'] for f in r['fields']
                         if f['inference'] and f['status'] != 'available'],
        'regression_failures': [r['case'] for r in rep['fixtures'] if r['regression'] and
                                any(f['inference'] and f['status'] != 'available' for f in r['fields'])],
        'kept_missing': sum(len(f.get('kept_missing', [])) for f in flds),
        'negatives_rejected': f"{sum(n['rejected'] for n in rep['negatives'])}/{len(rep['negatives'])}",
        'control_good_passes': ctrl.passed,
        'latency_avg_max_ms': (int(sum(lat) / len(lat)), max(lat)) if lat else None,
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=2)
    print(json.dumps(rep['summary'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

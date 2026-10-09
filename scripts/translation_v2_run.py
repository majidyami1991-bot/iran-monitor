"""Pipeline-v2 run (placeholder-free) for an existing, attested TranslateGemma
artifact. Evaluation only: the contract entry is read for identity checks
only (its state is not used or changed), nothing is written to a database,
nothing is published, nothing is corrected.

  python /harness/translation_v2_run.py --approval <id> --set dev|p7|p8|p10 --out /evidence/phase10/<file>.json

Sets: dev = the 35 gate fixtures (local_ai_quality_gate FIXTURES + TERMS),
p7 = translation_qc_heldout, p8 = translation_eval_set_p8, p10 = translation_eval_set_p10.
"""
import argparse
import json
import sys
import time
from urllib.request import ProxyHandler, Request, build_opener

import local_ai
import model_identity as mi
import translation_tg as tg
import translation_v2 as v2
import x_translation_validator as xv

sys.path.insert(0, '/harness')


def load_set(name):
    if name == 'dev':
        from local_ai_quality_gate import FIXTURES
        from translation_quality_gate_tg import TERMS
        out = []
        for case, kind, payload, _ in list(FIXTURES) + TERMS:
            if kind == 'rule':
                continue
            for f in (('title', 'summary') if kind == 'news' else ('text',)):
                t = payload.get(f, '')
                if t and t.strip() and not xv.is_persian_source(t):
                    out.append((f'{case}:{f}', t))
        return out
    if name == 'p7':
        from translation_qc_heldout import HELDOUT
        return [(i, t) for i, _, t in HELDOUT]
    if name == 'p8':
        from translation_eval_set_p8 import ITEMS
        return [(i, t) for i, _, t, _, _ in ITEMS]
    from translation_eval_set_p10 import ITEMS
    return [(i, t) for i, _, t, _ in ITEMS]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--approval', required=True)
    ap.add_argument('--set', choices=['dev', 'p7', 'p8', 'p10'], required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    appr = next(x for x in mi.load_contract()['approvals'] if x['id'] == a.approval)  # identity only
    base = local_ai.load_settings().base_url
    rt = appr['runtime']
    facts = mi.verify(appr, base, {'temperature': rt['temperature'], 'num_ctx': rt['num_ctx'], 'num_thread': rt['num_thread'],
                                   'seed': rt['seed'], 'translation_max': rt['translation_max_output_tokens']})
    opener = build_opener(ProxyHandler({}))

    def call(text, num_predict):
        body = tg.request_body(appr['tag'], text, seed=rt['seed'], num_ctx=rt['num_ctx'], num_thread=rt['num_thread'],
                               temperature=rt['temperature'], num_predict=num_predict)
        with opener.open(Request(base + '/api/chat', json.dumps(body, ensure_ascii=False).encode(),
                                 {'Content-Type': 'application/json'}), timeout=1800) as r:
            out = json.loads(r.read())
        if out.get('model') != appr['tag']:
            raise RuntimeError('model_identity_mismatch')
        if out.get('done_reason') == 'length':
            raise RuntimeError('output_truncated')
        mi.check_loaded(appr, base)
        return out['message']['content'], out.get('prompt_eval_count'), out.get('eval_count')

    rep = {'approval': appr['id'], 'fingerprint': facts['fingerprint'], 'pipeline': v2.PIPELINE_VERSION, 'facts': v2.FACTS_VERSION,
           'set': a.set, 'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'items': {}}
    for iid, text in load_set(a.set):
        r = v2.translate_direct(call, text)
        val = tg.validate(text, r.get('text') or '', {})
        dec, det = v2.decide(text, r.get('text'))
        rep['items'][iid] = {'source': text, 'output': r.get('text'), 'validator_status': 'available' if val.passed else 'needs_review',
                             'validator_flags': val.flags, 'v2_decision': dec, 'v2_details': det, 'latency_ms': r.get('latency_ms'),
                             'tokens_in': r.get('tokens_in'), 'tokens_out': r.get('tokens_out')}
        print(iid, dec, r.get('latency_ms'), flush=True)
    json.dump(rep, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()

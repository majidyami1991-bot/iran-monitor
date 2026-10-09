"""Runs a TranslateGemma artifact (identity-verified via its contract entry)
over a fixed evaluation set, evaluation only: no approval change, no DB
write, nothing published. Same pipeline as the gates (translation_tg:
salted placeholders, exact restore, validator v2.1.0, glossary v1.1.0);
QC (translation_qc) results are recorded as triage flags only.

Prepared in phase 8 for TranslateGemma 27B; NOT executed until the owner
authorises the download and a `proposed` contract entry exists.

  python /harness/translation_eval_run.py --approval <id> --set p8 --out /evidence/phase9/p8-<id>.json
  sets: p8 (48 hard items, translation_eval_set_p8), p7 (40 phase-7 held-out items)
"""
import argparse
import json
import sys
import time
from urllib.request import ProxyHandler, Request, build_opener

import local_ai
import model_identity as mi
import translation_qc as qc
import translation_tg as tg

sys.path.insert(0, '/harness')


def load_set(name):
    if name == 'p8':
        from translation_eval_set_p8 import ITEMS, SET_VERSION
        return SET_VERSION, [(i, c, t, kf) for i, c, t, kf, _ in ITEMS]
    from translation_qc_heldout import HELDOUT
    return 'translation-qc-heldout-p7', [(i, c, t, []) for i, c, t in HELDOUT]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--approval', required=True)
    ap.add_argument('--set', choices=['p8', 'p7'], required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--identity-only-baseline', action='store_true',
                    help='read a non-proposed (e.g. rejected) entry for identity checks only; its state is not used or changed')
    a = ap.parse_args()
    contract = mi.load_contract()
    if a.identity_only_baseline:
        appr = next(x for x in contract['approvals'] if x['id'] == a.approval)
    else:
        appr = mi.active_approval(contract, allow_proposed=a.approval, role='translation')
    assert appr and appr['id'] == a.approval, 'approval must exist and be in state proposed (evaluation only)'
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

    set_version, items = load_set(a.set)
    rep = {'approval': appr['id'], 'fingerprint': facts['fingerprint'], 'set': set_version, 'qc_version': qc.QC_VERSION,
           'validator_version': tg.VALIDATOR_VERSION, 'glossary_version': tg.GLOSSARY_VERSION,
           'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'items': {}}
    for iid, cat, text, key_facts in items:
        r = tg.translate_field(call, text)
        q = qc.check(text, r.get('text') or '')
        rep['items'][iid] = {'category': cat, 'source': text, 'key_facts': key_facts, 'output': r.get('text'),
                             'validator_status': r['status'], 'validator_flags': r.get('flags'), 'qc_flags': q['flags'],
                             'latency_ms': r.get('latency_ms'), 'tokens_in': r.get('tokens_in'), 'tokens_out': r.get('tokens_out'),
                             'human_label': None}
        print(iid, r['status'], r.get('latency_ms'), flush=True)
    json.dump(rep, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()

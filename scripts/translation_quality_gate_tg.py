"""Translation quality gate for translategemma (TRANSLATION_MODEL_CONTRACT).

Runs in the local-AI container in evaluation mode for ONE proposed approval;
nothing is written to the database. Inputs are SYNTHETIC. Full outputs go to
/evidence/translation-gate-tg.json (runtime, gitignored) for human review.

The 8 fixtures the rejected gemma4 artifact failed are permanent regression
cases (marked regression=True).
"""
import argparse
import json
import sys
import time
from urllib.request import ProxyHandler, Request, build_opener

import local_ai
import model_identity as mi
import translation_tg as tg
import x_translation_validator as xv

sys.path.insert(0, '/harness')
from local_ai_quality_gate import FIXTURES as BASE_FIXTURES, NEGATIVES as BASE_NEG, SRC as NSRC, GOOD as NGOOD  # noqa: E402

REGRESSION = {'person_names', 'acronyms', 'hashtags', 'emoji', 'simple_title', 'places', 'military_term', 'time'}
TERMS = [
    ('term_brigade', 'text', {'text': 'The 3rd Armored Brigade moved to the northern front on Monday.'}, {}),
    ('term_convoy', 'text', {'text': 'A military convoy of 40 trucks crossed the border at night.'}, {}),
    ('term_launch', 'text', {'text': 'Radar systems detected a ballistic missile launch from the coast.'}, {}),
    ('term_commission', 'text', {'text': 'The navy will commission two new frigates next year.'}, {}),
    ('term_frigate', 'text', {'text': 'The frigate escorted the tanker through the strait.'}, {}),
    ('term_missile', 'text', {'text': 'The cruise missile hit a fuel depot near the port.'}, {}),
    ('term_deployment', 'text', {'text': 'The deployment of 2,000 troops was completed within a week.'}, {}),
    ('term_strike_depot', 'text', {'text': 'A drone strike hit an ammunition depot near the border overnight.'}, {}),
    ('names_companies', 'text', {'text': 'Rheinmetall CEO Armin Papperger met Saab executives in Stockholm on Thursday.'}, {}),
    ('money_amount', 'text', {'text': 'The contract is valued at $1.2 billion and covers 48 launchers.'}, {}),
    ('empty_text', 'text', {'text': ''}, {}),
]
EXTRA_NEG = [  # (case, source, bad_output_after_restore_or_raw, mode, expected_flag)
    ('placeholder_removed', 'Spending rose 12% this year.', None, 'drop_token', 'placeholder_missing'),
    ('placeholder_duplicated', 'Spending rose 12% this year.', None, 'dup_token', 'placeholder_duplicated'),
    ('placeholder_changed', 'Spending rose 12% this year.', None, 'mangle_token', 'placeholder_missing'),
    ('foreign_script', 'Lloyd Austin met Yoav Gallant.', 'لوید آستین با 요אف گالانت دیدار کرد.', 'final', 'foreign_script'),
    ('mixed_script', 'Lloyd Austin arrived.', 'لloyd آستین وارد شد.', 'final', 'mixed_script_word'),
    ('english_word_left', 'The convoy moved north.', 'ا convoy به سمت شمال حرکت کرد.', 'final', 'latin_prose_residue'),
    ('glossary_violation', 'The brigade crossed the river.', 'بنیاد از رودخانه عبور کرد.', 'final', 'glossary_term_missing'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--approval', required=True)
    ap.add_argument('--out', default='/evidence/translation-gate-tg.json')
    a = ap.parse_args()
    contract = mi.load_contract()
    appr = mi.active_approval(contract, allow_proposed=a.approval, role='translation')
    assert appr and appr['id'] == a.approval, 'approval not evaluable'
    s = local_ai.load_settings()  # only for base_url
    base = s.base_url
    rt = appr['runtime']
    facts = mi.verify(appr, base, {'temperature': rt['temperature'], 'num_ctx': rt['num_ctx'], 'num_thread': rt['num_thread'],
                                   'seed': rt['seed'], 'translation_max': rt['translation_max_output_tokens']})
    opener = build_opener(ProxyHandler({}))
    calls = {'n': 0}

    def call(text, num_predict):
        body = tg.request_body(appr['tag'], text, seed=rt['seed'], num_ctx=rt['num_ctx'], num_thread=rt['num_thread'],
                               temperature=rt['temperature'], num_predict=num_predict)
        with opener.open(Request(base + '/api/chat', json.dumps(body, ensure_ascii=False).encode(),
                                 {'Content-Type': 'application/json'}), timeout=900) as r:
            out = json.loads(r.read())
        calls['n'] += 1
        if out.get('model') != appr['tag']:
            raise RuntimeError('model_identity_mismatch')
        if out.get('done_reason') == 'length':
            raise RuntimeError('output_truncated')
        mi.check_loaded(appr, base)  # post-inference identity check
        return out['message']['content'], out.get('prompt_eval_count'), out.get('eval_count')

    rep = {'approval': appr['id'], 'fingerprint': facts['fingerprint'], 'prompt_version': tg.PROMPT_VERSION,
           'glossary_version': tg.GLOSSARY_VERSION, 'validator_version': tg.VALIDATOR_VERSION, 'fixtures': [], 'negatives': []}
    for case, kind, payload, exp in list(BASE_FIXTURES) + TERMS:
        row = {'case': case, 'kind': kind, 'regression': case in REGRESSION, 'fields': []}
        if kind == 'rule':
            r = tg.translate_field(call, payload['text'])
            row['fields'].append({'field': 'text', 'status': r['status'], 'inference': r['inference']})
        else:
            for f in (('title', 'summary') if kind == 'news' else ('text',)):
                r = tg.translate_field(call, payload.get(f, ''))
                kept = [k for k in exp.get('keep', []) if k in payload.get(f, '')]
                row['fields'].append({'field': f, 'status': r['status'], 'inference': r['inference'], 'flags': r['flags'],
                                      'reasons': r['reasons'], 'output': r.get('text'), 'latency_ms': r.get('latency_ms'),
                                      'tokens_in': r.get('tokens_in'), 'tokens_out': r.get('tokens_out'),
                                      'kept_missing': [k for k in kept if not r.get('text') or k not in r['text']]})
                time.sleep(1)
        rep['fixtures'].append(row)

    # simulated invalid outputs: base 9 through the new validator + placeholder/script/glossary cases
    for case, src, bad, flag in BASE_NEG:
        if flag == 'invalid_json':  # not applicable to plain-text output; a truncated/garbled reply must still fail
            v = tg.validate(src, bad, {})
        else:
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
    rep['control_good_passes'] = ctrl.passed

    flds = [f for r in rep['fixtures'] for f in r['fields'] if f['inference']]
    rep['summary'] = {
        'fixtures': len(rep['fixtures']), 'inference_fields': len(flds), 'inferences': calls['n'],
        'available': sum(f['status'] == 'available' for f in flds),
        'needs_review': [f"{r['case']}:{f['field']}:{','.join(f['flags'])}" for r in rep['fixtures'] for f in r['fields']
                         if f['inference'] and f['status'] != 'available'],
        'regression_failures': [r['case'] for r in rep['fixtures'] if r['regression'] and
                                any(f['inference'] and f['status'] != 'available' for f in r['fields'])],
        'empty_summary_sent': [r['case'] for r in rep['fixtures'] for f in r['fields'] if f['field'] == 'summary' and f['status'] != 'skipped_empty'
                               and next((p for c, k, p, e in BASE_FIXTURES if c == r['case']), {}).get('summary') == ''],
        'persian_rule_not_required': [f['status'] for r in rep['fixtures'] if r['kind'] == 'rule' for f in r['fields']],
        'kept_missing': sum(len(f.get('kept_missing', [])) for f in flds),
        'negatives_rejected': f"{sum(n['rejected'] for n in rep['negatives'])}/{len(rep['negatives'])}",
        'control_good_passes': ctrl.passed,
        'latency_ms': [f['latency_ms'] for f in flds],
    }
    with open(a.out, 'w', encoding='utf-8') as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=2)
    out = dict(rep['summary'])
    lat = out.pop('latency_ms')
    out['latency_avg_max_ms'] = (int(sum(lat) / len(lat)), max(lat)) if lat else None
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

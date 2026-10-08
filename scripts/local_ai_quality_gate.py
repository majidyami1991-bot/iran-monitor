"""Offline quality + technical gate for a proposed local model artifact.

Runs inside the local-AI translate container (evaluation mode for ONE
proposed approval id; nothing is written to the database). All inputs are
SYNTHETIC fixtures; full outputs go to /evidence/quality-gate.json (runtime,
gitignored) for human review, never to Git.

    python /harness/local_ai_quality_gate.py --approval <id> [--out /evidence/quality-gate.json]
"""
import argparse
import dataclasses
import json
import sys
import time

import ai_gateway as gw
import local_ai
import local_translation as lt
import model_identity as mi
import x_translation_validator as xv

PV = 'translate-fa-v1.0.0'

# (case, kind, payload, expectations) — SYNTHETIC; not real events.
FIXTURES = [
    ('simple_title', 'news', {'title': 'Navy commissions new frigate', 'summary': ''}, {}),
    ('multi_sentence_summary', 'news', {'title': 'Army completes winter exercise', 'summary':
        'The army completed its annual winter exercise on Sunday. Several brigades took part in the drills. '
        'Officials said the exercise tested logistics in extreme cold.'}, {}),
    ('quotation', 'text', {'text': 'The minister said: "We will not accept any delay in the program."'}, {}),
    ('person_names', 'text', {'text': 'Lloyd Austin met Yoav Gallant in Washington on Tuesday.'}, {}),
    ('organizations', 'text', {'text': 'Lockheed Martin and Rafael Advanced Defense Systems signed a cooperation agreement.'}, {}),
    ('places', 'text', {'text': 'The convoy moved from Kharkiv toward Izium, near the Donets River.'}, {}),
    ('military_term', 'text', {'text': 'The brigade conducted a combined-arms live-fire exercise with close air support.'}, {}),
    ('acronyms', 'text', {'text': 'OSINT analysts used IMINT and GEOINT sources, while ELINT data was shared with NATO and CENTCOM.'},
     {'keep': ['OSINT', 'IMINT', 'GEOINT', 'ELINT', 'NATO', 'CENTCOM']}),
    ('date', 'text', {'text': 'The exercise will run from 12 March 2026 to 18 March 2026.'}, {}),
    ('time', 'text', {'text': 'The launch was detected at 03:45 local time.'}, {}),
    ('percent', 'text', {'text': 'Defense spending rose 12% compared with last year.'}, {}),
    ('decimal', 'text', {'text': 'The contract is worth 2.75 billion dollars.'}, {}),
    ('coordinates', 'text', {'text': 'Satellite images show new activity at 34.5521, 69.2075.'}, {}),
    ('equipment_codes', 'text', {'text': 'The MQ-9B and F-35A completed joint trials while the S-400 radar was active.'},
     {'keep': ['MQ-9B', 'F-35A', 'S-400']}),
    ('url', 'text', {'text': 'Read the full statement at https://www.defense.gov/News/Releases/Release/Article/3712345/'}, {}),
    ('mention', 'text', {'text': 'Footage shared by @IntelCrab shows the strike on the depot.'}, {}),
    ('hashtags', 'text', {'text': 'Protests continued for a third day in the capital. #Iran #Protests'}, {}),
    ('emoji', 'text', {'text': 'Air raid sirens are sounding across the city 🚨'}, {}),
    ('multilingual', 'text', {'text': 'The commander said «پیروزی نزدیک است» during the parade in Tehran.'}, {}),
    ('uncertain_claim', 'text', {'text': 'Unconfirmed reports suggest the facility may have been damaged.'}, {}),
    ('attributed_claim', 'text', {'text': 'According to Reuters, two officials said the deal could be signed next week.'}, {}),
    ('negation', 'text', {'text': 'The ministry denied that any aircraft were lost during the operation.'}, {}),
    ('title_summary_numbers', 'news', {'title': 'Poland orders 96 Apache helicopters', 'summary':
        'Poland signed a $10 billion agreement for 96 AH-64E Apache helicopters, with deliveries expected from 2028, '
        'the defense ministry said on 21 August 2023.'}, {'keep': ['AH-64E']}),
    ('persian_source', 'rule', {'text': 'نیروی دریایی رزمایش جدیدی را در خلیج فارس آغاز کرد.'}, {}),
]

# Simulated bad outputs the validator must reject: (case, source, bad_output, expected_flag)
SRC = 'Defense spending rose 12% to 2.75 billion dollars, said @MinDef. Details: https://example.org/report/12 #Budget'
GOOD = 'هزینه‌های دفاعی ۱۲٪ افزایش یافت و به 2.75 میلیارد دلار رسید، @MinDef گفت. جزئیات: https://example.org/report/12 #Budget'
NEGATIVES = [
    ('broken_json', SRC, '{"text_fa": "هزینه‌های دفاعی ۱۲٪', 'invalid_json'),
    ('markdown', SRC, '**' + GOOD + '**', 'model_commentary_or_markdown'),
    ('model_commentary', SRC, 'ترجمه: ' + GOOD, 'wrapped_or_labelled'),
    ('number_removed', SRC, GOOD.replace('۱۲٪ ', ''), 'number_mismatch'),
    ('number_added', SRC, GOOD.replace('رسید', 'در سال 2024 رسید'), 'number_added'),
    ('url_changed', SRC, GOOD.replace('report/12', 'report/13'), 'url_missing'),
    ('mention_removed', SRC, GOOD.replace('@MinDef', 'وزارت دفاع'), 'mention_missing'),
    ('untranslated_sentence', SRC, 'Defense spending rose sharply this year and officials said @MinDef 12% 2.75 https://example.org/report/12 #Budget', 'untranslated_english'),
    ('added_information', SRC, GOOD + ' این بودجه شامل 400 جنگنده جدید است.', 'number_added'),
]


def run_fixture(g, kind, payload):
    task = 'translate_news' if kind == 'news' else 'translate_text'
    chars = sum(len(v) for v in payload.values())
    g[task].adapter.predict_override = lt.predict_for(chars, 1536)
    t0 = time.monotonic()
    r = g[task].run(gw.GatewayRequest(task, json.dumps(payload, ensure_ascii=False), prompt_version=PV))
    return task, r, int((time.monotonic() - t0) * 1000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--approval', required=True)
    ap.add_argument('--out', default='/evidence/quality-gate.json')
    a = ap.parse_args()
    s = lt.load_settings(allow_proposed=a.approval)
    assert not s.errors, s.errors
    ai = dataclasses.replace(s.ai, max_output_tokens=s.output_tokens)
    facts = local_ai.preflight(ai, 'translation')
    g = {t: local_ai.build_gateway(ai, None, t, use_cache=False) for t in ('translate_news', 'translate_text')}
    report = {'approval': a.approval, 'fingerprint': facts['fingerprint'], 'preflight': {k: facts[k] for k in ('ollama_version', 'tag_entries')},
              'fixtures': [], 'negatives': [], 'technical': {}}

    # ---------------- technical checks
    t = report['technical']
    _, r, ms = run_fixture(g, 'text', {'text': 'The ship arrived.'})
    t['structured_json'] = r.status == 'available' and set(r.payload) == {'text_fa', 'translation_not_required'}
    t['post_check_loaded_digest'] = mi.check_loaded(ai.approval, ai.base_url)['digest'] == ai.approval['manifest_digest']
    slow = gw.OllamaAdapter(ai.base_url, ai.model, 1, expected_digest=ai.expected_digest, seed=42, num_thread=8, max_predict=1536)
    slow.json_schema = gw.OUTPUT_JSON_SCHEMAS['translate_text']
    slow.predict_override = 1536
    try:
        slow.complete(gw.prompt_for('translate_text', PV), json.dumps({'text': ' '.join(['The convoy moved north at night.'] * 40)}))
        t['timeout_enforced'] = False
    except gw.GatewayError as exc:
        t['timeout_enforced'] = str(exc).startswith('transient_timeout')
    streamer = gw.OllamaAdapter(ai.base_url, ai.model, 120, expected_digest=ai.expected_digest, seed=42, num_thread=8, max_predict=512)
    streamer.json_schema = gw.OUTPUT_JSON_SCHEMAS['translate_text']
    seen = {'n': 0}

    def cancel_after_two():
        seen['n'] += 1
        return seen['n'] > 2
    t0 = time.monotonic()
    try:
        streamer.stream_complete(gw.prompt_for('translate_text', PV), json.dumps({'text': ' '.join(['Officials confirmed the drill.'] * 20)}), cancel_after_two)
        t['cancellation'] = False
    except gw.GatewayError as exc:
        t['cancellation'] = str(exc) == 'cancelled'
    t['cancellation_ms'] = int((time.monotonic() - t0) * 1000)
    time.sleep(2)
    t['identity_after_cancel'] = mi.check_loaded(ai.approval, ai.base_url)['digest'] == ai.approval['manifest_digest']

    # ---------------- fixtures (sequential, concurrency 1)
    for case, kind, payload, exp in FIXTURES:
        row = {'case': case, 'kind': kind}
        if kind == 'rule':
            row.update(rule_not_required=xv.is_persian_source(payload['text']), inference=False)
            report['fixtures'].append(row)
            continue
        task, r, ms = run_fixture(g, kind, payload)
        row.update(task=task, status=r.status, error=r.error, latency_ms=r.latency_ms, wall_ms=ms,
                   tokens_in=r.tokens_in, tokens_out=r.tokens_out, served_by=r.response_model)
        row['schema_valid'] = r.status == 'available'
        if row['schema_valid']:
            out = r.payload
            row['output'] = out
            pairs = [('title', 'title_fa'), ('summary', 'summary_fa')] if kind == 'news' else [('text', 'text_fa')]
            fields = []
            for src_k, out_k in pairs:
                src = payload[src_k]
                if not src:
                    fields.append({'field': out_k, 'skipped_empty_source': True, 'empty_output': not out[out_k].strip()})
                    continue
                v = xv.validate(src, out[out_k])
                kept = [k for k in exp.get('keep', []) if k in src]
                fields.append({'field': out_k, 'passed': v.passed, 'flags': v.flags, 'reasons': v.reasons,
                               'kept_entities_missing': [k for k in kept if k not in out[out_k]],
                               'glitch': lt.decoding_glitch({src_k: src}, {out_k: out[out_k]})})
            row['fields'] = fields
            row['not_required_flag'] = out.get('translation_not_required')
        report['fixtures'].append(row)
        time.sleep(1)

    # ---------------- simulated invalid outputs
    for case, src, bad, flag in NEGATIVES:
        if flag == 'invalid_json':
            try:
                json.loads(bad)
                rejected = False
            except ValueError:
                rejected = True
            report['negatives'].append({'case': case, 'rejected': rejected, 'flags': ['invalid_json']})
            continue
        v = xv.validate(src, bad)
        report['negatives'].append({'case': case, 'rejected': not v.passed, 'expected_flag': flag,
                                    'flag_present': flag in v.flags, 'flags': v.flags})
    good = xv.validate(SRC, GOOD)
    report['negatives_control_good_output_passes'] = good.passed

    # ---------------- summary
    fx = [f for f in report['fixtures'] if f['kind'] != 'rule']
    flds = [x for f in fx for x in f.get('fields', []) if not x.get('skipped_empty_source')]
    report['summary'] = {
        'fixture_count': len(report['fixtures']), 'negative_count': len(report['negatives']),
        'inference_fixtures': len(fx), 'schema_valid': sum(f['schema_valid'] for f in fx),
        'fields_checked': len(flds), 'fields_passed': sum(x['passed'] for x in flds),
        'glitches': sum(x['glitch'] for x in flds),
        'entity_missing': sum(len(x['kept_entities_missing']) for x in flds),
        'negatives_rejected': sum(n['rejected'] for n in report['negatives']),
        'negatives_expected_flag': sum(n.get('flag_present', n['rejected']) for n in report['negatives']),
        'rule_persian_not_required': all(f['rule_not_required'] for f in report['fixtures'] if f['kind'] == 'rule'),
        'technical': t,
        'latency_ms': [f['latency_ms'] for f in fx if f.get('latency_ms')],
        'served_by': sorted({f.get('served_by') for f in fx if f.get('served_by')}),
    }
    with open(a.out, 'w', encoding='utf-8') as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, default=str)
    s2 = dict(report['summary'])
    s2.pop('latency_ms')
    print(json.dumps(s2, ensure_ascii=False, indent=2))
    lat = report['summary']['latency_ms']
    print('latency avg/max ms:', int(sum(lat) / len(lat)) if lat else None, max(lat) if lat else None)
    return 0


if __name__ == '__main__':
    sys.exit(main())

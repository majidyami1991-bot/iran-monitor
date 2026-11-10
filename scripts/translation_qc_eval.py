"""Evaluates translation_qc against reference labels.

Positive = a field labelled CRITICAL by the reviewer. A field is "flagged"
when any control fires. Reports detection (recall), false negatives,
false-positive rate on non-critical fields, precision, and per-control hits.

  dev:      python scripts/translation_qc_eval.py dev  --out <json>
  heldout:  python scripts/translation_qc_eval.py heldout --outputs <json> --labels <json> --out <json>

The dev set is the 35 earlier fixtures: stored outputs of TranslateGemma 12B,
MADLAD and NLLB, labels from runtime/local-ai-evidence/phase6/review-notes.json.
Nothing is translated here and nothing is written anywhere but --out.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'apps' / 'api'))
import translation_qc as qc  # noqa: E402

EV = ROOT / 'runtime' / 'local-ai-evidence'


def fields(path):
    d = json.load(open(path, encoding='utf-8'))
    return {f"{r['case']}:{f['field']}": f for r in d['fixtures'] for f in r['fields'] if f.get('inference')}


def score(items):
    """items: [(key, label_severity, qc_result)]"""
    tp = [k for k, sev, r in items if sev == 'critical' and r['suspect']]
    fn = [k for k, sev, r in items if sev == 'critical' and not r['suspect']]
    fp = [k for k, sev, r in items if sev != 'critical' and r['suspect']]
    tn = [k for k, sev, r in items if sev != 'critical' and not r['suspect']]
    fp_ok = [k for k, sev, r in items if sev in ('ok', 'minor') and r['suspect']]
    n_ok = sum(1 for _, sev, _ in items if sev in ('ok', 'minor'))
    mc_tp = sum(1 for _, sev, r in items if sev in ('major', 'critical') and r['suspect'])
    mc_n = sum(1 for _, sev, _ in items if sev in ('major', 'critical'))
    pos = len(tp) + len(fn)
    return {'fields': len(items), 'critical': pos, 'detected': len(tp), 'false_negatives': fn,
            'recall_critical': round(len(tp) / pos, 3) if pos else None,
            'false_positive_rate_non_critical': round(len(fp) / (len(fp) + len(tn)), 3) if fp or tn else None,
            'false_positive_rate_ok_minor': round(len(fp_ok) / n_ok, 3) if n_ok else None,
            'flagged': len(tp) + len(fp), 'precision': round(len(tp) / (len(tp) + len(fp)), 3) if tp or fp else None,
            'recall_major_or_critical': round(mc_tp / mc_n, 3) if mc_n else None,
            'false_positive_keys': fp, 'flagged_ok_minor': fp_ok}


def per_control(items):
    out = {}
    for k, sev, r in items:
        for c in r['by_control']:
            o = out.setdefault(c, {'fires': 0, 'on_critical': 0, 'on_ok_minor': 0})
            o['fires'] += 1
            o['on_critical'] += sev == 'critical'
            o['on_ok_minor'] += sev in ('ok', 'minor')
    return out


def run(model_rows, ref_rows, labels, src_rows, use_ref=True):
    items = []
    for k, f in model_rows.items():
        src = src_rows[k]['source']
        ref = (ref_rows.get(k) or {}).get('output') if use_ref and ref_rows else None
        r = qc.check(src, f.get('output') or '', ref)
        items.append((k, labels[k]['severity'], r))
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['dev', 'heldout'])
    ap.add_argument('--outputs')
    ap.add_argument('--labels')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    rep = {'qc_version': qc.QC_VERSION,
           'qc_sha256': hashlib.sha256(open(ROOT / 'apps' / 'api' / 'translation_qc.py', 'rb').read()).hexdigest(),
           'mode': a.mode}
    if a.mode == 'dev':
        labels = json.load(open(EV / 'phase6' / 'review-notes.json', encoding='utf-8'))
        tg = fields(EV / 'phase3' / 'translation-gate-tg12b.json')
        nl = fields(EV / 'phase6' / 'nmt-gate-nllb.json')
        md = fields(EV / 'phase6' / 'nmt-gate-madlad.json')
        src = nl  # NMT reports store the source text; identical fixtures
        sets = {'tg12b+nllb_ref': run(tg, nl, labels['tg12b'], src), 'tg12b_no_ref': run(tg, None, labels['tg12b'], src, False),
                'madlad+nllb_ref': run(md, nl, labels['madlad'], src), 'nllb+tg12b_ref': run(nl, tg, labels['nllb'], src)}
    else:
        outs = json.load(open(a.outputs, encoding='utf-8'))
        labels = json.load(open(a.labels, encoding='utf-8'))
        tg = {k: {'output': v['tg12b']} for k, v in outs['items'].items()}
        nl = {k: {'output': v['nllb']} for k, v in outs['items'].items()}
        src = {k: {'source': v['source']} for k, v in outs['items'].items()}
        sets = {'tg12b+nllb_ref': run(tg, nl, labels['tg12b'], src), 'tg12b_no_ref': run(tg, None, labels['tg12b'], src, False),
                'nllb+tg12b_ref': run(nl, tg, labels['nllb'], src)}
    rep['results'] = {}
    for name, items in sets.items():
        rep['results'][name] = {'score': score(items), 'per_control': per_control(items),
                                'items': [{'key': k, 'label': sev, 'suspect': r['suspect'], 'flags': r['flags']} for k, sev, r in items]}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(rep, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for name, v in rep['results'].items():
        s = v['score']
        print(f"{name}: critical {s['critical']} detected {s['detected']} recall {s['recall_critical']} | FN {s['false_negatives']} | "
              f"flagged {s['flagged']}/{s['fields']} precision {s['precision']} | FPR(non-crit) {s['false_positive_rate_non_critical']} "
              f"FPR(ok/minor) {s['false_positive_rate_ok_minor']} | recall(maj+crit) {s['recall_major_or_critical']}")


if __name__ == '__main__':
    main()

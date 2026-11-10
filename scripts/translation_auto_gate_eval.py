"""Applies translation_auto_gate to stored run outputs and (optionally)
compares item statuses with reference labels (calibration/diagnostics).

  python scripts/translation_auto_gate_eval.py --dev <gate json> --p7 <run json> --p8 <run json> \
      [--labels-dev <json> --labels-p7 <json>] [--model tg12b] [--technical-ok yes|no] --out <json>
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import translation_auto_gate as ag  # noqa: E402

DEV_SRC = ROOT / 'runtime' / 'local-ai-evidence' / 'phase6' / 'nmt-gate-nllb.json'  # stores the dev source texts


def dev_rows(path):
    src = {f"{r['case']}:{f['field']}": f['source'] for r in json.load(open(DEV_SRC, encoding='utf-8'))['fixtures']
           for f in r['fields'] if f.get('inference')}
    d = json.load(open(path, encoding='utf-8'))
    return {f"{r['case']}:{f['field']}": {'source': src[f"{r['case']}:{f['field']}"], 'output': f.get('output'),
                                          'validator_status': f['status'], 'validator_flags': f.get('flags')}
            for r in d['fixtures'] for f in r['fields'] if f.get('inference')}


def run_rows(path):
    d = json.load(open(path, encoding='utf-8'))
    return {k: {'source': v['source'], 'output': v.get('output'), 'validator_status': v.get('validator_status'),
                'validator_flags': v.get('validator_flags')} for k, v in d['items'].items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dev'); ap.add_argument('--p7'); ap.add_argument('--p8')
    ap.add_argument('--labels-dev'); ap.add_argument('--labels-p7'); ap.add_argument('--model', default='tg12b')
    ap.add_argument('--technical-ok', default='yes'); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    runs = {}
    if a.dev: runs['dev'] = dev_rows(a.dev)
    if a.p7: runs['p7'] = run_rows(a.p7)
    if a.p8: runs['p8'] = run_rows(a.p8)
    res = ag.evaluate(runs)
    labels = {}
    if a.labels_dev:
        labels.update({f'dev:{k}': v['severity'] for k, v in json.load(open(a.labels_dev, encoding='utf-8'))[a.model].items()})
    if a.labels_p7:
        labels.update({f'p7:{k}': v['severity'] for k, v in json.load(open(a.labels_p7, encoding='utf-8'))[a.model].items()})
    counts = {}
    for k, (s, _) in res.items():
        counts.setdefault(k.split(':')[0], {}).setdefault(s, 0)
        counts[k.split(':')[0]][s] += 1
    rep = {'gate_version': ag.GATE_VERSION, 'counts': counts,
           'gate_status': ag.gate(res, a.technical_ok == 'yes') if len(res) == 123 else 'n/a (not all 123 items present)',
           'items': {k: {'status': s, 'reasons': r, 'label': labels.get(k)} for k, (s, r) in res.items()}}
    if labels:
        conf = {}
        for k, (s, _) in res.items():
            if k in labels:
                conf.setdefault(labels[k], {}).setdefault(s, 0)
                conf[labels[k]][s] += 1
        rep['label_vs_status'] = conf
    json.dump(rep, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({'counts': counts, 'gate_status': rep['gate_status'], 'label_vs_status': rep.get('label_vs_status')}, ensure_ascii=False))


if __name__ == '__main__':
    main()

"""Pipeline-v2 decision (translation_v2.decide) on stored outputs, cross-
tabulated with the frozen gate status (translation_auto_gate, reference).

  python scripts/translation_v2_eval.py --name <label> [--dev <gate json>] [--p7 <run>] [--p8 <run>] [--p10 <run>] --out <json>
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'apps' / 'api')]
import translation_auto_gate as ag  # noqa: E402
import translation_auto_gate_eval as age  # noqa: E402
import translation_v2 as v2  # noqa: E402


def p10_keyfacts():
    from translation_eval_set_p10 import ITEMS
    return {i: kf for i, _, _, kf in ITEMS}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', required=True)
    ap.add_argument('--dev'); ap.add_argument('--p7'); ap.add_argument('--p8'); ap.add_argument('--p10')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    runs = {}
    if a.dev: runs['dev'] = age.dev_rows(a.dev)
    if a.p7: runs['p7'] = age.run_rows(a.p7)
    if a.p8: runs['p8'] = age.run_rows(a.p8)
    if a.p10: runs['p10'] = age.run_rows(a.p10)
    kf = dict(ag.KEYFACTS)
    kf['p10'] = p10_keyfacts()
    items, cross = {}, {}
    for s, rows in runs.items():
        for k, r in rows.items():
            gstat, greasons = ag.decide_item(r['source'], r.get('output'), r.get('validator_status'), r.get('validator_flags'), kf[s][k])
            dec, det = v2.decide(r['source'], r.get('output'))
            items[f'{s}:{k}'] = {'gate': gstat, 'v2': dec, 'v2_details': det, 'gate_reasons': greasons}
            cross.setdefault(gstat, {}).setdefault(dec, 0)
            cross[gstat][dec] += 1
    by_set = {}
    for k, v in items.items():
        s = k.split(':')[0]
        by_set.setdefault(s, {'gate': {}, 'v2': {}})
        by_set[s]['gate'][v['gate']] = by_set[s]['gate'].get(v['gate'], 0) + 1
        by_set[s]['v2'][v['v2']] = by_set[s]['v2'].get(v['v2'], 0) + 1
    rep = {'name': a.name, 'pipeline': v2.PIPELINE_VERSION, 'facts': v2.FACTS_VERSION, 'gate': ag.GATE_VERSION,
           'by_set': by_set, 'gate_vs_v2': cross, 'items': items}
    json.dump(rep, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({'name': a.name, 'by_set': by_set, 'gate_vs_v2': cross}, ensure_ascii=False))


if __name__ == '__main__':
    main()

"""Case-by-case comparison of translation gate reports (same fixtures,
same validator v2.1.0 / glossary v1.1.0): TranslateGemma 4B / 12B (stored
Ollama runs) and the NMT runs (MADLAD-400, NLLB-200).

Machine flags are grouped into the error classes of the brief. Additions
(invented facts) are not reliably detectable by the validator, so the
'additions' class comes only from the reviewer notes file, which is written
by hand after reading every output (never inferred).

  python scripts/translation_compare.py --report tg4b=<json> --report tg12b=<json> \
      --report madlad=<json> --report nllb=<json> [--notes notes.json] --out <md>
"""
import argparse
import json

CLASSES = {
    'numbers': {'number_mismatch', 'placeholder_missing', 'placeholder_residue', 'placeholder_duplicated'},
    'dates': {'date_mismatch'},
    'military_terms': set(),          # glossary misses on military terms (resolved below)
    'names': {'mixed_script_word', 'tech_code_missing', 'hashtag_missing', 'mention_missing', 'url_missing'},
    'script_or_residue': {'latin_prose_residue', 'foreign_script', 'not_persian', 'identical_to_source', 'stray_markup', 'empty_output'},
}
MILITARY = {'brigades', 'brigade', 'convoys', 'convoy', 'live-fire', 'frigates', 'frigate', 'commission', 'launch', 'deployment',
            'missile', 'strike', 'depot', 'battalion', 'navy', 'drone'}


def classify(field):
    out = {k: [] for k in ('numbers', 'dates', 'military_terms', 'names', 'script_or_residue', 'other')}
    for fl in field.get('flags') or []:
        placed = False
        for k, s in CLASSES.items():
            if fl in s:
                out[k].append(fl); placed = True
        if fl == 'glossary_term_missing':
            missing = (field.get('reasons') or {}).get('glossary_term_missing', '')
            terms = [t.strip(" '[]") for t in str(missing).split(':', 1)[-1].split(',')]
            mil = [t for t in terms if t.lower() in MILITARY]
            oth = [t for t in terms if t and t.lower() not in MILITARY]
            if mil:
                out['military_terms'].append('glossary:' + '/'.join(mil))
            if oth:
                out['names'].append('glossary:' + '/'.join(oth))
            placed = True
        if not placed:
            out['other'].append(fl)
    return {k: v for k, v in out.items() if v}


def load(path):
    d = json.load(open(path, encoding='utf-8'))
    rows = {}
    for r in d['fixtures']:
        for f in r['fields']:
            if f.get('inference'):
                rows[f"{r['case']}:{f['field']}"] = f
    return d, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', action='append', required=True)
    ap.add_argument('--notes')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    reps = {}
    for spec in a.report:
        name, path = spec.split('=', 1)
        reps[name] = load(path)
    notes = json.load(open(a.notes, encoding='utf-8')) if a.notes else {}
    names = list(reps)
    keys = []
    for n in names:
        for k in reps[n][1]:
            if k not in keys:
                keys.append(k)
    src_of = {k: f.get('source') for n in names for k, f in reps[n][1].items() if f.get('source')}
    md = ['| Case | ' + ' | '.join(names) + ' |', '|---|' + '---|' * len(names)]
    totals = {n: {'available': 0, 'fields': 0, 'numbers': 0, 'dates': 0, 'military_terms': 0, 'names': 0, 'script_or_residue': 0,
                  'additions': 0, 'critical': 0} for n in names}
    detail = []
    for k in keys:
        cells = []
        for n in names:
            f = reps[n][1].get(k)
            if not f:
                cells.append('—'); continue
            c = classify(f)
            t = totals[n]
            t['fields'] += 1
            t['available'] += f['status'] == 'available'
            for cls in ('numbers', 'dates', 'military_terms', 'names', 'script_or_residue'):
                t[cls] += bool(c.get(cls))
            nt = (notes.get(n) or {}).get(k) or {}
            if nt.get('addition'):
                t['additions'] += 1
            if nt.get('critical'):
                t['critical'] += 1
            mark = '✔' if f['status'] == 'available' and not nt.get('critical') else '✘'
            cells.append(f"{mark} " + (', '.join(f'{x}' for x in c) if c else '') + (' · ' + nt['note'] if nt.get('note') else ''))
            detail.append((k, n, f.get('source') or src_of.get(k), f.get('output'), c, nt))
        md.append(f'| {k} | ' + ' | '.join(cells) + ' |')
    summ = ['| Measure | ' + ' | '.join(names) + ' |', '|---|' + '---|' * len(names)]
    for m in ('fields', 'available', 'numbers', 'dates', 'military_terms', 'names', 'script_or_residue', 'additions', 'critical'):
        summ.append(f'| {m} | ' + ' | '.join(str(totals[n][m]) for n in names) + ' |')
    for n in names:
        s = reps[n][0]['summary']
        totals[n]['negatives'] = s.get('negatives_rejected')
    out = ['## Summary (fields with a machine flag per class; additions/critical from the reviewer notes)', ''] + summ + \
          ['', '## Case by case', ''] + md + ['', '## Outputs', '']
    for k, n, src, outp, c, nt in detail:
        out.append(f'- **{k} · {n}** — {"; ".join(f"{x}: {v}" for x, v in c.items()) or "no machine flag"}'
                   + (f" — reviewer: {nt.get('note')}" if nt.get('note') else ''))
        out.append(f'  - EN: {src}')
        out.append(f'  - FA: {outp}')
    open(a.out, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print(json.dumps(totals, ensure_ascii=False))


if __name__ == '__main__':
    main()

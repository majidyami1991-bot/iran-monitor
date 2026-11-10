"""Human review pack for the phase-7 held-out translations (TranslateGemma 12B).

Read-only: stored outputs, the AI reference labels, the frozen QC v1.0.0
results and the validator v2.1.0 flags. Every human field is left empty;
nothing is approved.

  python scripts/translation_review_pack.py <out.md>
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / 'runtime' / 'local-ai-evidence' / 'phase7'
sys.path.insert(0, str(ROOT / 'scripts'))
from translation_qc_heldout_labels import TG12B as LABELS  # noqa: E402

out = json.load(open(EV / 'heldout-tg12b.json', encoding='utf-8'))
qc = {x['key']: x for x in json.load(open(EV / 'qc-heldout.json', encoding='utf-8'))['results']['tg12b_no_ref']['items']}
SEV_FA = {'critical': 'بحرانی', 'major': 'عمده', 'minor': 'جزئی', 'ok': 'بدون خطا'}


# Pointers added for the pack where the label note quotes only English (marked
# as reviewer pointers in the pack; the frozen labels file is not changed).
SPAN_HINTS = {'H01': ['به میزان 3.5%']}


def suspect_spans(output, note, flags, hid=None):
    """Text in the output the label note or a flag points at (no inference)."""
    spans = [s for s in re.findall(r'«([^»]+)»', note or '') if s and s in (output or '')]
    spans += [h + ' (pointer)' for h in SPAN_HINTS.get(hid, []) if h in (output or '')]
    for f in flags:
        kind, _, val = f.partition(':')
        if kind in ('echelon_added', 'unsupported_word') and val:
            for w in re.findall(r'\S*' + re.escape(val.replace(' ', '')) + r'\S*', (output or '').replace('‌', '')):
                spans.append(w)
        if kind == 'placeholder_text':
            m = re.search(r'\[[^\]]+\]', output or '')
            if m:
                spans.append(m.group(0))
    return list(dict.fromkeys(spans))


md = ['# Phase-7 translations — human review pack (TranslateGemma 12B, 40 held-out items)', '',
      'Sources: `scripts/translation_qc_heldout.py` (commit `07b4ada`). Outputs: `runtime/local-ai-evidence/phase7/heldout-tg12b.json`.',
      'Prior labels: `scripts/translation_qc_heldout_labels.py` (commit `77b9a31`), written by **Claude (AI), not a human**.',
      'Detected errors: QC `translation-qc-v1.0.0` (frozen, sha256 `bfaa3c55…`) and validator `translation-validator-v2.1.0`.', '',
      '**Nothing here is pre-approved.** The decision and comment fields are empty for the human reviewer.', '',
      '## How to review', '',
      '1. Read the English source and the Persian translation. Judge the translation yourself first.',
      '2. Only then compare your judgement with the AI label and the detected errors.',
      '3. Choose one severity:',
      '   - **critical:** a wrong fact, number, entity, role or meaning; invented information; or a key fact dropped;',
      '   - **major:** a wrong military term, foreign words, or ungrammatical Persian;',
      '   - **minor:** small issues;',
      '   - **none:** no error.',
      '4. Note whether you agree with the AI label. Disagreements decide whether the phase-7 figures stand.', '',
      '| Summary (AI labels) | critical | major | minor | none |', '|---|---|---|---|---|',
      '| count | ' + ' | '.join(str(sum(1 for s, _ in LABELS.values() if s == k)) for k in ('critical', 'major', 'minor', 'ok')) + ' |', '']
for hid, item in out['items'].items():
    sev, note = LABELS[hid]
    q = qc[hid]
    vflags = item['validator_flags'] if item['validator_status'] != 'available' else []
    spans = suspect_spans(item['output'], note, q['flags'], hid)
    md += ['---', '', f'### {hid} ({item["topic"]})', '',
           f'**English source:** {item["source"]}', '',
           f'**TranslateGemma 12B:** {item["output"]}', '',
           f'**Prior label (AI):** {sev} ({SEV_FA[sev]}){" — " + note if note else ""}', '',
           f'**Detected by QC v1.0.0:** {", ".join(f"`{f}`" for f in q["flags"]) or "none"}  ',
           f'**Detected by validator v2.1.0:** {", ".join(f"`{f}`" for f in vflags) or "none"}', '',
           f'**Suspect part of the translation:** {" ؛ ".join(f"«{s}»" for s in spans) or "—"}', '',
           '| Human decision | |', '|---|---|',
           '| Severity (critical / major / minor / none) | |',
           '| Agrees with the AI label? (yes / no) | |',
           '| Correct translation of the key fact (if wrong) | |',
           '| Reviewer comment | |',
           '| Reviewer / date | |', '']
Path(sys.argv[1]).write_text('\n'.join(md) + '\n', encoding='utf-8')
print('written', sys.argv[1], len(out['items']), 'items')

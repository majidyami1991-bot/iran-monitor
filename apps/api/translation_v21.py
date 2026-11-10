"""Local translation pipeline v2.1 — operational QC filter for the 3003 lab.

Builds on translation_v2 (frozen at 4ff70b5, unchanged) and adds, as facts
version translation-facts-v1.1.0:

  * terminology the v2.0 run missed (phase 10, AI audit): "mobilisation /
    mobilization" must be rendered with «بسیج» (H25 was rendered as alert),
    "mechanised / mechanized" with «مکانیزه» (M01 was rendered as armoured);
  * Persian number words, «N هزار / میلیون / میلیارد» forms and ordinals are
    read as numbers (the v2.0 instrument limit behind most false FAILs:
    «دو هزار», «۸۰ هزار», «نوزدهمین»);
  * a scale ADDED in the output (source "80", output «۸۰ هزار») is a conflict.

Decision semantics are unchanged: ACCEPT only if every fact is verified and
no control objects; ACCEPT means "no automated objection", never "correct".
"""
import re

import translation_tg as tg
import translation_v2 as v2

PIPELINE_VERSION = 'translation-pipeline-v2.1.0'
FACTS_VERSION = 'translation-facts-v1.1.0'

TERMS = [(r'\bmobili[sz](?:e|es|ed|ing|ation|ations)\b', r'بسیج', 'mobilisation'),
         (r'\bmechani[sz]ed\b', r'مکانیزه', 'mechanised')]

_UNITS = {'صفر': 0, 'یک': 1, 'یه': 1, 'دو': 2, 'سه': 3, 'چهار': 4, 'پنج': 5, 'شش': 6, 'شیش': 6, 'هفت': 7, 'هشت': 8, 'نه': 9,
          'ده': 10, 'یازده': 11, 'دوازده': 12, 'سیزده': 13, 'چهارده': 14, 'پانزده': 15, 'پونزده': 15, 'شانزده': 16, 'هفده': 17,
          'هجده': 18, 'هیجده': 18, 'نوزده': 19, 'بیست': 20, 'سی': 30, 'چهل': 40, 'پنجاه': 50, 'شصت': 60, 'هفتاد': 70,
          'هشتاد': 80, 'نود': 90, 'صد': 100, 'یکصد': 100, 'دویست': 200, 'سیصد': 300, 'چهارصد': 400, 'پانصد': 500, 'ششصد': 600,
          'هفتصد': 700, 'هشتصد': 800, 'نهصد': 900}
_MULT = {'هزار': 1_000, 'میلیون': 1_000_000, 'میلیارد': 1_000_000_000, 'تریلیون': 1_000_000_000_000}
_ORD_STEM = {'اول': 1, 'یکم': 1, 'دوم': 2, 'سوم': 3}
_W = '[ء-يٱ-ۓ]'


def _word_value(w):
    """Value of one number word incl. ordinal forms (نوزدهم/نوزدهمین/سومین); None if not a number word."""
    if w in _UNITS:
        return _UNITS[w]
    if w in _ORD_STEM:
        return _ORD_STEM[w]
    if w.endswith('ین'):                 # اولین, سومین, نوزدهمین
        w = w[:-2]
        if w in _ORD_STEM:
            return _ORD_STEM[w]
    if w.endswith('م') and w[:-1] in _UNITS:   # نوزدهم, چهارم, دهم
        return _UNITS[w[:-1]]
    return None


def persian_number_values(fa):
    """All numeric values expressed in the output, including word numbers and
    digit+multiplier forms. Returns (values, digit_with_multiplier) where the
    second set holds (digit_value, multiplier) pairs seen as «N هزار»."""
    t = v2.norm(fa)
    vals, pairs = set(), set()
    for m in re.finditer(r'(\d+(?:\.\d+)?)\s*(هزار|میلیون|میلیارد|تریلیون)', t):
        d = float(m.group(1))
        vals.add(d * _MULT[m.group(2)])
        pairs.add((d, _MULT[m.group(2)]))
    words = re.findall(_W + '+|\\d+(?:\\.\\d+)?', t)
    i = 0
    while i < len(words):
        total, cur, used, j = 0, 0, False, i
        while j < len(words):
            w = words[j]
            if w == 'و' and used:
                j += 1
                continue
            v = _word_value(w)
            if v is not None and not (w == 'نه' and not used and j + 1 < len(words) and _word_value(words[j + 1]) is None
                                      and words[j + 1] not in _MULT):
                cur += v
                used = True
            elif w in _MULT and used:
                total += (cur or 1) * _MULT[w]
                cur = 0
            else:
                break
            j += 1
        if used:
            vals.add(float(total + cur))
            i = j
        else:
            i += 1
    return vals, pairs


def extract(source):
    facts = v2.extract(source)
    sl = (source or '').lower()
    for pat, fa, name in TERMS:
        if re.search(pat, sl):
            facts.append({'type': 'military', 'value': name, 'fa': fa})
    return facts


def verify(facts, output):
    res = v2.verify(facts, output)
    words, pairs = persian_number_values(output or '')
    fixed = []
    for f, st, det in res:
        if f['type'] == 'number' and st == 'missing' and det == f.get('text', '') and f.get('value') in words:
            st, det = 'ok', 'persian_number_form'
            # scale/currency/percent sub-checks still apply when the base value is matched only as words
            fa = v2.norm(output)
            if f.get('scale') and not re.search(v2.SCALE.get(f['scale'], f['scale']), fa):
                st, det = 'missing', 'scale:' + f['scale']
            if f.get('currency') and not re.search(v2.CURRENCY.get(f['currency'], f['currency']), fa):
                st, det = 'missing', 'currency:' + f['currency']
            if f.get('percent') is True and not re.search(r'%|درصد', fa):
                st, det = 'missing', 'percent'
        elif f['type'] == 'number_unit' and st == 'missing' and f.get('value') in words and re.search(f['unit'], v2.norm(output)):
            st, det = 'ok', 'persian_number_form'
        fixed.append((f, st, det))
    src_vals = {f['value'] for f in facts if f['type'] in ('number', 'number_unit') and f.get('value') is not None}
    src_scaled = {f['value'] for f in facts if f.get('scale')}
    for d, mult in sorted(pairs):
        if d in src_vals and d * mult not in src_vals and d not in src_scaled:
            fixed.append(({'type': 'scale_added', 'value': d}, 'conflict', f'x{mult}'))
    return fixed


def decide(source, output):
    """→ (decision, details), same contract as translation_v2.decide."""
    if not (output or '').strip():
        return 'REJECT_CRITICAL', {'reasons': ['empty_output']}
    facts = extract(source)
    ver = verify(facts, output)
    _, base = v2.decide(source, output)   # validator + QC layers (fact layer recomputed below)
    present = v2._out_numbers(output) | persian_number_values(output)[0]

    def number_really_missing(x):
        # QC's number check does not read word numbers / the Persian decimal separator (v2.0 instrument limit)
        m = re.match(r'qc:number_missing:([\d.,]+)$', x)
        if not m:
            return True
        try:
            return float(m.group(1).replace(',', '')) not in present
        except ValueError:
            return True
    keep = lambda xs: [x for x in xs if x.startswith(('validator:', 'qc:')) and number_really_missing(x)]
    crit = [f'{x[0]["type"]}:{x[0].get("value", x[0].get("kind"))}:{x[1]}{":" + x[2] if x[2] else ""}' for x in ver if x[1] in ('missing', 'conflict')]
    unc = [f'{x[0]["type"]}:{x[0].get("value", x[0].get("kind"))}' for x in ver if x[1] == 'unverifiable']
    details = {'facts': len(facts), 'critical': crit + keep(base.get('critical', [])),
               'uncertain': unc + keep(base.get('uncertain', [])),
               'verified': [f'{x[0]["type"]}:{x[0].get("value", x[0].get("kind"))}' for x in ver if x[1] == 'ok'],
               'pipeline': PIPELINE_VERSION, 'facts_version': FACTS_VERSION}
    if details['critical']:
        return 'REJECT_CRITICAL', details
    if details['uncertain']:
        return 'REJECT_UNCERTAIN', details
    return 'ACCEPT', details


translate_direct = v2.translate_direct
PROMPT_VERSION = tg.PROMPT_VERSION

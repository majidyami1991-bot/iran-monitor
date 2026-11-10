"""Local translation pipeline v2 (placeholder-free) — EVALUATION ONLY.

Differences from v1 (translation_tg.translate_field):
  * the English text is sent to the model unchanged (no salted `ZQ…`
    placeholders, no restore step);
  * sensitive information is extracted from the SOURCE into a structured
    fact list (numbers and values, dates and times, currencies, people and
    organisations, roles and their modifiers, military terms, negation,
    certainty, to/by/from relations, verbatim tokens) and each fact is
    verified in the Persian output by deterministic code that is
    independent of the model;
  * decision: ACCEPT only if every fact is verified and no other control
    flags the output; REJECT_CRITICAL on a missing or conflicting fact or a
    hard validator / QC finding; REJECT_UNCERTAIN otherwise. Nothing is
    corrected, approved or published here; ACCEPT means "no automated
    objection", not "proven correct".
"""
import re
import time
import unicodedata

import assistant_relevance as ar
import translation_qc as qc
import translation_tg as tg

PIPELINE_VERSION = 'translation-pipeline-v2.0.0'
FACTS_VERSION = 'translation-facts-v1.0.0'

_D = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩٫٬يكۀة', '0123456789012345678 9.,یکهه'.replace(' ', ''))
_L = 'ء-يٱ-ۓ'


def norm(t):
    t = unicodedata.normalize('NFC', t or '').translate(_D).replace('‌', ' ').replace('ـ', '')
    t = re.sub('[ً-ْ]', '', t)
    return re.sub(r'\s+', ' ', t)


SCALE = {'billion': r'میلیارد', 'bn': r'میلیارد', 'million': r'میلیون', 'm': r'میلیون', 'trillion': r'تریلیون|هزار میلیارد'}
CURRENCY = {'$': r'دلار|\$', '€': r'یورو|€', '£': r'پوند|£', '¥': r'ین|¥', 'dollar': r'دلار|\$', 'euro': r'یورو|€',
            'pound': r'پوند|£', 'yen': r'ین|¥', 'rouble': r'روبل', 'ruble': r'روبل', 'cents': r'سنت', 'cent': r'سنت'}
ALL_CURRENCY_FA = r'دلار|یورو|پوند|روبل|(?<![' + _L + r'])ین(?![' + _L + r'])'
MONTHS = qc.MONTHS
WEEKDAYS = qc.WEEKDAYS
NEG_EN = re.compile(r"\b(?:not|no|never|none|neither|nor|without|n't|failed to|cannot|denied|denies|deny)\b|n't\b", re.I)
NEG_FA = re.compile(r'(?<![' + _L + r'])(?:نمی|نخواه|نکرد|نکردند|نشد|نشده|ندارد|ندارند|نیست|نبود|نداد|نرسید|نپذیرفت|نتوانست|نزد|نخورد|نکرده|ناکام|هیچ|بدون|هرگز|نه|رد کرد|تکذیب|انکار|نادرست|فرو ?نپاشید)')
# Applied to the ORIGINAL-case source: the modal "may" is lowercase, the month "May" is not.
CERT = [(r'(?i:\breportedly\b|\bit is reported\b)', r'گزارش|ظاهرا|ظاهراً|گفته می ?شود|به نقل'),
        (r'(?i:\ballege[sd]?\b|\ballegedly\b|\bclaimed?\b|\bclaims\b)', r'ادعا|مدعی'),
        (r'\bmay\b|\bmight\b|\bcould\b|(?i:\bpossibly\b|\bperhaps\b)', r'ممکن|احتمال|شاید|می ?تواند|امکان'),
        (r'(?i:\bunlikely\b)', r'بعید|احتمال (کمی|ضعیفی|اندکی)|به نظر نمی ?رسد|به احتمال زیاد[^.]*(نخواهد|نخواهند|نمی)'),
        (r'(?i:\bunconfirmed\b|\bnot confirmed\b|\bdid not confirm\b)', r'تایید ?نشده|تأیید ?نشده|تایید نکرد|تأیید نکرد|غیر ?رسمی'),
        (r'(?i:\bconfirmed\b)(?! nor)', r'تایید|تأیید')]
MODIFIERS = [(r'\bformer\b', r'سابق|پیشین|اسبق'), (r'\b(?:deputy|vice)\b', r'معاون|نایب'),
             (r'\b(?:acting|interim|caretaker)\b', r'سرپرست|موقت|کفیل'), (r'\bopposition\b', r'مخالف|اپوزیسیون'),
             (r'\bsenior\b', r'ارشد|بلندپایه|عالی ?رتبه'), (r'\bchief of staff\b', r'رئیس ستاد|رییس ستاد')]
MIL_EXTRA = [(r'\blive[- ]fire\b', r'(شلیک|آتش|تیر|تیراندازی)\S* (واقعی|جنگی|زنده)'), (r'\bdecommission', r'از خدمت خارج|بازنشسته|از رده خارج|خروج از خدمت'),
             (r'\bsorties?\b', r'سورتی|پرواز|ماموریت|مأموریت'), (r'\b(?:artillery )?batter(?:y|ies)\b', r'آتشبار|آتش بار|باتری'),
             (r'\bcompan(?:y|ies) of\b', r'گروهان'), (r'\bbomber', r'بمب ?افکن'), (r'\bspecial forces\b', r'نیروهای ویژه|یگان ویژه'),
             (r'\bamphibious\b', r'آبی ?-?خاکی|دوزیست|دریایی ?-?زمینی'), (r'\btest[- ]fir', r'آزمایش|آزمایشی|تست')]
# attribution: "<actor> said/told/reported/confirmed" — the actor must survive
ATTRIBUTION = [(r'\binvestigators?\b', r'بازرس|محقق|تحقیق'), (r'\bofficials?\b', r'مقام|مسئول|مسوول'), (r'\bpolice\b', r'پلیس'),
               (r'\banalysts?\b', r'تحلیلگر|کارشناس'), (r'\bsources?\b', r'منبع|منابع'), (r'\bexperts?\b', r'کارشناس|متخصص'),
               (r'\bdiplomats?\b', r'دیپلمات'), (r'\bwitness(?:es)?\b', r'شاهد|شاهدان')]
_SAID = r'\b(?:said|says|told|reported|confirmed|claimed|stated|announced|warned)\b'
CHANGE_VERB = r'(?:rose|rise[ns]?|risen|increase[ds]?|grew|grow[sn]?|growth|fell|fall[sen]*|drop(?:ped|s)?|cut|reduce[ds]?|decline[ds]?|slow(?:ed|s)?|climb(?:ed|s)?|jump(?:ed|s)?|surge[ds]?|shrank|shrink[s]?|raise[ds]?|lower(?:ed|s)?)'
UNITS = {r'kilomet(?:re|er)s?|km': 'کیلومتر', r'met(?:re|er)s?': 'متر', r'kilograms?|kg': 'کیلوگرم', r'tonnes?|tons?': 'تن',
         r'hours?': 'ساعت', r'days?': 'روز', r'miles?': 'مایل', r'barrels?': 'بشکه', r'litres?|liters?': 'لیتر'}
_NUMRX = r'[$€£¥]?\d[\d,]*(?:\.\d+)?\s?(?:percentage points?|percent|%|billion|million|trillion|bn)?'


def _val(tok):
    m = re.search(r'\d[\d,]*(?:\.\d+)?', tok)
    return float(m.group(0).replace(',', '')) if m else None


def _out_numbers(fa):
    vals = set()
    for t in qc._num_tokens(fa, True) | set(re.findall(r'\d+(?:[.,]\d+)*', norm(fa))):
        try:
            vals.add(float(str(t).replace(',', '')))
        except ValueError:
            pass
    return vals


def _skeleton(word, latin):
    """Consonant skeleton for transliteration matching (heuristic)."""
    if latin:
        w = word.lower()
        for a, b in (('sch', 's'), ('sh', 's'), ('ch', 'c'), ('ph', 'f'), ('th', 't'), ('kh', 'k'), ('zh', 'z'), ('ck', 'k'), ('q', 'k'),
                     ('x', 'ks'), ('c', 'k'), ('w', 'v'), ('j', 'j'), ('y', '')):
            w = w.replace(a, b)
        w = re.sub(r'[aeiouäöüéèóáíúëï\W\d_]', '', w)
        return re.sub(r'(.)\1+', r'\1', w)
    m = {'ب': 'b', 'پ': 'p', 'ت': 't', 'ث': 's', 'ج': 'j', 'چ': 'c', 'ح': 'h', 'خ': 'k', 'د': 'd', 'ذ': 'z', 'ر': 'r', 'ز': 'z', 'ژ': 'z',
         'س': 's', 'ش': 's', 'ص': 's', 'ض': 'z', 'ط': 't', 'ظ': 'z', 'غ': 'g', 'ق': 'k', 'ف': 'f', 'ک': 'k', 'گ': 'g', 'ل': 'l', 'م': 'm',
         'ن': 'n', 'ه': 'h', 'و': 'v', 'ی': ''}
    s = ''.join(m.get(ch, '') for ch in norm(word))
    return re.sub(r'(.)\1+', r'\1', s)


def _name_in_output(name, fa):
    if re.search(re.escape(name), fa):
        return True
    sk = _skeleton(name, True).replace('h', '')
    if len(sk) < 2:
        return None
    words = re.findall(r'[' + _L + r']{2,}', norm(fa))
    for i in range(len(words)):
        for j in (1, 2, 3):
            cand = _skeleton(''.join(words[i:i + j]), False).replace('h', '')
            if cand and (cand == sk or (len(sk) >= 4 and (sk in cand or cand in sk) and abs(len(cand) - len(sk)) <= 1)):
                return True
    return None


def extract(source):
    """Structured sensitive facts of the English source (source unchanged)."""
    s = source or ''
    facts = []
    codes = set()
    for m in re.finditer(r'https?://\S+|@\w+|#\w+|\b[A-Z][A-Za-z]{0,4}-?\d+[A-Za-z]*\b|\b[A-Z]\d+[A-Z]+\b', s):
        tok = m.group(0).rstrip('.,;:)')
        facts.append({'type': 'token', 'value': tok})
        codes.add(m.span())
    for m in re.finditer(r'\b(\d{1,2}):(\d{2})\b', s):
        facts.append({'type': 'time', 'value': m.group(0)})
        codes.add(m.span())
    for m in re.finditer(_NUMRX, s):
        if any(a <= m.start() < b for a, b in codes) or not re.search(r'\d', m.group(0)):
            continue
        tok = m.group(0).strip()
        pre = s[max(0, m.start() - 1):m.start()]
        cur = tok[0] if tok[0] in '$€£¥' else None
        tail = s[m.end():m.end() + 14].lower()
        f = {'type': 'number', 'value': _val(tok), 'text': tok}
        if re.search(r'billion|million|trillion|bn\b', tok + ' ' + tail[:9]):
            f['scale'] = re.search(r'billion|million|trillion|bn', tok + ' ' + tail[:9]).group(0)
        if cur:
            f['currency'] = cur
        elif re.match(r'\s*(?:billion |million |trillion )?(dollars?|euros?|pounds?|yen|roubles?|rubles?|cents?)', tail):
            f['currency'] = re.match(r'\s*(?:billion |million |trillion )?(dollars?|euros?|pounds?|yen|roubles?|rubles?|cents?)', tail).group(1).rstrip('s')
        if '%' in tok or 'percent' in tok:
            f['percent'] = 'points' if 'point' in tok else True
        if re.match(r'\d{4}$', tok) and 1900 <= f['value'] <= 2100:
            f['year'] = True
        facts.append(f)
    for m in re.finditer(r'(\d[\d,]*(?:\.\d+)?)[\s-]*(' + '|'.join(UNITS) + r')\b', s, re.I):
        unit = next(u for u in UNITS if re.fullmatch(u, m.group(2), re.I))
        facts.append({'type': 'number_unit', 'value': _val(m.group(1)), 'unit': UNITS[unit]})
    for m in re.finditer(r'(?<![\d.,])(\d[\d,]*)\s+([A-Z][A-Za-z]{0,4}-?\d+[A-Za-z0-9]*)\b', s):
        facts.append({'type': 'count_token', 'value': _val(m.group(1)), 'token': m.group(2)})
    for m in re.finditer(CHANGE_VERB + r'\s+(' + _NUMRX + r')\s+to\s+(' + _NUMRX + r')', s, re.I):
        facts.append({'type': 'relation', 'kind': 'by', 'a': _val(m.group(1))})
    for w, v in qc.EN_WORDS.items():
        if re.search(r'\b' + w + r'\b', s, re.I) and v not in (1,) and w not in ('hundred', 'dozen', 'second'):
            facts.append({'type': 'number', 'value': float(v), 'text': w, 'word': True})
    for en in MONTHS:
        if re.search(r'\b' + en + r'\b', s, re.I) and not (en == 'may' and not re.search(r'\d\s+May\b|\bMay\s+\d|\bin May\b|for May\b', s)):
            facts.append({'type': 'month', 'value': en})
    for en, fa in WEEKDAYS.items():
        if re.search(r'\b' + en + r'\b', s, re.I):
            facts.append({'type': 'weekday', 'value': en, 'fa': fa})
    for a in ar._ENTITY_ANCHORS:
        if a.kind in ('person', 'org', 'country', 'place') and a.found(s):
            facts.append({'type': 'entity', 'value': a.canonical})
    known = ' '.join(f['value'] for f in facts if f['type'] in ('entity', 'token'))
    for m in re.finditer(r'(?<![.!?]\s)(?<!^)\b([A-Z][a-zé]+(?:[- ][A-Z][a-zé]+){0,2})\b', s):
        name = m.group(1)
        if name.lower() in ('the', 'a', 'an') or any(name in x or x in name for x in known.split()) or \
                name.lower() in {k for k in MONTHS} | set(WEEKDAYS) or name in ('Former', 'Vice', 'Interim', 'Deputy', 'Acting', 'General', 'Captain'):
            continue
        facts.append({'type': 'name', 'value': name})
    for pat, fa in qc.ROLES:
        if re.search(pat, s.lower()):
            facts.append({'type': 'role', 'value': pat, 'fa': fa})
    for pat, fa in MODIFIERS:
        if re.search(pat, s, re.I):
            facts.append({'type': 'role_modifier', 'value': pat, 'fa': fa})
    sl = s.lower()
    for e, fa in qc.ECHELONS.items():
        if re.search(r'\b' + e + r's?\b', sl):
            facts.append({'type': 'echelon', 'value': e, 'fa': fa})
    for e, fa in qc.SHIPS.items():
        if re.search(r'\b' + e + r's?\b', sl):
            facts.append({'type': 'ship', 'value': e, 'fa': fa})
    for pat, fa in MIL_EXTRA:
        if re.search(pat, sl):
            facts.append({'type': 'military', 'value': pat, 'fa': fa})
    for pat, fa in ATTRIBUTION:
        m = re.search(pat, sl)
        if m and re.search(_SAID, sl[max(0, m.start() - 40):m.end() + 40]):
            facts.append({'type': 'attribution', 'value': pat, 'fa': fa})
    for m in re.finditer(r'[«"“]([^»"”]*[؀-ۿЀ-ӿ֐-׿][^»"”]*)[»"”]', s):
        facts.append({'type': 'quoted_verbatim', 'value': m.group(1).strip()})
    if NEG_EN.search(s):
        facts.append({'type': 'negation', 'value': NEG_EN.search(s).group(0)})
    for pat, fa in CERT:
        if re.search(pat, s):
            facts.append({'type': 'certainty', 'value': pat, 'fa': fa})
            break
    for m in re.finditer(CHANGE_VERB + r'[^.]{0,40}?\b(from|to|by)\s+(' + _NUMRX + r')(?:[^.]{0,25}?\b(to)\s+(' + _NUMRX + r'))?', s, re.I):
        if m.group(1).lower() == 'from' and m.group(3):
            facts.append({'type': 'relation', 'kind': 'from_to', 'a': _val(m.group(2)), 'b': _val(m.group(4))})
        else:
            facts.append({'type': 'relation', 'kind': m.group(1).lower(), 'a': _val(m.group(2))})
    for m in re.finditer(r'\b(to|from)\s+(' + _NUMRX + r')[^.]{0,20}?\b(from|to)\s+(' + _NUMRX + r')', s, re.I):
        if m.group(1).lower() == 'to' and m.group(3).lower() == 'from' and re.search(CHANGE_VERB, s[:m.start()], re.I):
            facts.append({'type': 'relation', 'kind': 'from_to', 'a': _val(m.group(4)), 'b': _val(m.group(2))})
    return facts


def _num_pat(v):
    s = ('%g' % v)
    if v >= 1000 and float(v).is_integer():
        i = str(int(v))
        return r'(?<![\d.])(?:' + re.escape(i) + '|' + re.escape(f'{int(v):,}') + r')(?![\d])'
    return r'(?<![\d.])' + re.escape(s) + r'0*(?![\d])'


def verify(facts, output):
    """→ [(fact, status, detail)] status: ok | missing | conflict | unverifiable"""
    fa = norm(output)
    nums = _out_numbers(output)
    res = []
    src_currencies = {f.get('currency') for f in facts if f.get('currency')}
    for f in facts:
        t = f['type']
        if t == 'token':
            res.append((f, 'ok' if f['value'] in (output or '') else 'missing', ''))
        elif t == 'time':
            h, mnt = f['value'].split(':')
            ok = re.search(r'(?<!\d)0?' + str(int(h)) + ':' + mnt + r'(?!\d)', fa)
            res.append((f, 'ok' if ok else 'missing', ''))
        elif t == 'number':
            if f['value'] is None:
                continue
            if f['value'] not in nums:
                res.append((f, 'missing', f.get('text', ''))); continue
            st, det = 'ok', []
            if f.get('scale') and not re.search(SCALE.get(f['scale'], f['scale']), fa):
                st = 'missing'; det.append('scale:' + f['scale'])
            if f.get('currency'):
                cur = CURRENCY.get(f['currency'], f['currency'])
                if not re.search(cur, fa):
                    st = 'missing'; det.append('currency:' + f['currency'])
            if f.get('percent') == 'points' and not re.search(r'واحد درصد', fa):
                st = 'conflict'; det.append('points_as_percent')
            elif f.get('percent') is True and not re.search(r'%|درصد', fa):
                st = 'missing'; det.append('percent')
            if re.search(r'(?:مدل|نسخه|کد|رمز|شرکت|سازمان)\s*' + _num_pat(f['value']), fa):
                st = 'conflict'; det.append('number_relabelled')
            res.append((f, st, ','.join(det)))
        elif t == 'number_unit':
            p = _num_pat(f['value']) + r'\s*-?\s*(?:' + f['unit'] + r')'
            res.append((f, 'ok' if re.search(p, fa) else 'missing', f['unit']))
        elif t == 'count_token':
            if re.search(_num_pat(f['value']) + r'\s*و\s*' + re.escape(f['token']), fa):
                res.append((f, 'conflict', 'count_split_from_token'))
            else:
                res.append((f, 'ok', ''))
        elif t == 'month':
            if re.search(r'\b' + f['value'] + r'\b', output or '', re.I):
                res.append((f, 'conflict', 'month_untranslated'))
            else:
                res.append((f, 'ok' if qc._has(fa, MONTHS[f['value']]) else 'missing', ''))
        elif t == 'weekday':
            res.append((f, 'ok' if f['fa'].replace(' ', '') in fa.replace(' ', '') else 'missing', ''))
        elif t == 'entity':
            a = ar._BY_CANON[f['value']]
            fa_aliases = [x for x, c in ar._FA_ALIASES if c == f['value']] + qc.QC_ALIASES.get(f['value'], [])
            ok = a.found(output or '') or any(re.search(r'(?<![' + _L + r'])' + re.escape(x), ' ' + ar.norm_fa(fa)) for x in fa_aliases) \
                or any(f['value'] in ar._BY_CANON[o].parents for o in ar._BY_CANON if ar._BY_CANON[o].kind == 'place'
                       and any(re.search(re.escape(x), ar.norm_fa(fa)) for x, c in ar._FA_ALIASES if c == o))
            res.append((f, 'ok' if ok else 'unverifiable' if a.kind == 'place' else 'missing', ''))
        elif t == 'name':
            r = _name_in_output(f['value'], output or '')
            res.append((f, 'ok' if r else 'unverifiable', ''))
        elif t == 'quoted_verbatim':
            res.append((f, 'ok' if norm(f['value']) in fa else 'missing', 'quote_altered'))
        elif t in ('role', 'role_modifier', 'military', 'attribution'):
            ok = re.search(f['fa'], fa) if isinstance(f['fa'], str) else qc._has(fa, f['fa'])
            res.append((f, 'ok' if ok else 'missing', ''))
        elif t in ('echelon', 'ship'):
            ok = qc._has(fa, f['fa'])
            res.append((f, 'ok' if ok else 'missing', ''))
        elif t == 'negation':
            res.append((f, 'ok' if NEG_FA.search(fa) else 'missing', ''))
        elif t == 'certainty':
            res.append((f, 'ok' if re.search(f['fa'], fa) else 'missing', ''))
        elif t == 'relation':
            a = _num_pat(f['a'])
            by_a = re.search(r'(?:به میزان|به اندازه)\s*\$?' + a, fa)
            reach_a = re.search(a + r'[^.]{0,40}(?:رسید|رسیده|می ?رسد|برسد)', fa)
            to_a = re.search(r'(?<!میزان )(?<!اندازه )به\s*\$?' + a, fa)
            if f['kind'] == 'to':
                if (to_a or reach_a) and not (by_a and not reach_a):
                    res.append((f, 'ok', ''))
                elif by_a:
                    res.append((f, 'conflict', 'level_rendered_as_change'))
                else:
                    res.append((f, 'unverifiable', ''))
            elif f['kind'] == 'by':
                if re.search(r'از\s*\$?' + a, fa):
                    res.append((f, 'conflict', 'change_rendered_as_origin'))
                elif to_a and re.search(a + r'[^.]{0,15}(?:رسید|رسیده)', fa) and not by_a:
                    res.append((f, 'conflict', 'change_rendered_as_level'))
                elif by_a or re.search(a + r'\s*(?:%|درصد|واحد درصد)?[^.]{0,12}(?:افزایش|کاهش|رشد|افت)', fa):
                    res.append((f, 'ok', ''))
                else:
                    res.append((f, 'unverifiable', ''))
            elif f['kind'] == 'from_to':
                b = _num_pat(f['b'])
                if re.search(r'از\s*(?:سطح |میزان )?\$?' + a + r'[^.]{0,40}به\s*(?:سطح |میزان )?\$?' + b, fa):
                    res.append((f, 'ok', ''))
                elif re.search(r'از\s*\$?' + b + r'[^.]{0,40}به\s*\$?' + a, fa):
                    res.append((f, 'conflict', 'from_to_swapped'))
                else:
                    res.append((f, 'unverifiable', ''))
    for m in re.finditer(r'\d(?:[\d.,]*\d)?\s+([a-zA-Z]{1,2})(?![A-Za-z0-9-])', output or ''):
        res.append(({'type': 'stray_latin', 'value': m.group(1)}, 'conflict', 'stray_latin_after_number'))
    if re.search(r'%\s*(?:میلیارد|میلیون)', fa):
        res.append(({'type': 'garbled', 'value': 'percent+scale'}, 'conflict', 'percent_followed_by_scale'))
    other_cur = set(re.findall(ALL_CURRENCY_FA, fa))
    allowed = {re.findall(ALL_CURRENCY_FA, CURRENCY[c].replace('\\$', 'دلار'))[0] if re.findall(ALL_CURRENCY_FA, CURRENCY[c].replace('\\$', 'دلار')) else ''
               for c in src_currencies if c in CURRENCY}
    if src_currencies and other_cur - allowed:
        res.append(({'type': 'currency_extra', 'value': sorted(other_cur - allowed)}, 'conflict', 'other_currency_in_output'))
    return res


def decide(source, output, validator_status=None, validator_flags=None):
    """→ (decision, details). decision: ACCEPT | REJECT_CRITICAL | REJECT_UNCERTAIN"""
    if not (output or '').strip():
        return 'REJECT_CRITICAL', {'reasons': ['empty_output']}
    facts = extract(source)
    ver = verify(facts, output)
    v = tg.validate(source, output, {})
    hard_v = [f for f in v.flags if f in {'foreign_script', 'not_persian', 'identical_to_source', 'empty_output', 'stray_markup',
                                           'placeholder_residue'}]
    soft_v = [f for f in v.flags if f not in hard_v and f not in {'placeholder_missing', 'number_mismatch', 'date_mismatch'}]
    qcf = qc.check(source, output)['flags']
    hard_q = [f for f in qcf if f.startswith(('placeholder_text', 'month_untranslated', 'number_missing', 'unit_missing', 'echelon_added',
                                               'role_added', 'entity_added', 'number_relabelled_as_model', 'empty_output'))
              or f in {'unsupported_word:ویکی پدیا', 'unsupported_word:اعتصاب', 'unsupported_word:شبیه سازی', 'unsupported_word:وبگاه'}]
    soft_q = [f for f in qcf if f not in hard_q]
    crit = [f'{x[0]["type"]}:{x[0].get("value", x[0].get("kind"))}:{x[1]}{":" + x[2] if x[2] else ""}' for x in ver if x[1] in ('missing', 'conflict')]
    unc = [f'{x[0]["type"]}:{x[0].get("value", x[0].get("kind"))}' for x in ver if x[1] == 'unverifiable']
    details = {'facts': len(facts), 'critical': crit + [f'validator:{f}' for f in hard_v] + [f'qc:{f}' for f in hard_q],
               'uncertain': unc + [f'validator:{f}' for f in soft_v] + [f'qc:{f}' for f in soft_q],
               'verified': [f'{x[0]["type"]}:{x[0].get("value", x[0].get("kind"))}' for x in ver if x[1] == 'ok']}
    if details['critical']:
        return 'REJECT_CRITICAL', details
    if details['uncertain']:
        return 'REJECT_UNCERTAIN', details
    return 'ACCEPT', details


def translate_direct(adapter_call, source, cap=1536):
    """Placeholder-free translation call. adapter_call(text, num_predict) →
    (raw, tokens_in, tokens_out). Returns the raw model text and timings;
    acceptance is decided separately by decide()."""
    if not source or not source.strip():
        return {'status': 'skipped_empty', 'text': None, 'inference': False}
    t0 = time.monotonic()
    raw, tin, tout = adapter_call(source, tg.predict_for(len(source), cap))
    out = unicodedata.normalize('NFC', (raw or '').strip())
    return {'status': 'translated', 'text': out, 'latency_ms': int((time.monotonic() - t0) * 1000), 'tokens_in': tin,
            'tokens_out': tout, 'inference': True}

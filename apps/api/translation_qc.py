"""Deterministic quality controls for English→Persian machine translation.

Purpose: flag outputs that may contain a CRITICAL error so a human reviews
them. The controls never correct, approve or publish anything; a clean
result is not an approval.

Each control compares the English source with the Persian output (and,
optionally, an independent reference translation from a second model):

  numbers     every source number (digits, decimals, %, ordinals 3rd, number
              words) appears in the output; no number is added; billion /
              million / percent units are kept; a number is not re-labelled
              as a model/version («مدل 96»)
  dates       source month and weekday names appear in Persian; no English
              month is left in the output
  placeholder bracketed text («[تاریخ شروع]», «[واحد پول]») absent from the source
  entities    people, organisations, countries and places recognised by the
              versioned fa↔en lexicon (assistant_relevance) must not be added
              or dropped
  roles       official titles (minister, president, CEO, spokesman …) must
              not be added or dropped
  military    echelon (brigade/battalion/division/regiment/corps), ship type,
              live-fire, «اعتصاب» for a strike, «شبیه‌سازی» / «تمرین» not in
              the source
  suspicious  nouns that signal invented context (website, Wikipedia,
              station, organisation …) without a source equivalent
  coverage    output/source length ratio outside the band seen on correct
              dev translations (omission or hallucination)
  reference   (optional) content-word divergence from an independent
              translation of the same source

Designed on the 35 dev fixtures only; frozen before the held-out set was
translated. See docs/LOCAL TRANSLATION QUALITY CONTROL EVALUATION.md.
"""
import re

import assistant_relevance as ar

QC_VERSION = 'translation-qc-v1.0.2'  # v1.0.0 frozen at commit 9eec064, sha256 bfaa3c55…

_FA_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
_FA_LETTERS = str.maketrans({'ي': 'ی', 'ك': 'ک', 'ة': 'ه', 'ۀ': 'ه'})
EN_WORDS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'eleven': 11, 'twelve': 12, 'twenty': 20, 'thirty': 30, 'hundred': 100, 'dozen': 12,
            'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5, 'sixth': 6, 'seventh': 7, 'eighth': 8, 'ninth': 9,
            'tenth': 10}
FA_WORDS = {'یک': 1, 'دو': 2, 'سه': 3, 'چهار': 4, 'پنج': 5, 'شش': 6, 'هفت': 7, 'هشت': 8, 'ده': 10,  # v1.0.2: «نه» (no/neither) is not counted as 9
            'یازده': 11, 'دوازده': 12, 'بیست': 20, 'سی': 30, 'صد': 100, 'اول': 1, 'نخست': 1, 'دوم': 2, 'سوم': 3,
            'چهارم': 4, 'پنجم': 5, 'ششم': 6, 'هفتم': 7, 'هشتم': 8, 'نهم': 9, 'دهم': 10, 'سومین': 3, 'دومین': 2,
            'نخستین': 1, 'اولین': 1}
MONTHS = {'january': ['ژانویه'], 'february': ['فوریه'], 'march': ['مارس'], 'april': ['آوریل'], 'may': ['مه', 'می'],
          'june': ['ژوئن'], 'july': ['ژوئیه', 'جولای'], 'august': ['اوت', 'آگوست', 'اگوست'], 'september': ['سپتامبر'],
          'october': ['اکتبر'], 'november': ['نوامبر'], 'december': ['دسامبر']}
WEEKDAYS = {'monday': 'دوشنبه', 'tuesday': 'سه شنبه', 'wednesday': 'چهارشنبه', 'thursday': 'پنجشنبه', 'friday': 'جمعه',
            'saturday': 'شنبه', 'sunday': 'یکشنبه'}
# role / title: English source patterns ↔ Persian output forms
ROLES = [
    (r'\bprime ministers?\b', ['نخست وزیر']),
    # v1.0.1: plurals ("Foreign ministers")
    (r'\b(?:ministers?|secretar(?:y|ies) of (?:state|defen[cs]e|war)|defen[cs]e secretar(?:y|ies)|war ministers?)\b', ['وزیر']),
    (r'\bpresidents?\b', ['رئیس جمهور', 'رییس جمهور']),
    (r'\bchancellors?\b', ['صدراعظم', 'صدر اعظم']),
    (r'\b(?:ceos?|chief executives?)\b', ['مدیرعامل', 'مدیر عامل', 'مدیر اجرایی']),
    (r'\b(?:spokes(?:man|men|woman|women|person|persons|people))\b', ['سخنگو']),
    (r'\bambassadors?\b', ['سفیر']),
    (r'(?<!secretary )(?<!secretary-)\bgenerals?\b', ['ژنرال']),  # v1.0.2: not "secretary general"
    (r'\bcommanders?\b', ['فرمانده']),
]
# military echelons and ship types: English ↔ accepted Persian
ECHELONS = {'brigade': ['تیپ'], 'battalion': ['گردان'], 'division': ['لشکر'], 'regiment': ['هنگ'], 'corps': ['سپاه']}
ECHELON_FA = {'تیپ', 'گردان', 'لشکر', 'هنگ'}
SHIPS = {'frigate': ['ناوچه', 'فریگیت', 'فرگات'], 'corvette': ['ناوچه', 'کوروت'], 'destroyer': ['ناوشکن'],
         'submarine': ['زیردریایی', 'زیر دریایی'], 'aircraft carrier': ['ناو هواپیمابر', 'هواپیمابر']}
# nouns that signal invented context when the source has no equivalent
SUSPICIOUS = [('ایستگاه', r'\bstation'), ('سازمان', r'\b(?:organi[sz]ations?|agenc(?:y|ies)|organs?|nato|un|opec|osce|oecd|who|iaea)\b'), ('مدل', r'\b(?:model|type|variant)'),
              ('نسخه', r'\b(?:version|variant)'), ('وبگاه', r'\b(?:website|site)'), ('وب سایت', r'\b(?:website|site)'),
              ('ویکی پدیا', r'\bwikipedia'), ('سپاه', r'\b(?:corps|irgc|revolutionary guard)'),
              ('شبیه سازی', r'\bsimulat'), ('اعتصاب', r'\b(?:labou?r|union|workers|walkout|industrial action)')]


def _fa(text):
    t = (text or '').translate(_FA_DIGITS).translate(_FA_LETTERS).replace('‌', ' ').replace('ـ', '')
    return re.sub(r'\s+', ' ', t)


# v1.0.2: Persian LETTERS only (U+0621-U+064A, U+0671-U+06D3); the Persian comma,
# semicolon and question mark are not letters («دوم،» is the word «دوم»).
_L = 'ء-يٱ-ۓ'


def _has(fa_text, forms):
    return any(re.search(r'(?<![' + _L + r'])' + re.escape(f) + r'(?:\S{0,4})?(?![' + _L + r']{3})', fa_text) for f in forms)


def _num_tokens(text, persian):
    out = set()
    t = _fa(text) if persian else text
    if persian:  # weekday compounds («سه شنبه») are not numbers
        t = re.sub(r'(?:سه|چهار|پنج|یک|دو)\s?شنبه', ' ', t)
    for m in re.finditer(r'(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(?![\d])', t):
        whole = m.group(1).replace(',', '')
        out.add(whole + ('.' + m.group(2) if m.group(2) else ''))
    if not persian:
        for m in re.finditer(r'\b(\d+)(?:st|nd|rd|th)\b', t):
            out.add(m.group(1))
        for w, v in EN_WORDS.items():
            if re.search(r'\b' + w + r'\b', t, re.I):
                out.add(str(v))
    else:
        for w, v in FA_WORDS.items():
            if re.search(r'(?<![' + _L + r'])' + w + r'(?![' + _L + r'])', t):
                out.add(str(v))
    return out


def _years_or_codes(src):
    """Numbers inside equipment/code tokens (F-35A, S-400, MQ-9B, A400M) or
    URLs are carried verbatim as Latin text; not checked as quantities."""
    out = set()
    for m in re.finditer(r'\b[A-Za-z]+[-/]?\d+[A-Za-z]*\b|https?://\S+|[A-Za-z]\d+[A-Za-z]+', src):
        out |= set(re.findall(r'\d+', m.group(0)))
    return out


def check_numbers(src, out):
    flags = []
    s, o = _num_tokens(src, False), _num_tokens(out, True)
    codes = _years_or_codes(src)
    o_latin = set(re.findall(r'\d+(?:\.\d+)?', out.translate(_FA_DIGITS)))
    for n in sorted(s - codes):
        if n not in o and n not in o_latin:
            # "2,000" may legitimately become "دو هزار"; "1,500" … keep strict: flag for review
            flags.append(f'number_missing:{n}')
    src_all = s | codes | set(re.findall(r'\d+', src))
    for n in sorted(o - src_all):
        if n not in {'1'}:  # «یک» is also the indefinite article
            flags.append(f'number_added:{n}')
    sl, of = src.lower(), _fa(out)
    for en, fa in (('billion', ['میلیارد']), ('million', ['میلیون']), ('trillion', ['تریلیون'])):
        if re.search(r'\b' + en + r'\b|[$€£]\s?\d[\d.,]*' + en[0].upper() + r'\b', src) and not _has(of, fa):
            flags.append(f'unit_missing:{en}')
    if ('%' in src or re.search(r'\bpercent\b', sl)) and '%' not in out and 'درصد' not in of:
        flags.append('unit_missing:percent')
    if re.search(r'(?:مدل|نسخه)\s*\d', of) and not re.search(r'\b(?:model|version|variant|type)\b', sl):
        flags.append('number_relabelled_as_model')
    return flags


def check_dates(src, out):
    flags, sl, of = [], src.lower(), _fa(out)
    for en, fa in MONTHS.items():
        if re.search(r'\b' + en + r'\b|\b' + en[:3] + r'\.', sl) and not (en == 'may' and not re.search(r'\d\s+may\b|\bmay\s+\d', sl)):
            if not _has(of, fa):
                flags.append(f'month_missing:{en}')
    if re.search(r'\b(?:January|February|March|April|June|July|August|September|October|November|December)\b', out):
        flags.append('month_untranslated')
    for en, fa in WEEKDAYS.items():
        if re.search(r'\b' + en + r'\b', sl) and fa.replace(' ', '') not in of.replace(' ', ''):
            flags.append(f'weekday_missing:{en}')
    return flags


def check_placeholders(src, out):
    flags = []
    for m in re.finditer(r'\[[^\]]{1,40}\]|\{[^}]{1,40}\}|<[^>]{1,40}>', out):
        if m.group(0) not in src:
            flags.append('placeholder_text:' + m.group(0)[:20])
    return flags


# Transliteration variants accepted by QC only (assistant_relevance's lexicon is
# not modified). A variant may only satisfy 'missing'; it never adds entities.
QC_ALIASES = {'Kharkiv': ['خارکف', 'خرکف', 'خارکیو', 'خارکوف'], 'Lockheed Martin': ['لوکهید', 'لاکید'],
              'Rheinmetall': ['راین متال', 'رینمتال'], 'Volodymyr Zelensky': ['زلینسکی'],
              # v1.0.1: "Kyiv" implies Ukraine and "naval" implies Navy in the English
              # patterns; their Persian renderings satisfy the 'missing' check.
              'Ukraine': ['کی یف', 'کییف', 'کیف'], 'Navy': ['دریایی'],
              'Russia': ['کرملین', 'مسکو']}  # v1.0.2


def check_entities(src, out):
    """Lexicon entities (not equipment classes) added to or dropped from the
    output. English side: the lexicon's English patterns on the source;
    Persian side: its Persian aliases on the output."""
    flags, of = [], ' ' + _fa(ar.norm_fa(out)) + ' '
    src_ents = {a.canonical for a in ar._ENTITY_ANCHORS if a.kind not in ('class',) and a.found(src)}
    out_ents = set()
    for fa, canon in ar._FA_ALIASES:
        if ar._BY_CANON[canon].kind == 'class':
            continue
        if re.search(r'(?<![؀-ۿ])' + re.escape(fa) + ar._FA_SUFFIX + r'(?![؀-ۿ])', of):
            out_ents.add(canon)
    # parents: «اسرائیل» is supported by "IDF", «آمریکا» by "USS", etc. via English patterns already
    for c in sorted(out_ents - src_ents):
        parents = set(ar._BY_CANON[c].parents)
        if not (parents & src_ents) and not any(c in ar._BY_CANON[s].parents for s in src_ents):
            flags.append(f'entity_added:{c}')
    for c in sorted(src_ents - out_ents):
        a = ar._BY_CANON[c]
        latin_kept = a.found(out)  # name kept in Latin script (e.g. «Saab»)
        if any(c in ar._BY_CANON[o].parents for o in out_ents):  # «تهران» satisfies Iran
            continue
        if any(re.search(r'(?<![؀-ۿ])' + re.escape(v), of) for v in QC_ALIASES.get(c, [])):
            continue
        if not latin_kept and a.kind in ('org', 'person', 'country', 'place'):
            flags.append(f'entity_missing:{c}')
    return flags


def check_roles(src, out):
    flags, sl, of = [], src.lower(), _fa(out)
    for pat, fa in ROLES:
        in_src, in_out = bool(re.search(pat, sl)), _has(of, fa)
        if in_out and not in_src:
            if fa == ['وزیر'] and re.search(r'\bprime minister\b', sl):
                continue
            flags.append(f'role_added:{fa[0]}')
        if in_src and not in_out:
            flags.append(f'role_missing:{fa[0]}')
    return flags


def check_military(src, out):
    flags, sl, of = [], src.lower(), _fa(out)
    src_ech = {e for e in ECHELONS if re.search(r'\b' + e + r's?\b', sl)}
    for e in src_ech:
        if not _has(of, ECHELONS[e]):
            flags.append(f'echelon_missing:{e}')
    allowed = {f for e in src_ech for f in ECHELONS[e]}
    for f in ECHELON_FA - allowed:
        if _has(of, [f]) and not (f == 'هنگ' and 'regiment' not in sl and 'هنگام' in of):
            flags.append(f'echelon_added:{f}')
    for en, fa in SHIPS.items():
        if re.search(r'\b' + en + r's?\b', sl) and not _has(of, fa):
            flags.append(f'ship_type_missing:{en}')
    if re.search(r'\blive[- ]fire\b', sl) and not re.search(r'(?:شلیک|آتش|تیر)\S*\s*(?:واقعی|جنگی|زنده)', of):
        flags.append('live_fire_missing')
    if re.search(r'(?:تمرین|رزمایش|مانور)', of) and not re.search(r'\b(?:exercise|drill|training|manoeuvre|maneuver|wargame)', sl):
        flags.append('exercise_added')
    return flags


def check_suspicious(src, out):
    flags, sl, of = [], src.lower(), _fa(out)
    for fa, en_pat in SUSPICIOUS:
        if _has(of, [fa]) and not re.search(en_pat, sl):
            flags.append(f'unsupported_word:{fa}')
    return flags


COVERAGE_BAND = (0.55, 1.75)   # fitted on correct dev translations (see evaluation doc)


def check_coverage(src, out):
    if len(src) < 40:  # headlines expand a lot; the ratio is meaningless for short inputs
        return []
    r = len(_fa(out)) / max(1, len(src))
    return [f'coverage_ratio:{r:.2f}'] if not (COVERAGE_BAND[0] <= r <= COVERAGE_BAND[1]) else []


_FA_STOP = set('و در به از که را با این آن برای یک تا هم یا است شد شده بود می ها های ای خود را نیز اما'.split())


def content_words(fa_text):
    return {w for w in re.findall(r'[؀-ۿ]{3,}', _fa(fa_text)) if w not in _FA_STOP}


REFERENCE_MIN_OVERLAP = 0.20   # fitted on dev


def check_reference(src, out, ref):
    if not ref:
        return []
    a, b = content_words(out), content_words(ref)
    if not a or not b:
        return []
    j = len(a & b) / len(a | b)
    return [f'reference_divergence:{j:.2f}'] if j < REFERENCE_MIN_OVERLAP else []


CONTROLS = {'numbers': check_numbers, 'dates': check_dates, 'placeholder': check_placeholders, 'entities': check_entities,
            'roles': check_roles, 'military': check_military, 'suspicious': check_suspicious, 'coverage': check_coverage}


def check(source, output, reference=None):
    """→ {'suspect': bool, 'flags': [...], 'by_control': {...}, 'qc_version'}.
    Empty/None output is always suspect. Never modifies anything."""
    if not output or not output.strip():
        return {'suspect': True, 'flags': ['empty_output'], 'by_control': {'empty': ['empty_output']}, 'qc_version': QC_VERSION}
    by = {name: fn(source, output) for name, fn in CONTROLS.items()}
    by['reference'] = check_reference(source, output, reference)
    flags = [f for v in by.values() for f in v]
    return {'suspect': bool(flags), 'flags': flags, 'by_control': {k: v for k, v in by.items() if v}, 'qc_version': QC_VERSION}

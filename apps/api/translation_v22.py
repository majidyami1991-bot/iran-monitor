"""Translation QC pipeline v2.2 — targeted corrections of PROVEN instrument
defects of v2.1 (translation_v21, unchanged), found by auditing real 27B
outputs of the 3003 lab (design set frozen 2026-10-09 18:58:34 UTC).

Each correction removes a flag ONLY when the specific defect condition holds;
everything else is passed through unchanged. Proven defects (with examples):

  D1 role_added:فرمانده matched inside «فرماندهی» ("command"): "command posts"
     -> «مراکز فرماندهی», "command-and-control" -> «فرماندهی و کنترل».
  D2 entity_added from an alias inside the standard rendering of a SOURCE
     entity: "Marine Corps" -> «سپاه تفنگداران» flagged IRGC (alias «سپاه»);
     "IDF" -> «ارتش اسرائیل» flagged Army.
  D3 code tokens rendered by exact Persian letter names: "SM-3" -> «اس‌ام-۳»,
     "F-16s" -> «اف-۱۶», "B-52" -> «بی-۵۲»: same letters and digits, in order.
     The "F/A-18F" tokenizer split ("A-18F") is checked against the full form.
  D4 "[Sponsored]" translated as «[با حمایت مالی]» flagged as placeholder text.
     (An added "[ادامه مطلب]" for "[…]" or a left-over «[تاریخ]» stays flagged.)
  D5 «یکی» not read as 1 ("One source" -> «یکی از منابع»); "one-on-one" is an
     idiom, not a number.
  D6 the role "general" extracted from "Consulate General", "General Dynamics",
     "General Staff", "Attorney General", "Director General", "General Atomics".
  D9 Title Case headlines: capitalisation is no name signal; a title word is a
     name only if it is capitalised mid-sentence in the item's summary; common
     capitalised words are not names; a small exonym list (Greece -> «یونان»).
  D8 (stricter, new) year relation: "past 2055" must not become «تا ۲۰۵۵».
  D7 name facts: month abbreviations (Oct.) are months, not names; pronoun /
     determiner words (This, That, These, Those) are not names; transliteration
     skeletons treat Persian «و» as a possible vowel (Romania -> «رومانی»);
     demonyms -ian/-an match the country stem (Italian -> «ایتالیایی»).

Decision semantics are unchanged: ACCEPT only when no critical and no
uncertain flag remains; ACCEPT is "no automated objection", never proof.
"""
import re

import translation_v2 as v2
import translation_v21 as v21

PIPELINE_VERSION = 'translation-pipeline-v2.2.0'
FACTS_VERSION = 'translation-facts-v1.2.0'
_L = 'ء-يٱ-ۓ'

# D2: standard Persian renderings of SOURCE entities that contain another entity's alias
RENDERINGS = [(r'\bMarine Corps\b|\bMarines?\b', 'سپاه تفنگداران', 'IRGC'),
              (r'\bIDF\b|\bIsrael Defen[cs]e Forces\b', 'ارتش اسرائیل', 'Army'),
              (r'\bIDF\b|\bIsrael Defen[cs]e Forces\b', 'ارتش دفاعی اسرائیل', 'Army'),
              (r'\bIDF\b|\bIsrael Defen[cs]e Forces\b', 'نیروهای دفاعی اسرائیل', 'Army')]
# D3: Persian letter names
LETTERS = {'A': ['ای', 'آ', 'اِی'], 'B': ['بی'], 'C': ['سی'], 'D': ['دی'], 'E': ['ای', 'اِ'], 'F': ['اف'], 'G': ['جی'], 'H': ['اچ', 'اِچ'],
           'I': ['آی', 'ای'], 'J': ['جی', 'جِی'], 'K': ['کی', 'کِی'], 'L': ['ال', 'اِل'], 'M': ['ام', 'اِم'], 'N': ['ان', 'اِن'], 'O': ['او'],
           'P': ['پی'], 'Q': ['کیو'], 'R': ['آر'], 'S': ['اس', 'اِس'], 'T': ['تی'], 'U': ['یو'], 'V': ['وی'], 'W': ['دبلیو'], 'X': ['اکس', 'ایکس'],
           'Y': ['وای'], 'Z': ['زد', 'زی']}
_SEP = r'[\s‌\-‐–/]*'
# D4
SPONSORED = (r'\[\s*(?:Sponsored|Sponsored content|Advertisement|Paid content)\s*\]',
             r'\[\s*(?:با حمایت مالی|محتوای حمایت\s?شده|حمایت\s?شده|تبلیغ|تبلیغاتی|آگهی|محتوای تبلیغاتی|محتوای اسپانسری|اسپانسر)\s*\]')
# D6
GENERAL_NOT_ROLE = re.compile(r'\b(?:Consulate|Attorney|Director|Inspector|Surgeon|Secretary|Solicitor|Auditor|Governor|Consul)[- ]General\b'
                              r'|\bGeneral (?:Dynamics|Atomics|Staff|Electric|Motors|Assembly|Directorate|Secretariat|Prosecutor|Purpose|Election|Strike)\b')
# D7
MONTH_ABBR = {'Jan': 'ژانویه', 'Feb': 'فوریه', 'Mar': 'مارس', 'Apr': 'آوریل', 'Jun': 'ژوئن', 'Jul': 'ژوئیه', 'Aug': 'اوت|آگوست', 'Sep': 'سپتامبر',
              'Sept': 'سپتامبر', 'Oct': 'اکتبر', 'Nov': 'نوامبر', 'Dec': 'دسامبر'}
NOT_NAMES = {'This', 'That', 'These', 'Those'}


def _fa_word_re(word):
    return r'(?<![' + _L + r'])' + word + r'(?![' + _L + r'])'


def code_transliterated(token, output):
    """D3: True if `token` (e.g. SM-3, F-16s, AGM-158C) appears in the output written with
    Persian letter names for each Latin letter, the same digits, in the same order."""
    tok = re.sub(r's$', '', token) if re.search(r'\d[A-Z]*s$', token) else token
    parts = re.findall(r'[A-Z]|\d+', tok.upper())
    if not parts or not any(p.isdigit() for p in parts) or not any(not p.isdigit() for p in parts):
        return False
    rx = ''
    for p in parts:
        if p.isdigit():
            rx += _SEP + '(?:' + p + '|' + p.translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')) + ')'
        else:
            rx += _SEP + '(?:' + '|'.join(re.escape(x) for x in LETTERS[p]) + ')'
    rx = rx[len(_SEP):]
    return re.search(r'(?<![' + _L + r'0-9۰-۹])' + rx + r'(?![0-9۰-۹])', output or '') is not None


def _skeleton_variants(word):
    base = v2._skeleton(word, False)
    no_vav = v2._skeleton(word.replace('و', ''), False)
    return {base, no_vav, base.replace('v', ''), no_vav.rstrip('y')}


def name_matched(name, output):
    """D7: transliteration with «و» as a possible vowel, demonym -ian/-an -> country stem."""
    if re.search(re.escape(name), output or ''):
        return True
    targets = {v2._skeleton(name, True).replace('h', '')}
    m = re.match(r'(.+?)(?:ian|an)$', name)
    if m and len(m.group(1)) >= 3:
        targets.add(v2._skeleton(m.group(1), True).replace('h', ''))
    targets = {t for t in targets if len(t) >= 2}
    words = re.findall(r'[' + _L + r']{2,}', v2.norm(output or ''))
    for i in range(len(words)):
        for j in (1, 2, 3):
            w = ''.join(words[i:i + j])
            for cand in _skeleton_variants(re.sub(r'(?:یی|ی)$', '', w)) | _skeleton_variants(w):
                cand = cand.replace('h', '')
                for sk in targets:
                    if cand and (cand == sk or (len(sk) >= 4 and (sk in cand or cand in sk) and abs(len(cand) - len(sk)) <= 1)):
                        return True
    return False


# D9: capitalised common words are not names (headlines are Title Case; chunks glue role words to names)
COMMON_CAP = set('''A An And As At Be But By For From He Her His I If In Into Is It Its Me My No Not Of On Or Our She So That The Their
They This Those These To Up Us We What When Where Which Who Why With You Your After Before Over Under More Most New Old First Last Next
Act Administration Agency Air Airshow Ago Alliance Army Association Attacks Authority Award Base Board Bomb Brigade Bureau Campaign Center
Centre Ceremony Channel Chief Coalition Command Committee Company Conference Congress Consulate Corps Council Court Days Decades Defence
Defense Democratic Department Deputy Director Division Embassy Exercise Fleet Force Forces Foundation General Government Group Guard
Headquarters House Institute International Joint Management Memorial Minister Ministry Mission National Navy News Office Party Personnel
Plotting Poison Police Program Programme Republican Republic Senate Service Shadow Sanctions Squadron State Student Summit Systems Tankers
Transfers Treasury Union University Venture Years Indicted Proved Slams Skipping Told Says Said Reports Retires Unveils Wins Signs'''.split())
EXONYMS = {'Greece': 'یونان', 'Greek': 'یونان', 'Germany': 'آلمان', 'German': 'آلمان', 'British': 'بریتانیا|انگلیس', 'Britain': 'بریتانیا|انگلیس',
           'Jewish': 'یهود', 'Jews': 'یهود', 'Palestinian': 'فلسطین', 'Palestinians': 'فلسطین', 'Hungary': 'مجارستان', 'Hungarian': 'مجارستان',
           'Netherlands': 'هلند', 'Dutch': 'هلند', 'Switzerland': 'سوئیس', 'Swiss': 'سوئیس', 'Japan': 'ژاپن', 'Japanese': 'ژاپن', 'China': 'چین',
           'Chinese': 'چین', 'Egypt': 'مصر', 'Egyptian': 'مصر', 'Turkey': 'ترکیه|ترکیه‌ای', 'Turkish': 'ترکیه|ترک', 'Armenia': 'ارمنستان',
           'Swedish': 'سوئد', 'Finnish': 'فنلاند', 'Norwegian': 'نروژ', 'Danish': 'دانمارک', 'Polish': 'لهستان', 'French': 'فرانسه',
           'Spanish': 'اسپانیا', 'Italian': 'ایتالیا', 'Indian': 'هند', 'Saudi': 'سعود', 'Emirati': 'امارات', 'Israeli': 'اسرائیل',
           'Iranian': 'ایران', 'Russian': 'روس', 'Ukrainian': 'اوکراین', 'American': 'آمریکا', 'Australian': 'استرالیا', 'Korean': 'کره',
           'Taiwanese': 'تایوان', 'Lebanese': 'لبنان', 'Syrian': 'سوریه', 'Iraqi': 'عراق', 'Yemeni': 'یمن', 'Moroccan': 'مراکش',
           'Dhabi': 'ظبی', 'Reuters': 'رویترز'}


def title_case(text):
    w = re.findall(r"\b[A-Za-z][A-Za-z'’]{3,}\b", text or '')
    return len(w) >= 3 and sum(x[0].isupper() for x in w) / len(w) >= 0.6 and len(text) < 220


def name_resolved(nm, source, fa, context):
    """D9: True when the 'name' fact is not a name signal, or every real name word in it is found."""
    words = [x for x in re.split(r'[\s-]+', nm) if x]
    if title_case(source):
        if context is None:
            return False                       # cannot tell names from Title Case words: stays uncertain
        words = [x for x in words if re.search(r'(?<![.!?]\s)(?<!^)\b' + re.escape(x) + r'\b', context)]
    words = [x for x in words if x not in COMMON_CAP]
    if not words:
        return True
    for x in words:
        ex = EXONYMS.get(x)
        if ex and re.search(ex, v2.norm(fa)):
            continue
        if not name_matched(x, fa):
            return False
    return True


def _reasons_for_flag(flag, source, output, fixes, context=None):
    """Return None to drop the flag (with a recorded fix), or the flag unchanged."""
    fa = output or ''
    if flag == 'qc:role_added:فرمانده':                                          # D1
        if not re.search(_fa_word_re(r'فرمانده(?:ان|‌ها|ها)?'), v2.norm(fa).replace('فرمانده ی', 'فرماندهی')):
            fixes.append('D1'); return None
    m = re.match(r'qc:entity_added:(.+)$', flag)                                 # D2
    if m:
        ent = m.group(1)
        for src_rx, rendering, alias_ent in RENDERINGS:
            if alias_ent == ent and re.search(src_rx, source) and rendering in v2.norm(fa):
                # every occurrence of the alias must sit inside the accepted rendering
                stripped = v2.norm(fa).replace(rendering, ' ')
                if ent == 'IRGC' and 'سپاه' not in stripped:
                    fixes.append('D2'); return None
                if ent == 'Army' and 'ارتش' not in stripped:
                    fixes.append('D2'); return None
    m = re.match(r'token:([^:]+):missing$', flag)                                # D3
    if m:
        tok = m.group(1)
        full = re.search(r'\b([A-Z]{1,3}/' + re.escape(tok) + r')\b', source)
        if full and (full.group(1) in fa or code_transliterated(full.group(1).replace('/', '-'), fa)):
            fixes.append('D3'); return None
        if not full and code_transliterated(tok, fa):
            fixes.append('D3'); return None
    if flag.startswith('validator:tech_code_missing'):                          # D3 (validator side)
        toks = re.findall(r'\b[A-Z][A-Za-z]{0,4}-?\d+[A-Za-z]*\b', source)
        if toks and all(t in fa or code_transliterated(t, fa) for t in toks):
            fixes.append('D3'); return None
    m = re.match(r'qc:placeholder_text:\[(.+)\]$', flag)                         # D4
    if m and re.search(SPONSORED[0], source, re.I) and re.fullmatch(SPONSORED[1], '[' + m.group(1) + ']'):
        fixes.append('D4'); return None
    if flag == 'qc:number_missing:1':                                            # D5
        has_digit_one = re.search(r'(?<![\d.,])1(?![\d.,])', source)
        idiom_only = not re.search(r'\bone\b(?!-(?:on-one|off|way|time|stop))', re.sub(r'\bone-on-one\b', '', source, flags=re.I), re.I)
        if not has_digit_one and (idiom_only or re.search(_fa_word_re('یکی'), v2.norm(fa))):
            fixes.append('D5'); return None
    if flag.startswith('role:') and 'generals' in flag and flag.endswith(':missing'):   # D6
        rest = GENERAL_NOT_ROLE.sub(' ', source)
        if not re.search(r'(?<!secretary )(?<!secretary-)\bgenerals?\b', rest, re.I):
            fixes.append('D6'); return None
    m = re.match(r'name:(.+)$', flag)                                            # D7 (uncertain)
    if m:
        nm = m.group(1)
        if nm in NOT_NAMES:
            fixes.append('D7'); return None
        if nm.rstrip('.') in MONTH_ABBR and re.search(MONTH_ABBR[nm.rstrip('.')], v2.norm(fa)):
            fixes.append('D7'); return None
        if name_matched(nm, fa):
            fixes.append('D7'); return None
        if name_resolved(nm, source, fa, context):
            fixes.append('D9'); return None
    return flag


_FA_DIG = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')


def time_relation_checks(source, output):
    """D8 (NEW, stricter than v2.1): the relation to a year must survive.
    "past / beyond / after 2055" must not become «تا ۲۰۵۵» (until);
    "until / through 2055" must not become «پس از / بعد از ۲۰۵۵» (after).
    Found in the design set: "keep V-22 Osprey flying past 2055" -> «تا سال ۲۰۵۵»."""
    fa = v2.norm(output or '').translate(_FA_DIG)
    out = []
    for m in re.finditer(r'\b(past|beyond|after|until|through|till)\s+((?:19|20)\d{2})\b', source or '', re.I):
        rel, year = m.group(1).lower(), m.group(2)
        until_fa = re.search(r'(?<![' + _L + r'])تا\s*(?:پایان\s*)?(?:سال\s*)?' + year, fa)
        after_fa = re.search(r'(?:پس از|بعد از|فراتر از|از)\s*(?:سال\s*)?' + year + r'(?:\s*(?:به بعد|به این سو))?', fa) or \
            re.search(year + r'[^.]{0,12}(?:به بعد|فراتر)', fa)
        if rel in ('past', 'beyond', 'after') and until_fa and not after_fa:
            out.append(f'time_relation:{rel}_{year}:conflict:rendered_as_until')
        elif rel in ('until', 'through', 'till') and after_fa and not until_fa:
            out.append(f'time_relation:{rel}_{year}:conflict:rendered_as_after')
    return out


def decide(source, output, context=None):
    """→ (decision, details), same contract as translation_v21.decide.
    context: the item's summary when `source` is its title (D9: names in a Title Case headline)."""
    d, det = v21.decide(source, output)
    if (det.get('reasons') or []) == ['empty_output']:
        return d, det
    fixes = []
    crit = [f for f in (_reasons_for_flag(x, source, output, fixes, context) for x in det.get('critical', [])) if f]
    crit += time_relation_checks(source, output)
    unc = [f for f in (_reasons_for_flag(x, source, output, fixes, context) for x in det.get('uncertain', [])) if f]
    det = {**det, 'critical': crit, 'uncertain': unc, 'v22_fixes': fixes, 'pipeline': PIPELINE_VERSION, 'facts_version': FACTS_VERSION}
    if crit:
        return 'REJECT_CRITICAL', det
    if unc:
        return 'REJECT_UNCERTAIN', det
    return 'ACCEPT', det

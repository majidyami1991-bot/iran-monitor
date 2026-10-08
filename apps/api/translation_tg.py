"""TranslateGemma (translategemma:4b) field translation: official prompt,
plain-text output, deterministic placeholder protection, versioned glossary
validation and an independent validator. No JSON is requested from the model;
this module puts the validated text into the DB contract.

Flow for one field (title or summary, translated separately):
  1. Persian source  -> not_required (no inference); empty source -> not sent.
  2. protect(): URLs, @mentions, #hashtags, technical codes, coordinates,
     numbers/dates/times/percentages and ALL-CAPS acronyms are replaced by
     tokens ZQ<salt><index> (salt = 3 random capitals per request; a token
     that already occurs in the text is never used).
  3. one inference with the official TranslateGemma prompt (+ two blank lines).
  4. restore(): every token must appear exactly once and unchanged, and no
     fragment of the salt may remain; otherwise the output is rejected.
  5. validate(): content checks (numbers, URLs, mentions, hashtags, codes,
     times, commentary/Markdown/debris, untranslated prose, length) plus
     foreign scripts, mixed-script words, lowercase English residue and the
     glossary of sensitive terms.
"""
import re
import secrets
import string
import time
import unicodedata

import content_validator as cv
import x_translation_validator as xv

PROMPT_VERSION = 'translategemma-official-en-fa-v1'
GLOSSARY_VERSION = 'defence-glossary-fa-v1.0.0'
VALIDATOR_VERSION = 'translation-validator-v2.0.0'

PROMPT = ('You are a professional English (en) to Persian (fa-IR) translator. Your goal is to accurately convey the meaning '
          'and nuances of the original English text while adhering to Persian grammar, vocabulary and cultural sensitivities.\n'
          'Produce only the Persian translation, without any additional explanations or commentary. Please translate the '
          'following English text into Persian:\n\n\n')

# Order matters: longer / more specific patterns first.
_PROTECT = [
    ('url', xv.URL_RE),
    ('mention', xv.MENTION_RE),
    ('hashtag', re.compile(r'(?<![\w#])#[A-Za-z0-9_]+')),
    ('coord', re.compile(r'-?\d{1,3}\.\d{2,}\s*°?\s*[NSEW]?(?:\s*,\s*-?\d{1,3}\.\d{2,}\s*°?\s*[NSEW]?)?')),
    ('code', re.compile(r'\b(?:[A-Za-z]{1,5}-\d{1,5}[A-Za-z]{0,3}|[A-Z]{1,5}\d{1,5}[A-Z]{0,3})\b')),
    ('time', re.compile(r'\b\d{1,2}:\d{2}(?::\d{2})?\b')),
    ('date', re.compile(r'\b\d{1,4}[/-]\d{1,2}[/-]\d{1,4}\b')),
    ('number', re.compile(r'(?<![\w.])\$?\d[\d,]*(?:\.\d+)?%?(?![\w])')),
    ('acronym', re.compile(r'\b[A-Z]{2,8}s?\b')),
]
_FOREIGN = re.compile(r'[\u0370-\u03ff\u0400-\u04ff\u0590-\u05ff\u0900-\u097f\u0e00-\u0e7f\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]')
_MIXED = re.compile(r'[\u0600-\u06ff][A-Za-z]|[A-Za-z][\u0600-\u06ff]')
_LOWER_LATIN = re.compile(r'\b[a-z][a-z\-]{1,}\b')

# Sensitive terms: when the English matches (and the context condition, if
# any), the Persian must contain one of the accepted renderings. Proper names
# may also stay in Latin script.
GLOSSARY = [
    {'en': r'\bbrigades?\b', 'fa': ['تیپ']},
    {'en': r'\bconvoys?\b', 'fa': ['کاروان', 'ستون']},
    {'en': r'\blaunch(?:es|ed|ing)?\b', 'when': r'\b(missile|rocket|ballistic|detected|interceptor|drone)s?\b', 'fa': ['پرتاب', 'شلیک']},
    {'en': r'\bcommission(?:s|ed|ing)?\b', 'when': r'\b(frigate|ship|vessel|navy|destroyer|submarine|carrier|corvette)s?\b',
     'fa': ['به خدمت', 'وارد خدمت', 'به ناوگان']},
    {'en': r'\bfrigates?\b', 'fa': ['ناوچه', 'ناو']},
    {'en': r'\bmissiles?\b', 'fa': ['موشک']},
    {'en': r'\bdeploy(?:ment|ments|ed|s|ing)?\b', 'fa': ['استقرار', 'مستقر', 'اعزام']},
    {'en': r'\bnavy\b|\bnaval\b', 'fa': ['نیروی دریایی', 'دریایی']},
    {'en': r'\bdrones?\b', 'fa': ['پهپاد']},
    {'en': r'\bair defen[cs]e\b', 'fa': ['پدافند هوایی']},
    {'en': r'\bclose air support\b', 'fa': ['پشتیبانی هوایی نزدیک']},
    {'en': r'\blive-fire\b', 'fa': ['جنگی', 'واقعی', 'با مهمات']},
    {'en': r'\bLloyd Austin\b', 'fa': ['لوید آستین', 'Lloyd Austin']},
    {'en': r'\bYoav Gallant\b', 'fa': ['یوآو گالانت', 'یواو گالانت', 'Yoav Gallant']},
    {'en': r'\bKharkiv\b', 'fa': ['خارکیف', 'خارکف', 'Kharkiv']},
    {'en': r'\bIzium\b', 'fa': ['ایزیوم', 'ایزیم', 'Izium']},
    {'en': r'\bLockheed Martin\b', 'fa': ['لاکهید مارتین', 'لاکهید', 'Lockheed Martin']},
    {'en': r'\bReuters\b', 'fa': ['رویترز', 'Reuters']},
]

HARD = frozenset(xv.HARD_FAIL | {'placeholder_missing', 'placeholder_duplicated', 'placeholder_residue', 'foreign_script',
                                  'mixed_script_word', 'latin_prose_residue', 'glossary_term_missing', 'empty_output',
                                  'model_commentary_or_markdown'})


def protect(text, rng=secrets):
    """Returns (protected_text, mapping token->original, salt)."""
    alphabet = string.ascii_uppercase
    while True:
        salt = ''.join(rng.choice(alphabet) for _ in range(3))
        if 'ZQ' + salt not in text:
            break
    mapping, counter = {}, [0]

    def token():
        i = counter[0]
        counter[0] += 1
        idx = ''
        while True:
            idx = alphabet[i % 26] + idx
            i = i // 26 - 1
            if i < 0:
                break
        return f'ZQ{salt}{idx}'

    out = text
    for _kind, rx in _PROTECT:
        def sub(m):
            t = token()
            mapping[t] = m.group(0)
            return t
        # never re-protect inside an existing token
        parts = re.split(r'(ZQ' + salt + r'[A-Z]+)', out)
        out = ''.join(p if p.startswith('ZQ' + salt) else rx.sub(sub, p) for p in parts)
    return out, mapping, salt


def restore(translated, mapping, salt):
    """Returns (restored_text, flags). Each token exactly once; no residue."""
    flags = []
    out = translated
    for t, original in sorted(mapping.items(), key=lambda kv: -len(kv[0])):
        n = len(re.findall(r'(?<![A-Z])' + re.escape(t) + r'(?![A-Z])', out))
        if n == 0:
            flags.append('placeholder_missing')
        elif n > 1:
            flags.append('placeholder_duplicated')
        out = re.sub(r'(?<![A-Z])' + re.escape(t) + r'(?![A-Z])', lambda m: original, out)
    if re.search(r'ZQ\s?' + salt, out) or re.search(r'\bZQ[A-Z]{3,}', out):
        flags.append('placeholder_residue')
    return out, sorted(set(flags))


_FA_LETTER = '؀-ۿ'


def _has_word(text, term):
    """Whole-word match for a Persian (or Latin) term, allowing common Persian
    suffixes; 'ناو' does not match inside 'ناوگان'."""
    if re.match(r'[A-Za-z]', term):
        return re.search(r'(?<![A-Za-z])' + re.escape(term) + r'(?![A-Za-z])', text) is not None
    return re.search(r'(?<![' + _FA_LETTER + r'])' + re.escape(term) + r'(?:‌?(?:ها|های|ی|ای|ان|هایی))?(?![' + _FA_LETTER + r'])',
                     text) is not None


def glossary_check(source, translated):
    missing = []
    for g in GLOSSARY:
        if re.search(g['en'], source, re.I if not g['en'][2:3].isupper() else 0) and \
                (not g.get('when') or re.search(g['when'], source, re.I)):
            if not any(_has_word(translated, fa) for fa in g['fa']):
                missing.append(re.sub(r'\\b|\(\?:.*?\)\??|[\\?]', '', g['en'])[:24])
    return missing


def validate(source, translated, mapping):
    """content_validator ValidationResult with the extra TranslateGemma checks."""
    base = xv.validate(source, translated)
    flags, reasons = list(base.flags), dict(base.reasons)
    if not translated.strip():
        return cv.ValidationResult(False, 0.0, ['empty_output'], {'empty_output': 'empty'})
    if _FOREIGN.search(translated):
        flags.append('foreign_script'); reasons['foreign_script'] = 'Non-Persian, non-Latin script in output.'
    if _MIXED.search(translated):
        flags.append('mixed_script_word'); reasons['mixed_script_word'] = 'A word mixes Persian and Latin letters.'
    # Lowercase Latin words that were not protected originals (URLs, hashtags…) = untranslated prose.
    stripped = translated
    for original in mapping.values():
        stripped = stripped.replace(original, ' ')
    lower = [w for w in _LOWER_LATIN.findall(stripped) if w not in ('km', 'kg', 'mm', 'cm')]
    if lower:
        flags.append('latin_prose_residue'); reasons['latin_prose_residue'] = f'Untranslated English word(s): {lower[:4]}'
    if re.search(r'(?i)\b(translation|translated|here is|note:|persian)\b', stripped) or '<' in stripped:
        flags.append('model_commentary_or_markdown'); reasons['model_commentary_or_markdown'] = 'Commentary or markup.'
    miss = glossary_check(source, translated)
    if miss:
        flags.append('glossary_term_missing'); reasons['glossary_term_missing'] = f'Missing accepted rendering for: {miss}'
    flags = list(dict.fromkeys(flags))
    passed = not any(f in HARD for f in flags)
    return cv.ValidationResult(passed, 0.0 if not passed else base.quality_score, flags, reasons)


def request_body(model, text, *, seed, num_ctx, num_thread, temperature, num_predict, keep_alive='5m'):
    return {'model': model, 'stream': False, 'keep_alive': keep_alive,
            'options': {'temperature': temperature, 'seed': seed, 'num_ctx': num_ctx, 'num_thread': num_thread,
                        'num_predict': num_predict},
            'messages': [{'role': 'user', 'content': PROMPT + text}]}


def predict_for(chars, cap):
    return max(64, min(cap, 48 + int(chars * 0.8)))


def translate_field(adapter_call, source, cap=1536):
    """adapter_call(body_text, num_predict) -> (raw_text, tokens_in, tokens_out).
    Returns dict(status, text, flags, reasons, latency_ms, tokens_in, tokens_out, inference)."""
    if not source or not source.strip():
        return {'status': 'skipped_empty', 'text': None, 'flags': [], 'reasons': {}, 'inference': False}
    if xv.is_persian_source(source):
        return {'status': 'not_required', 'text': None, 'flags': [], 'reasons': {}, 'inference': False}
    protected, mapping, salt = protect(source)
    t0 = time.monotonic()
    raw, tin, tout = adapter_call(protected, predict_for(len(protected), cap))
    latency = int((time.monotonic() - t0) * 1000)
    raw = unicodedata.normalize('NFC', (raw or '').strip())
    restored, pflags = restore(raw, mapping, salt)
    v = validate(source, restored, mapping)
    flags = list(dict.fromkeys(pflags + v.flags))
    passed = v.passed and not pflags
    return {'status': 'available' if passed else 'needs_review', 'text': restored if restored else None, 'flags': flags,
            'reasons': v.reasons, 'latency_ms': latency, 'tokens_in': tin, 'tokens_out': tout, 'inference': True,
            'placeholders': len(mapping)}

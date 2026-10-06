"""Validator for local machine translations of X posts.

Independent of the gateway and of the model that produced the output: it
only compares the analyst-recorded source text with the Persian candidate.
Builds on content_validator.validate_translation (numbers, dates, model
codes, untranslated prose, commentary, length) and adds the checks that
matter for social posts: URLs, @mentions, #hashtags, emoji, and anything the
model added that the source does not contain.

Entities that legitimately stay in Latin script (acronyms such as OSINT or
CENTCOM, capitalised names, codes such as F-35, URLs, mentions, hashtags)
are removed before the untranslated-prose check, so a correct translation
that keeps them is never failed for "too much English".
"""
import re
import unicodedata

import content_validator as cv

URL_RE = re.compile(r'https?://[^\s<>"\'«»]+', re.IGNORECASE)
MENTION_RE = re.compile(r'(?<![\w@])@[A-Za-z0-9_]{1,15}\b')
HASHTAG_RE = re.compile(r'(?<![\w#])#[\w؀-ۿ‌]+')
TIME_RE = re.compile(r'\b\d{1,2}:\d{2}(?::\d{2})?\b')
COORD_RE = re.compile(r'-?\d{1,3}\.\d+\s*°?\s*[NSEWnsew]?')
# Technical identifiers that must survive verbatim: F-35, MQ-9B, S-400, Su-57,
# Type 055 hull numbers are numbers already; also all-caps+digit codes (J20, AIM120D).
TECH_CODE_RE = re.compile(r'\b(?:[A-Za-z]{1,5}-\d{1,5}[A-Za-z]{0,3}|[A-Z]{1,5}\d{1,5}[A-Z]{0,3})\b')

# Labels or wrappers a model adds around the translation.
_WRAPPER_RE = re.compile(r'^\s*(["“«\'])(.*)(["”»\'])\s*$', re.DOTALL)
_LABEL_RE = re.compile(r'^\s*(ترجمه(\s*فارسی)?\s*[:：]|translation\s*[:：]|persian\s*[:：])', re.IGNORECASE)

HARD_FAIL = frozenset(cv._HARD_FAIL_FLAGS | {
    'url_missing', 'url_added', 'mention_missing', 'mention_added', 'hashtag_missing', 'hashtag_added',
    'tech_code_missing', 'time_missing', 'identical_to_source', 'wrapped_or_labelled', 'output_too_short',
    'stray_markup', 'invisible_characters',
})

# Template/JSON debris a local model can append (seen in the first real smoke
# run: a translation ending in `"} %}` + U+200B). Brackets count only when the
# output has more of them than the source.
_MARKUP_CHARS = '{}[]<>'
_TEMPLATE_RE = re.compile(r'\{%|%\}|\{\{|\}\}')
# Zero-width / BOM / word-joiner / bidi controls. ZWNJ (U+200C) is ordinary
# Persian orthography (می‌شود) and is deliberately not in this set.
_INVISIBLE = frozenset('​‍⁠﻿‪‫‬‭‮⁦⁧⁨⁩')


def _emoji(text):
    return [ch for ch in (text or '') if unicodedata.category(ch) == 'So' and ord(ch) > 0x2100]


def _strip_entities(text):
    """Text with URLs, mentions, hashtags and technical codes removed, used
    only for the untranslated-prose check."""
    for rx in (URL_RE, MENTION_RE, HASHTAG_RE, TECH_CODE_RE):
        text = rx.sub(' ', text or '')
    return text


def _norm_url(u):
    return u.rstrip('.,;:!?)]}،؛')


def is_persian_source(text):
    """A post is 'already Persian' when Persian script dominates its prose,
    ignoring URLs, mentions and hashtags."""
    core = _strip_entities(text)
    letters = [ch for ch in core if ch.isalpha()]
    if not letters:
        return False
    persian = sum(1 for ch in letters if '؀' <= ch <= 'ۿ' or ch in 'پچژگکی')
    return persian / len(letters) >= 0.6


def validate(source_text, translated_text):
    """Returns content_validator.ValidationResult. passed=False means the
    output must not be shown as a translation (status needs_review)."""
    flags, reasons = [], {}
    out = translated_text or ''
    if not out.strip():
        return cv.ValidationResult(False, 0.0, ['empty_output'], {'empty_output': 'Translation is empty.'})

    if _WRAPPER_RE.match(out) or _LABEL_RE.match(out):
        flags.append('wrapped_or_labelled')
        reasons['wrapped_or_labelled'] = 'Output is wrapped in quotes or starts with a label such as «ترجمه:».'

    src_wo_urls = URL_RE.sub(' ', source_text or '')
    out_wo_urls = URL_RE.sub(' ', out)
    extra = [ch for ch in _MARKUP_CHARS if out_wo_urls.count(ch) > src_wo_urls.count(ch)]
    if extra or (_TEMPLATE_RE.search(out_wo_urls) and not _TEMPLATE_RE.search(src_wo_urls)):
        flags.append('stray_markup')
        reasons['stray_markup'] = f'Output contains bracket/template characters not in the source: {extra or "template tag"}'
    hidden = sorted({f'U+{ord(ch):04X}' for ch in out if ch in _INVISIBLE and ch not in (source_text or '')})
    if hidden:
        flags.append('invisible_characters')
        reasons['invisible_characters'] = f'Output contains invisible control characters: {hidden[:3]}'

    if out.strip().casefold() == (source_text or '').strip().casefold():
        flags.append('identical_to_source')
        reasons['identical_to_source'] = 'Output is identical to the source text.'

    # Base checks on entity-stripped text so kept acronyms, codes, links and
    # handles never count as untranslated prose; numbers are compared on the
    # full text below instead (the base number check would also see the
    # digits inside a stripped URL).
    base = cv.validate_translation(_strip_entities(source_text), _strip_entities(out),
                                   min_length_ratio=0.25, max_length_ratio=3.5)
    for f in base.flags:
        if f in ('number_mismatch', 'number_added', 'distinctive_code_missing'):
            continue
        flags.append(f)
        reasons[f] = base.reasons.get(f)

    def _set(rx, text, norm=lambda x: x):
        return {norm(m) for m in rx.findall(text or '')}

    checks = (
        ('url', URL_RE, _norm_url),
        ('mention', MENTION_RE, str.lower),
        ('hashtag', HASHTAG_RE, lambda h: h),
    )
    for name, rx, norm in checks:
        src, dst = _set(rx, source_text, norm), _set(rx, out, norm)
        if src - dst:
            flags.append(f'{name}_missing')
            reasons[f'{name}_missing'] = f'{len(src - dst)} {name}(s) not preserved exactly: {sorted(src - dst)[:3]}'
        if dst - src:
            flags.append(f'{name}_added')
            reasons[f'{name}_added'] = f'{len(dst - src)} {name}(s) not in the source: {sorted(dst - src)[:3]}'

    # Numbers: compare after removing URLs and handles from both sides, so the
    # digits in a status URL or @user123 are checked by the URL/mention rules.
    def _nums(t):
        return cv.extract_numbers(MENTION_RE.sub(' ', URL_RE.sub(' ', t or '')))
    src_n, out_n = _nums(source_text), _nums(out)
    if src_n - out_n:
        flags.append('number_mismatch')
        reasons['number_mismatch'] = f'Number(s) missing: {sorted(src_n - out_n)[:5]}'
    codes_digits = {d for c in TECH_CODE_RE.findall(source_text or '') for d in re.findall(r'\d+', c)}
    added = {n for n in out_n - src_n if not any(n in s or s in n for s in src_n) and n not in codes_digits}
    if added:
        flags.append('number_added')
        reasons['number_added'] = f'Number(s) not in the source: {sorted(added)[:5]}'

    src_codes = set(TECH_CODE_RE.findall(_strip_url_mentions(source_text)))
    out_codes = set(TECH_CODE_RE.findall(_strip_url_mentions(out)))
    if src_codes - out_codes:
        flags.append('tech_code_missing')
        reasons['tech_code_missing'] = f'Technical code(s) not preserved: {sorted(src_codes - out_codes)[:5]}'

    src_t = {cv.normalize_digits(t) for t in TIME_RE.findall(cv.normalize_digits(source_text))}
    out_t = {cv.normalize_digits(t) for t in TIME_RE.findall(cv.normalize_digits(out))}
    if src_t - out_t:
        flags.append('time_missing')
        reasons['time_missing'] = f'Time(s) not preserved: {sorted(src_t - out_t)[:3]}'

    if len(set(_emoji(source_text)) - set(_emoji(out))) > 0:
        flags.append('emoji_dropped')  # soft: the prompt allows dropping decorative duplicates
        reasons['emoji_dropped'] = 'One or more emoji from the source are absent.'

    flags = list(dict.fromkeys(flags))
    passed = not any(f in HARD_FAIL for f in flags)
    soft = [f for f in flags if f not in HARD_FAIL]
    score = 0.0 if not passed else round(max(0.0, 1.0 - 0.12 * len(soft)), 2)
    return cv.ValidationResult(passed, score, flags, reasons)


def _strip_url_mentions(text):
    return MENTION_RE.sub(' ', URL_RE.sub(' ', text or ''))

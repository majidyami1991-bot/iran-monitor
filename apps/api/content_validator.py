"""Content Intelligence validator — independent of the AI Gateway and of
whichever provider produced a translation, summary, or key point. Every
AI-generated field must pass through here before it can ever be marked
review_status='approved' or shown as anything but a draft.

Deliberately narrow in what it claims to detect. This module checks
mechanically verifiable properties (numbers, dates, a class of proper nouns
that plausibly survive translation unchanged, output length, placeholder
text, gross negation loss) — it does not claim to detect semantic
hallucination or verify factual accuracy, which no deterministic rule can
honestly do. Where a real check isn't possible, the result says so via a
flag rather than silently passing everything.
"""
import re
from dataclasses import dataclass, field

PERSIAN_DIGITS = '۰۱۲۳۴۵۶۷۸۹'
LATIN_DIGITS = '0123456789'
_DIGIT_MAP = str.maketrans(PERSIAN_DIGITS, LATIN_DIGITS)

_MONTHS = ('january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
           'september', 'october', 'november', 'december',
           'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'sept', 'oct', 'nov', 'dec')

NEGATION_WORDS_EN = frozenset(('not', 'never', 'no', 'denies', 'denied', 'without', 'fails', 'failed', 'refuses', 'refused', "n't"))
NEGATION_MARKERS_FA = ('نیست', 'نبود', 'نشد', 'هرگز', 'بدون', 'رد کرد', 'انکار', 'نمی', 'ندارد', 'نکرد')

_PLACEHOLDER_PATTERNS = (
    re.compile(r'\blorem ipsum\b', re.IGNORECASE),
    re.compile(r'\btodo\b', re.IGNORECASE),
    re.compile(r'\btbd\b', re.IGNORECASE),
    re.compile(r'\[\s*(insert|placeholder|translation|summary)[^\]]*\]', re.IGNORECASE),
    re.compile(r'\{\{.*?\}\}'),
    re.compile(r'^\s*(n/?a|none|null)\s*$', re.IGNORECASE),
)


def normalize_digits(text):
    return (text or '').translate(_DIGIT_MAP)


def extract_numbers(text):
    """Numbers and percentages as a comparable set. Persian-Indic digits are
    normalized to Latin first, so a number correctly preserved in Persian
    script is never flagged as missing just because of the digit script.
    Trailing punctuation (a sentence comma or period right after the number)
    is stripped — English and Persian sentence punctuation never lines up
    the same way, so keeping it would flag identical numbers as mismatched
    purely because of where a comma happened to fall."""
    text = normalize_digits(text or '')
    raw = re.findall(r'\d[\d,.]*%?', text)
    return {tok.rstrip('.,') for tok in raw}


def extract_dates(text):
    """Numeric (DD/MM/YYYY-shaped) and month-name dates. Deliberately loose
    — a false-positive "date" token is harmless here since this only feeds a
    set-overlap check, not a hard rejection on its own."""
    text = normalize_digits(text or '')
    numeric = re.findall(r'\b\d{1,4}[/-]\d{1,2}[/-]\d{1,4}\b', text)
    month_based = re.findall(r'\b(?:' + '|'.join(_MONTHS) + r')\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{0,4}\b',
                              text, re.IGNORECASE)
    return set(numeric) | set(m.strip() for m in month_based)


def extract_distinctive_codes(text):
    """Alphanumeric model/unit codes (F-35, S-400, Su-57, B-2) — the class of
    tokens most likely to survive translation into Persian completely
    unchanged, in Latin script, so their disappearance is a real, checkable
    preservation signal.

    Deliberately excludes bare all-caps acronyms (NATO, IAEA, CIA): those are
    routinely and *correctly* transliterated into Persian script in real
    translation (ناتو, آژانس بین‌المللی انرژی اتمی, سیا) rather than kept
    verbatim, so requiring a verbatim match would flag good translations as
    defective. Verifying a transliteration is correct would need a
    translation dictionary this module doesn't have — out of scope for an
    honest deterministic check."""
    return set(re.findall(r'\b[A-Za-z]{1,4}-\d{1,4}\b', text or ''))


def _looks_persian(text):
    if not text:
        return False
    persian = sum(1 for ch in text if '؀' <= ch <= 'ۿ')
    return persian >= max(8, len(text.strip()) * 0.2)


def _has_placeholder(text):
    for pattern in _PLACEHOLDER_PATTERNS:
        if pattern.search(text or ''):
            return True
    return False


def _negation_present_en(text):
    words = set(re.findall(r"[a-z']+", (text or '').lower()))
    return bool(words & NEGATION_WORDS_EN)


def _negation_present_fa(text):
    text = text or ''
    return any(marker in text for marker in NEGATION_MARKERS_FA)


@dataclass
class ValidationResult:
    passed: bool
    quality_score: float  # 0.0-1.0
    flags: list = field(default_factory=list)
    reasons: dict = field(default_factory=dict)  # flag -> human-readable reason

    def to_dict(self):
        return {'passed': self.passed, 'quality_score': self.quality_score,
                'flags': self.flags, 'reasons': self.reasons}


# Flags that are automatically disqualifying — any one of these means
# passed=False regardless of how well the other checks scored. Everything
# else only lowers quality_score; a translator legitimately rephrases, so a
# missing distinctive code alone (for example) is a flag worth a reviewer's
# attention, not an automatic rejection.
_HARD_FAIL_FLAGS = frozenset(('empty_output', 'placeholder_text_detected', 'not_persian', 'echoes_source_language',
                              'untranslated_english'))

# Names and acronyms legitimately stay in Latin script (NORTHCOM, Air & Space
# Forces Magazine, F-35). Ordinary lowercase English words ("the", "we",
# "have") in a Persian output mean prose was left untranslated — found in the
# first free-tier smoke test (2026-09-29), where a summary kept whole English
# sentences and still scored 1.0 under the checks above.
UNTRANSLATED_LOWERCASE_WORDS_MAX = 3


def _untranslated_lowercase_words(text):
    return [w for w in re.findall(r"(?<![A-Za-z'’\-])[a-z][a-z'’]+(?![A-Za-z])", text or '') if len(w) >= 2]


def validate_translation(source_text, translated_text, *, min_length_ratio=0.3, max_length_ratio=3.0):
    """For a full or short translation of `source_text` into `translated_text`
    (Persian). Returns a ValidationResult; `passed=False` means this output
    must not be published as-is — review_status becomes needs_review or
    rejected, and the original text stays visible regardless."""
    flags, reasons = [], {}

    if not translated_text or not translated_text.strip():
        flags.append('empty_output')
        reasons['empty_output'] = 'Translated text is empty or whitespace-only.'
        return ValidationResult(False, 0.0, flags, reasons)

    if _has_placeholder(translated_text):
        flags.append('placeholder_text_detected')
        reasons['placeholder_text_detected'] = 'Output contains placeholder-looking text (e.g. "TODO", "[insert]").'

    if not _looks_persian(translated_text):
        flags.append('not_persian')
        reasons['not_persian'] = 'Output does not contain enough Persian script to be a real translation.'
    elif source_text and _looks_persian(source_text) is False and translated_text.strip().casefold() == (source_text or '').strip().casefold():
        flags.append('echoes_source_language')
        reasons['echoes_source_language'] = 'Output is identical to the English source — provider echoed the input.'
    else:
        leftover = _untranslated_lowercase_words(translated_text)
        if len(leftover) > UNTRANSLATED_LOWERCASE_WORDS_MAX:
            flags.append('untranslated_english')
            reasons['untranslated_english'] = (f'{len(leftover)} ordinary English words left untranslated '
                                               f'(e.g. {", ".join(leftover[:6])}).')

    src_numbers, out_numbers = extract_numbers(source_text), extract_numbers(translated_text)
    missing_numbers = src_numbers - out_numbers
    if missing_numbers:
        flags.append('number_mismatch')
        reasons['number_mismatch'] = f'{len(missing_numbers)} number(s) in the source do not appear in the translation: {sorted(missing_numbers)[:5]}'

    src_dates, out_dates = extract_dates(source_text), extract_dates(translated_text)
    if src_dates and not (src_dates & out_dates) and not (extract_numbers(source_text) & extract_numbers(translated_text)):
        # Only flag a total date loss when the numeric check above didn't
        # already catch it via shared digit sequences (dates and numbers
        # overlap heavily; avoid double-penalizing the same root cause).
        flags.append('date_mismatch')
        reasons['date_mismatch'] = f'None of the source dates appear (even as numbers) in the translation: {sorted(src_dates)[:3]}'

    src_codes, out_codes = extract_distinctive_codes(source_text), extract_distinctive_codes(translated_text)
    missing_codes = src_codes - out_codes
    if missing_codes:
        flags.append('distinctive_code_missing')
        reasons['distinctive_code_missing'] = f'{len(missing_codes)} acronym/model-code token(s) not found verbatim in the translation: {sorted(missing_codes)[:5]}'

    if source_text and _negation_present_en(source_text) and not _negation_present_fa(translated_text):
        flags.append('possible_negation_loss')
        reasons['possible_negation_loss'] = 'Source contains a negation word (not/never/denied/...) with no corresponding Persian negation marker found in the translation — meaning may have flipped.'

    src_len, out_len = len(source_text or ''), len(translated_text or '')
    if src_len > 0:
        ratio = out_len / src_len
        if ratio < min_length_ratio:
            flags.append('output_too_short')
            reasons['output_too_short'] = f'Translation is {ratio:.2f}x the source length (below {min_length_ratio}x) — likely truncated or incomplete.'
        elif ratio > max_length_ratio:
            flags.append('output_too_long')
            reasons['output_too_long'] = f'Translation is {ratio:.2f}x the source length (above {max_length_ratio}x) — may contain added, unsupported content.'

    passed = not any(f in _HARD_FAIL_FLAGS for f in flags)
    penalty = 0.12 * len([f for f in flags if f not in _HARD_FAIL_FLAGS])
    quality_score = 0.0 if not passed else round(max(0.0, 1.0 - penalty), 2)
    return ValidationResult(passed, quality_score, flags, reasons)


def validate_summary(source_text, summary_text, *, min_length_ratio=0.02, max_length_ratio=0.9):
    """Summaries are expected to be much shorter than the source — the
    length-ratio bounds are inverted relative to a full translation."""
    result = validate_translation(source_text, summary_text,
                                   min_length_ratio=min_length_ratio, max_length_ratio=max_length_ratio)
    # A summary correctly omits most source numbers/codes by design — that
    # check is only meaningful for a full translation, not a condensation.
    result.flags = [f for f in result.flags if f not in ('number_mismatch', 'date_mismatch', 'distinctive_code_missing')]
    for key in ('number_mismatch', 'date_mismatch', 'distinctive_code_missing'):
        result.reasons.pop(key, None)
    result.passed = not any(f in _HARD_FAIL_FLAGS for f in result.flags)
    penalty = 0.12 * len(result.flags)
    result.quality_score = 0.0 if not result.passed else round(max(0.0, 1.0 - penalty), 2)
    return result


def validate_key_point(point_text_fa, evidence_span, source_text):
    """A key point's evidence_span must actually occur (case-insensitive,
    whitespace-normalized) in the source text — otherwise it is fabricated
    evidence, not a real citation, and the point must not be published."""
    flags, reasons = [], {}
    if not point_text_fa or not point_text_fa.strip():
        flags.append('empty_point')
        reasons['empty_point'] = 'Key point text is empty.'
        return ValidationResult(False, 0.0, flags, reasons)
    if not evidence_span or not evidence_span.strip():
        flags.append('missing_evidence_span')
        reasons['missing_evidence_span'] = 'No evidence span was provided for this key point.'
        return ValidationResult(False, 0.0, flags, reasons)

    normalize = lambda s: re.sub(r'\s+', ' ', s).strip().casefold()
    if normalize(evidence_span) not in normalize(source_text or ''):
        flags.append('evidence_not_found_in_source')
        reasons['evidence_not_found_in_source'] = 'The cited evidence span does not appear in the source text — likely fabricated.'
        return ValidationResult(False, 0.0, flags, reasons)

    return ValidationResult(True, 1.0, [], {})

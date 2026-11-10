"""Fault-injection tests for the Content Intelligence validator. Each test
starts from a plausible real translation and injects exactly one defect, to
prove the validator catches that specific class of fault — not just that it
accepts good input."""
import content_validator as cv

SOURCE = ('The Israeli Air Force conducted a strike on 15 March 2026, deploying '
          'an F-35 fighter jet near the Lebanese border. NATO condemned the '
          'action. Officials confirmed 3 casualties and $2.5 million in damage.')
GOOD_TRANSLATION_FA = ('نیروی هوایی اسرائیل در تاریخ ۱۵ مارس ۲۰۲۶ حمله‌ای را با استقرار '
                        'یک جنگنده F-35 در نزدیکی مرز لبنان انجام داد. ناتو این اقدام را '
                        'محکوم کرد. مقامات ۳ کشته و ۲.۵ میلیون دلار خسارت را تأیید کردند.')


def test_good_translation_passes():
    r = cv.validate_translation(SOURCE, GOOD_TRANSLATION_FA)
    assert r.passed is True
    assert r.quality_score > 0.8
    assert r.flags == []


def test_empty_output_fails_hard():
    r = cv.validate_translation(SOURCE, '')
    assert r.passed is False
    assert 'empty_output' in r.flags
    assert r.quality_score == 0.0


def test_whitespace_only_output_fails_hard():
    r = cv.validate_translation(SOURCE, '   \n\t  ')
    assert r.passed is False
    assert 'empty_output' in r.flags


def test_placeholder_text_is_detected_and_fails_hard():
    r = cv.validate_translation(SOURCE, 'ترجمه اینجا [insert translation here] قرار می‌گیرد')
    assert r.passed is False
    assert 'placeholder_text_detected' in r.flags


def test_english_echo_is_detected_and_fails_hard():
    r = cv.validate_translation(SOURCE, SOURCE)
    assert r.passed is False
    assert 'not_persian' in r.flags


def test_number_dropped_in_translation_is_flagged():
    # Real defect class: casualty count silently dropped.
    bad = GOOD_TRANSLATION_FA.replace('۳ کشته', 'تعدادی کشته')
    r = cv.validate_translation(SOURCE, bad)
    assert 'number_mismatch' in r.flags
    # Changed 2026-09-29 (owner requirement for the free-tier pilot): numbers,
    # dates and codes must be preserved, so a dropped number is now a hard
    # fail — the translation is stored as needs_review and not displayed.
    assert r.passed is False
    assert r.quality_score == 0.0


def test_number_altered_in_translation_is_flagged():
    # Real defect class: the dollar figure silently changed from 2.5 to 25.
    bad = GOOD_TRANSLATION_FA.replace('۲.۵ میلیون دلار', '۲۵ میلیون دلار')
    r = cv.validate_translation(SOURCE, bad)
    assert 'number_mismatch' in r.flags


def test_persian_digit_numbers_are_correctly_recognized_as_preserved():
    # Must NOT flag a number as missing just because it's in Persian-Indic
    # script rather than Latin digits — that would be a false positive.
    r = cv.validate_translation('The event happened on 15 March.', 'رویداد در ۱۵ مارس رخ داد.')
    assert 'number_mismatch' not in r.flags


def test_distinctive_code_dropped_is_flagged():
    # Real defect class: the aircraft model silently disappears.
    bad = GOOD_TRANSLATION_FA.replace('F-35', 'جنگنده')
    r = cv.validate_translation(SOURCE, bad)
    assert 'distinctive_code_missing' in r.flags


def test_transliterated_acronym_is_not_falsely_flagged():
    # Real risk this test guards against: NATO is correctly and routinely
    # transliterated as "ناتو" rather than kept verbatim in real Persian
    # translation. A naive verbatim-acronym check would flag every correct
    # translation as defective for this reason alone — extract_distinctive_
    # codes deliberately excludes bare acronyms so this never happens.
    r = cv.validate_translation(SOURCE, GOOD_TRANSLATION_FA)
    assert 'distinctive_code_missing' not in r.flags


def test_negation_loss_is_flagged():
    source = 'Officials denied any involvement in the incident.'
    bad_translation = 'مقامات دخالت در این حادثه را تأیید کردند.'  # "confirmed" instead of "denied" — meaning flipped
    r = cv.validate_translation(source, bad_translation)
    assert 'possible_negation_loss' in r.flags


def test_negation_preserved_is_not_flagged():
    source = 'Officials denied any involvement in the incident.'
    good_translation = 'مقامات دخالت در این حادثه را رد کردند.'
    r = cv.validate_translation(source, good_translation)
    assert 'possible_negation_loss' not in r.flags


def test_truncated_output_is_flagged_too_short():
    r = cv.validate_translation(SOURCE, 'نیروی هوایی.')
    assert 'output_too_short' in r.flags


def test_wildly_expanded_output_is_flagged_too_long():
    padded = GOOD_TRANSLATION_FA + (' این متن اضافی و بدون منبع است.' * 30)
    r = cv.validate_translation(SOURCE, padded)
    assert 'output_too_long' in r.flags


def test_summary_is_not_penalized_for_expected_number_omission():
    # A short summary correctly drops most numbers by design — must not be
    # flagged the same way a full translation would be.
    short_summary = 'نیروی هوایی اسرائیل نزدیک مرز لبنان حمله کرد و ناتو آن را محکوم کرد.'
    r = cv.validate_summary(SOURCE, short_summary)
    assert 'number_mismatch' not in r.flags
    assert 'distinctive_code_missing' not in r.flags


def test_summary_empty_output_still_fails_hard():
    r = cv.validate_summary(SOURCE, '')
    assert r.passed is False


# --- key point evidence span checks -----------------------------------------

def test_key_point_with_real_evidence_passes():
    r = cv.validate_key_point('نیروی هوایی اسرائیل حمله‌ای انجام داد.',
                               'The Israeli Air Force conducted a strike', SOURCE)
    assert r.passed is True


def test_key_point_with_fabricated_evidence_fails():
    # Real defect class: the model invents a citation that never appeared
    # in the source text — this must never be published as evidence.
    r = cv.validate_key_point('روسیه نیز درگیر بود.', 'Russia was also involved in the strike', SOURCE)
    assert r.passed is False
    assert 'evidence_not_found_in_source' in r.flags


def test_key_point_with_missing_evidence_span_fails():
    r = cv.validate_key_point('یک نکته کلیدی', '', SOURCE)
    assert r.passed is False
    assert 'missing_evidence_span' in r.flags


def test_key_point_evidence_check_is_whitespace_and_case_insensitive():
    r = cv.validate_key_point('نکته', 'the israeli   air force conducted   a strike', SOURCE)
    assert r.passed is True


def test_empty_key_point_text_fails():
    r = cv.validate_key_point('', 'The Israeli Air Force conducted a strike', SOURCE)
    assert r.passed is False
    assert 'empty_point' in r.flags


def test_extract_numbers_normalizes_persian_digits():
    assert cv.extract_numbers('قیمت ۱۵۰ دلار بود') == {'150'}


def test_extract_distinctive_codes_finds_model_numbers_but_not_bare_acronyms():
    codes = cv.extract_distinctive_codes('The F-35 and S-400 systems, per NATO and IAEA reports.')
    assert 'F-35' in codes
    assert 'S-400' in codes
    assert 'NATO' not in codes
    assert 'IAEA' not in codes

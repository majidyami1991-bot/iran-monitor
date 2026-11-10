"""Offline tests for the TranslateGemma pipeline (placeholders, glossary,
validator) and the per-role model contracts. The eight failures of the
rejected gemma4 artifact are kept as permanent regression cases."""
import random

import pytest

import assistant as asst
import model_identity as mi
import translation_tg as tg


class FixedRng:
    def __init__(self, seq):
        self.seq = list(seq)

    def choice(self, alphabet):
        return self.seq.pop(0) if self.seq else random.choice(alphabet)


def test_official_prompt_has_exactly_two_blank_lines_before_text():
    body = tg.request_body('translategemma:4b', 'Hello.', seed=42, num_ctx=4096, num_thread=8, temperature=0.1, num_predict=64)
    content = body['messages'][0]['content']
    assert content.endswith('into Persian:\n\n\nHello.') and 'format' not in body and 'think' not in body
    assert content.startswith('You are a professional English (en) to Persian (fa-IR) translator.')


def test_protect_and_restore_roundtrip():
    src = 'CENTCOM said 3 MQ-9 drones flew at 14:30 on 12/10/2026, 40% more, per @OSINTdefender https://e.org/a #OSINT 34.55, 69.20'
    protected, mapping, salt = tg.protect(src)
    for kept in ('CENTCOM', 'MQ-9', '14:30', '12/10/2026', '40%', '@OSINTdefender', 'https://e.org/a', '#OSINT'):
        assert kept not in protected and kept in mapping.values(), kept
    restored, flags = tg.restore(protected, mapping, salt)
    assert restored == src and flags == []


def test_tokens_are_salted_and_collision_safe():
    # The first salt would collide with text already containing ZQAAA; a new one is drawn.
    _, mapping, salt = tg.protect('ZQAAA appears here and 12 too.', rng=FixedRng('AAABBB'))
    assert salt == 'BBB' and all(t.startswith('ZQBBB') for t in mapping)


@pytest.mark.parametrize('mode,flag', [('drop', 'placeholder_missing'), ('dup', 'placeholder_duplicated'),
                                       ('mangle', 'placeholder_missing')])
def test_placeholder_tampering_rejected(mode, flag):
    _, mapping, salt = tg.protect('Spending rose 12% this year.')
    tok = next(iter(mapping))
    text = {'drop': 'هزینه‌ها افزایش یافت.', 'dup': f'هزینه‌ها {tok} {tok} افزایش یافت.',
            'mangle': f'هزینه‌ها {tok[:-1]}Z افزایش یافت.'}[mode]
    _, flags = tg.restore(text, mapping, salt)
    assert flag in flags


def test_placeholder_residue_rejected():
    _, mapping, salt = tg.protect('Worth 2.75 billion dollars.')
    _, flags = tg.restore('ارزش ZQAPP میلیارد دلار.', mapping, salt)
    assert 'placeholder_missing' in flags and 'placeholder_residue' in flags


# ------------------------------------------------------------------ permanent regressions (rejected gemma4)
REGRESSIONS = [
    ('person_names_foreign_script', 'Lloyd Austin met Yoav Gallant in Washington on Tuesday.',
     'لوید آستین روز سه‌شنبه در واشنگتن با 요אف گالانت دیدار کرد.', 'foreign_script'),
    ('person_names_mixed', 'Lloyd Austin met Yoav Gallant in Washington on Tuesday.',
     'لloyd austin روز سه‌شنبه در واشنگتن با یوآو گالانت دیدار کرد.', 'mixed_script_word'),
    ('hashtags_commentary', 'Protests continued for a third day in the capital. #Iran #Protests',
     'اعتراضات به روز سوم ادامه یافت. #ایران #اعتراضات"} is the translation. However<channel|>{', 'model_commentary_or_markdown'),
    ('emoji_commentary', 'Air raid sirens are sounding across the city 🚨',
     'آژیرها به صدا درآمده‌اند 🚨 is the translation.', 'latin_prose_residue'),
    ('simple_title_object_lost', 'Navy commissions new frigate', 'دریایی جدیدی را به ناوگان اختصاص داد', 'glossary_term_missing'),
    ('places_untranslated', 'The convoy moved from Kharkiv toward Izium.', 'ا convoy از خارکیف به سمت ایزیوم حرکت کرد.', 'latin_prose_residue'),
    ('military_term_wrong', 'The brigade conducted a combined-arms live-fire exercise with close air support.',
     'بنیاد یک تمرین آتش زنی زنده ترکیبی با پشتیبانی هوایی نزدیک انجام داد.', 'glossary_term_missing'),
    ('time_launch_sense', 'The missile launch was detected at 03:45 local time.',
     'راه‌اندازی موشک در ساعت 03:45 به وقت محلی شناسایی شد.', 'glossary_term_missing'),
]


@pytest.mark.parametrize('case,src,bad,flag', REGRESSIONS, ids=[r[0] for r in REGRESSIONS])
def test_gemma_regressions_rejected(case, src, bad, flag):
    v = tg.validate(src, bad, {})
    assert not v.passed and flag in v.flags, (case, v.flags)


def test_acronyms_must_survive():
    src = 'OSINT analysts shared ELINT data with NATO and CENTCOM.'
    _, mapping, salt = tg.protect(src)
    assert {'OSINT', 'ELINT', 'NATO', 'CENTCOM'} <= set(mapping.values())


@pytest.mark.parametrize('src,good', [
    ('The 3rd Armored Brigade moved north.', 'تیپ زرهی سوم به سمت شمال حرکت کرد.'),
    ('A military convoy crossed the border.', 'یک کاروان نظامی از مرز عبور کرد.'),
    ('Radar detected a ballistic missile launch.', 'رادار پرتاب یک موشک بالستیک را شناسایی کرد.'),
    ('The navy will commission two new frigates.', 'نیروی دریایی دو ناوچه جدید را به خدمت خواهد گرفت.'),
    ('The deployment of troops was completed.', 'استقرار نیروها به پایان رسید.'),
])
def test_glossary_accepts_correct_terms(src, good):
    assert tg.glossary_check(src, good) == []


def test_empty_and_persian_sources_never_reach_the_model():
    called = []
    assert tg.translate_field(lambda *a: called.append(a), '')['status'] == 'skipped_empty'
    assert tg.translate_field(lambda *a: called.append(a), 'نیروی دریایی رزمایش را آغاز کرد.')['status'] == 'not_required'
    assert called == []


# ------------------------------------------------------------------ per-role contracts
def test_roles_are_separate_and_none_active_now():
    c = mi.load_contract()
    state = mi.approval_state(c)
    assert state['translategemma-4b-ollama0401-llamacpp-6d2c3b38bc4a'] == 'rejected_quality_gate'
    assert state['qwen3-8b-500a1f067a9f'] == 'rejected_quality_gate'
    assert state['translategemma-4b-c49d986b0764'] == 'superseded'
    assert mi.active_approval(c, role='translation') is None and mi.active_approval(c, role='assistant') is None
    by = {a['id']: a for a in c['approvals']}
    assert by['translategemma-4b-ollama0401-llamacpp-6d2c3b38bc4a']['contract'] == 'TRANSLATION_MODEL_CONTRACT'
    assert by['qwen3-8b-500a1f067a9f']['contract'] == 'ASSISTANT_MODEL_CONTRACT'


def test_role_filter_and_fingerprint_binds_glossary_and_validator():
    c = mi.load_contract()
    tr = next(a for a in c['approvals'] if a['id'] == 'translategemma-4b-ollama0401-llamacpp-6d2c3b38bc4a')
    fp = mi.fingerprint(tr)
    assert mi.fingerprint(dict(tr, glossary_version='x')) != fp and mi.fingerprint(dict(tr, validator_version='y')) != fp
    c2 = {'approvals': c['approvals'], 'events': c['events'] + [{'approval': tr['id'], 'event': 'approved'}]}
    assert mi.active_approval(c2, role='translation')['id'] == tr['id']
    assert mi.active_approval(c2, role='assistant') is None  # an approved translator never serves the assistant


# ------------------------------------------------------------------ assistant validator additions
REC = [{'evidence_id': 'E1', 'title': 'Navy holds exercise in Baltic', 'excerpt': 'The navy held a two-day exercise with 12 ships.',
        'published_at': '2026-10-07T10:00:00+00:00', 'source_name': 'A', 'canonical_url': 'https://a.example/1'}]
BASE = {'answer_fa': '', 'confidence': 'medium', 'evidence_ids': ['E1'], 'limitations': [], 'follow_up_suggestions': []}


@pytest.mark.parametrize('text,reason', [
    ('حمله سه дрон گزارش شد [E1].', 'foreign_or_mixed_script'),
    ('رزمایش در بaltic انجام شد [E1].', 'foreign_or_mixed_script'),
    ('۹۹ کشتی شرکت کردند [E1].', 'number_not_in_evidence'),
    ('جزئیات: https://fake.example/x [E1]', 'url_not_in_evidence'),
])
def test_assistant_rejects_scripts_numbers_urls(text, reason):
    assert (asst.validate_answer(dict(BASE, answer_fa=text), REC)[1] or '').startswith(reason)


def test_question_numbers_are_not_invented():
    ok, why = asst.validate_answer(dict(BASE, answer_fa='در ۲۴ ساعت گذشته رزمایشی با ۱۲ کشتی برگزار شد [E1].'), REC,
                                   question='در ۲۴ ساعت گذشته چه شد؟')
    assert ok, why


def test_insufficient_answer_is_classified():
    ok, why = asst.validate_answer(dict(BASE, answer_fa='شواهد کافی نیست.', evidence_ids=[], confidence='low',
                                        limitations=['هیچ سندی مرتبط نیست.']), REC)
    assert not ok and why == 'insufficient_evidence'

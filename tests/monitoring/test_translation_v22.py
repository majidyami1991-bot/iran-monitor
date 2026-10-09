"""v2.2 QC corrections: each proven defect is fixed narrowly, the real error it
resembles stays rejected (no model, no database)."""
import translation_v22 as v22


def test_d1_command_is_not_commander():
    d, det = v22.decide('Ukraine reports strikes on Russian launchers and command posts', 'اوکراین از حملات به پرتابگرهای روسیه و مراکز فرماندهی خبر داد.')
    assert 'qc:role_added:فرمانده' not in det['critical']


def test_d1_real_commander_added_stays():
    d, det = v22.decide('Officials visited the base.', 'فرمانده و مقامات از پایگاه بازدید کردند.')
    assert d == 'REJECT_CRITICAL'


def test_d2_marine_corps_rendering_not_irgc():
    assert v22._reasons_for_flag('qc:entity_added:IRGC', 'A U.S. Marine Corps aircraft flew.', 'هواپیمای سپاه تفنگداران دریایی آمریکا پرواز کرد.', []) is None


def test_d2_real_irgc_addition_stays():
    assert v22._reasons_for_flag('qc:entity_added:IRGC', 'A U.S. Marine Corps aircraft flew.', 'هواپیمای سپاه تفنگداران و سپاه پاسداران پرواز کرد.', []) == 'qc:entity_added:IRGC'


def test_d2_marines_rendered_as_navy_stays_rejected():
    d, det = v22.decide('U.S. Marine Corps wants AI to spot aircraft failures early', 'نیروی دریایی ایالات متحده می‌خواهد از هوش مصنوعی برای تشخیص زودهنگام نقص‌های هواپیما استفاده کند.')
    assert d == 'REJECT_CRITICAL'


def test_d3_exact_letter_name_transliteration():
    assert v22.code_transliterated('SM-3', 'موشک‌های اس‌ام-۳ آی‌بی')
    assert v22.code_transliterated('F-16s', 'جنگنده‌های اف-۱۶')
    assert v22.code_transliterated('AGM-158C', 'موشک ای‌جی‌ام-۱۵۸سی')


def test_d3_wrong_digits_or_letters_rejected():
    assert not v22.code_transliterated('SM-3', 'موشک‌های اس‌ام-۶')
    assert not v22.code_transliterated('F-16', 'جنگنده‌های اف-۳۵')
    assert not v22.code_transliterated('F-16', 'جنگنده‌های بی-۱۶')


def test_d4_sponsored_tag_translated():
    assert v22._reasons_for_flag('qc:placeholder_text:[با حمایت مالی]', '[Sponsored] New batteries.', '[با حمایت مالی] باتری‌های جدید.', []) is None


def test_d4_leftover_placeholder_stays():
    assert v22._reasons_for_flag('qc:placeholder_text:[تاریخ]', 'The ship docked on Monday.', 'کشتی در [تاریخ] پهلو گرفت.', []) == 'qc:placeholder_text:[تاریخ]'


def test_d5_yeki_is_one_and_idiom_is_not_a_number():
    assert v22._reasons_for_flag('qc:number_missing:1', 'One source said so.', 'یکی از منابع چنین گفت.', []) is None
    assert v22._reasons_for_flag('qc:number_missing:1', 'Every one-on-one slot is booked.', 'همه جلسات انفرادی رزرو شده‌اند.', []) is None


def test_d5_real_missing_one_stays():
    assert v22._reasons_for_flag('qc:number_missing:1', 'Israel sent 1 battery.', 'اسرائیل باتری فرستاد.', []) == 'qc:number_missing:1'


def test_d6_general_in_compounds_is_not_a_role():
    flag = 'role:(?<!secretary )(?<!secretary-)\\bgenerals?\\b:missing'
    assert v22._reasons_for_flag(flag, 'The British Consulate General closed. General Dynamics delivered.', 'کنسولگری بریتانیا بسته شد.', []) is None
    assert v22._reasons_for_flag(flag, 'General Smith met the Consulate General staff.', 'آقای اسمیت دیدار کرد.', []) == flag


def test_d8_past_year_rendered_as_until_is_critical():
    d, det = v22.decide('U.S. plans to keep V-22 Osprey flying past 2055', 'ایالات متحده قصد دارد تا سال ۲۰۵۵ به استفاده از هواپیماهای V-22 اوسپری ادامه دهد.')
    assert d == 'REJECT_CRITICAL' and any(c.startswith('time_relation:past_2055') for c in det['critical'])


def test_d8_past_year_rendered_correctly_passes_that_check():
    assert v22.time_relation_checks('flying past 2055', 'پرواز پس از سال ۲۰۵۵') == []


def test_d9_title_case_words_need_summary_confirmation():
    title = 'Eisenkot Slams Channel 14 for Skipping October 7th Memorial Ceremony'
    fa = 'آیزنکوت، شبکه ۱۴ را به دلیل عدم شرکت در مراسم یادبود هفتم اکتبر مورد انتقاد قرار داد.'
    assert v22.name_resolved('Memorial Ceremony', title, fa, 'Eisenkot criticised the channel for skipping the memorial ceremony.')
    assert not v22.name_resolved('Memorial Ceremony', title, fa, None)          # no context: stays uncertain


def test_d9_real_name_confirmed_in_summary_must_still_match():
    title = 'Zamir Briefed On Plans By Kurilla'
    summary = 'Chief of staff Zamir was briefed on Monday by Kurilla about the plans.'
    assert not v22.name_resolved('Kurilla', title, 'رئیس ستاد زمیر توسط فرمانده دیگری توجیه شد.', summary)
    assert v22.name_resolved('Kurilla', title, 'زمیر توسط کوریلا توجیه شد.', summary)


def test_versions():
    d, det = v22.decide('Talks resumed.', 'مذاکرات از سر گرفته شد.')
    assert det['pipeline'] == 'translation-pipeline-v2.2.0' and det['facts_version'] == 'translation-facts-v1.2.0'

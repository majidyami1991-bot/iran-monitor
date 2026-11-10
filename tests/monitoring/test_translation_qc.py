"""translation_qc: deterministic controls (dev-style examples only; the
held-out set is never used in tests)."""
import translation_qc as qc


def flags(src, out, ref=None):
    return qc.check(src, out, ref)['flags']


def test_clean_translation_not_suspect():
    r = qc.check('The army completed its annual winter exercise on Sunday.', 'ارتش تمرین زمستانی سالانه خود را روز یکشنبه به پایان رساند.')
    assert not r['suspect'], r


def test_number_missing_and_added():
    assert 'number_missing:12' in flags('Defense spending rose 12% this year.', 'هزینه‌های دفاعی امسال افزایش یافت.')
    assert any(f.startswith('number_added:7') for f in flags('Four soldiers were wounded.', 'هفت سرباز زخمی شدند.'))


def test_unit_and_model_relabel():
    assert 'unit_missing:billion' in flags('The contract is worth $3 billion.', 'ارزش قرارداد 3 دلار است.')
    assert 'number_relabelled_as_model' in flags('Spain orders 30 Rafale jets', 'اسپانیا جنگنده رافال مدل 30 سفارش داد')


def test_placeholder_text():
    assert any(f.startswith('placeholder_text') for f in flags('The talks ended on 4 May.', 'مذاکرات در [تاریخ] پایان یافت.'))


def test_month_untranslated_and_missing():
    f = flags('The visit is planned for 9 October.', 'این سفر برای 9 October برنامه‌ریزی شده است.')
    assert 'month_untranslated' in f and 'month_missing:october' in f


def test_role_and_entity_added():
    f = flags('Lloyd Austin met Yoav Gallant.', 'لوید آستین، وزیر دفاع آمریکا، با یوآو گالانت، وزیر جنگ اسرائیل، دیدار کرد.')
    assert 'role_added:وزیر' in f and 'entity_added:Israel' in f


def test_role_missing():
    assert 'role_missing:مدیرعامل' in flags('Rheinmetall CEO Armin Papperger spoke.', 'آرمین پاپرگر سخن گفت.')


def test_echelon_wrong():
    f = flags('The brigade moved north.', 'گردان به سمت شمال حرکت کرد.')
    assert 'echelon_missing:brigade' in f and 'echelon_added:گردان' in f


def test_strike_as_labour_and_simulated():
    assert 'unsupported_word:اعتصاب' in flags('The strike hit a depot.', 'اعتصاب به یک انبار اصابت کرد.')
    assert 'unsupported_word:شبیه سازی' in flags('A live-fire drill was held.', 'یک تمرین شبیه‌سازی‌شده برگزار شد.')


def test_weekday_compound_is_not_a_number():
    assert not any(f.startswith('number_added') for f in flags('They met on Tuesday.', 'آن‌ها روز سه‌شنبه دیدار کردند.'))


def test_equipment_code_not_billion():
    assert not any(f.startswith('unit_missing') for f in flags('The MQ-9B flew.', 'MQ-9B پرواز کرد.'))


def test_empty_output_suspect():
    assert qc.check('Text.', '')['suspect']


# v1.0.1 fixes (bugs found by the phase-7 held-out run)
def test_v101_plural_agencies_not_unsupported():
    assert not any(f.startswith('unsupported_word') for f in
                   flags('The attack affected 200 government agencies.', 'این حمله 200 سازمان دولتی را تحت تأثیر قرار داد.'))


def test_v101_plural_ministers_not_role_added():
    assert not any(f.startswith('role_added') for f in
                   flags('Foreign ministers met in Rome.', 'وزیران امور خارجه در رم دیدار کردند.'))


def test_v101_kyiv_and_naval_not_missing():
    assert not any(f.startswith('entity_missing') for f in flags('The Kyiv Independent reported it.', 'کی‌یف ایندپندنت آن را گزارش داد.'))
    assert not any(f.startswith('entity_missing') for f in flags('They attacked a naval base.', 'آن‌ها به یک پایگاه دریایی حمله کردند.'))


# v1.0.2 fixes (found while calibrating the automated gate on 12B phase-8 output, before 27B existed)
def test_v102_persian_comma_is_not_a_letter():
    assert not any(f.startswith('number_missing') for f in flags('No casualties were reported in the second attack.', 'در حمله دوم، هیچ تلفاتی گزارش نشد.'))


def test_v102_neither_nor_is_not_nine():
    assert not any(f.startswith('number_added') for f in flags('The ministry neither confirmed nor denied the report.',
                                                               'وزارتخانه نه این گزارش را تأیید کرد و نه آن را رد کرد.'))


def test_v102_secretary_general_is_not_general_and_nato_is_an_organisation():
    f = flags('Mark Rutte, NATO secretary general, arrived.', 'مارک روته، دبیرکل سازمان ناتو، وارد شد.')
    assert not any(x.startswith(('role_missing', 'unsupported_word')) for x in f), f


def test_v102_kremlin_satisfies_russia():
    assert not any(f.startswith('entity_missing') for f in flags('Moscow alleged it.', 'کرملین چنین ادعا کرد.'))


# ---- translation pipeline v2 (fact extraction / verification), dev-style cases only
import translation_v2 as v2


def test_v2_level_vs_change_conflict():
    d, det = v2.decide('Unemployment rose to 7.2% in September.', 'نرخ بیکاری در ماه سپتامبر به میزان 7.2% افزایش یافت.')
    assert d == 'REJECT_CRITICAL' and any('level_rendered_as_change' in x for x in det['critical'])


def test_v2_percentage_points():
    d, det = v2.decide('Unemployment rose by 0.4 percentage points.', 'نرخ بیکاری 0.4 درصد افزایش یافت.')
    assert d == 'REJECT_CRITICAL'


def test_v2_number_unit_and_relabel():
    assert v2.decide('The 15-kilometre zone.', 'منطقه یک کیلومتری 15.')[0] == 'REJECT_CRITICAL'
    assert v2.decide('Ukraine received 31 Abrams tanks.', 'اوکراین تانک‌های آبرامز مدل 31 دریافت کرد.')[0] == 'REJECT_CRITICAL'


def test_v2_correct_level_accepted():
    d, det = v2.decide('Oil exports fell by a third to 1.1 million barrels a day.',
                       'حجم صادرات نفت یک‌سوم کاهش یافت و به میزان 1.1 میلیون بشکه در روز رسید.')
    assert d == 'ACCEPT', det


def test_v2_quote_attribution_negation():
    assert v2.decide('The commander said «پیروزی نزدیک است» in Tehran.', 'فرمانده در تهران گفت «پیروزی در نزدیکی است».')[0] == 'REJECT_CRITICAL'
    assert v2.decide('The group may have used gas, investigators said.', 'گزارش‌ها می‌گویند این گروه ممکن است از گاز استفاده کرده باشد.')[0] == 'REJECT_CRITICAL'
    assert v2.decide('The missile did not hit its target.', 'موشک به هدف اصابت کرد.')[0] == 'REJECT_CRITICAL'


def test_v2_month_may_is_not_modal():
    facts = v2.extract('Elections, originally set for May, were postponed until October.')
    assert not any(f['type'] == 'certainty' for f in facts)

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

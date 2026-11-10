"""Offline tests for the v2.1 operational QC filter (no model, no database)."""
import translation_v21 as v21


def test_persian_number_words_and_forms():
    assert 2000.0 in v21.persian_number_values('دو هزار سرباز')[0]
    assert 80000.0 in v21.persian_number_values('۸۰ هزار نفر')[0]
    assert 19.0 in v21.persian_number_values('نوزدهمین نشست')[0]
    assert 25.0 in v21.persian_number_values('بیست و پنج پهپاد')[0]
    assert 1200000.0 in v21.persian_number_values('یک میلیون و دویست هزار')[0]
    assert v21.persian_number_values('نه، او نیامد')[0] == set()     # «نه» = no, not 9


def test_number_in_words_is_accepted():
    d, det = v21.decide('About 2,000 soldiers were deployed to the border.', 'حدود دو هزار سرباز به مرز اعزام شدند.')
    assert d == 'ACCEPT', det


def test_mobilisation_must_be_rendered():
    d, det = v21.decide('Moscow ordered a partial mobilisation of reservists.',
                        'مسکو دستور داد بخشی از نیروهای ذخیره به حالت آماده‌باش درآیند.')
    assert d == 'REJECT_CRITICAL' and any('mobilisation' in c for c in det['critical'])


def test_mechanised_must_be_rendered():
    d, det = v21.decide('A mechanised battalion moved north.', 'یک گردان زرهی به سمت شمال حرکت کرد.')
    assert d == 'REJECT_CRITICAL' and any('mechanised' in c for c in det['critical'])


def test_strike_as_labour_strike_is_critical():
    d, det = v21.decide('A drone strike hit the depot.', 'اعتصاب پهپادی به انبار اصابت کرد.')
    assert d == 'REJECT_CRITICAL'


def test_points_vs_percent_still_critical():
    d, det = v21.decide('The rate rose by 0.4 percentage points.', 'نرخ ۰٫۴ درصد افزایش یافت.')
    assert d == 'REJECT_CRITICAL'


def test_added_scale_is_conflict():
    d, det = v21.decide('Police arrested 80 protesters.', 'پلیس ۸۰ هزار معترض را بازداشت کرد.')
    assert d == 'REJECT_CRITICAL' and any(c.startswith('scale_added') for c in det['critical'])


def test_versions_recorded():
    d, det = v21.decide('Talks resumed.', 'مذاکرات از سر گرفته شد.')
    assert det['pipeline'] == 'translation-pipeline-v2.1.0' and det['facts_version'] == 'translation-facts-v1.1.0'

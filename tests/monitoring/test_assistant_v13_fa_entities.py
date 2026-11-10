"""Persian entity recognition of the v1.3 question analyser (lexicon v1.1.0).
The safety property: a Persian term is either resolved to the RIGHT entity
or left unresolved (the assistant then refuses and names the term); it is
never resolved to a wrong entity, including inside longer words."""
import pytest

import assistant_relevance as ar

CASES = [
    ('اخبار مرتبط با بوئینگ', {'Boeing'}, None),
    ('اخبار مرتبط با بویینگ', {'Boeing'}, None),
    ('اخبار مرتبط با لاکهید مارتین', {'Lockheed Martin'}, None),
    ('اخبار مرتبط با ناتو', {'NATO'}, None),
    ('اخبار مرتبط با سپاه پاسداران', {'IRGC'}, None),
    ('اخبار مرتبط با حزب‌الله', {'Hezbollah'}, None),
    ('اخبار مرتبط با حزب الله', {'Hezbollah'}, None),
    ('اخبار مرتبط با حوثی‌ها', {'Houthis'}, None),
    ('اخبار مرتبط با نتانیاهو', {'Benjamin Netanyahu'}, None),
    ('اخبار مرتبط با زلنسکی', {'Volodymyr Zelensky'}, None),
    ('اخبار مرتبط با اردوغان', {'Recep Tayyip Erdogan'}, None),
    ('اخبار مرتبط با راینمتال', {'Rheinmetall'}, None),
    ('اخبار مرتبط با ايران', {'Iran'}, None),                    # Arabic yeh
    ('اخبار مرتبط با تهران', {'Tehran'}, None),
    ('اخبار مرتبط با اسرائیلی‌ها', {'Israel'}, None),
    ('اخبار مرتبط با روس‌ها', {'Russia'}, None),
    ('اخبار مرتبط با ارتش اسرائیل', {'IDF'}, None),
    ('اخبار مرتبط با نیروی هوایی آمریکا', {'Air Force', 'United States'}, None),
    ('اخبار مرتبط با نیروی دریایی آمریکا', {'Navy', 'United States'}, None),
    ('درباره سقوط اف ۳۵ چه گزارش شده است؟', {'F-35'}, {'crash'}),
    ('درباره سقوط F35 چه گزارش شده است؟', {'F-35'}, {'crash'}),
    ('درباره سقوط اف‌-۱۶ در آلمان چه گزارش شده است؟', {'F-16', 'Germany'}, {'crash'}),
    ('درباره سقوط جنگنده در میشیگان چه گزارش شده است؟', {'fighter', 'Michigan'}, {'crash'}),
    ('درباره سقوط بالگرد بلک هاوک چه گزارش شده است؟', {'helicopter', 'Black Hawk'}, {'crash'}),
    ('درباره سامانه پاتریوت در اوکراین چه گزارش شده است؟', {'Patriot', 'Ukraine'}, None),
    ('درباره تحویل جگوار به ارتش فرانسه چه گزارش شده است؟', {'Jaguar', 'Army', 'France'}, {'delivery'}),
    ('درباره قرارداد ۱۴٫۷ میلیارد دلاری PAC-3 چه گزارش شده است؟', {'Patriot'}, {'contract'}),
    ('درباره پهلوگیری ناو جورج بوش در تایلند چه گزارش شده است؟', {'USS George H.W. Bush', 'Thailand'}, {'port_call'}),  # «ناو جورج بوش» is one alias
    ('درباره آزمایش موشک بالستیک کره شمالی چه گزارش شده است؟', {'ballistic missile', 'North Korea'}, {'test'}),
    ('درباره حمله پهپادی به اودسا چه گزارش شده است؟', {'drone', 'Odesa'}, {'attack'}),
    ('درباره رزمایش ناتو در دریای بالتیک چه گزارش شده است؟', {'NATO', 'Baltic Sea'}, {'exercise'}),
    ('درباره تنگه هرمز چه گزارش شده است؟', {'Strait of Hormuz'}, None),
    ('درباره غزه چه گزارش شده است؟', {'Gaza'}, None),
    ('درباره کرانه باختری چه گزارش شده است؟', {'West Bank'}, None),
    # must NOT resolve to a wrong entity: unknown → unresolved (refusal)
    ('درباره خلیج فارس چه گزارش شده است؟', 'UNRESOLVED', None),
    ('اخبار مرتبط با شرکت فایرپوینت', 'UNRESOLVED', None),
    ('اخبار مرتبط با سیاستمداران', 'UNRESOLVED', None),    # «سیا» (CIA) must not fire inside a word
    ('اخبار مرتبط با مصرف سوخت', 'UNRESOLVED', None),       # «مصر» (Egypt) must not fire inside «مصرف»
    ('اخبار مرتبط با هفتاد فروند', 'UNRESOLVED', None),     # «تاد» (THAAD) must not fire inside «هفتاد»
    ('اخبار مرتبط با بنتلی', 'UNRESOLVED', None),           # «بنت» (Bennett) must not fire inside a longer name
]


@pytest.mark.parametrize('question,expected,events', CASES)
def test_persian_entity_resolution(question, expected, events):
    p = ar.analyse(question)
    got = {a.canonical for a in p.anchors}
    if expected == 'UNRESOLVED':
        assert p.unresolved and not got, (got, p.unresolved)
    else:
        assert got == expected and not p.unresolved, (got, p.unresolved)
        if events is not None:
            assert set(p.event_types) == events, p.event_types

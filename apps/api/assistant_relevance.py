"""Deterministic relevance gate for the extractive assistant (contract v1.3).

The model in the extractive assistant only selects verbatim sentences. v1.2
showed that a verbatim, correctly cited quote can still be irrelevant: lexical
retrieval returned unrelated records and the model quoted them. This module
decides relevance with no model at all:

1. analyse(question) → a Plan: the intent (one of the contract's allowed
   intents, or an out-of-contract reason), the anchors (people,
   organisations, places, equipment, equipment classes, codes such as F-16),
   the event types (crash, contract, test …), a time window, a
   quantity flag, and the question words that could not be resolved.
   Persian questions are resolved through a versioned Persian→English
   lexicon, because the evidence is the original (English) text and stored
   machine translations are never evidence.
2. record_relevance(plan, record): a record is relevant only when EVERY
   anchor and the event type of the question occur in its original title or
   excerpt (word-bounded English patterns), and it lies in the window.
3. quote_relevant(plan, quote): a selected quote must itself mention an
   anchor or the event type; a true sentence about something else is dropped.
4. same_event(a, b, plan): two records are one event only when ALL hold —
   the clustering placed them in the same event, they are ≤ 72 h apart, they
   share the event type, they share ≥ 2 distinctive entities (at least one not
   a country), and their places do not conflict. Shared words alone, topic
   similarity or time proximity alone never suffice.
5. conflicts(...): different numbers or a denial across sources of one event
   make a single answer to a quantity question unreliable (refuse; a
   comparison question shows each source instead).

Unknown words fail closed: a question term the lexicon cannot resolve makes
the assistant refuse and name the term, instead of silently ignoring a word
that may have been the point of the question.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

LEXICON_VERSION = 'assistant-lexicon-fa-en-v1.1.0'
RELEVANCE_VERSION = 'relevance-gate-v1.0.0'
MAX_EVENT_HOURS = 72

_FA_NORM = str.maketrans({'ي': 'ی', 'ك': 'ک', 'ۀ': 'ه', 'ة': 'ه', 'ؤ': 'و', 'إ': 'ا', 'أ': 'ا', 'ٔ': None,
                          '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
                          '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'})
_FA_LETTER = 'آ-ی'
_FA_SUFFIX = r'(?:‌?(?:های|ها|ای|یان|ان|ی|ش|ه))?'


def norm_fa(text):
    t = (text or '').translate(_FA_NORM).replace('‌', ' ').replace('ـ', '')
    t = re.sub(r'[،؛؟?!:«»()\[\]"]', ' ', t)  # '.', '/', '-' kept: U.S., F/A-XX, F-16
    return re.sub(r'\s+', ' ', t).strip()


# --------------------------------------------------------------------------- lexicon
# (canonical, kind, Persian aliases, English patterns, parents)
# kind: country | place | org | person | equipment | class
# English patterns are regex fragments matched word-bounded; an all-caps
# pattern is case-sensitive (US ≠ "us"), anything else is case-insensitive.
ENTITIES = [
    # countries
    ('Iran', 'country', ['ایران'], [r'Iran(?:ian)?s?', r'Tehran'], ()),
    ('Israel', 'country', ['اسرائیل', 'اسراییل'], [r'Israel(?:i|is)?', r'IDF'], ()),
    ('United States', 'country', ['آمریکا', 'امریکا', 'ایالات متحده'], [r'U\.?S\.?A?', r'United States', r'American?s?', r'USAF', r'USS'], ()),
    ('Russia', 'country', ['روسیه', 'روس'], [r'Russian?s?', r'Moscow', r'Kremlin'], ()),
    ('Ukraine', 'country', ['اوکراین'], [r'Ukrain(?:e|ian|ians)', r'Kyiv'], ()),
    ('China', 'country', ['چین'], [r'Chin(?:a|ese)', r'PLA', r'Beijing'], ()),
    ('Saudi Arabia', 'country', ['عربستان', 'عربستان سعودی'], [r'Saudi(?: Arabia)?'], ()),
    ('Germany', 'country', ['آلمان'], [r'German(?:y|s)?', r'Bundeswehr'], ()),
    ('France', 'country', ['فرانسه'], [r'Fran(?:ce|ç|c)', r'French'], ()),
    ('United Kingdom', 'country', ['انگلیس', 'بریتانیا', 'انگلستان'], [r'UK', r'Brit(?:ain|ish)', r'United Kingdom', r'Royal Navy', r'RAF'], ()),
    ('Poland', 'country', ['لهستان'], [r'Pol(?:and|ish)'], ()),
    ('Latvia', 'country', ['لتونی'], [r'Latvia(?:n)?'], ()),
    ('Lithuania', 'country', ['لیتوانی'], [r'Lithuania(?:n)?'], ()),
    ('Estonia', 'country', ['استونی'], [r'Estonia(?:n)?'], ()),
    ('Finland', 'country', ['فنلاند'], [r'Finland', r'Finnish'], ()),
    ('Sweden', 'country', ['سوئد'], [r'Swed(?:en|ish)'], ()),
    ('Norway', 'country', ['نروژ'], [r'Norw(?:ay|egian)'], ()),
    ('Denmark', 'country', ['دانمارک'], [r'Denmark', r'Danish'], ()),
    ('Netherlands', 'country', ['هلند'], [r'Netherlands', r'Dutch'], ()),
    ('Italy', 'country', ['ایتالیا'], [r'Ital(?:y|ian)'], ()),
    ('Spain', 'country', ['اسپانیا'], [r'Spa(?:in|nish)'], ()),
    ('Turkey', 'country', ['ترکیه'], [r'Turk(?:ey|ish|iye)', r'Türkiye'], ()),
    ('Australia', 'country', ['استرالیا'], [r'Australia(?:n)?'], ()),
    ('Japan', 'country', ['ژاپن'], [r'Japan(?:ese)?'], ()),
    ('South Korea', 'country', ['کره جنوبی'], [r'South Korea(?:n)?', r'ROK'], ()),
    ('North Korea', 'country', ['کره شمالی'], [r'North Korea(?:n)?', r'DPRK', r'Pyongyang'], ()),
    ('Taiwan', 'country', ['تایوان'], [r'Taiwan(?:ese)?'], ()),
    ('India', 'country', ['هند'], [r'India(?:n)?'], ()),
    ('Pakistan', 'country', ['پاکستان'], [r'Pakistan(?:i)?'], ()),
    ('Thailand', 'country', ['تایلند'], [r'Thai(?:land)?'], ()),
    ('Uzbekistan', 'country', ['ازبکستان'], [r'Uzbek(?:istan)?'], ()),
    ('Canada', 'country', ['کانادا'], [r'Canad(?:a|ian)'], ()),
    ('Egypt', 'country', ['مصر'], [r'Egypt(?:ian)?'], ()),
    ('Jordan', 'country', ['اردن'], [r'Jordan(?:ian)?'], ()),
    ('Lebanon', 'country', ['لبنان'], [r'Leban(?:on|ese)'], ()),
    ('Syria', 'country', ['سوریه'], [r'Syria(?:n)?'], ()),
    ('Iraq', 'country', ['عراق'], [r'Iraq(?:i)?'], ()),
    ('Yemen', 'country', ['یمن'], [r'Yemen(?:i)?'], ()),
    ('UAE', 'country', ['امارات'], [r'UAE', r'Emirat(?:es|i)'], ()),
    ('Qatar', 'country', ['قطر'], [r'Qatar(?:i)?'], ()),
    ('Argentina', 'country', ['آرژانتین'], [r'Argentin(?:a|e|ian)'], ()),
    ('Brazil', 'country', ['برزیل'], [r'Brazil(?:ian)?'], ()),
    ('Mexico', 'country', ['مکزیک'], [r'Mexic(?:o|an)'], ()),
    ('Afghanistan', 'country', ['افغانستان'], [r'Afghan(?:istan)?'], ()),
    ('Morocco', 'country', ['مراکش'], [r'Morocc(?:o|an)'], ()),
    # places (sub-national, cities, seas, bases); parents expand for conflicts
    ('Tehran', 'place', ['تهران'], [r'Tehran'], ('Iran',)),
    ('Gaza', 'place', ['غزه'], [r'Gaza'], ('Palestine',)),
    ('West Bank', 'place', ['کرانه باختری'], [r'West Bank', r'Judea', r'Samaria'], ('Palestine',)),
    ('Tel Aviv', 'place', ['تل آویو'], [r'Tel Aviv'], ('Israel',)),
    ('Jerusalem', 'place', ['اورشلیم', 'بیت المقدس', 'قدس'], [r'Jerusalem'], ('Israel',)),
    ('Michigan', 'place', ['میشیگان'], [r'Michigan'], ('United States',)),
    ('Nevada', 'place', ['نوادا'], [r'Nevada'], ('United States',)),
    ('Nellis', 'place', ['نلیس'], [r'Nellis'], ('Nevada', 'United States')),
    ('Alaska', 'place', ['آلاسکا'], [r'Alaska(?:n)?'], ('United States',)),
    ('Hawaii', 'place', ['هاوایی'], [r'Hawaii(?:an)?'], ('United States',)),
    ('Virginia', 'place', ['ویرجینیا'], [r'Virginia'], ('United States',)),
    ('Washington', 'place', ['واشنگتن'], [r'Washington'], ('United States',)),
    ('Guam', 'place', ['گوام'], [r'Guam'], ('United States', 'Pacific')),
    ('Spangdahlem', 'place', ['اشپانگدالم', 'اسپانگدالم'], [r'Spangdahlem'], ('Germany',)),
    ('Fairford', 'place', ['فرفورد', 'فیرفورد'], [r'Fairford'], ('United Kingdom',)),
    ('Odesa', 'place', ['اودسا'], [r'Odes?sa'], ('Ukraine',)),
    ('Kharkiv', 'place', ['خارکیف'], [r'Kharkiv'], ('Ukraine',)),
    ('Crimea', 'place', ['کریمه'], [r'Crimea(?:n)?'], ('Ukraine',)),
    ('Baltic Sea', 'place', ['بالتیک', 'دریای بالتیک'], [r'Baltic'], ()),
    ('Black Sea', 'place', ['دریای سیاه'], [r'Black Sea'], ()),
    ('Red Sea', 'place', ['دریای سرخ'], [r'Red Sea'], ()),
    ('Strait of Hormuz', 'place', ['هرمز', 'تنگه هرمز'], [r'Hormuz'], ()),
    ('Bab el-Mandeb', 'place', ['باب المندب'], [r'Mandab'], ()),
    ('South China Sea', 'place', ['دریای چین جنوبی'], [r'South China Sea'], ('Pacific',)),
    ('Arctic', 'place', ['قطب شمال', 'شمالگان'], [r'Arctic'], ()),
    ('Pacific', 'place', ['اقیانوس آرام'], [r'Pacific', r'Indo-Pacific'], ()),
    ('Middle East', 'place', ['خاورمیانه'], [r'Middle East'], ()),
    ('Europe', 'place', ['اروپا'], [r'Europe(?:an)?'], ()),
    # organisations
    ('NATO', 'org', ['ناتو'], [r'NATO'], ()),
    ('United Nations', 'org', ['سازمان ملل'], [r'UN', r'United Nations'], ()),
    ('Pentagon', 'org', ['پنتاگون', 'وزارت دفاع آمریکا'], [r'Pentagon', r'Department of (?:Defense|War)', r'DoD'], ()),
    ('State Department', 'org', ['وزارت خارجه آمریکا'], [r'State Department'], ()),
    ('Navy', 'org', ['نیروی دریایی'], [r'Navy', r'naval'], ()),
    ('Air Force', 'org', ['نیروی هوایی'], [r'Air Force', r'USAF', r'RAF', r'Airmen'], ()),
    ('Army', 'org', ['ارتش', 'نیروی زمینی'], [r'Army'], ()),
    ('Marine Corps', 'org', ['تفنگداران دریایی'], [r'Marine Corps', r'Marines', r'USMC'], ()),
    ('Space Force', 'org', ['نیروی فضایی'], [r'Space Force'], ()),
    ('Coast Guard', 'org', ['گارد ساحلی'], [r'Coast Guard'], ()),
    ('IDF', 'org', ['ارتش اسرائیل'], [r'IDF', r'Israel Defense Forces'], ('Israel',)),
    ('Shin Bet', 'org', ['شین بت'], [r'Shin Bet'], ('Israel',)),
    ('IRGC', 'org', ['سپاه', 'سپاه پاسداران'], [r'IRGC', r'Revolutionary Guard'], ('Iran',)),
    ('Hamas', 'org', ['حماس'], [r'Hamas'], ()),
    ('Hezbollah', 'org', ['حزب الله'], [r'Hezbollah', r'Hizballah'], ()),
    ('Houthis', 'org', ['حوثی', 'حوثی ها', 'انصارالله'], [r'Houthis?', r'Ansar Allah'], ()),
    ('CIA', 'org', ['سیا'], [r'CIA'], ()),
    ('Boeing', 'org', ['بوئینگ', 'بویینگ'], [r'Boeing'], ()),
    ('Lockheed Martin', 'org', ['لاکهید', 'لاکهید مارتین'], [r'Lockheed(?: Martin)?'], ()),
    ('Northrop Grumman', 'org', ['نورثروپ', 'نورتروپ', 'نورثروپ گرومن'], [r'Northrop(?: Grumman)?'], ()),
    ('RTX', 'org', ['ریتیون', 'رایتیون'], [r'RTX', r'Raytheon'], ()),
    ('General Dynamics', 'org', ['جنرال داینامیکس'], [r'General Dynamics'], ()),
    ('General Atomics', 'org', ['جنرال اتامیکس', 'جنرال اتمیکس'], [r'General Atomics'], ()),
    ('BAE Systems', 'org', ['بی ای ای', 'بی‌ای‌ای سیستمز'], [r'BAE(?: Systems)?'], ()),
    ('Rheinmetall', 'org', ['راینمتال'], [r'Rheinmetall'], ()),
    ('Saab', 'org', ['ساب'], [r'Saab'], ()),
    ('Thales', 'org', ['تالس'], [r'Thales'], ()),
    ('Leonardo', 'org', ['لئوناردو'], [r'Leonardo(?: DRS)?'], ()),
    ('Airbus', 'org', ['ایرباس'], [r'Airbus'], ()),
    ('Dassault', 'org', ['داسو'], [r'Dassault'], ()),
    ('Anduril', 'org', ['اندوریل', 'اندریل'], [r'Anduril'], ()),
    ('Embraer', 'org', ['امبرائر', 'امبرایر'], [r'Embraer'], ()),
    ('Navantia', 'org', ['ناوانتیا'], [r'Navantia'], ()),
    ('KNDS', 'org', ['کی ان دی اس'], [r'KNDS'], ()),
    ('Kongsberg', 'org', ['کونگسبرگ'], [r'Kongsberg', r'KONGSBERG'], ()),
    ('Hanwha', 'org', ['هانوا'], [r'Hanwha'], ()),
    ('Fincantieri', 'org', ['فینکانتیری'], [r'Fincantieri'], ()),
    ('Rolls-Royce', 'org', ['رولزرویس', 'رولز رویس'], [r'Rolls-Royce'], ()),
    # people
    ('Benjamin Netanyahu', 'person', ['نتانیاهو'], [r'Netanyahu'], ()),
    ('Donald Trump', 'person', ['ترامپ'], [r'Trump'], ()),
    ('Vladimir Putin', 'person', ['پوتین'], [r'Putin'], ()),
    ('Volodymyr Zelensky', 'person', ['زلنسکی'], [r'Zelensk(?:y|yy|iy)'], ()),
    ('Pete Hegseth', 'person', ['هگست', 'هگزت'], [r'Hegseth'], ()),
    ('Israel Katz', 'person', ['کاتز', 'یسرائیل کاتز'], [r'Katz'], ()),
    ('Itamar Ben Gvir', 'person', ['بن گویر', 'بن گوير'], [r'Ben[- ]Gvir'], ()),
    ('Gadi Eisenkot', 'person', ['آیزنکوت', 'آیزنکوت'], [r'Eisenkot'], ()),
    ('Naftali Bennett', 'person', ['بنت', 'نفتالی بنت'], [r'Bennett'], ()),
    ('Yair Lapid', 'person', ['لاپید'], [r'Lapid'], ()),
    ('Avigdor Liberman', 'person', ['لیبرمن'], [r'Lie?berman'], ()),
    ('Recep Tayyip Erdogan', 'person', ['اردوغان'], [r'Erdo[gğ]an'], ()),
    ('Ali Khamenei', 'person', ['خامنه ای'], [r'Khamenei'], ()),
    ('Masoud Pezeshkian', 'person', ['پزشکیان'], [r'Pezeshkian'], ()),
    ('Abbas Araghchi', 'person', ['عراقچی'], [r'Araghchi'], ()),
    ('Ed Miliband', 'person', ['میلیبند'], [r'Miliband'], ()),
    ('Yahya Sinwar', 'person', ['سنوار', 'یحیی سنوار'], [r'Sinwar'], ()),
    ('Hassan Nasrallah', 'person', ['نصرالله'], [r'Nasrallah'], ()),
    ('Armin Papperger', 'person', ['پاپرگر'], [r'Papperger'], ()),
    # named equipment / programmes (codes such as F-16 are resolved by pattern)
    ('Patriot', 'equipment', ['پاتریوت'], [r'Patriot', r'PAC-3'], ()),
    ('THAAD', 'equipment', ['تاد'], [r'THAAD'], ()),
    ('HIMARS', 'equipment', ['هایمارس'], [r'HIMARS'], ()),
    ('Typhoon', 'equipment', ['تایفون', 'یوروفایتر'], [r'Typhoons?', r'Eurofighter'], ()),
    ('Rafale', 'equipment', ['رافال'], [r'Rafale'], ()),
    ('Gripen', 'equipment', ['گریپن'], [r'Gripen'], ()),
    ('Black Hawk', 'equipment', ['بلک هاوک'], [r'Black ?Hawks?', r'UH-60'], ()),
    ('Apache', 'equipment', ['آپاچی'], [r'Apaches?', r'AH-64[A-Z]?'], ()),
    ('Abrams', 'equipment', ['آبرامز'], [r'Abrams'], ()),
    ('Leopard', 'equipment', ['لئوپارد'], [r'Leopard'], ()),
    ('Talon Blue', 'equipment', ['تالون بلو'], [r'Talon Blue'], ()),
    ('Barracuda', 'equipment', ['باراکودا'], [r'Barracuda'], ()),
    ('Jaguar', 'equipment', ['جگوار', 'ژاگوار'], [r'Jaguar'], ()),
    ('BladeHAUL', 'equipment', ['بلیدهال'], [r'BladeHAUL'], ()),
    ('Golden Dome', 'equipment', ['گنبد طلایی'], [r'Golden Dome'], ()),
    ('Iron Dome', 'equipment', ['گنبد آهنین'], [r'Iron Dome'], ()),
    ('Hwasong', 'equipment', ['هواسونگ'], [r'Hwasong(?:-\S+)?'], ()),
    ('AMRAAM', 'equipment', ['امرام'], [r'AMRAAM', r'AIM-120'], ()),
    ('F/A-XX', 'equipment', ['اف ای ایکس ایکس'], [r'F/A-XX'], ()),
    ('USS George H.W. Bush', 'equipment', ['جورج بوش', 'ناو جورج بوش'], [r'George H\. ?W\. Bush'], ()),
    ('USS Abraham Lincoln', 'equipment', ['آبراهام لینکلن'], [r'Abraham Lincoln'], ()),
    ('USS Dwight D. Eisenhower', 'equipment', ['آیزنهاور'], [r'(?:Dwight D\. )?Eisenhower'], ()),
    ('USS Gerald R. Ford', 'equipment', ['جرالد فورد'], [r'Gerald R\. Ford'], ()),
    # equipment classes: a generic Persian noun still restricts the answer
    ('fighter', 'class', ['جنگنده'], [r'fighters?', r'jets?', r'F-\d{1,3}[A-Z]{0,2}', r'F/A-\S+', r'Typhoons?', r'Rafale', r'Gripen'], ()),
    ('aircraft', 'class', ['هواپیما', 'هواپیماها', 'هواگرد'], [r'aircraft', r'planes?', r'jets?', r'airframes?', r'[ABCEFKP]-\d{1,3}[A-Z]{0,2}', r'bombers?', r'airliners?'], ()),
    ('helicopter', 'class', ['بالگرد', 'هلیکوپتر', 'هلی کوپتر'], [r'helicopters?', r'Black ?Hawks?', r'Apaches?', r'[AMUC]H-\d{1,3}[A-Z]?', r'NH90', r'AW\d{3}', r'rotorcraft'], ()),
    ('drone', 'class', ['پهپاد', 'پهپادها', 'پهباد'], [r'drones?', r'UAVs?', r'UAS', r'uncrewed', r'unmanned', r'[MR]Q-\d{1,3}[A-Z]?', r'CCAs?', r'Collaborative Combat Aircraft', r'loitering munitions?', r'wingman'], ()),
    ('cruise missile', 'class', ['موشک کروز', 'کروز'], [r'cruise missiles?'], ()),
    ('ballistic missile', 'class', ['موشک بالستیک', 'بالستیک', 'بالیستیک'], [r'ballistic'], ()),
    ('hypersonic', 'class', ['هایپرسونیک', 'فراصوت', 'ابرصوت', 'مافوق صوت'], [r'hypersonic'], ()),
    ('missile', 'class', ['موشک', 'موشکی', 'موشک ها'], [r'missiles?', r'rockets?', r'interceptors?', r'AIM-\d+[A-Z]?', r'SM-\d', r'PAC-3', r'Hwasong\S*', r'Barracuda'], ()),
    ('warship', 'class', ['ناو', 'کشتی', 'ناوچه', 'رزم ناو', 'ناوشکن', 'ناو هواپیمابر', 'هواپیمابر'], [r'ships?', r'vessels?', r'frigates?', r'destroyers?', r'carriers?', r'corvettes?', r'USS', r'HMS', r'warships?'], ()),
    ('submarine', 'class', ['زیردریایی', 'زیر دریایی'], [r'submarines?', r'SSN', r'S-\d{2}'], ()),
    ('tank', 'class', ['تانک'], [r'tanks?', r'Abrams', r'Leopard', r'KF51'], ()),
    ('armoured vehicle', 'class', ['خودرو زرهی', 'خودروی زرهی', 'نفربر'], [r'armou?red vehicles?', r'IFVs?', r'APCs?', r'Jaguar', r'XM-?30'], ()),
    ('ground vehicle', 'class', ['خودرو زمینی', 'خودروی زمینی'], [r'ground vehicles?', r'UGVs?'], ()),
    ('air defence', 'class', ['پدافند', 'پدافند هوایی'], [r'air defen[cs]e', r'missile defen[cs]e', r'Patriot', r'THAAD', r'interceptors?', r'Iron Dome', r'Golden Dome'], ()),
    ('satellite', 'class', ['ماهواره'], [r'satellites?', r'SATCOM'], ()),
    ('pilot', 'class', ['خلبان'], [r'pilots?', r'aircrew'], ()),
    ('base', 'class', ['پایگاه', 'پایگاه هوایی', 'پایگاه نظامی'], [r'bases?', r'air ?bases?', r'AFB', r'RAF [A-Z][a-z]+', r'airfields?'], ()),
    ('seeker', 'class', ['جستجوگر'], [r'seekers?'], ()),
    ('thermal sight', 'class', ['دوربین حرارتی', 'دید حرارتی'], [r'thermal sights?', r'thermal'], ()),
    ('cybersecurity', 'class', ['سایبری', 'امنیت سایبری'], [r'cyber\S*'], ()),
]

# event type → (Persian words, English patterns)
EVENT_TYPES = {
    'crash': (['سقوط', 'سانحه', 'حادثه هوایی'], [r'crash(?:es|ed|ing)?', r'mishaps?', r'went down', r'goes down']),
    'mishap': (['سانحه', 'حادثه'], [r'mishaps?', r'accidents?', r'incidents?', r'crash(?:es|ed)?']),
    'contract': (['قرارداد', 'سفارش', 'معامله'], [r'contracts?', r'deals?', r'orders?', r'ordered', r'award(?:s|ed)?', r'wins?', r'won',
                                                r'secures?', r'inks?', r'nabs?', r'tapped', r'buy(?:s|ing)?', r'purchas\w*', r'procure\w*']),
    'purchase': (['خرید'], [r'buy(?:s|ing)?', r'purchas\w*', r'procure\w*', r'orders?', r'ordered', r'acquir\w*']),
    'delivery': (['تحویل'], [r'deliver(?:s|ed|y|ies|ing)?', r'hand(?:s|ed)? over', r'handover', r'receiv(?:es|ed)']),
    'test': (['آزمایش', 'آزمون', 'تست', 'پرتاب', 'شلیک آزمایشی', 'شلیک'], [r'tests?', r'tested', r'testing', r'trials?', r'launch(?:es|ed)?', r'test-fir\w*', r'fired']),
    'first_flight': (['پرواز نخست', 'نخستین پرواز', 'اولین پرواز', 'پرواز اول'], [r'first flight', r'maiden flight', r'has flown', r'flies for the first time']),
    'exercise': (['رزمایش', 'مانور', 'تمرین'], [r'exercises?', r'drills?', r'war ?games?', r'training']),
    'attack': (['حمله', 'حملات', 'ضربه', 'بمباران'], [r'strikes?', r'struck', r'attacks?', r'attacked', r'air ?strikes?', r'bomb(?:ed|ing|ardment)', r'hits?']),
    'sale': (['فروش'], [r'sales?', r'sells?', r'sold', r'approv(?:e|es|ed|al)', r'clears?', r'cleared']),
    'port_call': (['پهلوگیری', 'ورود به بندر', 'بندر'], [r'port calls?', r'pulls? into', r'arriv(?:es|ed|al)', r'reaches', r'logistics stop']),
    'deployment': (['استقرار', 'اعزام'], [r'deploy(?:s|ed|ment|ments)?']),
    'unveil': (['رونمایی'], [r'unveil(?:s|ed)?', r'debut(?:s|ed)?', r'reveal(?:s|ed)?', r'present(?:s|ed)']),
    'visit': (['بازدید', 'بازرسی'], [r'visit(?:s|ed)?', r'inspect(?:s|ed|ion)?', r'tour(?:s|ed)?']),
    'arrest': (['بازداشت', 'دستگیری'], [r'arrest(?:s|ed)?', r'detain(?:s|ed)?']),
    'casualties': (['کشته', 'زخمی', 'مجروح', 'تلفات', 'مصدوم'], [r'kill(?:s|ed)?', r'dead', r'deaths?', r'injur(?:y|ies|ed)', r'wounded', r'casualt(?:y|ies)']),
    'sanctions': (['تحریم'], [r'sanction(?:s|ed)?']),
    'retirement': (['بازنشستگی', 'کنار گذاشته', 'خروج از خدمت'], [r'retir(?:e|es|ed|ement)', r'era (?:is )?over', r'era comes to a close', r'last \w+ departs', r'decommission\w*']),
    'combat_use': (['استفاده رزمی', 'کاربرد رزمی', 'به کارگیری رزمی'], [r'combat use', r'used in combat', r'combat debut', r'first combat']),
    'election': (['انتخابات'], [r'elections?', r'polls?', r'vote']),
}

# intents of the v1.3 contract
INTENTS = ('specific_record', 'entity_lookup', 'event_evidence', 'common_coverage', 'compare')

_OUT_PREDICTION = re.compile(r'پیش بینی|پیشبینی|آینده|خواهد شد|خواهد کرد|خواهند|احتمال|احتمالا|چه می شود|چه خواهد|سناریو'
                             r'|(?i:forecast|predict|will happen|likely|future|what will)')
_OUT_ANALYSIS = re.compile(r'(?<![آ-ی])چرا(?![آ-ی])|عدم قطعیت|قطعیت|ابهام|نامشخص|مبهم|(?i:uncertain)|انگیزه|قصد|نیت|هدف (?:اصلی )?.{0,30}چیست|تحلیل|ارزیابی|پیامد|تاثیر|تأثیر|به نفع|استراتژی|راهبرد'
                           r'|نتیجه گیری|نتیجه بگیر|توصیه|پیشنهاد|بهتر است|باید چه|موضع .* چیست|مقصر|درست می گوید|راست می گوید'
                           r'|(?i:\bwhy\b|motiv|intent|analy[sz]|implication|impact|strategy|should|recommend|who is right|blame)')
_OUT_RANKING = re.compile(r'مهم ترین|مهمترین|بیشترین|کمترین|بهترین|بدترین|برترین|خطرناک ترین|(?i:most important|biggest|top \d|worst|best)')
_COMPARE = re.compile(r'تفاوت|مقایسه|اختلاف|فرق|متفاوت|تناقض|ناسازگار|(?i:differ|compare|comparison|contrast|discrepan)')
_COMMON = re.compile(r'مشترک|چند منبع|کدام منبع|کدام منابع|چه منابعی|کدام رسانه|چه رسانه|پوشش|بازتاب|منابع مختلف|چند رسانه'
                     r'|(?i:which sources|what sources|which outlets|covered|coverage|in common)')
_LOOKUP = re.compile(r'اخبار مرتبط با|اخبار مربوط به|خبرهای مربوط|اخبار درباره|خبرهای مرتبط|چه خبرهایی|چه اخباری|(?i:news (?:about|on|related)|related to)')
_QUANTITY = re.compile(r'(?<![آ-ی])چند(?![آ-ی])|چه تعداد|تعداد|چقدر|چه مبلغ|مبلغ|ارزش|میزان|(?i:how many|how much|number of|value|amount)')
_RECORD_ID = re.compile(r'(?<![0-9a-f])([0-9a-f]{16,64})(?![0-9a-f])')

# Persian function words and meta words that carry no anchor (they never
# restrict the answer, so they may be ignored safely).
_GENERIC = frozenset('''
از به با در که را این آن برای یا و تا هم چه چی چگونه کدام کدامیک آیا است هست هستند بود بودند شد شده شدند شدن می نمی های ها ای
یک دو سه چند درباره مورد چیست کجا کی بگو بده لطفا اخبار خبر خبرها خبری منابع منبع روایت روایات اطلاعات موجود کافی شواهد سند اسناد
گزارش گزارشی گزارش ها گزارشات داده داده اند داده است کرده کرده اند کردند کرد کند کنند دارد دارند داشته ای اند ام
رسانه رسانه ها رسانه ای پوشش بازتاب مشترک مختلف تفاوت مقایسه اختلاف فرق متفاوت میان بین هر همه برخی دیگر نیز اما ولی
چه چیزی چیزهایی مواردی موارد گفته گفته اند گفت اعلام اعلام شده منتشر منتشرشده نوشته نوشته اند آمده ذکر ذکرشده شده است
رویداد رویدادی رویدادها اتفاق حادثه ای مربوط مرتبط مرتبطی درمورد خصوص باره سامانه سیستم اینجا ثبت ثبت شده
کشور کشورهای شرکت شرکتی سازمان نهاد شخص فرد رئیس مقام مقامات وزیر وزارت دولت نیروهای نیرو جدید اخیر اخیرا گذشته امروز دیروز
هفته ماه روز روزهای ساعت ساعات تاریخ زمان کی کجا کجای چطور چگونه آنچه چیست کیست کسی کسانی جزئیات شرح توضیح وضعیت
تعداد چقدر میزان مبلغ ارزش قیمت عدد اعداد رقم ارقام درصد نفر نفری پیرامون حول راجع رخ رخداد داد دادند افتاد افتاده
مقدار نوع کدامند چیستند هستند بوده بوده اند شود شوند گردید آیا علت دلیل هدف منبعی منابعی خبرگزاری روزنامه سایت نقل قول ادعا ادعای
تایید تأیید رد نشده توسط هنوز بر دلار دلاری یورو میلیارد میلیون هزار نزدیک حوالی اطراف نخستین اولین نخست انتخاب گوید گویند نویسد نوشت می‌گوید چگونه طور شکل همین همان کدامیک دیگری بیان بیانیه طبق براساس اساس پس پیش قبل بعد طی حدود حدودا
the a an of to in on for and or is are was were be been what which who how why when where about any some
news latest today yesterday last past week month hours hour day days report reports reported source sources tell me please
did does do happened happen there their with from by this that these those than then into over under say said
near at after before during against between new first all its it has have had being also both each other more most many much
according cover covered coverage describe described different differ compare common account accounts story stories
event events item items record records outlet outlets media evidence information details detail exactly
'''.split())

_CODE = re.compile(r'(?<![A-Za-z0-9])([A-Z]{1,4}(?:/[A-Z])?-?\d{1,4}[A-Z]{0,3}|F/A-XX|XM-?\d{2})(?![A-Za-z0-9])')
_FA_CODE = re.compile(r'(?<![آ-ی])(اف|بی|سی|ام ?کیو|ای|کی سی|سو|میگ)\s*-?\s*(\d{1,3})')
_FA_CODE_PREFIX = {'اف': 'F', 'بی': 'B', 'سی': 'C', 'امکیو': 'MQ', 'ام کیو': 'MQ', 'ای': 'E', 'کی سی': 'KC', 'سو': 'Su', 'میگ': 'MiG'}


def _generic_fa(w):
    if w in _GENERIC or re.fullmatch(r'(?:می|نمی)\S*|\S*(?:اند|ایم|اید|است)', w):
        return True
    for suf in ('های', 'ها', 'ای', 'ی', 'ان'):
        if w.endswith(suf) and len(w) - len(suf) >= 2 and w[: -len(suf)] in _GENERIC:
            return True
    return False


def _en_regex(patterns):
    """Word-bounded alternation; all-caps fragments case-sensitive."""
    parts = []
    for p in patterns:
        caps = re.fullmatch(r'[A-Z0-9\\.?\-/\[\]{}(),]+', p) is not None and any(ch.isalpha() for ch in p)
        parts.append(p if caps else f'(?i:{p})')
    return re.compile(r'(?<![A-Za-z0-9])(?:' + '|'.join(parts) + r')(?![A-Za-z0-9])')


@dataclass
class Anchor:
    canonical: str
    kind: str
    regex: re.Pattern
    parents: tuple = ()
    source: str = ''      # the question text that produced it

    def found(self, text):
        return bool(self.regex.search(text or ''))


_ENTITY_ANCHORS = [Anchor(c, k, _en_regex(en), tuple(par)) for c, k, fa, en, par in ENTITIES]
_BY_CANON = {a.canonical: a for a in _ENTITY_ANCHORS}
_EVENT_REGEX = {t: _en_regex(en) for t, (fa, en) in EVENT_TYPES.items()}

# Persian alias → canonical, longest first (so «نیروی دریایی آمریکا» wins over «آمریکا»)
_FA_ALIASES = sorted(((norm_fa(fa), c) for c, k, fas, en, par in ENTITIES for fa in fas), key=lambda x: -len(x[0]))
_FA_EVENTS = sorted(((norm_fa(fa), t) for t, (fas, en) in EVENT_TYPES.items() for fa in fas), key=lambda x: -len(x[0]))


def _code_anchor(code, source=''):
    code = code.upper().replace('–', '-')
    m = re.fullmatch(r'([A-Z/]{1,5})-?(\d{1,4})([A-Z]{0,3})', code)
    if m:
        pat = re.escape(m.group(1)) + r'-?' + m.group(2) + (re.escape(m.group(3)) if m.group(3) else r'[A-Z]{0,2}')
        canonical = f'{m.group(1)}-{m.group(2)}{m.group(3)}'
    else:
        pat, canonical = re.escape(code), code
    return Anchor(canonical, 'code', re.compile(r'(?<![A-Za-z0-9])' + pat + r'(?![A-Za-z0-9])'), (), source)


@dataclass
class Plan:
    question: str
    intent: str = 'event_evidence'
    out_of_contract: str | None = None
    anchors: list = field(default_factory=list)
    event_types: list = field(default_factory=list)
    unresolved: list = field(default_factory=list)
    quantity: bool = False
    record_ids: list = field(default_factory=list)
    since: datetime | None = None
    window: str | None = None

    def view(self):
        return {'intent': self.intent, 'out_of_contract': self.out_of_contract,
                'anchors': [{'canonical': a.canonical, 'kind': a.kind, 'from': a.source} for a in self.anchors],
                'event_types': self.event_types, 'unresolved': self.unresolved, 'quantity': self.quantity,
                'record_ids': self.record_ids, 'window': self.window,
                'lexicon_version': LEXICON_VERSION, 'relevance_version': RELEVANCE_VERSION}


def _window(qn, now):
    if re.search(r'امروز|(?i:today)', qn):
        return now - timedelta(hours=24), '24h'
    if re.search(r'(?:24) ساعت|(?i:24 hours?)', qn):
        return now - timedelta(hours=24), '24h'
    if re.search(r'دیروز|(?i:yesterday)', qn):
        return now - timedelta(hours=48), '48h'
    if re.search(r'هفته|(?i:week)', qn):
        return now - timedelta(days=7), '7d'
    if re.search(r'(?<![آ-ی])ماه(?![آ-ی])|(?i:month)', qn):
        return now - timedelta(days=30), '30d'
    return None, None


def analyse(question, now=None):
    """Question → Plan. Pure; deterministic."""
    now = now or datetime.now(timezone.utc)
    raw = (question or '')[:1000]
    plan = Plan(question=raw)
    qn = norm_fa(raw)
    plan.since, plan.window = _window(qn, now)
    plan.quantity = bool(_QUANTITY.search(qn))
    plan.record_ids = list(dict.fromkeys(_RECORD_ID.findall(raw.lower())))

    if _OUT_PREDICTION.search(qn):
        plan.out_of_contract = 'prediction'
    elif _OUT_ANALYSIS.search(qn):
        plan.out_of_contract = 'analysis'
    elif _OUT_RANKING.search(qn):
        plan.out_of_contract = 'ranking'

    rest = ' ' + qn + ' '
    seen = set()
    raw_d = raw.translate(_FA_NORM)

    # record ids
    for rid in plan.record_ids:
        rest = re.sub(re.escape(rid), ' ', rest, flags=re.I)
    # Latin codes (F-16, PAC-3 …) — before entity aliases so «F-35» is one anchor
    for m in _CODE.finditer(raw_d):
        code = m.group(1)
        named = [a for a in _ENTITY_ANCHORS if a.kind == 'equipment' and a.found(code)]
        a = Anchor(named[0].canonical, named[0].kind, named[0].regex, named[0].parents, code) if named else _code_anchor(code, code)
        if a.canonical not in seen:
            seen.add(a.canonical); plan.anchors.append(a)
        rest = re.sub(r'(?<![A-Za-z0-9])' + re.escape(code) + r'(?![A-Za-z0-9])', ' ', rest)
    for m in _FA_CODE.finditer(qn):
        prefix = _FA_CODE_PREFIX.get(m.group(1).replace(' ', ''), _FA_CODE_PREFIX.get(m.group(1)))
        if prefix:
            a = _code_anchor(f'{prefix}-{m.group(2)}', m.group(0))
            if a.canonical not in seen:
                seen.add(a.canonical); plan.anchors.append(a)
            rest = rest.replace(m.group(0), ' ')
    # Persian entity aliases (longest first)
    for fa, canon in _FA_ALIASES:
        rx = re.compile(r'(?<![' + _FA_LETTER + r'])' + re.escape(fa) + _FA_SUFFIX + r'(?![' + _FA_LETTER + r'])')
        if rx.search(rest):
            base = _BY_CANON[canon]
            if canon not in seen:
                seen.add(canon); plan.anchors.append(Anchor(base.canonical, base.kind, base.regex, base.parents, fa))
            rest = rx.sub(' ', rest)
    # Persian event words
    for fa, etype in _FA_EVENTS:
        rx = re.compile(r'(?<![' + _FA_LETTER + r'])' + re.escape(fa) + _FA_SUFFIX + r'(?![' + _FA_LETTER + r'])')
        if rx.search(rest):
            if etype not in plan.event_types:
                plan.event_types.append(etype)
            rest = rx.sub(' ', rest)
    # English words: entity patterns, event patterns, capitalised unknown names
    for m in re.finditer(r'[A-Za-z][A-Za-z\'\-\.]*(?: [A-Z][A-Za-z\'\-\.]*)*', rest):
        phrase = m.group(0).strip(" .'-")
        if not phrase:
            continue
        hit = False
        for a in _ENTITY_ANCHORS:
            if a.found(phrase):
                hit = True
                if a.canonical not in seen:
                    seen.add(a.canonical); plan.anchors.append(Anchor(a.canonical, a.kind, a.regex, a.parents, phrase))
        for etype, rx in _EVENT_REGEX.items():
            if rx.search(phrase):
                hit = True
                if etype not in plan.event_types:
                    plan.event_types.append(etype)
        words = [w for w in re.findall(r"[A-Za-z][A-Za-z'\-]+", phrase) if w.lower() not in _GENERIC]
        if not hit and words and any(w[0].isupper() for w in words):
            # an unknown capitalised name: an exact anchor on its own spelling
            name = ' '.join(words)
            if name.lower() not in seen:
                seen.add(name.lower())
                plan.anchors.append(Anchor(name, 'name', re.compile(r'(?<![A-Za-z0-9])' + re.escape(name) + r'(?![A-Za-z0-9])', re.I), (), name))
        elif not hit:
            plan.unresolved.extend(w for w in words if len(w) > 2)
        rest = rest.replace(m.group(0), ' ')
    # whatever Persian is left must be generic, otherwise it is unresolved
    for w in re.findall(r'[' + _FA_LETTER + r']{2,}', rest):
        if not _generic_fa(w):
            plan.unresolved.append(w)
    plan.unresolved = list(dict.fromkeys(plan.unresolved))

    if plan.record_ids:
        plan.intent = 'specific_record'
    elif _COMPARE.search(qn):
        plan.intent = 'compare'
    elif _COMMON.search(qn):
        plan.intent = 'common_coverage'
    elif _LOOKUP.search(qn) or (plan.anchors and not plan.event_types):
        plan.intent = 'entity_lookup'
    else:
        plan.intent = 'event_evidence'
    return plan


def precheck(plan):
    """Reason to refuse before any retrieval or model call, or None."""
    if plan.out_of_contract:
        return f'out_of_contract_{plan.out_of_contract}'
    if plan.unresolved:
        return 'unresolved_terms'
    if plan.intent == 'specific_record':
        return None
    if plan.intent == 'common_coverage' and not plan.anchors and not plan.event_types:
        return None  # overview of verified multi-source events
    if not plan.anchors:
        return 'no_anchor'
    return None


# --------------------------------------------------------------------------- record relevance
def _text(r):
    return f"{r.get('title_original') or r.get('title') or ''} \n {r.get('excerpt') or ''}"


def _parse_dt(v):
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(str(v).replace('Z', '+00:00'))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def record_relevance(plan, record):
    """(ok, reasons). Every anchor and (if any) one of the question's event
    types must occur in the original title/excerpt; the date must be in the
    window."""
    text = _text(record)
    missing = [a.canonical for a in plan.anchors if not a.found(text)]
    reasons = {'missing_anchors': missing}
    if plan.event_types:
        hit = [t for t in plan.event_types if _EVENT_REGEX[t].search(text)]
        reasons['event_types_found'] = hit
        if not hit:
            reasons['missing_event_type'] = plan.event_types
    if plan.since:
        d = _parse_dt(record.get('published_at'))
        if d is None or d < plan.since:
            reasons['outside_window'] = True
    ok = not missing and not reasons.get('missing_event_type') and not reasons.get('outside_window')
    return ok, reasons


def quote_relevant(plan, quote):
    if any(a.found(quote) for a in plan.anchors):
        return True
    return any(_EVENT_REGEX[t].search(quote) for t in plan.event_types)


# --------------------------------------------------------------------------- same-event verification
def entities_in(text):
    out = {a.canonical for a in _ENTITY_ANCHORS if a.kind != 'class' and a.found(text)}
    out |= {_code_anchor(m.group(1)).canonical for m in _CODE.finditer(text or '')}
    return out


def places_in(text):
    ps = set()
    for a in _ENTITY_ANCHORS:
        if a.kind == 'place' and a.found(text):
            ps.add(a.canonical)
            ps.update(a.parents)
    return ps


def event_types_in(text):
    return {t for t, rx in _EVENT_REGEX.items() if rx.search(text or '')}


def same_event(a, b, plan=None):
    """(ok, reasons). All conditions must hold; see module docstring."""
    ta, tb = _text(a), _text(b)
    r = {}
    r['same_cluster'] = bool(a.get('event_id')) and a.get('event_id') == b.get('event_id')
    da, db = _parse_dt(a.get('published_at')), _parse_dt(b.get('published_at'))
    r['hours_apart'] = round(abs((da - db).total_seconds()) / 3600, 1) if da and db else None
    r['time_ok'] = r['hours_apart'] is not None and r['hours_apart'] <= MAX_EVENT_HOURS
    ea, eb = event_types_in(ta), event_types_in(tb)
    want = set(plan.event_types) if plan and plan.event_types else None
    r['shared_event_types'] = sorted((ea & eb) & want if want else ea & eb)
    r['event_type_ok'] = bool(r['shared_event_types'])
    shared = entities_in(ta) & entities_in(tb)
    countries = {c for c, k, *_ in ENTITIES if k == 'country'}
    r['shared_entities'] = sorted(shared)
    r['entities_ok'] = len(shared) >= 2 and bool(shared - countries)
    pa, pb = places_in(ta), places_in(tb)
    r['place_conflict'] = bool(pa) and bool(pb) and not (pa & pb)
    ok = r['same_cluster'] and r['time_ok'] and r['event_type_ok'] and r['entities_ok'] and not r['place_conflict']
    return ok, r


def verified_groups(records, plan=None):
    """Complete-linkage groups of records that are pairwise the same event.
    Returns [{'members': [records], 'pairs': [...]}] with ≥ 2 members, most
    members first, then most recent."""
    groups = []
    for rec in records:
        placed = False
        for g in groups:
            checks = [same_event(rec, m, plan) for m in g['members']]
            if all(ok for ok, _ in checks):
                g['members'].append(rec)
                g['pairs'].extend({'a': rec['evidence_id'], 'b': m['evidence_id'], **why}
                                  for m, (ok, why) in zip(g['members'][:-1], checks))
                placed = True
                break
        if not placed:
            groups.append({'members': [rec], 'pairs': []})
    multi = [g for g in groups if len(g['members']) >= 2]
    multi.sort(key=lambda g: (-len(g['members']), -max((_parse_dt(m.get('published_at')) or datetime.min.replace(tzinfo=timezone.utc)).timestamp() for m in g['members'])))
    return multi


def republished(a, b):
    """Syndicated copy: same canonical URL, same normalised title, or same excerpt."""
    n = lambda s: re.sub(r'\W+', ' ', (s or '').lower()).strip()
    if a.get('canonical_url') and a.get('canonical_url', '').rstrip('/').lower() == (b.get('canonical_url') or '').rstrip('/').lower():
        return True
    if n(a.get('title_original') or a.get('title')) and n(a.get('title_original') or a.get('title')) == n(b.get('title_original') or b.get('title')):
        return True
    return bool(n(a.get('excerpt'))) and len(n(a.get('excerpt'))) > 40 and n(a.get('excerpt')) == n(b.get('excerpt'))


# --------------------------------------------------------------------------- conflicts
_NUM = re.compile(r'(?<![A-Za-z0-9\-])[$€£]?\d[\d,]*(?:\.\d+)?(?:\s?(?:%|percent|billion|million|bn|[BM])(?![A-Za-z]))?')
_DENIAL = re.compile(r'(?i)\b(?:den(?:y|ies|ied)|refut\w*|dismiss(?:ed|es)? (?:the )?(?:report|claim)s?|false (?:report|claim)s?|not true|fabricat\w*|reject(?:s|ed)? (?:the )?(?:report|claim)s?)\b')
_YEAR = re.compile(r'^(?:19|20)\d{2}$')


def numbers_in(quote):
    out = []
    for m in _NUM.finditer(quote or ''):
        tok = m.group(0).strip()
        if _YEAR.match(tok):
            continue
        out.append(tok)
    return out


def _num_value(tok):
    t = tok.lower().replace(',', '').replace('$', '').replace('€', '').replace('£', '')
    mult = 1
    for suf, k in (('billion', 1e9), ('bn', 1e9), ('b', 1e9), ('million', 1e6), ('m', 1e6), ('percent', 1), ('%', 1)):
        if t.endswith(suf):
            mult, t = k, t[: -len(suf)].strip()
            break
    try:
        return float(t) * mult
    except ValueError:
        return None


def conflicts(facts, records_by_id):
    """Conflicting quantities or a denial across different sources."""
    by_source = {}
    for f in facts:
        r = records_by_id[f['evidence_id']]
        vals = {v for v in (_num_value(t) for t in numbers_in(f['quote'])) if v is not None}
        by_source.setdefault(r.get('source_name') or r['evidence_id'], set()).update(vals)
    sets = [v for v in by_source.values() if v]
    numeric = len(sets) >= 2 and any(s != sets[0] for s in sets[1:])
    denial = len(by_source) >= 2 and any(_DENIAL.search(f['quote']) for f in facts)
    return {'numbers_differ': numeric, 'denial': denial, 'numbers_by_source': {k: sorted(v) for k, v in by_source.items()}}


# money questions: conflicts are checked on the full original text of every
# record of the event, not only on the quotes the model happened to choose
_MONEY_Q = re.compile(r'مبلغ|ارزش|قیمت|دلار|یورو|هزینه|بودجه|(?i:value|worth|cost|price|dollar|budget|\$)')
_MONEY = re.compile(r'(?:[$€£]\s?\d[\d,]*(?:\.\d+)?\s?(?:billion|million|bn|[BM])?|\d[\d,]*(?:\.\d+)?\s?(?:billion|million)\s?(?:dollars|euros|USD|EUR)?)(?![A-Za-z])')


def money_question(plan):
    return plan.quantity and bool(_MONEY_Q.search(norm_fa(plan.question)))


def money_in(text):
    return {v for v in (_num_value(m.group(0).replace(' ', '')) for m in _MONEY.finditer(text or '')) if v}


def money_conflict(records):
    by_source = {}
    for r in records:
        by_source.setdefault(r.get('source_name'), set()).update(money_in(_text(r)))
    sets = [s for s in by_source.values() if s]
    return {'money_by_source': {k: sorted(v) for k, v in by_source.items()},
            'money_differ': len(sets) >= 2 and any(not (s & sets[0]) for s in sets[1:])}

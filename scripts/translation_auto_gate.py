"""Automated multi-layer gate for translation evaluation (phase 9).

PRE-REGISTERED: written, calibrated on TranslateGemma 12B outputs, and
frozen (commit + sha256) BEFORE TranslateGemma 27B was downloaded, so no rule
can be fitted to 27B output. The quality bar is unchanged from the 27B
readiness report: ZERO critical errors over 123 fields. Human review is
removed by owner decision; uncertainty is never counted as success.

Layers per item:
  1. validator translation-validator-v2.1.0 (inside the pipeline)
  2. QC translation-qc-v1.0.1 (deterministic source/output controls)
  3. key-fact checks below (per item, fixed in advance):
       ('num', [values])      every value must appear in the output
       ('req', name, regex)   an accepted rendering must appear
       ('forbid', name, regex) a known critical error pattern must NOT appear

Item status:
  FAIL        high-confidence critical error: a forbid pattern matched, a
              required number is missing, a hard validator flag, or a
              high-confidence QC class (see HIGH_QC)
  VERIFIED    every req matched, every number present, no flag of any layer
  UNVERIFIED  no FAIL, but a req not matched or a soft flag present
Gate:
  AUTO_GATE_FAIL     any FAIL item, or a technical criterion breached
  AUTO_GATE_PASS     all 123 items VERIFIED and all technical criteria met
  INCONCLUSIVE       otherwise (never counted as a pass)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'apps' / 'api'))
import translation_qc as qc  # noqa: E402

GATE_VERSION = 'translation-auto-gate-v1.0.0'

# Calibration (12B, before 27B existed): validator number_mismatch / date_mismatch
# are SOFT — v2.1.0 has a documented ordinal false positive ("3rd" → «سوم»);
# numbers are checked independently by key facts (num) and QC. Soft flags still
# block VERIFIED, so this cannot make a PASS easier.
HARD_VALIDATOR = {'placeholder_missing', 'placeholder_residue', 'placeholder_duplicated', 'stray_markup', 'empty_output',
                  'identical_to_source', 'not_persian', 'foreign_script'}
HIGH_QC_PREFIX = ('placeholder_text', 'month_untranslated', 'number_missing', 'unit_missing', 'echelon_added', 'role_added',
                  'entity_added', 'number_relabelled_as_model', 'empty_output')
HIGH_QC_WORDS = {'unsupported_word:ویکی پدیا', 'unsupported_word:اعتصاب', 'unsupported_word:شبیه سازی', 'unsupported_word:وبگاه'}

_D = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩٫٬يكأإۀة', '0123456789012345678 9.,یکااهه'.replace(' ', ''))


def norm(t):
    t = (t or '').translate(_D).replace('‌', ' ').replace('ـ', '')
    t = re.sub('[ً-ْ]', '', t)  # diacritics
    return re.sub(r'\s+', ' ', t)


N, R, F = 'num', 'req', 'forbid'
DEV = {
    'simple_title:title': [(R, 'navy', r'نیروی دریایی'), (R, 'frigate', r'ناوچه|فریگیت|فرگات'),
                           (R, 'commission', r'به خدمت|وارد خدمت|ملحق|اضافه|به کار|راه اندازی'), (F, 'wrong_sense', r'فرمانده|خرید|هواپیما')],
    'multi_sentence_summary:title': [(R, 'army', r'ارتش'), (R, 'exercise', r'رزمایش|تمرین|مانور'), (R, 'winter', r'زمستان')],
    'multi_sentence_summary:summary': [(R, 'sunday', r'یکشنبه'), (R, 'brigade', r'تیپ'), (F, 'echelon', r'گردان|لشکر|گروهان'),
                                       (R, 'logistics', r'لجستیک|تدارکات|پشتیبانی'), (R, 'cold', r'سرما|سرد')],
    'quotation:text': [(R, 'minister', r'وزیر'), (F, 'president', r'(رئیس|رییس) ?جمهور'), (R, 'negation', r'نخواهیم|نمی ?پذیریم|قبول نمی|نپذیر'),
                       (R, 'delay', r'تاخیر|تأخیر')],
    'person_names:text': [(R, 'austin', r'آستین'), (R, 'gallant', r'گالانت|گالنت'), (R, 'washington', r'واشنگتن'), (R, 'tuesday', r'سه ?شنبه'),
                          (F, 'added_title', r'وزیر|رئیس|رییس|ژنرال')],
    'organizations:text': [(R, 'lockheed', r'لاکهید|لاکید'), (R, 'rafael', r'رافائل'), (R, 'cooperation', r'همکاری'), (F, 'name_as_description', r'متخصص|تخصص')],
    'places:text': [(R, 'convoy', r'کاروان'), (R, 'kharkiv', r'خارکیف|خارکف|خارکیو'), (R, 'izium', r'ایزیوم|ایزیم'), (R, 'donets', r'دونتس')],
    'military_term:text': [(R, 'brigade', r'تیپ'), (F, 'echelon_or_simulated', r'گردان|لشکر|شبیه'), (R, 'live_fire', r'(شلیک|آتش|تیر)\S* (واقعی|جنگی|زنده)'),
                           (R, 'cas', r'پشتیبانی (هوایی|نزدیک)')],
    'acronyms:text': [(R, t, re.escape(t)) for t in ('OSINT', 'IMINT', 'GEOINT', 'ELINT', 'NATO', 'CENTCOM')],
    'date:text': [(N, [12, 18, 2026]), (R, 'march', r'مارس'), (F, 'bracket', r'\[')],
    'time:text': [(R, 'time', r'0?3:45'), (F, 'station', r'ایستگاه')],
    'percent:text': [(N, [12]), (R, 'percent', r'%|درصد')],
    'decimal:text': [(N, [2.75]), (R, 'billion', r'میلیارد'), (F, 'stray_latin', r'2\.75 ?[a-zA-Z]')],
    'coordinates:text': [(R, 'lat', r'34\.5521'), (R, 'lon', r'69\.2075')],
    'equipment_codes:text': [(R, t, re.escape(t)) for t in ('MQ-9B', 'F-35A', 'S-400')],
    'url:text': [(R, 'url', re.escape('https://www.defense.gov/News/Releases/Release/Article/3712345/'))],
    'mention:text': [(R, 'mention', r'@IntelCrab'), (R, 'strike', r'حمله|ضربه'), (F, 'labour_or_org', r'اعتصاب|سازمان')],
    'hashtags:text': [(R, 'tags', r'#Iran #Protests'), (R, 'third', r'سوم')],
    'emoji:text': [(R, 'sirens', r'آژیر')],
    'multilingual:text': [(R, 'quote', r'پیروزی نزدیک است'), (R, 'tehran', r'تهران'), (R, 'parade', r'رژه')],
    'uncertain_claim:text': [(R, 'unconfirmed', r'تایید ?نشده|تأیید ?نشده|غیر ?رسمی'), (R, 'may', r'ممکن|احتمال|شاید'), (R, 'damage', r'آسیب|خسارت')],
    'attributed_claim:text': [(R, 'reuters', r'رویترز'), (R, 'two_officials', r'(دو|2) مقام'), (R, 'could', r'ممکن|احتمال|می ?تواند'),
                              (R, 'next_week', r'هفته (آینده|بعد)')],
    'negation:text': [(R, 'denied', r'رد کرد|تکذیب|انکار'), (R, 'aircraft', r'هواپیما|طیاره')],
    'title_summary_numbers:title': [(N, [96]), (R, 'poland', r'لهستان'), (R, 'apache', r'آپاچی|Apache'), (F, 'model_96', r'مدل ?96'),
                                    (R, 'count', r'96 (فروند )?(بالگرد|هلیکوپتر)|(بالگرد|هلیکوپتر)\S* (آپاچی )?96')],
    'title_summary_numbers:summary': [(N, [10, 96, 2028, 21, 2023]), (R, 'ah64e', r'AH-64E'), (R, 'billion', r'میلیارد'), (R, 'august', r'اوت|آگوست|اگوست')],
    'term_brigade:text': [(R, 'brigade', r'تیپ'), (F, 'echelon', r'گردان|لشکر'), (R, 'third', r'سوم|3'), (R, 'armored', r'زرهی'), (R, 'monday', r'دوشنبه')],
    'term_convoy:text': [(N, [40]), (R, 'convoy', r'کاروان'), (R, 'border', r'مرز'), (R, 'night', r'شب')],
    'term_launch:text': [(R, 'radar', r'رادار'), (R, 'launch', r'پرتاب'), (R, 'ballistic', r'بالستیک|بالیستیک'), (R, 'coast', r'ساحل')],
    'term_commission:text': [(R, 'frigate', r'ناوچه|فریگیت|فرگات'), (F, 'wrong_sense', r'خرید|هواپیما|آمریکا'), (R, 'two', r'دو|2'), (R, 'next_year', r'سال (آینده|بعد)')],
    'term_frigate:text': [(R, 'frigate', r'ناوچه|فریگیت|فرگات'), (R, 'tanker', r'نفتکش|تانکر'), (R, 'strait', r'تنگه'), (R, 'escort', r'اسکورت|همراهی|محافظت|حفاظت')],
    'term_missile:text': [(R, 'cruise', r'موشک کروز'), (R, 'depot', r'(انبار|مخزن) سوخت'), (R, 'port', r'بندر')],
    'term_deployment:text': [(N, [2000]), (R, 'deployment', r'استقرار|اعزام'), (R, 'week', r'هفته')],
    'term_strike_depot:text': [(R, 'drone', r'پهپاد'), (R, 'ammo_depot', r'انبار مهمات'), (R, 'border', r'مرز'), (F, 'labour', r'اعتصاب')],
    'names_companies:text': [(R, 'rheinmetall', r'راینمتال|Rheinmetall'), (R, 'ceo', r'مدیرعامل|مدیر ?عامل|مدیر اجرایی'), (R, 'papperger', r'پاپرگر|Papperger'),
                             (R, 'saab', r'ساب|Saab'), (R, 'stockholm', r'استکهلم'), (R, 'thursday', r'پنج ?شنبه'), (F, 'latin_residue', r'CEO')],
    'money_amount:text': [(N, [1.2, 48]), (R, 'billion', r'میلیارد'), (F, 'bracket', r'\[')],
}
P7 = {
    'H01': [(N, [3.5, 2027]), (R, 'level_to', r'به 3\.5'), (R, 'gdp', r'تولید ناخالص|GDP'), (F, 'by', r'(به میزان|به اندازه) 3\.5'),
            (R, 'estonia', r'استونی'), (R, 'pm', r'نخست ?وزیر'), (R, 'wednesday', r'چهارشنبه')],
    'H02': [(N, [14]), (R, 'november', r'نوامبر'), (R, 'paris', r'پاریس'), (F, 'bracket', r'\[')],
    'H03': [(N, [45]), (R, 'nineteenth', r'نوزدهم|19'), (F, 'company_or_90', r'شرکت 45|نود')],
    'H04': [(N, [4.2, 87.6]), (R, 'barrel', r'بشکه')],
    'H05': [(N, [82, 1500, 48]), (R, 'division', r'لشکر'), (F, 'battalion', r'گردان'), (R, 'paratroopers', r'چترباز')],
    'H06': [(R, 'battalion', r'گردان'), (F, 'echelon', r'تیپ|لشکر|دسته|گروهان'), (R, 'marines', r'تفنگدار'), (R, 'amphibious', r'آبی ?-?خاکی|دوزیست')],
    'H07': [(N, [3]), (R, 'destroyer', r'ناوشکن'), (F, 'ship_type', r'ناوچه|کشتیرانی'), (R, 'shot_down', r'سرنگون|ساقط|منهدم'), (R, 'red_sea', r'دریای سرخ'),
            (R, 'saturday', r'شنبه')],
    'H08': [(N, [30]), (R, 'batteries', r'(دو|2) (آتشبار|آتش بار|باتری)'), (F, 'battalion', r'گردان'), (R, 'live_fire', r'(شلیک|آتش|تیر)\S* (واقعی|جنگی|زنده)')],
    'H09': [(N, [2027]), (R, 'corvette', r'ناوچه|کوروت'), (R, 'march', r'مارس'), (R, 'indonesia', r'اندونزی')],
    'H10': [(N, [4]), (R, 'hamburg', r'هامبورگ'), (R, 'synagogue', r'کنیسه'), (R, 'arrested', r'دستگیر|بازداشت')],
    'H11': [(R, 'spokesman', r'سخنگو'), (R, 'interior', r'وزارت کشور'), (R, 'denied', r'رد کرد|تکذیب'), (R, 'border', r'مرز')],
    'H12': [(N, [12]), (R, 'claimed', r'ادعا|مدعی'), (R, 'no_evidence', r'بدون ارائه|بی آنکه'), (F, 'organisation', r'سازمان')],
    'H13': [(R, 'unclear', r'(مشخص|روشن) نیست'), (R, 'missile', r'موشک'), (R, 'accident', r'حادثه|سانحه|تصادف')],
    'H14': [(N, [200, 11]), (R, 'microsoft', r'مایکروسافت')],
    'H15': [(N, [300, 450]), (R, 'km', r'کیلومتر')],
    'H16': [(N, [2.1, 6]), (R, 'euro', r'یورو'), (R, 'billion', r'میلیارد'), (R, 'a400m', r'A400M'), (R, 'airbus', r'ایرباس')],
    'H17': [(R, 'ceo', r'مدیرعامل|مدیر ?عامل|مدیر اجرایی'), (R, 'bae', r'BAE|بی ای ای'), (R, 'q2', r'فصل دوم|سه ماهه دوم'),
            (R, 'woodburn', r'وودبرن|ودبرن|Woodburn')],
    'H18': [(N, [95, 70, 29]), (R, 'billion', r'میلیارد'), (R, 'senate', r'سنا')],
    'H19': [(R, 'ambassador', r'سفیر'), (R, 'name', r'توماس|گرینفیلد'), (R, 'unsc', r'شورای امنیت'), (R, 'resolution', r'قطعنامه')],
    'H20': [(R, 'general', r'ژنرال'), (R, 'cavoli', r'کاوولی|کاولی|Cavoli'), (R, 'russia', r'روسیه'), (R, 'faster', r'سریع|سرعت')],
    'H21': [(R, 'f16', r'F-16'), (R, 'il20', r'Il-20'), (R, 'recon', r'شناسایی'), (R, 'intercept', r'رهگیری'), (F, 'wrong_sense', r'بازجویی|دستگیر')],
    'H22': [(N, [3]), (R, 'brigade', r'تیپ'), (F, 'echelon', r'گردان|لشکر|گروه'), (R, 'withdrew', r'عقب ?نشینی')],
    'H23': [(N, [7]), (R, 'convoy', r'کاروان'), (R, 'ambush', r'کمین'), (R, 'gao', r'گائو|گاو'), (R, 'menaka', r'مناکا|منکا')],
    'H24': [(N, [55]), (R, 'billion', r'میلیارد'), (R, 'cubic', r'متر مکعب')],
    'H25': [(N, [3, 2026]), (R, 'january', r'ژانویه'), (R, 'mobilisation', r'بسیج'), (F, 'bracket', r'\[')],
    'H26': [(R, 'minister', r'وزیر'), (R, 'will_not', r'نخواهند|ترک نمی'), (R, 'mission', r'ماموریت|مأموریت')],
    'H27': [(R, 'test', r'آزمایش|آزمایشی|تست'), (R, 'submarine', r'زیر ?دریایی'), (R, 'hypersonic', r'هایپرسونیک|فراصوت|ابرصوت|مافوق صوت|هیپرسونیک'),
            (R, 'first_time', r'(اولین|نخستین) بار')],
    'H28': [(N, [40, 25]), (R, 'at_least', r'حداقل|دست ?کم'), (R, 'last_month', r'ماه گذشته'), (F, 'months_ago', r'25 ماه')],
    'H29': [(R, 'drone', r'پهپاد'), (R, 'no_casualties', r'هیچ تلفات|تلفاتی (نداشت|برجای نگذاشت|بر جای نگذاشت|نشد)|بدون تلفات'), (R, 'depot', r'انبار')],
    'H30': [(R, 'time', r'23:30'), (R, 'geneva', r'ژنو'), (R, 'no_agreement', r'(بدون|بی) (حصول )?(به )?توافق')],
    'H31': [(N, [24]), (R, 'k9', r'K9'), (R, 'poland', r'لهستان'), (R, 'hanwha', r'هانوا|Hanwha'), (F, 'garbled', r'24 و K9|هواپیمای هانوا')],
    'H32': [(R, 'kyiv_independent', r'(کی ?یف|کییف) ?ایندپندنت|Kyiv Independent'), (R, 'ammo_depot', r'انبار مهمات'), (R, 'toropets', r'توروپتس')],
    'H33': [(R, 'simulated', r'شبیه ?سازی'), (R, 'exercise', r'تمرین|رزمایش'), (R, 'naval_base', r'پایگاه دریایی')],
    'H34': [(R, 'chancellor', r'صدراعظم|صدر اعظم'), (R, 'merz', r'مرتس|مرز'), (R, 'taurus', r'تاوروس|توروس|Taurus'), (R, 'ukraine', r'اوکراین'),
            (F, 'wrong_role', r'حزب|دموکرات مسیحی')],
    'H35': [(N, [1.4]), (R, 'million', r'میلیون'), (R, 'treasury', r'خزانه ?داری'), (R, 'froze', r'مسدود|توقیف|بلوکه|منجمد')],
    'H36': [(R, 'frigate', r'ناوچه|فریگیت|فرگات'), (R, 'two_warships', r'(دو|2) (فروند )?(کشتی|ناو)'), (R, 'channel', r'کانال (مانش|انگلیس)'),
            (R, 'shadowed', r'تعقیب|زیر نظر|همراهی|سایه')],
    'H37': [(N, [471]), (R, 'hostage', r'گروگان'), (F, 'few_days', r'چند روز')],
    'H38': [(N, [18]), (R, 'regiment', r'هنگ'), (F, 'echelon_or_company', r'گردان|تیپ|لشکر|شرکت 18'), (R, 'leopard', r'لئوپارد|Leopard'), (R, '2a8', r'2A8'),
            (R, 'friday', r'جمعه')],
    'H39': [(R, 'time', r'06:12'), (R, 'falcon9', r'(فالکون|Falcon) ?9'), (R, 'vandenberg', r'وندنبرگ|واندنبرگ|Vandenberg'), (F, 'commentary', r'\(')],
    'H40': [(R, 'not_confirm', r'(تایید|تأیید) (نکردند|نکرد|ننمودند)'), (R, 'casualties', r'تلفات')],
}
P8 = {
    'A01': [(N, [7.2]), (R, 'level_to', r'به 7\.2'), (F, 'by', r'(به میزان|به اندازه|معادل) 7\.2'), (R, 'september', r'سپتامبر')],
    'A02': [(N, [0.4]), (R, 'points', r'0\.4 واحد درصد'), (F, 'percent_not_points', r'0\.4 ?(%|درصد)'), (F, 'level_to', r'به 0\.4 ?(%|درصد|واحد)? ?(رسید|رسیده)'),
            (R, 'september', r'سپتامبر')],
    'A03': [(N, [80000]), (R, 'level_to', r'به 80,?000'), (F, 'by', r'(به میزان|به اندازه) 80,?000')],
    'A04': [(N, [1.1]), (R, 'third', r'یک ?سوم|33'), (R, 'level_to', r'به 1\.1 میلیون'), (F, 'by', r'(به میزان|به اندازه) 1\.1')],
    'A05': [(N, [9.1, 6.5]), (R, 'from_to', r'از (سطح |میزان )?9\.1.*به (سطح |میزان )?6\.5'), (F, 'swapped', r'از 6\.5.*به 9\.1')],
    'A06': [(N, [12, 886]), (R, 'level_to', r'به \$?886|886 میلیارد دلار (خواهد )?رسید'), (R, 'billion', r'میلیارد'), (F, 'by', r'(به میزان|به اندازه) \$?886'), (F, 'change_as_level', r'از 12 ?%|% ?میلیارد')],
    'B01': [(N, [31, 2]), (R, 'tanks_31', r'31 (دستگاه |فروند )?تانک|تانک[^.]{0,25}31'), (R, 'billion', r'میلیارد'), (F, 'moved', r'31 میلیارد')],
    'B02': [(N, [2000, 500]), (R, 'range_km', r'2,?000 کیلومتر'), (R, 'warhead_kg', r'500 کیلوگرم'), (F, 'swapped', r'2,?000 کیلوگرم|500 کیلومتر')],
    'B03': [(N, [15, 600]), (R, 'zone_km', r'15 کیلومتر'), (R, 'soldiers', r'600 (نفر )?(سرباز|نیرو)|(سرباز|نیرو)\S* 600'), (F, 'swapped', r'15 (نفر|سرباز)|600 کیلومتر'), (F, 'garbled_zone', r'یک کیلومتر|توسط 15')],
    'B04': [(N, [4, 7000]), (R, 'each', r'هر ?یک|هر ?کدام|هرکدام'), (F, 'total', r'مجموع|جمعا|جمعاً')],
    'B05': [(N, [12, 1.8]), (R, 'total', r'مجموع|جمعا|جمعاً|کل'), (F, 'each', r'هر ?یک|هر ?کدام|هرکدام|هر فروند|هر بالگرد|هر هلیکوپتر')],
    'B06': [(N, [250, 40]), (R, 'flew_km', r'250 کیلومتر'), (R, 'inside_km', r'40 کیلومتر')],
    'C01': [(R, 'former', r'سابق|پیشین|اسبق'), (R, 'defence_minister', r'وزیر دفاع'), (R, 'wallace', r'والاس|Wallace')],
    'C02': [(R, 'deputy_pm', r'معاون نخست ?وزیر'), (F, 'pm_without_deputy', r'(?<!معاون )نخست ?وزیر'), (R, 'nato', r'ناتو|NATO'), (R, 'brussels', r'بروکسل')],
    'C03': [(R, 'sg', r'دبیر ?کل'), (R, 'nato', r'ناتو|NATO'), (R, 'vilnius', r'ویلنیوس'), (R, 'monday', r'دوشنبه'), (F, 'wrong_role', r'(رئیس|رییس) ناتو')],
    'C04': [(R, 'acting', r'سرپرست|موقت|کفیل'), (R, 'defence_secretary', r'وزیر دفاع|(سرپرست|کفیل)( موقت)? وزارت دفاع')],
    'C05': [(R, 'spokesman', r'سخنگو'), (R, 'rank', r'ناخدا|کاپیتان|سروان'), (R, 'declined', r'خودداری|امتناع|اظهار ?نظر نکرد|حاضر به اظهار'),
            (R, 'navy', r'نیروی دریایی'), (F, 'wrong_rank', r'سرلشکر|سرتیپ|ژنرال|دریادار|سرهنگ')],
    'C06': [(R, 'opposition_leader', r'(رهبر|رئیس|رییس) (جناح )?(اپوزیسیون|مخالفان|مخالف)'), (R, 'early_elections', r'انتخابات (زودهنگام|زود ?هنگام|پیش از موعد)')],
    'D01': [(R, 'reportedly', r'گزارش|ظاهرا|ظاهراً|گفته می ?شود'), (R, 'killed', r'کشته')],
    'D02': [(R, 'confirmed', r'تایید|تأیید'), (F, 'not_confirmed', r'(تایید|تأیید) ?ن(کرد|کردند|شد)'), (R, 'seized', r'توقیف|ضبط|تصرف|مصادره|بازداشت')],
    'D03': [(R, 'may_have', r'ممکن است|احتمالا|احتمالاً|احتمال دارد|شاید'), (R, 'chemical', r'شیمیایی'), (R, 'investigators', r'بازرس|محقق|تحقیق')],
    'D04': [(R, 'alleged', r'ادعا|مدعی'), (R, 'estonia', r'استونی'), (R, 'moscow', r'مسکو|روسیه|کرملین')],
    'D05': [(R, 'unlikely', r'بعید|احتمال (کمی|ضعیفی|اندکی)|به احتمال زیاد[^.]*(نخواهد|نخواهند|نمی)'),
            (F, 'likely', r'(به احتمال زیاد|احتمال زیادی)(?![^.]*(نخواهد|نخواهند|نمی))')],
    'D06': [(R, 'neither_nor', r'نه [^.]{0,15}(تایید|تأیید)[^.]{0,15} ?(و )?نه [^.]{0,15}(رد|تکذیب)')],
    'E01': [(N, [101]), (R, 'companies', r'گروهان'), (R, 'division', r'لشکر'), (F, 'firm', r'شرکت')],
    'E02': [(N, [40]), (R, 'battery', r'آتشبار|آتش بار|باتری'), (F, 'battalion_or_simulated', r'گردان|شبیه'), (R, 'live_fire', r'(شلیک|آتش|تیر)\S* (واقعی|جنگی|زنده)|جنگی')],
    'E03': [(R, 'destroyer', r'ناوشکن'), (R, 'amphibious', r'آبی ?-?خاکی|دوزیست|هجومی'), (F, 'ship_type', r'ناوچه')],
    'E04': [(N, [120]), (R, 'sorties', r'سورتی|پرواز|ماموریت پروازی|مأموریت پروازی'), (R, 'fighters', r'جنگنده'), (F, 'garbled_sorties', r'(رمز|کد) 120')],
    'E05': [(N, [30]), (R, 'decommission', r'از خدمت خارج|بازنشسته|کنار گذاشته|خروج از خدمت|از رده خارج'),
            (F, 'commission', r'به خدمت (گرفته|درآمد|در خواهد)|وارد خدمت|ملحق')],
    'E06': [(R, 'corps', r'سپاه|قرارگاه'), (F, 'irgc', r'پاسداران'), (R, 'front', r'خط مقدم|جبهه')],
    'F01': [(R, 'after', r'(دو|2) ساعت (پس|بعد) از'), (F, 'before', r'(دو|2) ساعت (قبل|پیش) از')],
    'F02': [(R, 'before_attack', r'(پیش|قبل) از (وقوع )?(حمله|این حمله)'), (R, 'evacuated', r'تخلیه'), (F, 'after_attack', r'(پس|بعد) از (حمله|این حمله)')],
    'F03': [(N, [2027]), (R, 'by', r'تا (پایان|آخر|انتهای)'), (R, 'future', r'خواهند|خواهد')],
    'F04': [(R, 'last_week', r'هفته (گذشته|پیش)'), (R, 'march', r'مارس'), (R, 'future', r'خواهد|می ?شود|بازگشایی می|قرار است')],
    'F05': [(R, 'since_june', r'از (ماه )?ژوئن')],
    'F06': [(R, 'may', r'(ماه )?(مه|می)(?![؀-ۿ])'), (R, 'until_october', r'(تا|به) (ماه )?اکتبر'), (F, 'until_may', r'تا (ماه )?(مه|می)(?![؀-ۿ])')],
    'G01': [(R, 'did_not_hit', r'نکرد|نخورد|نزد|نرسید|نشد|ناکام|موفق نشد|نتوانست')],
    'G02': [(R, 'no_casualties', r'(هیچ|بدون) (تلفات|کشته|مصدوم)|تلفاتی (گزارش )?(نشد|نشده|نداشت)'), (R, 'second', r'دوم|دومین')],
    'G03': [(R, 'failed', r'نتوانست|ناکام|موفق نشد|نرسید|شکست'), (R, 'orbit', r'مدار')],
    'G04': [(R, 'without_escort', r'بدون (اسکورت|همراه|محافظ)'), (R, 'border', r'مرز')],
    'G05': [(R, 'neither_side', r'(هیچ ?یک|هیچ ?کدام|هیچکدام) (از )?(دو )?(طرف|طرفین)'), (R, 'not_accepted', r'نپذیرفت|قبول نکرد|موافقت نکرد')],
    'G06': [(R, 'not_threat', r'در معرض (تهدید|خطر) (قرار )?(نیست|نبود|ندارد)|تهدیدی (متوجه|وجود) (ندارد|نیست|نبود)|تهدید نمی|تحت تهدید نیست|تحت تهدید نبود'),
            (R, 'general', r'ژنرال')],
    'H01': [(R, 'starmer', r'استارمر'), (R, 'zelensky', r'زلنسکی'), (R, 'phone', r'تلفن'),
            (F, 'added_title_or_country', r'نخست ?وزیر|(رئیس|رییس) ?جمهور|انگلیس|بریتانیا|اوکراین')],
    'H02': [(R, 'explosion', r'انفجار'), (R, 'warehouse', r'انبار|سوله'), (F, 'added_context', r'کشته|زخمی|مصدوم|حمله|موشک|پهپاد|در شهر')],
    'H03': [(R, 'hensoldt', r'هنزولت|هنسولت|هنسولد|Hensoldt'), (R, 'radars', r'رادار'), (F, 'added_nationality', r'آلمان')],
    'H04': [(R, 'embassy', r'سفارت'), (R, 'shots', r'تیراندازی|شلیک'),
            (F, 'added_context', r'کشته|زخمی|مصدوم|آمریکا|اسرائیل|ایران|روسیه|افراد مسلح|پلیس')],
    'H05': [(N, [54, 46]), (F, 'added_body_or_outcome', r'مجلس|سنا|پارلمان|کنگره|تصویب|رد شد')],
    'H06': [(R, 'sweden', r'سوئد'), (R, 'exercise', r'رزمایش|تمرین|مانور'), (F, 'added_nato', r'ناتو|NATO')],
}
KEYFACTS = {'dev': DEV, 'p7': P7, 'p8': P8}
# Applied to EVERY item (each seen in 12B output: «شرکت 45», «سازمان 12», «ساخت شرکت 31»,
# «[واحد پول]», bracketed placeholders).
GLOBAL_FORBID = [('number_as_company', r'(شرکت|سازمان) \d'), ('currency_placeholder', r'واحد پول'), ('bracket_text', r'\[')]


def _numbers(out):
    vals = set()
    for t in qc._num_tokens(out, True) | set(re.findall(r'\d+(?:[.,]\d+)*', norm(out))):
        try:
            vals.add(float(str(t).replace(',', '')))
        except ValueError:
            pass
    return vals


def decide_item(source, output, validator_status, validator_flags, checks):
    out = norm(output)
    reasons = {'fail': [], 'unverified': [], 'soft_flags': []}
    if not out.strip():
        reasons['fail'].append('empty_output')
        return 'FAIL', reasons
    for c in list(checks) + [(F, name, rx) for name, rx in GLOBAL_FORBID]:
        if c[0] == N:
            have = _numbers(output)
            for v in c[1]:
                if float(v) not in have:
                    reasons['fail'].append(f'number_missing:{v}')
        elif c[0] == F:
            if re.search(c[2], out):
                reasons['fail'].append(f'forbidden:{c[1]}')
        elif c[0] == R:
            if not re.search(c[2], out):
                reasons['unverified'].append(f'not_found:{c[1]}')
    vflags = list(validator_flags or []) if validator_status != 'available' else []
    for f in vflags:
        (reasons['fail'] if f in HARD_VALIDATOR else reasons['soft_flags']).append(f'validator:{f}')
    for f in qc.check(source, output)['flags']:
        if f.startswith(HIGH_QC_PREFIX) or f in HIGH_QC_WORDS:
            reasons['fail'].append(f'qc:{f}')
        else:
            reasons['soft_flags'].append(f'qc:{f}')
    if reasons['fail']:
        return 'FAIL', reasons
    if reasons['unverified'] or reasons['soft_flags']:
        return 'UNVERIFIED', reasons
    return 'VERIFIED', reasons


def gate(items, technical_ok):
    statuses = [s for s, _ in items.values()]
    if not technical_ok or 'FAIL' in statuses:
        return 'AUTO_GATE_FAIL'
    if all(s == 'VERIFIED' for s in statuses) and len(statuses) == 123:
        return 'AUTO_GATE_PASS'
    return 'INCONCLUSIVE'


def evaluate(runs):
    """runs: {'dev': {key: {source, output, validator_status, validator_flags}}, 'p7': {...}, 'p8': {...}}"""
    res = {}
    for set_name, rows in runs.items():
        for k, r in rows.items():
            res[f'{set_name}:{k}'] = decide_item(r['source'], r.get('output'), r.get('validator_status'), r.get('validator_flags'),
                                                 KEYFACTS[set_name][k])
    return res


if __name__ == '__main__':
    n = {s: len(v) for s, v in KEYFACTS.items()}
    print(GATE_VERSION, n, 'total', sum(n.values()))

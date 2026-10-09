"""Phase-10 independent test set for the placeholder-free pipeline (v2).

Fixed and versioned BEFORE any pipeline-v2 output of TranslateGemma 27B
exists. Synthetic news-style sentences; none repeats a dev, phase-7 or
phase-8 sentence (checked). Key facts are in the frozen gate format
(scripts/translation_auto_gate.py): ('num', [values]) must appear,
('req', name, regex) an accepted rendering must appear, ('forbid', name,
regex) a known critical error must not appear.

Categories (6 each): numbers, dates, currency, names, roles, military,
negation, relations; plus 4 'tokens' items (URL / mention / hashtag / code),
which test what removing the placeholders does to verbatim tokens.
"""
SET_VERSION = 'translation-eval-p10-v1.0.1'
# v1.0.1 (calibrated on TranslateGemma 12B pipeline-v2 output, BEFORE any 27B
# pipeline-v2 output existed; sentences unchanged): N01 accepts «کشتی»;
# N03 «از مجموع ۳۱ … ۹»; T03 «بین تاریخ‌های ۱ تا ۵»; R02 «وانس»; R04 «هالهوی»;
# G04 'denied only' no longer matches «رد» inside «مورد».
N, R, F = 'num', 'req', 'forbid'

ITEMS = [
    # numbers and quantities
    ('N01', 'numbers', 'The navy ordered 14 patrol boats and 3 tankers.',
     [(N, [14, 3]), (R, 'boats_14', r'14 (فروند )?(قایق|شناور|کشتی)|(قایق|شناور|کشتی)\S*[^.]{0,20}14'), (R, 'tankers', r'نفتکش|تانکر'), (F, 'swapped', r'3 (فروند )?(قایق|شناور)|14 (فروند )?(نفتکش|تانکر)')]),
    ('N02', 'numbers', 'About 2.4 million people have fled the region since 2022.',
     [(N, [2.4, 2022]), (R, 'million', r'میلیون'), (R, 'about', r'حدود|تقریبا|تقریباً|نزدیک به|حدودا'), (R, 'since', r'از (سال )?2022')]),
    ('N03', 'numbers', 'The brigade lost 9 of its 31 tanks.',
     [(N, [9, 31]), (R, 'brigade', r'تیپ'), (R, 'of_total', r'9 (دستگاه )?(تانک )?از (مجموع )?31|از (مجموع )?31[^.]{0,25}9')]),
    ('N04', 'numbers', 'Turnout was 61.3%, the lowest since 1999.',
     [(N, [61.3, 1999]), (R, 'percent', r'%|درصد'), (R, 'lowest', r'کمترین|پایین ترین|پایین‌ترین')]),
    ('N05', 'numbers', 'More than 300 drones were launched in a single night.',
     [(N, [300]), (R, 'more_than', r'بیش از|بیشتر از'), (R, 'drones', r'پهپاد'), (R, 'one_night', r'(یک|یک ) ?شب|شبی')]),
    ('N06', 'numbers', 'The bridge is 1.2 kilometres long and 18 metres wide.',
     [(N, [1.2, 18]), (R, 'km', r'1\.2 کیلومتر'), (R, 'm', r'18 متر'), (F, 'swapped', r'1\.2 متر|18 کیلومتر')]),
    # dates and times
    ('T01', 'dates', 'The summit will be held on 9 July 2026 in Ankara.',
     [(N, [9, 2026]), (R, 'july', r'ژوئیه|جولای'), (R, 'ankara', r'آنکارا'), (F, 'bracket', r'\[')]),
    ('T02', 'dates', 'The strike happened at 02:40 on Thursday morning.',
     [(R, 'time', r'0?2:40'), (R, 'thursday', r'پنج ?شنبه'), (R, 'morning', r'صبح|بامداد')]),
    ('T03', 'dates', 'Between 1 and 5 March, 40 flights were cancelled.',
     [(N, [1, 5, 40]), (R, 'march', r'مارس'), (R, 'range', r'(بین|از) (تاریخ ?های )?1 (تا|و) 5'), (R, 'cancelled', r'لغو')]),
    ('T04', 'dates', 'The law takes effect on 1 January 2027 and expires in 2030.',
     [(N, [1, 2027, 2030]), (R, 'january', r'ژانویه'), (R, 'expires', r'منقضی|پایان|اعتبار')]),
    ('T05', 'dates', 'Talks resumed on Monday after a pause of 11 days.',
     [(N, [11]), (R, 'monday', r'دوشنبه'), (R, 'days', r'روز'), (R, 'resumed', r'از سر گرفته|ازسرگیری|دوباره آغاز')]),
    ('T06', 'dates', 'The report covers the period from October 2024 to June 2025.',
     [(N, [2024, 2025]), (R, 'october', r'اکتبر'), (R, 'june', r'ژوئن'), (F, 'swapped', r'ژوئن 2024|اکتبر 2025')]),
    # currency
    ('C01', 'currency', 'The EU pledged €50 billion over four years.',
     [(N, [50]), (R, 'euro', r'یورو|€'), (R, 'billion', r'میلیارد'), (R, 'four_years', r'(چهار|4) سال'), (F, 'dollar', r'دلار')]),
    ('C02', 'currency', 'The fine was £3.2 million.',
     [(N, [3.2]), (R, 'pound', r'پوند|£'), (R, 'million', r'میلیون'), (F, 'other_currency', r'دلار|یورو')]),
    ('C03', 'currency', 'Japan approved a defence budget of ¥8.7 trillion.',
     [(N, [8.7]), (R, 'yen', r'ین|¥'), (R, 'trillion', r'تریلیون|هزار میلیارد'), (F, 'other_currency', r'دلار|یورو')]),
    ('C04', 'currency', 'Each missile costs about $4 million, officials said.',
     [(N, [4]), (R, 'each', r'هر (فروند |یک )?(موشک)'), (R, 'million', r'میلیون'), (R, 'dollar', r'دلار|\$'), (F, 'total', r'مجموع|جمعاً|جمعا')]),
    ('C05', 'currency', 'The rouble fell 8% against the dollar.',
     [(N, [8]), (R, 'rouble', r'روبل'), (R, 'dollar', r'دلار'), (R, 'fell', r'کاهش|افت|سقوط')]),
    ('C06', 'currency', 'India signed a $3.9 billion deal for 31 drones.',
     [(N, [3.9, 31]), (R, 'billion', r'میلیارد'), (R, 'dollar', r'دلار|\$'), (R, 'drones', r'پهپاد'), (F, 'moved', r'31 میلیارد|3\.9 (فروند )?پهپاد')]),
    # names and organisations
    ('P01', 'names', 'Kaja Kallas met Antony Blinken and Josep Borrell in Brussels.',
     [(R, 'kallas', r'کالاس'), (R, 'blinken', r'بلینکن'), (R, 'borrell', r'بورل'), (R, 'brussels', r'بروکسل'), (F, 'added_title', r'وزیر|رئیس|رییس|نخست')]),
    ('P02', 'names', 'Lockheed Martin and Raytheon will supply the interceptors.',
     [(R, 'lockheed', r'لاکهید|لاکید|Lockheed'), (R, 'raytheon', r'ریتیون|رایتیون|ریتئون|Raytheon'), (R, 'interceptors', r'رهگیر|رهگیری|پدافند')]),
    ('P03', 'names', 'The International Atomic Energy Agency sent inspectors to Zaporizhzhia.',
     [(R, 'iaea', r'آژانس بین ?المللی انرژی اتمی|IAEA'), (R, 'inspectors', r'بازرس'), (R, 'zaporizhzhia', r'زاپوریژیا|زاپروژیا|زاپوریژژیا')]),
    ('P04', 'names', 'Volodymyr Zelensky and Recep Tayyip Erdogan spoke on Tuesday.',
     [(R, 'zelensky', r'زلنسکی'), (R, 'erdogan', r'اردوغان'), (R, 'tuesday', r'سه ?شنبه'), (F, 'added_title', r'رئیس ?جمهور|رییس ?جمهور')]),
    ('P05', 'names', 'Hamas and Israel exchanged prisoners through Egyptian mediation.',
     [(R, 'hamas', r'حماس'), (R, 'israel', r'اسرائیل'), (R, 'egypt', r'مصر'), (R, 'prisoners', r'زندانی|اسیر|اسرا')]),
    ('P06', 'names', 'Saab and Kongsberg submitted rival bids.',
     [(R, 'saab', r'ساب|Saab'), (R, 'kongsberg', r'کونگسبرگ|Kongsberg'), (R, 'bids', r'پیشنهاد|مناقصه')]),
    # roles and titles
    ('R01', 'roles', 'Former president Donald Trump criticised the deal.',
     [(R, 'former', r'سابق|پیشین'), (R, 'president', r'رئیس ?جمهور|رییس ?جمهور'), (R, 'trump', r'ترامپ')]),
    ('R02', 'roles', 'Vice President JD Vance arrived in Munich.',
     [(R, 'vice', r'معاون'), (R, 'president', r'رئیس ?جمهور|رییس ?جمهور'), (R, 'vance', r'ونس|وانس'), (R, 'munich', r'مونیخ'), (F, 'pres_only', r'(?<!معاون )(?<!معاون)رئیس ?جمهور ج')]),
    ('R03', 'roles', 'Interim Prime Minister Michel Barnier resigned.',
     [(R, 'interim', r'موقت|سرپرست'), (R, 'pm', r'نخست ?وزیر'), (R, 'barnier', r'بارنیه'), (R, 'resigned', r'استعفا|کناره')]),
    ('R04', 'roles', 'Army chief of staff General Herzi Halevi visited the border.',
     [(R, 'chief_of_staff', r'رئیس ستاد|رییس ستاد|فرمانده ستاد'), (R, 'general', r'ژنرال|سپهبد|سرلشکر'), (R, 'halevi', r'هالوی|هلوی|هالهوی'), (R, 'border', r'مرز')]),
    ('R05', 'roles', 'Foreign Minister Abbas Araghchi denied the report.',
     [(R, 'fm', r'وزیر (امور )?خارجه'), (R, 'araghchi', r'عراقچی'), (R, 'denied', r'رد کرد|تکذیب')]),
    ('R06', 'roles', 'A senior Pentagon official, speaking anonymously, confirmed the move.',
     [(R, 'senior', r'ارشد|بلندپایه|عالی ?رتبه'), (R, 'pentagon', r'پنتاگون|وزارت دفاع'), (R, 'anonymous', r'نام|ناشناس'), (R, 'confirmed', r'تایید|تأیید')]),
    # military terms
    ('M01', 'military', 'A mechanised battalion crossed the river at dawn.',
     [(R, 'battalion', r'گردان'), (F, 'echelon', r'تیپ|لشکر|گروهان|هنگ'), (R, 'mechanised', r'مکانیزه'), (R, 'dawn', r'سپیده|طلوع|بامداد')]),
    ('M02', 'military', 'The frigate and two corvettes took part in the drill.',
     [(R, 'frigate', r'ناوچه|فریگیت|فرگات'), (R, 'corvettes', r'کوروت|ناوچه'), (R, 'two', r'(دو|2)'), (R, 'drill', r'رزمایش|تمرین|مانور')]),
    ('M03', 'military', 'Air defence units intercepted 12 cruise missiles.',
     [(N, [12]), (R, 'air_defence', r'پدافند'), (R, 'intercepted', r'رهگیری|منهدم|ساقط|سرنگون'), (R, 'cruise', r'کروز')]),
    ('M04', 'military', 'The division will be redeployed to the southern front.',
     [(R, 'division', r'لشکر'), (F, 'echelon', r'تیپ|گردان|هنگ'), (R, 'southern', r'جنوب'), (R, 'front', r'جبهه')]),
    ('M05', 'military', 'Special forces conducted a raid, not an air strike.',
     [(R, 'special_forces', r'نیروهای ویژه|یگان ویژه'), (R, 'raid', r'یورش|عملیات|هجوم|حمله زمینی'), (R, 'not_air', r'نه (یک )?حمله هوایی|حمله هوایی (نبود|نکردند)')]),
    ('M06', 'military', 'The bomber flew a training sortie over the Baltic Sea.',
     [(R, 'bomber', r'بمب ?افکن'), (R, 'training', r'آموزشی|تمرینی'), (R, 'sortie', r'پرواز|سورتی|ماموریت|مأموریت'), (R, 'baltic', r'بالتیک')]),
    # negation and affirmation
    ('G01', 'negation', 'The ministry said the reports were not accurate.',
     [(R, 'not_accurate', r'(دقیق|صحیح|درست) نیست|نادرست|(دقیق|صحیح|درست) نبود|نادقیق')]),
    ('G02', 'negation', 'No agreement was reached on the prisoner exchange.',
     [(R, 'no_agreement', r'(هیچ|بدون) توافق|توافقی (حاصل|به دست) ?ن|به توافق نرسید|توافق نشد|حاصل نشد'), (R, 'exchange', r'تبادل|مبادله')]),
    ('G03', 'negation', 'The pilot never lost contact with the base.',
     [(R, 'never_lost', r'هرگز|هیچ ?گاه|هیچ وقت|ارتباط (خود را )?(با پایگاه )?از دست نداد'), (R, 'base', r'پایگاه')]),
    ('G04', 'negation', 'Officials confirmed, rather than denied, the transfer.',
     [(R, 'confirmed', r'تایید|تأیید'), (F, 'denied_only', r'^(?!.*(تایید|تأیید)).*(رد کرد|تکذیب کرد|انکار کرد)')]),
    ('G05', 'negation', 'The talks did not collapse, but no deal was signed.',
     [(R, 'not_collapse', r'(فرو ?نپاشید|شکست نخورد|متوقف نشد|به بن ?بست نرسید)'), (R, 'no_deal', r'(هیچ|بدون) (توافق|قرارداد)|امضا نشد|امضا نکرد')]),
    ('G06', 'negation', 'None of the 20 detainees has been released.',
     [(N, [20]), (R, 'none', r'هیچ ?یک|هیچ ?کدام|هیچکدام'), (R, 'not_released', r'آزاد نشده|آزاد نشد|آزاد نکرده')]),
    # relations: to / by / from
    ('E01', 'relations', 'Military spending rose to 4% of GDP.',
     [(N, [4]), (R, 'level_to', r'به 4 ?(%|درصد)|4 ?(%|درصد)[^.]{0,30}رسید'), (F, 'by', r'(به میزان|به اندازه) 4 ?(%|درصد)(?![^.]*رسید)'), (R, 'gdp', r'تولید ناخالص|GDP')]),
    ('E02', 'relations', 'Military spending rose by 4% this year.',
     [(N, [4]), (R, 'change_by', r'(به میزان|به اندازه)? ?4 ?(%|درصد) (افزایش|رشد)'), (F, 'to', r'به 4 ?(%|درصد) (رسید|رسیده)')]),
    ('E03', 'relations', 'Exports dropped from $12 billion to $9 billion.',
     [(N, [12, 9]), (R, 'from_to', r'از \$?12[^.]{0,20}به \$?9'), (F, 'swapped', r'از \$?9[^.]{0,20}به \$?12')]),
    ('E04', 'relations', 'The interest rate was cut by half a point to 3.75%.',
     [(N, [3.75]), (R, 'half_point', r'نیم (واحد|درصد)|0\.5'), (R, 'level_to', r'به 3\.75'), (F, 'by_level', r'(به میزان|به اندازه) 3\.75(?![^.]*رسید)')]),
    ('E05', 'relations', 'Troop numbers were reduced to 5,000 from 8,000.',
     [(N, [5000, 8000]), (R, 'to_5000', r'به 5,?000'), (R, 'from_8000', r'از 8,?000'), (F, 'swapped', r'به 8,?000|از 5,?000')]),
    ('E06', 'relations', 'Prices increased by 15 cents to $1.40 a litre.',
     [(N, [15, 1.4]), (R, 'cents', r'سنت'), (R, 'level_to', r'به \$?1\.40?'), (R, 'litre', r'لیتر')]),
    # verbatim tokens (what placeholders used to protect)
    ('K01', 'tokens', 'Details are at https://www.nato.int/cps/en/natohq/news_229411.htm according to the alliance.',
     [(R, 'url', r'https://www\.nato\.int/cps/en/natohq/news_229411\.htm')]),
    ('K02', 'tokens', 'The video was first posted by @DefenceU on Sunday.',
     [(R, 'mention', r'@DefenceU'), (R, 'sunday', r'یکشنبه')]),
    ('K03', 'tokens', 'Protesters used the hashtag #StopTheWar during the rally.',
     [(R, 'hashtag', r'#StopTheWar')]),
    ('K04', 'tokens', 'The Su-34 and Ka-52 were seen near the MiG-31K base.',
     [(R, 'su34', r'Su-34'), (R, 'ka52', r'Ka-52'), (R, 'mig31k', r'MiG-31K')]),
]

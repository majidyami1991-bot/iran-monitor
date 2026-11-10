# Phase-7 translations — human review pack (TranslateGemma 12B, 40 held-out items)

Sources: `scripts/translation_qc_heldout.py` (commit `07b4ada`). Outputs: `runtime/local-ai-evidence/phase7/heldout-tg12b.json`.
Prior labels: `scripts/translation_qc_heldout_labels.py` (commit `77b9a31`), written by **Claude (AI), not a human**.
Detected errors: QC `translation-qc-v1.0.0` (frozen, sha256 `bfaa3c55…`) and validator `translation-validator-v2.1.0`.

**Nothing here is pre-approved.** The decision and comment fields are empty for the human reviewer.

## How to review

1. Read the English source and the Persian translation. Judge the translation yourself first.
2. Only then compare your judgement with the AI label and the detected errors.
3. Choose one severity:
   - **critical:** a wrong fact, number, entity, role or meaning; invented information; or a key fact dropped;
   - **major:** a wrong military term, foreign words, or ungrammatical Persian;
   - **minor:** small issues;
   - **none:** no error.
4. Note whether you agree with the AI label. Disagreements decide whether the phase-7 figures stand.

| Summary (AI labels) | critical | major | minor | none |
|---|---|---|---|---|
| count | 14 | 7 | 2 | 17 |

---

### H01 (politics)

**English source:** Prime Minister Kaja Kallas said on Wednesday that Estonia would raise defence spending to 3.5% of GDP in 2027.

**TranslateGemma 12B:** نخست‌وزیر کاجا کالاس روز چهارشنبه اعلام کرد که استونی میزان هزینه‌های دفاعی خود را به میزان 3.5% در سال 2027 افزایش خواهد داد.

**Prior label (AI):** critical (بحرانی) — "raise TO 3.5% of GDP" → "increase BY 3.5%"; "of GDP" dropped

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** `placeholder_missing`

**Suspect part of the translation:** «به میزان 3.5% (pointer)»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H02 (diplomacy)

**English source:** Foreign ministers of France and Germany met in Paris on 14 November to discuss the ceasefire proposal.

**TranslateGemma 12B:** وزیران امور خارجه فرانسه و آلمان در پاریس، در تاریخ [تاریخ دقیق را جایگزین کنید]، برای بررسی پیشنهاد آتش‌بس با یکدیگر دیدار کردند.

**Prior label (AI):** critical (بحرانی) — date replaced by «[تاریخ دقیق را جایگزین کنید]»

**Detected by QC v1.0.0:** `number_missing:14`, `month_missing:november`, `placeholder_text:[تاریخ دقیق را جایگز`, `role_added:وزیر`  
**Detected by validator v2.1.0:** `placeholder_missing`, `stray_markup`, `number_mismatch`

**Suspect part of the translation:** «[تاریخ دقیق را جایگزین کنید]»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H03 (sanctions)

**English source:** The European Union adopted its 19th sanctions package, targeting 45 vessels of the so-called shadow fleet.

**TranslateGemma 12B:** اتحادیه اروپا، نوزدهمین بسته تحریم‌های خود را تصویب کرد که شامل کشتی‌های متعلق به شرکت 45 از آنچه که "ناوگان سایه" نامیده می‌شود، می‌شود.

**Prior label (AI):** critical (بحرانی) — "45 vessels" → «کشتی‌های متعلق به شرکت 45» (vessels of company 45)

**Detected by QC v1.0.0:** `number_missing:19`  
**Detected by validator v2.1.0:** `number_mismatch`

**Suspect part of the translation:** «کشتی‌های متعلق به شرکت 45»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H04 (energy)

**English source:** Brent crude rose 4.2% to $87.60 a barrel after the attack on the refinery.

**TranslateGemma 12B:** قیمت نفت خام برنت پس از حمله به پالایشگاه، به میزان 4.2% دلار به ازای هر بشکه افزایش یافت.

**Prior label (AI):** critical (بحرانی) — "to $87.60 a barrel" dropped; «4.2% دلار»

**Detected by QC v1.0.0:** `number_missing:87.60`  
**Detected by validator v2.1.0:** `placeholder_missing`, `number_mismatch`

**Suspect part of the translation:** «4.2% دلار»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H05 (military)

**English source:** The 82nd Airborne Division deployed 1,500 paratroopers to the region within 48 hours.

**TranslateGemma 12B:** گردان‌های چترباز 1,500 از لشکر 82 پیاده‌نظام هوایی، ظرف چند ساعت (48) در این منطقه مستقر شدند.

**Prior label (AI):** critical (بحرانی) — adds «گردان‌ها» and «پیاده‌نظام»; "within 48 hours" → «ظرف چند ساعت (48)»

**Detected by QC v1.0.0:** `echelon_added:گردان`  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** «گردان‌ها» ؛ «پیاده‌نظام» ؛ «ظرف چند ساعت (48)» ؛ «گردانهای»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H06 (military)

**English source:** A battalion of marines landed on the island during the amphibious exercise.

**TranslateGemma 12B:** یک گردان از تفنگداران دریایی در جریان یک تمرین دریایی، در جزیره پیاده شدند.

**Prior label (AI):** major (عمده) — amphibious exercise → «تمرین دریایی»

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** «تمرین دریایی»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H07 (military)

**English source:** The destroyer USS Carney shot down three drones over the Red Sea on Saturday.

**TranslateGemma 12B:** روز شنبه، ناوچه USS Carney، سه پهپاد را بر فراز دریای سرخ سرنگون کرد.

**Prior label (AI):** critical (بحرانی) — destroyer → «ناوچه» (wrong ship type)

**Detected by QC v1.0.0:** `ship_type_missing:destroyer`  
**Detected by validator v2.1.0:** `mixed_script_word`

**Suspect part of the translation:** «ناوچه»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H08 (military)

**English source:** The live-fire drill involved 30 tanks and two artillery batteries.

**TranslateGemma 12B:** این تمرین نظامی شامل شلیک گلوله واقعی بود و در آن از تانک‌های 30 و دو گردان توپخانه استفاده شد.

**Prior label (AI):** critical (بحرانی) — two artillery batteries → «دو گردان توپخانه» (battalions)

**Detected by QC v1.0.0:** `echelon_added:گردان`, `live_fire_missing`  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** «دو گردان توپخانه» ؛ «گردان»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H09 (military)

**English source:** The corvette will be commissioned into the Indonesian Navy in March 2027.

**TranslateGemma 12B:** این ناوچه در ماه مارس سال 2027 به ناوگان نیروی دریایی اندونزی ملحق خواهد شد.

**Prior label (AI):** ok (بدون خطا)

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** —

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H10 (security)

**English source:** Police arrested four suspects in Hamburg on charges of planning an attack on a synagogue.

**TranslateGemma 12B:** پلیس در هامبورگ، چهار نفر را به اتهام برنامه‌ریزی برای حمله به یک کنیسه دستگیر کرد.

**Prior label (AI):** ok (بدون خطا)

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** —

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H11 (security)

**English source:** The spokesman for the interior ministry denied reports that the border had been closed.

**TranslateGemma 12B:** سخنگوی وزارت کشور، گزارش‌هایی مبنی بر بسته شدن مرز را رد کرد.

**Prior label (AI):** ok (بدون خطا)

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** —

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H12 (claims)

**English source:** Rebel sources claimed, without providing evidence, that 12 soldiers had been killed.

**TranslateGemma 12B:** منابع وابسته به گروه‌های شورشی مدعی شدند، بدون ارائه هیچ مدرکی، که تعدادی از سربازان سازمان 12 کشته شده‌اند.

**Prior label (AI):** critical (بحرانی) — "12 soldiers" → «سربازان سازمان 12» (soldiers of organisation 12)

**Detected by QC v1.0.0:** `unsupported_word:سازمان`  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** «سربازان سازمان 12» ؛ «سازمان»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H13 (claims)

**English source:** It is not yet clear whether the explosion was caused by a missile or by an accident.

**TranslateGemma 12B:** هنوز مشخص نیست که آیا انفجار ناشی از یک موشک بوده است یا یک حادثه.

**Prior label (AI):** ok (بدون خطا)

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** —

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H14 (tech)

**English source:** Microsoft said the cyberattack affected about 200 government agencies in 11 countries.

**TranslateGemma 12B:** شرکت مایکروسافت اعلام کرد که این حمله سایبری، حدود 200 سازمان دولتی را در 11 کشور تحت تأثیر قرار داده است.

**Prior label (AI):** ok (بدون خطا)

**Detected by QC v1.0.0:** `unsupported_word:سازمان`  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** «سازمان»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H15 (tech)

**English source:** The new radar can track up to 300 targets at a range of 450 kilometres.

**TranslateGemma 12B:** این رادار جدید می‌تواند تا 300 هدف را در شعاع 450 کیلومتر ردیابی کند.

**Prior label (AI):** ok (بدون خطا)

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** —

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H16 (industry)

**English source:** Airbus Defence and Space signed a €2.1 billion contract for six A400M transport aircraft.

**TranslateGemma 12B:** شرکت ایرباس، در بخش دفاع و فضا، قراردادی به ارزش 2.1 میلیارد یورو برای تولید شش فروند هواپیمای ترابری منعقد کرد.

**Prior label (AI):** major (عمده) — A400M dropped; «تولید» added

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** `placeholder_missing`, `number_mismatch`, `tech_code_missing`

**Suspect part of the translation:** «تولید»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H17 (industry)

**English source:** BAE Systems chief executive Charles Woodburn said deliveries would begin in the second quarter.

**TranslateGemma 12B:** چارلز وُدبِرن، مدیرعامل شرکت BAE Systems، اعلام کرد که تحویل محصولات از فصل دوم سال آغاز خواهد شد.

**Prior label (AI):** minor (جزئی) — «تحویل محصولات»

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** `mixed_script_word`

**Suspect part of the translation:** «تحویل محصولات»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H18 (politics)

**English source:** The Senate approved the $95 billion aid package by a vote of 70 to 29.

**TranslateGemma 12B:** سنا با رای 70 به 29، بسته کمک مالی به مبلغ $95 را تصویب کرد.

**Prior label (AI):** critical (بحرانی) — "$95 billion" → «$95» (billion dropped)

**Detected by QC v1.0.0:** `unit_missing:billion`  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** «$95»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H19 (diplomacy)

**English source:** Ambassador Linda Thomas-Greenfield told the Security Council that the resolution had failed.

**TranslateGemma 12B:** سفیر لیندا توماس-گرینفیلد به شورای امنیت گفت که این قطعنامه با شکست مواجه شد.

**Prior label (AI):** ok (بدون خطا)

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** —

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H20 (military)

**English source:** General Christopher Cavoli warned that Russia was rebuilding its forces faster than expected.

**TranslateGemma 12B:** ژنرال کریستوفر کاولی هشدار داد که روسیه نیروهای خود را با سرعتی بیشتر از حد انتظار بازسازی می‌کند.

**Prior label (AI):** ok (بدون خطا)

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** —

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H21 (military)

**English source:** Two F-16 fighter jets intercepted a Russian Il-20 reconnaissance aircraft near the border.

**TranslateGemma 12B:** دو جنگنده از نوع F-16 یک هواپیمای شناسایی روسی به نام Il-20 را در نزدیکی مرز رهگیری کردند.

**Prior label (AI):** ok (بدون خطا)

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** —

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H22 (military)

**English source:** The brigade withdrew from the town after three days of heavy fighting.

**TranslateGemma 12B:** گردان مذکور پس از سه روز درگیری شدید، از شهر عقب‌نشینی کرد.

**Prior label (AI):** critical (بحرانی) — brigade → «گردان» (battalion)

**Detected by QC v1.0.0:** `echelon_missing:brigade`, `echelon_added:گردان`  
**Detected by validator v2.1.0:** `glossary_term_missing`

**Suspect part of the translation:** «گردان»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H23 (security)

**English source:** The convoy was ambushed on the road between Gao and Ménaka, killing seven civilians.

**TranslateGemma 12B:** گروهی از خودروها در مسیر بین شهرهای گائو و مناکا مورد حمله قرار گرفت و در این حادثه، هفت غیرنظامی کشته شدند.

**Prior label (AI):** major (عمده) — convoy → «گروهی از خودروها»; ambushed → attacked

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** `glossary_term_missing`

**Suspect part of the translation:** «گروهی از خودروها»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H24 (energy)

**English source:** The pipeline carries up to 55 billion cubic metres of gas per year.

**TranslateGemma 12B:** این خط لوله، تا 55 میلیارد متر مکعب گاز در سال را حمل می‌کند.

**Prior label (AI):** ok (بدون خطا)

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** —

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H25 (politics)

**English source:** The president signed the decree on 3 January 2026, ordering a partial mobilisation.

**TranslateGemma 12B:** رئیس جمهور، فرمان مربوط به بسیج جزئی را در تاریخ [تاریخ مشخص] امضا کرد.

**Prior label (AI):** critical (بحرانی) — date replaced by «[تاریخ مشخص]»

**Detected by QC v1.0.0:** `number_missing:2026`, `number_missing:3`, `month_missing:january`, `placeholder_text:[تاریخ مشخص]`  
**Detected by validator v2.1.0:** `placeholder_missing`, `stray_markup`, `date_mismatch`, `number_mismatch`

**Suspect part of the translation:** «[تاریخ مشخص]»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H26 (quote)

**English source:** The minister said: "Our troops will not leave until the mission is complete."

**TranslateGemma 12B:** وزیر گفت: "نیروهای ما تا زمانی که ماموریت به پایان نرسد، منطقه را ترک نخواهند کرد."

**Prior label (AI):** minor (جزئی) — «منطقه» added

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** «منطقه»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H27 (military)

**English source:** The navy test-fired a hypersonic missile from a submarine for the first time.

**TranslateGemma 12B:** نیروی دریایی برای اولین بار، یک موشک فراصوت را از یک زیردریایی شلیک کرد.

**Prior label (AI):** major (عمده) — "test-fired" → «شلیک کرد» (test lost)

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** «شلیک کرد»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H28 (military)

**English source:** Satellite images show at least 40 aircraft parked at the air base, up from 25 last month.

**TranslateGemma 12B:** تصاویر ماهواره‌ای نشان می‌دهند که حداقل 40 فروند هواپیما در پایگاه هوایی مستقر هستند، که این تعداد نسبت به ماه گذشته (25) افزایش داشته است.

**Prior label (AI):** ok (بدون خطا)

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** —

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H29 (security)

**English source:** Authorities said the drone strike on the depot caused no casualties.

**TranslateGemma 12B:** مقامات اعلام کردند که حمله پهپادی به این انبار هیچ تلفاتی برجای نگذاشت.

**Prior label (AI):** ok (بدون خطا)

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** —

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H30 (diplomacy)

**English source:** Talks in Geneva ended at 23:30 local time without an agreement.

**TranslateGemma 12B:** گفت‌وگوها در ژنو، بدون حصول به توافق، در ساعت 23:30 به وقت محلی به پایان رسید.

**Prior label (AI):** ok (بدون خطا)

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** —

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H31 (industry)

**English source:** Hanwha Aerospace will build 24 K9 howitzers in Poland under the deal.

**TranslateGemma 12B:** شرکت Hanwha Aerospace در چارچوب این قرارداد، توپ‌های خودکششی 24 و K9 را در لهستان تولید خواهد کرد.

**Prior label (AI):** major (عمده) — "24 K9 howitzers" → «توپ‌های خودکششی 24 و K9»

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** «توپ‌های خودکششی 24 و K9»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H32 (claims)

**English source:** According to the Kyiv Independent, the strike hit an ammunition depot in Toropets.

**TranslateGemma 12B:** به گزارش خبرگزاری کی‌یف ایندپندنت، این حمله به یک انبار مهمات در شهر توروپتس وارد شده است.

**Prior label (AI):** ok (بدون خطا)

**Detected by QC v1.0.0:** `entity_missing:Ukraine`  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** —

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H33 (military)

**English source:** The exercise simulated an attack on a naval base, officials said.

**TranslateGemma 12B:** این تمرین، شبیه‌سازی یک حمله به یک پایگاه دریایی بود، به گفته مقامات.

**Prior label (AI):** ok (بدون خطا)

**Detected by QC v1.0.0:** `entity_missing:Navy`  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** —

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H34 (politics)

**English source:** Chancellor Friedrich Merz rejected calls to send Taurus missiles to Ukraine.

**TranslateGemma 12B:** رییس حزب دموکرات مسیحی آلمان، فردریک مرتس، درخواست‌ها برای ارسال موشک‌های "تاوروس" به اوکراین را رد کرد.

**Prior label (AI):** critical (بحرانی) — Chancellor → «رییس حزب دموکرات مسیحی آلمان» (wrong role, added)

**Detected by QC v1.0.0:** `entity_added:Germany`, `role_missing:صدراعظم`  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** «رییس حزب دموکرات مسیحی آلمان»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H35 (sanctions)

**English source:** Treasury officials froze assets worth $1.4 million linked to the network.

**TranslateGemma 12B:** مقامات وزارت خزانه‌داری دارایی‌هایی به ارزش $1.4 میلیون را که به این شبکه مرتبط بودند، مسدود کردند.

**Prior label (AI):** ok (بدون خطا)

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** —

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H36 (military)

**English source:** A frigate of the Royal Navy shadowed two Russian warships through the English Channel.

**TranslateGemma 12B:** یک ناو جنگی از نیروی دریایی سلطنتی بریتانیا، دو کشتی جنگی روسی را در طول مسیر عبورشان از کانال انگلیسی، از نزدیک همراهی کرد.

**Prior label (AI):** major (عمده) — frigate → generic «ناو جنگی»

**Detected by QC v1.0.0:** `ship_type_missing:frigate`  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** «ناو جنگی»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H37 (security)

**English source:** The hostage was released after 471 days in captivity.

**TranslateGemma 12B:** افراد گروگان گرفته شده پس از چند روز اسارت، آزاد شدند.

**Prior label (AI):** critical (بحرانی) — 471 days → «چند روز» (a few days)

**Detected by QC v1.0.0:** `number_missing:471`  
**Detected by validator v2.1.0:** `placeholder_missing`, `number_mismatch`

**Suspect part of the translation:** «چند روز»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H38 (military)

**English source:** The regiment received its first batch of 18 Leopard 2A8 tanks on Friday.

**TranslateGemma 12B:** گردان مذکور، اولین محموله از تانک‌های لئوپارد 2A8 ساخت شرکت 18 را روز جمعه دریافت کرد.

**Prior label (AI):** critical (بحرانی) — regiment → «گردان»; «ساخت شرکت 18» (made by company 18)

**Detected by QC v1.0.0:** `echelon_missing:regiment`, `echelon_added:گردان`  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** «گردان» ؛ «ساخت شرکت 18»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H39 (tech)

**English source:** The satellite was launched at 06:12 GMT on a Falcon 9 rocket from Vandenberg.

**TranslateGemma 12B:** این ماهواره از پایگاه وندنبِرگ با استفاده از موشک فالکون پرتاب شد. (تاریخ دقیق پرتاب: 06:12 GMT)

**Prior label (AI):** major (عمده) — Falcon 9 → «فالکون»; commentary «(تاریخ دقیق پرتاب: …)» added

**Detected by QC v1.0.0:** `number_missing:9`  
**Detected by validator v2.1.0:** `placeholder_missing`, `number_mismatch`

**Suspect part of the translation:** «فالکون»

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |

---

### H40 (claims)

**English source:** Officials did not confirm the number of casualties.

**TranslateGemma 12B:** مقامات، تعداد تلفات را تایید نکردند.

**Prior label (AI):** ok (بدون خطا)

**Detected by QC v1.0.0:** none  
**Detected by validator v2.1.0:** none

**Suspect part of the translation:** —

| Human decision | |
|---|---|
| Severity (critical / major / minor / none) | |
| Agrees with the AI label? (yes / no) | |
| Correct translation of the key fact (if wrong) | |
| Reviewer comment | |
| Reviewer / date | |


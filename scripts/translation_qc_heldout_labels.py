"""Reference labels for the held-out QC set, written by reading source and
outputs only, BEFORE the frozen QC controls (translation_qc v1.0.0, sha256
bfaa3c55…) were run on these outputs. Labeller: Claude (AI reviewer) — not a
human review; the same severity rules as the dev labels:
  critical = wrong fact/number/entity/role/meaning, invented information, key fact dropped
  major    = wrong/vague military term, untranslated or foreign words, ungrammatical, colloquial
  minor    = spelling variant, Arabic letter forms, harmless word additions
Outputs: runtime/local-ai-evidence/phase7/heldout-{tg12b,nllb}.json
"""
TG12B = {
    'H01': ('critical', '"raise TO 3.5% of GDP" → "increase BY 3.5%"; "of GDP" dropped'),
    'H02': ('critical', 'date replaced by «[تاریخ دقیق را جایگزین کنید]»'),
    'H03': ('critical', '"45 vessels" → «کشتی‌های متعلق به شرکت 45» (vessels of company 45)'),
    'H04': ('critical', '"to $87.60 a barrel" dropped; «4.2% دلار»'),
    'H05': ('critical', 'adds «گردان‌ها» and «پیاده‌نظام»; "within 48 hours" → «ظرف چند ساعت (48)»'),
    'H06': ('major', 'amphibious exercise → «تمرین دریایی»'),
    'H07': ('critical', 'destroyer → «ناوچه» (wrong ship type)'),
    'H08': ('critical', 'two artillery batteries → «دو گردان توپخانه» (battalions)'),
    'H09': ('ok', ''),
    'H10': ('ok', ''),
    'H11': ('ok', ''),
    'H12': ('critical', '"12 soldiers" → «سربازان سازمان 12» (soldiers of organisation 12)'),
    'H13': ('ok', ''),
    'H14': ('ok', ''),
    'H15': ('ok', ''),
    'H16': ('major', 'A400M dropped; «تولید» added'),
    'H17': ('minor', '«تحویل محصولات»'),
    'H18': ('critical', '"$95 billion" → «$95» (billion dropped)'),
    'H19': ('ok', ''),
    'H20': ('ok', ''),
    'H21': ('ok', ''),
    'H22': ('critical', 'brigade → «گردان» (battalion)'),
    'H23': ('major', 'convoy → «گروهی از خودروها»; ambushed → attacked'),
    'H24': ('ok', ''),
    'H25': ('critical', 'date replaced by «[تاریخ مشخص]»'),
    'H26': ('minor', '«منطقه» added'),
    'H27': ('major', '"test-fired" → «شلیک کرد» (test lost)'),
    'H28': ('ok', ''),
    'H29': ('ok', ''),
    'H30': ('ok', ''),
    'H31': ('major', '"24 K9 howitzers" → «توپ‌های خودکششی 24 و K9»'),
    'H32': ('ok', ''),
    'H33': ('ok', ''),
    'H34': ('critical', 'Chancellor → «رییس حزب دموکرات مسیحی آلمان» (wrong role, added)'),
    'H35': ('ok', ''),
    'H36': ('major', 'frigate → generic «ناو جنگی»'),
    'H37': ('critical', '471 days → «چند روز» (a few days)'),
    'H38': ('critical', 'regiment → «گردان»; «ساخت شرکت 18» (made by company 18)'),
    'H39': ('major', 'Falcon 9 → «فالکون»; commentary «(تاریخ دقیق پرتاب: …)» added'),
    'H40': ('ok', ''),
}
NLLB = {
    'H01': ('major', 'Kallas first name → «کجا»; «GDP» untranslated'),
    'H02': ('critical', '"14 November" → «در ماه نوامبر» (day dropped)'),
    'H03': ('critical', '19th → «نودمین» (90th)'),
    'H04': ('critical', '"rose 4.2% to $87.60" → «به 4.2% به $87.60 a» (rose TO 4.2%)'),
    'H05': ('critical', 'degenerate repetition «فرقه ی فرقه ی …»'),
    'H06': ('critical', 'battalion → «دسته»; marines → «نیروی دریایی»'),
    'H07': ('critical', 'destroyer → «کشتیرانی» (shipping); shot down → «فرود آورد» (landed)'),
    'H08': ('minor', 'batteries → «باتری»'),
    'H09': ('critical', '2027 dropped; corvette → «کربت»'),
    'H10': ('minor', 'suspects → «مشکوک»'),
    'H11': ('major', 'ungrammatical'),
    'H12': ('minor', 'word order'),
    'H13': ('minor', 'accident → «تصادف»'),
    'H14': ('minor', 'word order'),
    'H15': ('major', 'ungrammatical'),
    'H16': ('critical', '€2.1 billion → «ملیارد یورو» (2.1 dropped)'),
    'H17': ('major', 'BAE Systems → «سیستم BAE»'),
    'H18': ('minor', '«میلیارد دلاری $95»'),
    'H19': ('ok', ''),
    'H20': ('minor', 'Cavoli → «کابولی»'),
    'H21': ('critical', 'reconnaissance → «بازجویی» (interrogation); intercepted → «دستگیر» (arrested)'),
    'H22': ('major', 'brigade → «گروه» (vague)'),
    'H23': ('major', 'Arabic «مدني», awkward'),
    'H24': ('ok', ''),
    'H25': ('minor', 'syntax'),
    'H26': ('major', 'Arabic «قوات»'),
    'H27': ('minor', '«هیپرسونک»'),
    'H28': ('critical', '"up from 25 last month" → «از 25 ماه گذشته» (from 25 months ago)'),
    'H29': ('major', '«حمله بدون سرنشین»'),
    'H30': ('ok', ''),
    'H31': ('critical', 'Hanwha Aerospace → «هواپیمای هانوا» (Hanwha aircraft); «هابیتز»'),
    'H32': ('minor', 'depot → «مخزن»'),
    'H33': ('major', 'simulated → «شبیه» (like)'),
    'H34': ('minor', 'Arabic letters; «تايوروس»'),
    'H35': ('minor', '«میلیون دلاری»'),
    'H36': ('major', '«فرگات»; shadowed → «زیر سایه گذاشت»'),
    'H37': ('critical', '471 days → «چند روز»'),
    'H38': ('major', 'regiment → «فوج»'),
    'H39': ('minor', 'Latin names kept'),
    'H40': ('ok', ''),
}

if __name__ == '__main__':
    import json
    import sys
    json.dump({m: {k: {'severity': s, 'note': n} for k, (s, n) in d.items()} for m, d in (('tg12b', TG12B), ('nllb', NLLB))},
              open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for m, d in (('tg12b', TG12B), ('nllb', NLLB)):
        sev = [s for s, _ in d.values()]
        print(m, {x: sev.count(x) for x in ('ok', 'minor', 'major', 'critical')})

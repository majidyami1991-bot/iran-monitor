# منابع خبری، نرخ ورودی و پوشش خبرگزاری‌ها (Sources & Intake Analysis)

این سند گزارش فنی از نرخ ورودی داده‌ها به سامانه Iran Monitor، مشخصات خزشگر و وضعیت انطباق با سند منابع خبری (`sites.docx`) را ارائه می‌دهد.

---

## ۱. نرخ ورودی اخبار به سامانه (News Intake Rate)

بر اساس آمارهای ثبت‌شده در جدول‌های `news_items` و `collection_runs`:

| شاخص | مقدار واقعی | توضیحات |
| :--- | :--- | :--- |
| **مجموع کل اخبار ذخیره‌شده** | **۷,۹۸۳ خبر** | ذخیره‌شده در جدول `news_items` |
| **تعداد کل چرخه‌های اجراشده** | **۴,۷۵۹ چرخه** | وضعیت سلامت و زمان پایان در `collection_runs` |
| **فاصله زمانی خزش** | **هر ۱۵ دقیقه** | معادل **۹۶ چرخه در شبانه‌روز** (۴ چرخه در ساعت) |
| **میانگین اخبار اسکن‌شده در هر چرخه** | **~۲۶۰ خبر** | بررسی فیدهای فعال برای رصد موارد جدید |
| **نرخ ورودی ۲۴ ساعت گذشته** | **۹۳ خبر جدید** | میانگین ۳.۹ خبر در ساعت |
| **نرخ ورودی ۷ روز گذشته** | **۹۹۶ خبر جدید** | میانگین **۱۴۲.۳ خبر در شبانه‌روز** |
| **نرخ ورودی ۳۰ روز گذشته** | **۳,۷۰۲ خبر جدید** | میانگین **۱۲۳.۴ خبر در شبانه‌روز** |

---

## ۲. تحلیل تطبیقی پوشش منابع با فایل `sites.docx`

فایل `sites.docx` موجود در ریشه پروژه شامل یک جدول ۳ ستونه با عناوین زیر است:
- **News (خبرگزاری‌های نظامی و دفاعی):** ۱۷ نشانی وب
- **Think Tanks (اندیشکده‌های مطالعاتی و راهبردی):** ۹ نشانی وب
- **X (اکانت‌های رصد توییتری و OSINT):** ۳۸ شناسه کاربری

### ۲.۱. پوشش در رجیستری منابع (`config/sources/source-registry.json`)
- **خبرگزاری‌ها (News):** **۱۷ از ۱۷ منبع (۱۰۰٪ پوشش)**
  تمام خبرگزاری‌های ذکرشده در داکیومنت در رجیستری مرکزی پروژه پیکربندی و شناسایی شده‌اند:
  - `twz.com`, `defensenews.com`, `breakingdefense.com`, `thedefensepost.com`, `armyrecognition.com`
  - `janes.com`, `realcleardefense.com`, `defence-blog.com`, `nationaldefensemagazine.org`, `edrmagazine.eu`
  - `war.gov`, `airandspaceforces.com`, `missiledefenseadvocacy.org`, `centcom.mil`, `defence-industry.eu`
  - `airuniversity.af.edu`, `jfeed.com`
- **اندیشکده‌ها (Think Tanks):** **۹ از ۹ منبع (۱۰۰٪ پوشش)**
  تمام اندیشکده‌های جدول در رجیستری موجود هستند:
  - `iiss.org`, `csis.org`, `rand.org`, `brookings.edu`, `rusi.org`, `inss.org.il`, `jcfa.org`, `mwi.westpoint.edu`, `news.usni.org`

### ۲.۲. وضعیت فعال بودن در دیتابیس فعلی (`sources` table)
در دیتابیس فعلی، منابع فعال از طریق فیدهای معتبر RSS جمع‌آوری می‌شوند. از جمله منابع فعال و مستمر:
- **خبرگزاری‌ها (News):** `twz.com`, `breakingdefense.com`, `defensenews.com`, `thedefensepost.com`, `armyrecognition.com`, `defence-blog.com`, `realcleardefense.com` (RSS: `https://www.realcleardefense.com/index.xml`), `news.usni.org` (RSS: `https://news.usni.org/feed`), `airandspaceforces.com`, `edrmagazine.eu`, `defence-industry.eu`, `jfeed.com`
- **اندیشکده‌ها (Think Tanks):** `rand.org` (RSS: `https://www.rand.org/news/press.xml`), `rusi.org`, `csis.org`, `brookings.edu`, `mwi.westpoint.edu`, `jcfa.org`

> [!NOTE]
> منابع RAND Corporation، RealClearDefense و USNI News پیش‌تر به دلیل خطای ۴۰۳ در ریکوئست ریشه دامنه (Homepage/Robots) در دسته‌بندی وب‌اسکرپینگ قرار گرفته بودند، اما اکنون همگی با موفقیت به پایپ‌لاین رسمی RSS متصل شده و مقالات آن‌ها به صورت خودکار و بدون ایجاد رکوردهای تکراری ذخیره و دسته‌بندی می‌شوند.

### ۲.۳. اکانت‌های توییتر / X
در فایل `sites.docx` تعداد ۳۸ اکانت توییتر مانند `@inbarspace`, `@GEOIMINT`, `@OSINTWarfare`, `@Schizointel`, `@MenchOsint` تعریف شده است.
- این اکانت‌ها در بخش جمع‌آوری شبکه‌های اجتماعی طبقه‌بندی شده‌اند و جمع‌آوری مداوم آن‌ها مستلزم تنظیم توکن دسترسی یا API رابط X در ماژول مربوطه است.

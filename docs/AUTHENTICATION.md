# راهنمای احراز هویت و کاربران سازمانی (Authentication & Users)

سامانه Iran Monitor از احراز هویت کنترل‌شده سازمانی بدون ثبت‌نام عمومی استفاده می‌کند.

## ۱. معماری امنیت و رمزنگاری رمزهای عبور
- **الگوریتم:** استاندارد OWASP یعنی **PBKDF2-HMAC-SHA256** با **۱۰۰,۰۰۰ دور محاسباتی**.
- **نمک تصادفی (Salt):** به ازای هر کاربر یک رشته ۳۲ کاراکتری هگزادسیمال کاملاً تصادفی و غیرقابل پیش‌بینی (`secrets.token_hex(16)`) در جدول دیتابیس ذخیره می‌شود.
- **بررسی صحت (Verification):** مقایسه رشته هش‌ها در زمان ثابت (`hmac.compare_digest`) صورت می‌پذیرد تا امکان حملات مبتنی بر اندازه‌گیری زمان (Timing Attacks) از بین برود.
- **نشست کاربر:** ایجاد توکن امنیتی رندوم و ثبت تاریخ آخرین ورود (`last_login`) در جدول `users`.

---

## ۲. فهرست ۱۰ کاربر سازمانی پیش‌فرض

تمامی کاربران در دیتابیس PostgreSQL ذخیره و رمزهای آن‌ها هش شده است:

| شناسه کاربری (Username) | رمز عبور ساده | نام کاربر | سمت و نقش سازمانی | اداره / دپارتمان | سطح دسترسی |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `admin` | `admin123` | مدیر ارشد سامانه | Super Admin | مرکز فرماندهی و رصد استراتژیک | Level 5 (Top Secret) |
| `intel_officer` | `intel123` | افسر ارشد اطلاعات | Senior Intelligence Analyst | اداره کل اطلاعات و امنیت راهبردی | Level 4 (Secret) |
| `defense_analyst` | `defense123` | تحلیل‌گر استراتژی دفاعی | Defense Strategy Analyst | قرارگاه مطالعات دفاعی و موشکی | Level 4 (Secret) |
| `osint_lead` | `osint123` | سرپرست رصد متن‌باز | OSINT Collection Lead | شبکه پایش ماهواره‌ای و منابع باز | Level 3 (Confidential) |
| `cyber_intel` | `cyber123` | کارشناس پایش سایبری | Cyber Threat Analyst | مرکز تحلیل تهدیدات فضای مجازی | Level 3 (Confidential) |
| `geo_specialist` | `geo123` | متخصص مطالعات ژئوپلیتیک | Geopolitical Strategist | اندیشکده ژئوپلیتیک غرب آسیا | Level 3 (Confidential) |
| `ai_operator` | `ai123` | اپراتور هوش مصنوعی | AI & NLP Operator | آزمایشگاه پردازش داده و هوش محلی | Level 3 (Confidential) |
| `field_editor` | `editor123` | ویراستار صحت‌سنجی اخبار | News Verification Editor | اتاق خبر و راستی‌آزمایی روایت‌ها | Level 2 (Restricted) |
| `strategic_planner` | `foresight123` | پژوهشگر آینده‌پژوهی | Strategic Foresight Officer | مرکز تحقیقات روندها و سناریونگاری | Level 2 (Restricted) |
| `guest_viewer` | `guest123` | کاربر ناظر / مهمان | Observer / Guest | پژوهشکده روابط بین‌الملل | Level 1 (Internal Only) |

---

## ۳. روت‌های API احراز هویت
- `POST /api/v1/auth/login`: دریافت `{ "username": "...", "password": "..." }` و بازگرداندن پروفایل کاربر به همراه Session Token.
- `GET /api/v1/auth/users/summary`: مشاهده لیست کاربران فعال سازمانی برای مدیران (بدون بازگرداندن هش یا نمک).

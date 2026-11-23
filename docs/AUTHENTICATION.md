# راهنمای احراز هویت و کاربران سازمانی (Authentication & Users)

سامانه Iran Monitor از احراز هویت کنترل‌شده سازمانی بدون ثبت‌نام عمومی استفاده می‌کند.

## ۱. معماری امنیت و رمزنگاری رمزهای عبور
- **الگوریتم:** استاندارد OWASP یعنی **PBKDF2-HMAC-SHA256** با **۱۰۰,۰۰۰ دور محاسباتی**.
- **نمک تصادفی (Salt):** به ازای هر کاربر یک رشته ۳۲ کاراکتری هگزادسیمال کاملاً تصادفی و غیرقابل پیش‌بینی (`secrets.token_hex(16)`) در جدول دیتابیس ذخیره می‌شود.
- **بررسی صحت (Verification):** مقایسه رشته هش‌ها در زمان ثابت (`hmac.compare_digest`) صورت می‌پذیرد تا امکان حملات مبتنی بر اندازه‌گیری زمان (Timing Attacks) از بین برود.
- **نشست کاربر:** ایجاد توکن امنیتی رندوم و ثبت تاریخ آخرین ورود (`last_login`) در جدول `users`.

---

## ۲. فهرست کاربران و نقش‌های سازمانی

تمامی کاربران در دیتابیس PostgreSQL ذخیره و رمزهای آن‌ها با هش نمک‌دار محافظت شده است:

| شناسه کاربری (Username) | نام کاربر | سمت و نقش سازمانی | اداره / دپارتمان | سطح دسترسی |
| :--- | :--- | :--- | :--- | :--- |
| `admin` | مدیر ارشد سامانه | Chief Information Security Officer | مرکز فرماندهی و رصد استراتژیک | Level 5 (Top Secret // SCI) |
| `r.karimi` | رضا کریمی | Senior Defense Analyst | قرارگاه مطالعات دفاعی و موشکی | Level 5 (Top Secret) |
| `m.alavi` | محمد علوی | Head of Geopolitical Research | اندیشکده ژئوپلیتیک غرب آسیا | Level 4 (Secret) |
| `s.hashemi` | سارا هاشمی | OSINT Collection Lead | شبکه پایش ماهواره‌ای و منابع باز | Level 4 (Secret) |
| `a.moradi` | علی مرادی | Aerospace & Missile Analyst | مرکز مطالعات هوافضا و موشکی | Level 4 (Secret) |
| `f.tehrani` | فرناز تهرانی | Cyber Intelligence Architect | مرکز تحلیل تهدیدات فضای مجازی | Level 4 (Secret) |
| `n.ebrahimi` | نوید ابراهیمی | Regional Strategic Forecaster | مرکز تحقیقات روندها و سناریونگاری | Level 4 (Secret) |
| `k.rostami` | کیوان رستمی | Senior Data Pipeline Engineer | اداره زیرساخت و مهندسی داده | Level 3 (Confidential) |
| `z.ahmadi` | زهرا احمدی | 24/7 Watch Operations Officer | اتاق مانیتورینگ و دیده‌بانی شبانه‌روزی | Level 3 (Confidential) |
| `h.soleimani` | حسین سلیمانی | Advanced Threat Analyst | دپارتمان تحلیل تهدیدات تاکتیکی | Level 3 (Confidential) |
| `d.rezvani` | داوود رضوانی | Compliance & Security Auditor | بازرسی و تطبیق استانداردهای امنیتی | Level 3 (Confidential) |

> [!IMPORTANT]
> کلمه‌های عبور اولیه و سازمانی به دلایل امنیتی درون مستندات عمومی یا ریپازیتوری نگهداری نمی‌شوند و از طریق پروتکل‌های امن سازمانی در اختیار پرسنل مجاز قرار می‌گیرند.

---

## ۳. روت‌های API احراز هویت
- `POST /api/v1/auth/login`: دریافت `{ "username": "...", "password": "..." }` و بازگرداندن پروفایل کاربر به همراه Session Token.
- `GET /api/v1/auth/users/summary`: مشاهده لیست کاربران فعال سازمانی برای مدیران (بدون بازگرداندن هش یا نمک).

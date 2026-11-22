# Iran Monitor — سامانه پایش و رصد هوشمند اطلاعات دفاعی

سامانه **Iran Monitor** یک پلتفرم جامع و مدرن برای پایش، جمع‌آوری، رصد، طبقه‌بندی و تحلیل پیوسته داده‌های متنی و اخبار منابع باز (OSINT) در حوزه دفاعی و ژئوپلیتیک است. این پروژه بر پایه معماری میکروسرویس و کانتینری (Docker) پیاده‌سازی شده و تمامی اجزای آن به صورت هماهنگ و تنها با یک دستور راه‌اندازی می‌شوند.

---

## ۱. ساختار یکپارچه سرویس‌ها (Docker Services)

| نام سرویس | نام کانتینر | پورت | فناوری / فریم‌ورک | وظیفه |
| :--- | :--- | :--- | :--- | :--- |
| **frontend** | `iran_monitor_web` | `3000` | Next.js 16 (App Router) + React 19 | داشبورد رصد، صفحه ورود سه‌بعدی ماژستیک و نمایش اخبار |
| **backend** | `iran_monitor_api` | `8000` | Python 3.12 + FastAPI | وب‌سرویس REST API، احراز هویت دیتابیسی و تحلیل محتوا |
| **collector** | `iran_monitor_collector` | — | Python 3.12 | خزشگر دوره‌ای اخبار (هر ۱۵ دقیقه) |
| **postgres** | `iran_monitor_db` | `5433` | PostgreSQL 16 Alpine | پایگاه داده پایدار با بیش از ۸,۰۰۰ خبر |

---

## ۲. راهنمای سریع راه‌اندازی (Quickstart)

```bash
# ۱. کپی فایل متغیرهای محیطی
cp .env.example .env

# ۲. ساخت و اجرای تمامی کانتینرها
docker compose up -d --build

# ۳. بررسی وضعیت کانتینرها
docker compose ps
```

### آدرس‌های دسترسی:
- **سامانه و داشبورد:** [http://localhost:3000](http://localhost:3000)
- **صفحه ورود امنیتی:** [http://localhost:3000/login](http://localhost:3000/login)
- **وضعیت سلامت بک‌اند:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- **دیتابیس PostgreSQL:** پورت `5433` هاست (کاربر: `iran_monitor_user`)

---

## ۳. احراز هویت و کاربران نمونه

رمزهای عبور با الگوریتم استاندارد **PBKDF2-HMAC-SHA256 (۱۰۰,۰۰۰ دور)** و نمک اختصاصی در دیتابیس هش شده‌اند. نمونه‌ای از کاربران پیش‌فرض جهت تست:

| شناسه کاربری (Username) | رمز عبور | سمت و نقش سازمانی | سطح دسترسی |
| :--- | :--- | :--- | :--- |
| `admin` | `admin123` | مدیر ارشد سامانه (Super Admin) | Level 5 (Top Secret) |
| `intel_officer` | `intel123` | افسر ارشد اطلاعات (Senior Intelligence Analyst) | Level 4 (Secret) |
| `defense_analyst` | `defense123` | تحلیل‌گر استراتژی دفاعی (Defense Strategy Analyst) | Level 4 (Secret) |
| `osint_lead` | `osint123` | سرپرست رصد متن‌باز (OSINT Collection Lead) | Level 3 (Confidential) |
| `guest_viewer` | `guest123` | کاربر ناظر / مهمان (Observer / Guest) | Level 1 (Internal Only) |

---

## ۴. آمار و نرخ ورودی اخبار (News Intake Rate)
- **بسامد چرخه‌ها:** هر ۱۵ دقیقه (۹۶ چرخه در شبانه‌روز)
- **نرخ ورودی متوسط:** **~۱۲۰ الی ۱۴۰ خبر جدید در شبانه‌روز** (~۴ الی ۶ خبر در ساعت)
- **کل اخبار ذخیره‌شده:** بیش از **۷,۹۸۰ خبر** با تاریخچه کامل

---

## ۵. اسناد تخصصی معماری و راهنماها (`docs/`)

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): معماری کلان سیستم، جریان داده و برنامه آینده اتصال موتور ترجمه vLLM
- [docs/SOURCES_AND_COLLECTION.md](docs/SOURCES_AND_COLLECTION.md): نرخ ورودی اخبار و جدول تطبیق پوشش منابع با `sites.docx`
- [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md): راهنمای کامل احراز هویت، هشینگ و سطوح دسترسی
- [docs/DEPLOYMENT_RUNBOOK.md](docs/DEPLOYMENT_RUNBOOK.md): راهنمای گام‌به‌گام دیپلوی، بک‌آپ‌گیری و عیب‌یابی

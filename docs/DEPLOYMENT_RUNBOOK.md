# راهنمای جامع استقرار و عملیات (Deployment Runbook)

این سند مراحل راه‌اندازی، نگهداری و مهاجرت سامانه Iran Monitor بر روی هر سرور یا سیستم‌عامل جدید را شرح می‌دهد.

## ۱. نیازمندی‌ها
- **Docker Engine** (نسخه ۲۴ یا بالاتر)
- **Docker Compose** (نسخه v2.20 یا بالاتر)
- **Git**
- *نکته:* نیازی به نصب پایتون، نود جی‌اس یا پستگرس روی سیستم‌عامل میزبان نیست؛ تمامی فرآیندها داخل کانتینرهای ایزوله اجرا می‌شوند.

---

## ۲. مراحل استقرار گام‌به‌گام (Quick Deployment)

### گام اول: کپی تنظیمات محیطی
```bash
cp .env.example .env
```
در صورت نیاز می‌توانید مقادیر پسورد دیتابیس و پورت‌ها را داخل فایل `.env` ویرایش کنید.

### گام دوم: ساخت و اجرای هم‌زمان کانتینرها
```bash
docker compose up -d --build
```

### گام سوم: بررسی وضعیت سلامت
```bash
docker compose ps
```
خروجی باید نشان‌دهنده وضعیت `healthy` برای هر ۴ سرویس باشد.

---

## ۳. پورت‌های دسترسی و خدمات

| سرویس | آدرس دسترسی | پورت |
| :--- | :--- | :--- |
| **داشبورد و فرانت‌اند** | `http://localhost:3000` | ۳۰۰۰ |
| **صفحه ورود** | `http://localhost:3000/login` | ۳۰۰۰ |
| **وب‌سرویس بک‌اند** | `http://localhost:8000/api/v1/health` | ۸۰۰۰ |
| **پایگاه داده PostgreSQL** | `localhost:5433` (نام کاربری: `iran_monitor_user`) | ۵۴۳۳ |

---

## ۴. پشتیبان‌گیری و بازیابی داده‌ها (Backup & Restore)

### بازیابی بک‌آپ اولیه یا بک‌آپ موجود:
```bash
docker exec -i iran_monitor_db psql -U iran_monitor_user -d iran_monitor < iran_monitor_db_backup.sql
```

### تهیه بک‌آپ جدید از وضعیت فعلی:
```bash
docker exec -t iran_monitor_db pg_dump -U iran_monitor_user -d iran_monitor > backup_$(date +%Y%m%d).sql
```

---

## ۵. مشاهده لاگ‌ها و عیب‌یابی
- لاگ‌های زنده خزشگر اخبار: `docker compose logs -f collector`
- لاگ‌های وب‌سرویس بک‌اند: `docker compose logs -f backend`
- لاگ‌های فرانت‌اند: `docker compose logs -f frontend`
- راه‌اندازی مجدد یک سرویس خاص: `docker compose restart backend`
- متوقف‌سازی کل سامانه: `docker compose down`

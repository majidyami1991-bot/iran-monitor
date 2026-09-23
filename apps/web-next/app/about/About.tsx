'use client';
import { Shell } from '../design/Shell';
import { useApi } from '../design/useApi';
import { fmt } from '../design/format';

interface Coverage { registered: number; executable: number; monitored: number }

export function About() {
  const { data } = useApi<Coverage>('sources/coverage');
  return (
    <Shell title="درباره سامانه" breadcrumb="درباره سامانه">
      <div className="page-head"><div><h1>درباره ایران مانیتور</h1></div></div>
      <div className="card about-card">
        <p>ایران مانیتور در مرحله فعلی یک سامانه <strong>رصد و دیده‌بانی</strong> است: گردآوری، پالایش، حذف تکرار، دسته‌بندی
          و نمایش یکپارچه اخبار از منابع باز تعریف‌شده.</p>
        <p>این نسخه <strong>تحلیل علّی، ارتباط رویداد، پیش‌بینی یا هشدار هوشمند ارائه نمی‌دهد</strong>. آمار و نمودارهای
          موجود، شمارش توصیفی رکوردهای ذخیره‌شده در PostgreSQL‌اند، نه تحلیل روند یا آینده‌نگاری.</p>
        {data && (
          <p className="about-coverage">
            از {fmt(data.registered)} منبع ثبت‌شده در سند اولیه، {fmt(data.executable)} منبع مسیر جمع‌آوری معتبر دارند و
            {' '}{fmt(data.monitored)} منبع در حال پایش واقعی است. جزئیات کامل در <a href="/sources">صفحه منابع</a>.
          </p>
        )}
        <p>داده‌ها فقط از خوراک‌های RSS منابعی گردآوری می‌شوند که روش دسترسی مجاز و آزموده دارند؛ ورود به سایت‌های
          دارای محدودیت، دور زدن ۴۰۳، CAPTCHA یا paywall در این سامانه انجام نمی‌شود.</p>
      </div>
    </Shell>
  );
}

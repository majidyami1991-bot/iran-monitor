'use client';
import { Shell } from '../design/Shell';
import { PageHead } from '../design/ui';
import { StoriesRail, useStories } from '../components/Stories';
import { fmt, fmtDateTime } from '../design/format';

export function Stories() {
  const q = useStories();
  const last = q.data?.stories.reduce<string | null>((m, s) => (!m || s.generated_at > m ? s.generated_at : m), null);
  return (
    <Shell>
      <PageHead eyebrow="استوری‌ها" title="استوری‌ها"
        lede="مجموعه‌های کوتاه و قابل مرور که هر ۱۵ دقیقه از داده‌های واقعی ساخته می‌شوند: مهم‌ترین تحول، خبرهای فوری، رویدادهای در حال تحول، موضوعات داغ، گزارش روزانه، منابع فعال، سیگنال‌های ضعیف و پرونده‌های موضوعی. هر بخش به خبر، رویداد یا صفحه مرجع خود پیوند دارد.">
        {q.data && <span className="muted">{fmt(q.data.total)} استوری · آخرین ساخت {fmtDateTime(last)} · قاعده {q.data.rule_version}</span>}
      </PageHead>
      <StoriesRail layout="grid" />
      <p className="note">حلقه رنگی یعنی محتوای استوری از آخرین بازدید شما تغییر کرده است (در همین مرورگر ذخیره می‌شود). کلیدها: ← و → برای جابه‌جایی، فاصله برای توقف، Esc برای بستن. استوری‌ها از تصویر تبلیغاتی یا نامرتبط ساخته نمی‌شوند؛ اگر تصویر معتبر خبر نباشد، نگاره داخلی دسته نمایش داده می‌شود.</p>
    </Shell>
  );
}

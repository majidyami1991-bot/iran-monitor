'use client';
import { Shell } from '../design/Shell';
import { useApi } from '../design/useApi';
import type { Integration } from '../design/types';
import { IntegrationNotice, PageHead, Tag } from '../design/ui';

interface Rules { importance: { id: string; description_fa: string }; breaking: { id: string; description_fa: string }; taxonomy_version: string; clustering: { method: string; version: string }; stories: string; briefing: string }

export function About() {
  const r = useApi<Rules>('rules');
  const integ = useApi<{ integrations: Integration[] }>('integrations');
  return (
    <Shell>
      <PageHead eyebrow="درباره" title="روش‌ها، قواعد و محدودیت‌ها"
        lede="ایران مانیتور نشان می‌دهد چه چیزی، کِی، از کدام منبع و درباره چه موضوعی منتشر شده است. هر خروجی مشتق‌شده با قاعده نسخه‌دار ساخته می‌شود و در رابط کاربری با منشأ خود برچسب می‌خورد." />
      <section className="panel">
        <div className="panel-title"><h3>اصول داده</h3></div>
        <ul className="prov">
          <li><span /><div>پایگاه داده PostgreSQL تنها منبع حقیقت است؛ رابط کاربری هیچ منبعی را مستقیم فراخوانی نمی‌کند.</div></li>
          <li><span /><div>هیچ عدد، ترجمه، خلاصه، تصویر یا پستی ساخته یا حدس زده نمی‌شود؛ مقدار نامشخص با عبارت صریح نمایش داده می‌شود.</div></li>
          <li><span /><div>گردآوری: یک درخواست به ازای هر منبع در هر چرخه ۹۰۰ ثانیه‌ای، بدون دنبال‌کردن تغییر مسیر و بدون دورزدن ۴۰۳، robots یا دیوار پرداخت.</div></li>
          <li><span /><div>امکان دریافت محتوا به معنای اجازه بازنشر آن نیست؛ متن کامل فقط وقتی نمایش داده می‌شود که ناشر آن را در خوراک خود منتشر کرده باشد.</div></li>
          <li><span /><div>ترجمه ماشینی همیشه برچسب «ترجمه ماشینی» و وضعیت بازبینی دارد و متن اصلی کنار آن حفظ می‌شود.</div></li>
          <li><span /><div>خروجی هوش مصنوعی از متن منبع جدا، دارای مدل و نسخه دستور، نیازمند بازبینی و هرگز به‌عنوان واقعیت قطعی نمایش داده نمی‌شود.</div></li>
        </ul>
      </section>
      {r.data && (
        <section className="panel">
          <div className="panel-title"><h3>قواعد فعال</h3></div>
          <dl className="kv">
            <dt>اهمیت <Tag>{r.data.importance.id}</Tag></dt><dd>{r.data.importance.description_fa}</dd>
            <dt>خبر فوری <Tag>{r.data.breaking.id}</Tag></dt><dd>{r.data.breaking.description_fa}</dd>
            <dt>طبقه‌بندی</dt><dd>نسخه {r.data.taxonomy_version} — قواعد کلیدواژه‌ای قطعی با شواهد، موضوعات فرعی و کد دلیل برای «سایر»؛ تاریخچه هر تغییر حفظ می‌شود.</dd>
            <dt>رویدادها</dt><dd dir="ltr" style={{ textAlign: 'right' }}>{r.data.clustering.method} v{r.data.clustering.version}</dd>
            <dt>استوری‌ها</dt><dd>{r.data.stories} — ساخته‌شده از داده پایگاه داده هر ۱۵ دقیقه</dd>
            <dt>گزارش روزانه</dt><dd>{r.data.briefing} — شمارش‌ها و قواعد، بدون هوش مصنوعی</dd>
          </dl>
        </section>
      )}
      <section>
        <h2 className="brief-sub">وضعیت اتصال‌ها</h2>
        <div className="grid-3" style={{ marginTop: 12 }}>
          {integ.data?.integrations.map((i) => <IntegrationNotice key={i.integration_id} integration={i} />)}
        </div>
      </section>
    </Shell>
  );
}

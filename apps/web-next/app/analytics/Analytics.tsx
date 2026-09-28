'use client';
import Link from 'next/link';
import { Shell } from '../design/Shell';
import { useApi } from '../design/useApi';
import { fmt, fmtDay, fmtPercent, fmtSigned } from '../design/format';
import { CardBones, Empty, Failure, PageHead, Tag } from '../design/ui';
import { Bars, Columns, Figure, Matrix, SeqLegend, ShareBar, Sparkline } from '../design/charts';

interface Insights {
  volume_30d: { day: string; n: number; sources: number }[];
  heatmap_30d: { dow: number; h: number; n: number }[];
  source_topic: { source_id: string; source: string; category_id: string; n: number }[];
  topic_change_7d: { category_id: string; category_label: string; n7: number; p7: number }[];
  translation_coverage: { field: string; status: string; n: number }[];
  provenance: { source: string; status: string | null; n: number }[];
  event_velocity_30d: { day: string; events: number; items: number }[];
  confidence_histogram: { bucket: number; n: number }[];
  source_activity_14d: { source: string; day: string; n: number }[];
  labels: Record<string, string>;
  taxonomy_version: string;
}

const DOW = ['', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه', 'شنبه', 'یکشنبه'];
const DOW_ORDER = [6, 7, 1, 2, 3, 4, 5]; // Saturday first, Persian week
const TR: Record<string, [string, string]> = {
  available: ['ترجمه موجود', 'var(--ai)'], pending: ['در انتظار', 'var(--line-3)'], error: ['ناموفق', 'var(--error)'], unavailable: ['ناموجود', 'var(--ink-4)'],
};

function lastNDays(n: number, rows: { day: string }[], val: (r: { day: string }) => number) {
  const map = new Map(rows.map((r) => [r.day.slice(0, 10), val(r)]));
  return Array.from({ length: n }, (_, i) => { const d = new Date(Date.now() - (n - 1 - i) * 86400000).toISOString().slice(0, 10); return { key: d, label: fmtDay(d), value: map.get(d) ?? 0 }; });
}

export function Analytics() {
  const q = useApi<Insights>('insights/overview');
  const d = q.data;
  return (
    <Shell>
      <PageHead eyebrow="تحلیل" title="تحلیل آماری پوشش"
        lede="هر نمودار به یک پرسش مشخص درباره داده‌های گردآوری‌شده پاسخ می‌دهد. همه اعداد شمارش توصیفی پایگاه داده‌اند؛ تغییر حجم پوشش به معنای تغییر در واقعیت یا پیش‌بینی نیست.">
        {d && <Tag tone="info">طبقه‌بندی نسخه {d.taxonomy_version}</Tag>}
      </PageHead>
      {q.error && <Failure onRetry={q.reload} />}
      {!d && !q.error && <CardBones n={4} image={false} />}
      {d && <Body d={d} />}
    </Shell>
  );
}

function Body({ d }: { d: Insights }) {
  const vol = lastNDays(30, d.volume_30d, (r) => (r as unknown as { n: number }).n);
  const vel = lastNDays(30, d.event_velocity_30d, (r) => (r as unknown as { events: number }).events);
  const heatMax = Math.max(1, ...d.heatmap_30d.map((h) => h.n));
  const heat = (r: string, c: string) => d.heatmap_30d.find((x) => x.dow === Number(r) && x.h === Number(c))?.n ?? 0;
  const sources = [...new Set(d.source_topic.map((x) => x.source))].sort();
  const cats = Object.keys(d.labels).filter((c) => d.source_topic.some((x) => x.category_id === c));
  const matVal = (r: string, c: string) => d.source_topic.filter((x) => x.source === r && x.category_id === c).reduce((a, x) => a + x.n, 0);
  const matMax = Math.max(1, ...sources.flatMap((s) => cats.map((c) => matVal(s, c))));
  const provBySource = [...new Set(d.provenance.map((p) => p.source))].map((s) => {
    const rows = d.provenance.filter((p) => p.source === s);
    const total = rows.reduce((a, r) => a + r.n, 0);
    const ok = rows.filter((r) => r.status === 'COMPLETE').reduce((a, r) => a + r.n, 0);
    return { key: s, label: <bdi>{s}</bdi>, value: total ? Math.round((1000 * ok) / total) / 10 : 0, note: `${fmt(ok)} از ${fmt(total)}` };
  }).sort((a, b) => a.value - b.value);
  const conf = Array.from({ length: 10 }, (_, i) => ({ key: String(i + 1), label: `${fmt(i * 10)}–${fmt((i + 1) * 10)}٪`, value: d.confidence_histogram.find((h) => h.bucket === i + 1)?.n ?? 0 }));
  const actSources = [...new Set(d.source_activity_14d.map((x) => x.source))];
  return (
    <>
      <div className="grid-2">
        <Figure title="حجم روزانه خبر" question="هر روز چند خبر از همه منابع ثبت شده است؟" unit="خبر در روز" range="۳۰ روز اخیر" source="زمان انتشار، به وقت تهران"
          table={{ head: ['روز', 'خبر'], rows: vol.map((v) => [v.label, v.value]) }}>
          <Columns data={vol} height={170} highlightLast />
        </Figure>
        <Figure title="الگوی زمانی انتشار" question="منابع در چه روزها و ساعت‌هایی بیشتر منتشر می‌کنند؟" unit="خبر" range="۳۰ روز اخیر" source="به وقت تهران"
          legend={<SeqLegend max={heatMax} unit="خبر" />}>
          <Matrix rows={DOW_ORDER.map(String)} cols={Array.from({ length: 24 }, (_, i) => String(i))} value={heat}
            rowLabel={(r) => DOW[Number(r)]} colLabel={(c) => `${fmt(Number(c))}`} />
        </Figure>
      </div>

      <div className="grid-2">
        <Figure title="تغییر پوشش موضوعی" question="پوشش کدام موضوعات در ۷ روز اخیر نسبت به ۷ روز قبل بیشتر یا کمتر شده است؟" unit="خبر" range="۱۴ روز" source={`طبقه‌بندی نسخه ${d.taxonomy_version}`}
          table={{ head: ['موضوع', '۷ روز قبل', '۷ روز اخیر', 'تغییر'], rows: d.topic_change_7d.map((t) => [t.category_label, t.p7, t.n7, fmtSigned(t.n7 - t.p7)]) }}>
          <Bars data={d.topic_change_7d.map((t) => ({ key: t.category_id, label: t.category_label, value: t.n7,
            note: <span className={t.n7 - t.p7 >= 0 ? 'delta-up' : 'delta-down'}>{fmtSigned(t.n7 - t.p7)}</span> }))} href={(k) => `/topics/${k}`} />
        </Figure>
        <Figure title="سرعت شکل‌گیری رویداد" question="هر روز چند رویداد چندخبری آغاز شده است؟" unit="رویداد" range="۳۰ روز" source="خوشه‌بندی رویداد نسخه ۲"
          empty={vel.some((v) => v.value) ? undefined : <Empty title="رویدادی در این بازه آغاز نشده است" />}
          table={{ head: ['روز', 'رویداد'], rows: vel.map((v) => [v.label, v.value]) }}>
          <Columns data={vel} unit="رویداد" height={170} color="var(--series-3)" />
        </Figure>
      </div>

      <Figure title="ماتریس منبع و موضوع" question="هر منبع کدام موضوعات را پوشش می‌دهد؟" unit="خبر" range="همه زمان‌ها" source="طبقه‌بندی نسخه ۳"
        legend={<SeqLegend max={matMax} unit="خبر" />}>
        <Matrix rows={sources} cols={cats} value={matVal} rowLabel={(r) => <bdi>{r}</bdi>} colLabel={(c) => d.labels[c] ?? c} />
      </Figure>

      <div className="grid-2">
        <Figure title="پوشش ترجمه فارسی" question="چه بخشی از عنوان‌ها و خلاصه‌ها ترجمه فارسی ذخیره‌شده دارند؟" unit="خبر" source="جدول news_item_translations"
          table={{ head: ['فیلد', 'وضعیت', 'تعداد'], rows: d.translation_coverage.map((t) => [t.field, TR[t.status]?.[0] ?? t.status, t.n]) }}>
          {['title', 'summary'].map((f) => (
            <div key={f} style={{ marginBottom: 12 }}>
              <strong style={{ fontSize: 13 }}>{f === 'title' ? 'عنوان' : 'خلاصه'}</strong>
              <ShareBar parts={d.translation_coverage.filter((t) => t.field === f).map((t) => ({ key: t.status, label: TR[t.status]?.[0] ?? t.status, value: t.n, color: TR[t.status]?.[1] ?? 'var(--ink-4)' }))} />
            </div>
          ))}
          <p className="muted">ارائه‌دهنده ترجمه در حال حاضر فعال نیست؛ وضعیت آن در <Link href="/monitoring" className="sec-link">پایش سامانه</Link> آمده است.</p>
        </Figure>
        <Figure title="کامل بودن منشأ به تفکیک منبع" question="برای چه درصدی از خبرهای هر منبع زنجیره منشأ کامل ثبت شده است؟" unit="درصد" source="news_items.provenance_status">
          <Bars data={provBySource} max={100} unit="درصد" />
        </Figure>
      </div>

      <div className="grid-2">
        <Figure title="توزیع اطمینان طبقه‌بندی" question="طبقه‌بندی موضوعی خبرها چقدر بر شواهد قوی تکیه دارد؟" unit="خبر" source="شمارش شواهد کلیدواژه‌ای، نه احتمال"
          table={{ head: ['بازه اطمینان', 'خبر'], rows: conf.map((c) => [c.label, c.value]) }}>
          <Columns data={conf} unit="خبر" height={150} color="var(--series-7)" />
          <p className="fig-note">خبرهای «سایر» در این توزیع نیستند. اطمینان کم یعنی شواهد کم یا نزدیک بودن امتیاز دو دسته.</p>
        </Figure>
        <Figure title="فعالیت منابع" question="کدام منابع در دو هفته اخیر پیوسته منتشر کرده‌اند؟" unit="خبر در روز" range="۱۴ روز" source="زمان انتشار">
          <ul className="bars">
            {actSources.map((s) => {
              const series = lastNDays(14, d.source_activity_14d.filter((x) => x.source === s), (r) => (r as unknown as { n: number }).n);
              const total = series.reduce((a, x) => a + x.value, 0);
              return <li key={s}><div className="bars-row"><span className="bars-label"><bdi>{s}</bdi></span><Sparkline values={series.map((x) => x.value)} width={180} height={26} label={`${s}: ${fmt(total)} خبر در ۱۴ روز`} /><span className="bars-value">{fmt(total)}</span></div></li>;
            })}
          </ul>
        </Figure>
      </div>
      <p className="muted">درصد کلی کامل بودن منشأ: {fmtPercent(100 * d.provenance.filter((p) => p.status === 'COMPLETE').reduce((a, p) => a + p.n, 0) / Math.max(1, d.provenance.reduce((a, p) => a + p.n, 0)), 1)}</p>
    </>
  );
}

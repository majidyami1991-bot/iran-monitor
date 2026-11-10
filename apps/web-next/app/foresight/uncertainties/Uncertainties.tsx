'use client';
import Link from 'next/link';
import { Shell } from '../../design/Shell';
import { useApi } from '../../design/useApi';
import { fmt, fmtPercent } from '../../design/format';
import { CardBones, CategoryTag, Empty, Failure, PageHead, Stat } from '../../design/ui';
import { ForesightNote } from '../ForesightNote';

interface Resp {
  scope_fa: string;
  classification: { other_n: number; low_conf: number; multi_topic: number; total: number };
  events: { low: number; unknown: number; total: number };
  coverage_gaps: { no_summary: number; no_date: number; total: number };
  ambiguous_items: { item_id: string; title: string; category_label: string; confidence: number; secondary: { id: string; label: string }[] }[];
  strategic_uncertainties: unknown[]; strategic_status: string;
}

export function Uncertainties() {
  const q = useApi<Resp>('foresight/uncertainties');
  const d = q.data;
  return (
    <Shell>
      <PageHead eyebrow="آینده‌پژوهی" title="عدم‌قطعیت‌ها" />
      <ForesightNote>{d?.scope_fa ?? 'عدم‌قطعیت داده و پردازش.'}</ForesightNote>
      {q.error && <Failure onRetry={q.reload} />}
      {!d && !q.error && <CardBones n={3} image={false} />}
      {d && (
        <>
          <div className="stat-row">
            <Stat label="طبقه‌بندی کم‌اطمینان" value={d.classification.low_conf} note={`${fmtPercent((100 * d.classification.low_conf) / Math.max(1, d.classification.total), 1)} از خبرها`} />
            <Stat label="خبرهای چندموضوعی" value={d.classification.multi_topic} note="دارای موضوع فرعی" />
            <Stat label="رویداد کم‌اطمینان" value={d.events.low} note={`از ${fmt(d.events.total)} رویداد؛ ${fmt(d.events.unknown)} نامشخص`} />
            <Stat label="بدون خلاصه منبع" value={d.coverage_gaps.no_summary} note={`${fmt(d.coverage_gaps.no_date)} خبر بدون تاریخ انتشار`} />
          </div>
          <section className="panel">
            <div className="panel-title"><h3>خبرهای مبهم از نظر موضوع</h3></div>
            <p className="muted" style={{ marginBottom: 10 }}>خبرهایی که شواهد دو یا چند دسته را هم‌زمان دارند و اطمینان دسته اصلی زیر ۶۰٪ است — نامزد بازبینی انسانی.</p>
            {d.ambiguous_items.length === 0 ? <Empty title="خبر مبهمی نیست" /> : (
              <ul className="prov">
                {d.ambiguous_items.map((i) => (
                  <li key={i.item_id}><span /><div><Link href={`/news/${i.item_id}`} dir="ltr">{i.title}</Link>
                    <small>{i.category_label} ({fmtPercent(i.confidence * 100)}) · رقیب: {i.secondary.map((s) => <CategoryTag key={s.id} id={s.id} label={s.label} />)}</small></div></li>
                ))}
              </ul>
            )}
          </section>
          <Empty title="عدم‌قطعیت‌های راهبردی ثبت نشده است">این بخش برای عدم‌قطعیت‌های کلیدی است که تحلیلگر با شواهد ثبت می‌کند. هیچ موردی ثبت نشده و موردی به‌صورت خودکار یا نمایشی ساخته نمی‌شود.</Empty>
        </>
      )}
    </Shell>
  );
}

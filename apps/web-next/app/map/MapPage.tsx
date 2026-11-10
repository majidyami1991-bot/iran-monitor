'use client';
import { MapPinned } from 'lucide-react';
import { Shell } from '../design/Shell';
import { useApi } from '../design/useApi';
import type { Integration } from '../design/types';
import { fmt } from '../design/format';
import { Empty, Failure, IntegrationNotice, PageHead, Bone } from '../design/ui';

interface Geo { integration: Integration; points: unknown[]; total: number; note_fa: string }

export function MapPage() {
  const q = useApi<Geo>('geo');
  const integ = useApi<{ integrations: Integration[] }>('integrations');
  const osint = integ.data?.integrations.filter((i) => ['geolocation', 'connectivity', 'flight_marine'].includes(i.integration_id)) ?? [];
  return (
    <Shell>
      <PageHead eyebrow="تحلیل" title="نقشه رصد" lede="نقشه فقط نقاطی را نشان می‌دهد که مکان آن‌ها با شواهد متنی از خود خبر استخراج و ثبت شده باشد. هیچ مختصات حدسی یا تزئینی ساخته نمی‌شود." />
      {q.error && <Failure onRetry={q.reload} />}
      {!q.data && !q.error && <Bone h={320} />}
      {q.data && q.data.total === 0 && (
        <Empty title="هنوز هیچ موقعیت مکانی معتبری ثبت نشده است" icon={<MapPinned size={28} />}>
          {q.data.note_fa} پس از فعال‌شدن استخراج مکان، لایه‌های رویداد، فیلتر موضوع و زمان، خوشه‌بندی نشانگرها، راهنما و پنل جزئیات با منشأ هر نقطه در همین صفحه فعال می‌شوند. تعداد نقاط ثبت‌شده: {fmt(q.data.total)}.
        </Empty>
      )}
      <div className="grid-3">
        {osint.map((i) => <IntegrationNotice key={i.integration_id} integration={i} />)}
      </div>
      <section className="panel">
        <div className="panel-title"><h3>قرارداد ثبت داده مکانی</h3></div>
        <p className="muted">هر ردیف در جدول <code>geo_mentions</code> باید دارای نام مکان، دقت (کشور، استان، شهر یا مختصات)، روش استخراج، اطمینان و <b>متن شاهد</b> از خود خبر باشد و به خبر یا رویداد پیوند بخورد. نقطه بدون شاهد متنی پذیرفته نمی‌شود.</p>
      </section>
    </Shell>
  );
}

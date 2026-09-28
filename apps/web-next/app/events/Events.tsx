'use client';
import { useState } from 'react';
import { Shell } from '../design/Shell';
import { useApi, useNow } from '../design/useApi';
import type { EventRow } from '../design/types';
import { fmt } from '../design/format';
import { CardBones, Empty, Failure, PageHead, Pager, Segmented } from '../design/ui';
import { EventTimeline } from '../components/EventTimeline';

export function Events() {
  const [sort, setSort] = useState<'latest' | 'important' | 'largest'>('latest');
  const [page, setPage] = useState(1);
  const q = useApi<{ events: EventRow[]; total: number; has_next: boolean; method: { current: string; version: string } }>(`timeline/events?sort=${sort}&page=${page}&page_size=20`, [sort, page]);
  const now = useNow();
  return (
    <Shell>
      <PageHead eyebrow="رویدادها" title="خط زمانی رویدادها"
        lede="خبرهایی که با شواهد متنی به یک رخداد واحد اشاره می‌کنند در یک رویداد گروه‌بندی می‌شوند. گروه‌بندی قطعی و قابل توضیح است؛ دلیل عضویت هر خبر در صفحه رویداد نمایش داده می‌شود.">
        {q.data && <span className="muted">{fmt(q.data.total)} رویداد · روش {q.data.method.current} نسخه {q.data.method.version}</span>}
      </PageHead>
      <Segmented label="ترتیب" value={sort} onChange={(v) => { setSort(v); setPage(1); }} items={[['latest', 'جدیدترین تحول'], ['important', 'بیشترین منبع مستقل'], ['largest', 'بیشترین خبر']]} />
      {q.error && <Failure onRetry={q.reload} />}
      {!q.data && !q.error && <CardBones n={5} image={false} />}
      {q.data && (q.data.events.length ? (
        <>
          <EventTimeline events={q.data.events} now={now} />
          <Pager page={page} hasNext={q.data.has_next} total={q.data.total} onPage={setPage} />
        </>
      ) : <Empty title="هنوز رویدادی شناسایی نشده است">خوشه‌بندی هر ۱۵ دقیقه روی همه خبرها اجرا می‌شود؛ فقط خبرهایی که نام‌های خاص کم‌بسامد و واژگان مشترک دارند گروه می‌شوند.</Empty>)}
    </Shell>
  );
}

'use client';
import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Shell } from '../../design/Shell';
import { useApi, useNow } from '../../design/useApi';
import type { FeedResponse } from '../../design/types';
import { catVar, fmt, fmtDay, fmtRelative } from '../../design/format';
import { CardBones, Empty, Failure, PageHead, Pager, Segmented, Tag, Bone } from '../../design/ui';
import { Bars, Columns, Figure } from '../../design/charts';
import { NewsCard } from '../../components/NewsCard';

interface Topic {
  slug: string; kind: 'category' | 'subtopic'; label: string; parent: { id: string; label: string } | null;
  subtopics: { id: string; label: string }[]; keywords_en: string[]; total: number;
  series_30d: { day: string; n: number }[]; top_sources: { source_id: string; name: string; n: number }[];
  events: { event_id: string; title: string; member_count: number; source_count: number; last_updated_at: string }[]; taxonomy_version: string;
}

export function TopicDetail() {
  const { slug } = useParams<{ slug: string }>();
  const t = useApi<Topic>('topics/' + encodeURIComponent(slug), [slug]);
  const [sort, setSort] = useState<'newest' | 'important'>('newest');
  const [page, setPage] = useState(1);
  const param = t.data?.kind === 'subtopic' ? `topic=${slug}` : `category=${slug}`;
  const f = useApi<FeedResponse>(t.data ? `feed?${param}&sort=${sort}&page=${page}&page_size=15` : null, [slug, sort, page, t.data?.kind]);
  const now = useNow();
  if (t.error) return <Shell><Failure onRetry={t.reload}>این موضوع در طبقه‌بندی فعلی وجود ندارد.</Failure></Shell>;
  if (!t.data) return <Shell><Bone h={28} w="40%" /><CardBones n={3} /></Shell>;
  const d = t.data;
  const days: { key: string; label: string; value: number }[] = [];
  const byDay = new Map(d.series_30d.map((s) => [s.day.slice(0, 10), s.n]));
  for (let i = 29; i >= 0; i--) {
    const day = new Date(Date.now() - i * 86400000).toISOString().slice(0, 10);
    days.push({ key: day, label: fmtDay(day), value: byDay.get(day) ?? 0 });
  }
  const catId = d.kind === 'category' ? d.slug : d.parent?.id;
  return (
    <Shell>
      <nav className="muted" aria-label="مسیر"><Link href="/topics">موضوعات</Link>{d.parent && <> / <Link href={`/topics/${d.parent.id}`}>{d.parent.label}</Link></>}</nav>
      <PageHead eyebrow={d.kind === 'category' ? 'دسته اصلی' : 'زیرموضوع'} title={d.label}
        lede={<>{fmt(d.total)} خبر در این {d.kind === 'category' ? 'دسته' : 'زیرموضوع'}. نشانی این صفحه و فیلترهای آن قابل اشتراک‌گذاری است.</>}>
        <span style={{ width: 14, height: 14, borderRadius: 3, background: catVar(catId) }} aria-hidden="true" />
        <Link href={`/news?${param}`} className="btn-ghost">باز کردن در جریان خبر</Link>
      </PageHead>
      {d.subtopics.length > 0 && <div className="topic-subs">{d.subtopics.map((s) => <Link key={s.id} href={`/topics/${s.id}`}>{s.label}</Link>)}</div>}
      <div className="grid-2">
        <Figure title="حجم پوشش روزانه" question="پوشش این موضوع در ۳۰ روز اخیر چگونه تغییر کرده است؟" unit="خبر در روز" range="۳۰ روز" source="زمان انتشار خبرها، به وقت تهران"
          table={{ head: ['روز', 'تعداد'], rows: days.map((x) => [x.label, x.value]) }}>
          <Columns data={days} height={150} />
        </Figure>
        <Figure title="منابع پوشش‌دهنده" question="کدام منابع بیشترین خبر را در این موضوع منتشر کرده‌اند؟" unit="خبر" source="همه زمان‌ها"
          empty={d.top_sources.length ? undefined : <Empty title="منبعی ثبت نشده" />}>
          <Bars data={d.top_sources.map((s) => ({ key: s.source_id, label: <bdi>{s.name}</bdi>, value: s.n }))} href={(k) => `/sources/${k}`} />
        </Figure>
      </div>
      {d.events.length > 0 && (
        <section className="panel"><h2 className="brief-sub">رویدادهای این موضوع</h2>
          <ul className="prov" style={{ marginTop: 10 }}>{d.events.map((e) => <li key={e.event_id}><Tag>{fmt(e.member_count)}</Tag><div><Link href={`/events/${e.event_id}`} dir="ltr">{e.title}</Link><small>{fmt(e.source_count)} منبع · {fmtRelative(e.last_updated_at, now)}</small></div></li>)}</ul>
        </section>
      )}
      <section>
        <div className="stream-head"><h2 className="brief-sub">خبرها</h2><Segmented label="مرتب‌سازی" value={sort} onChange={(v) => { setSort(v); setPage(1); }} items={[['newest', 'جدیدترین'], ['important', 'مهم‌ترین']]} /></div>
        {f.error && <Failure onRetry={f.reload} />}
        {!f.data && !f.error && <CardBones n={4} />}
        {f.data && (f.data.items.length ? <>{f.data.items.map((i) => <NewsCard key={i.item_id} item={i} now={now} variant="row" />)}<Pager page={page} hasNext={f.data.has_next} total={f.data.total} onPage={setPage} /></> : <Empty title="خبری در این موضوع نیست" />)}
      </section>
      <details className="note"><summary>کلیدواژه‌های قاعده این موضوع (نسخه {d.taxonomy_version})</summary><p dir="ltr" style={{ marginTop: 8 }}>{d.keywords_en.join(' · ')}</p></details>
    </Shell>
  );
}

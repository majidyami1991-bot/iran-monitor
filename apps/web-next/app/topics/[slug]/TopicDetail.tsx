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
import { usePrefs } from '../../design/prefs';
import { getCategoryLabel, getSubtopicLabel } from '../../design/taxonomy';

interface Topic {
  slug: string; kind: 'category' | 'subtopic'; label: string; parent: { id: string; label: string } | null;
  subtopics: { id: string; label: string }[]; keywords_en: string[]; total: number;
  series_30d: { day: string; n: number }[]; top_sources: { source_id: string; name: string; n: number }[];
  events: { event_id: string; title: string; member_count: number; source_count: number; last_updated_at: string }[]; taxonomy_version: string;
}

export function TopicDetail() {
  const { slug } = useParams<{ slug: string }>();
  const { contentLang } = usePrefs();
  const isEn = contentLang === 'en';
  const t = useApi<Topic>('topics/' + encodeURIComponent(slug), [slug]);
  const [sort, setSort] = useState<'newest' | 'important'>('newest');
  const [page, setPage] = useState(1);
  const param = t.data?.kind === 'subtopic' ? `topic=${slug}` : `category=${slug}`;
  const f = useApi<FeedResponse>(t.data ? `feed?${param}&sort=${sort}&page=${page}&page_size=15` : null, [slug, sort, page, t.data?.kind]);
  const now = useNow();
  if (t.error) return <Shell><Failure onRetry={t.reload}>{isEn ? 'This topic does not exist in the current taxonomy.' : 'این موضوع در طبقه‌بندی فعلی وجود ندارد.'}</Failure></Shell>;
  if (!t.data) return <Shell><Bone h={28} w="40%" /><CardBones n={3} /></Shell>;
  const d = t.data;
  const days: { key: string; label: string; value: number }[] = [];
  const byDay = new Map(d.series_30d.map((s) => [s.day.slice(0, 10), s.n]));
  for (let i = 29; i >= 0; i--) {
    const day = new Date(Date.now() - i * 86400000).toISOString().slice(0, 10);
    days.push({ key: day, label: fmtDay(day), value: byDay.get(day) ?? 0 });
  }
  const catId = d.kind === 'category' ? d.slug : d.parent?.id;
  const topicTitle = d.kind === 'category' ? getCategoryLabel(d.slug, isEn) : getSubtopicLabel(d.slug, isEn);
  return (
    <Shell>
      <nav className="muted" aria-label={isEn ? 'Breadcrumbs' : 'مسیر'}><Link href="/topics">{isEn ? 'Topics' : 'موضوعات'}</Link>{d.parent && <> / <Link href={`/topics/${d.parent.id}`}>{getCategoryLabel(d.parent.id, isEn)}</Link></>}</nav>
      <PageHead eyebrow={d.kind === 'category' ? (isEn ? 'Primary Category' : 'دسته اصلی') : (isEn ? 'Subtopic' : 'زیرموضوع')} title={topicTitle}
        lede={<>{fmt(d.total)} {isEn ? `articles in this ${d.kind === 'category' ? 'category' : 'subtopic'}.` : `خبر در این ${d.kind === 'category' ? 'دسته' : 'زیرموضوع'}. نشانی این صفحه و فیلترهای آن قابل اشتراک‌گذاری است.`}</>}>
        <span style={{ width: 14, height: 14, borderRadius: 3, background: catVar(catId) }} aria-hidden="true" />
        <Link href={`/news?${param}`} className="btn-ghost">{isEn ? 'Open in News Stream' : 'باز کردن در جریان خبر'}</Link>
      </PageHead>
      {d.subtopics.length > 0 && <div className="topic-subs">{d.subtopics.map((s) => <Link key={s.id} href={`/topics/${s.id}`}>{getSubtopicLabel(s.id, isEn)}</Link>)}</div>}
      <div className="grid-2">
        <Figure title={isEn ? 'Daily Coverage Volume' : 'حجم پوشش روزانه'} question={isEn ? 'How has coverage changed over the past 30 days?' : 'پوشش این موضوع در ۳۰ روز اخیر چگونه تغییر کرده است؟'} unit={isEn ? 'articles/day' : 'خبر در روز'} range={isEn ? '30 days' : '۳۰ روز'} source={isEn ? 'Publication time, Tehran time' : 'زمان انتشار خبرها، به وقت تهران'}
          table={{ head: isEn ? ['Day', 'Count'] : ['روز', 'تعداد'], rows: days.map((x) => [x.label, x.value]) }}>
          <Columns data={days} height={150} />
        </Figure>
        <Figure title={isEn ? 'Top Sources' : 'منابع پوشش‌دهنده'} question={isEn ? 'Which sources published the most articles on this topic?' : 'کدام منابع بیشترین خبر را در این موضوع منتشر کرده‌اند؟'} unit={isEn ? 'articles' : 'خبر'} source={isEn ? 'All time' : 'همه زمان‌ها'}
          empty={d.top_sources.length ? undefined : <Empty title={isEn ? 'No sources recorded' : 'منبعی ثبت نشده'} />}>
          <Bars data={d.top_sources.map((s) => ({ key: s.source_id, label: <bdi>{s.name}</bdi>, value: s.n }))} href={(k) => `/sources/${k}`} />
        </Figure>
      </div>
      {d.events.length > 0 && (
        <section className="panel"><h2 className="brief-sub">{isEn ? 'Events in this topic' : 'رویدادهای این موضوع'}</h2>
          <ul className="prov" style={{ marginTop: 10 }}>{d.events.map((e) => <li key={e.event_id}><Tag>{fmt(e.member_count)}</Tag><div><Link href={`/events/${e.event_id}`} dir="ltr">{e.title}</Link><small>{fmt(e.source_count)} {isEn ? (e.source_count === 1 ? 'source' : 'sources') : 'منبع'} · {fmtRelative(e.last_updated_at, now, isEn)}</small></div></li>)}</ul>
        </section>
      )}
      <section>
        <div className="stream-head"><h2 className="brief-sub">{isEn ? 'News' : 'خبرها'}</h2><Segmented label={isEn ? 'Sort' : 'مرتب‌سازی'} value={sort} onChange={(v) => { setSort(v); setPage(1); }} items={[['newest', isEn ? 'Newest' : 'جدیدترین'], ['important', isEn ? 'Most Important' : 'مهم‌ترین']]} /></div>
        {f.error && <Failure onRetry={f.reload} />}
        {!f.data && !f.error && <CardBones n={4} />}
        {f.data && (f.data.items.length ? <>{f.data.items.map((i) => <NewsCard key={i.item_id} item={i} now={now} variant="row" />)}<Pager page={page} hasNext={f.data.has_next} total={f.data.total} onPage={setPage} /></> : <Empty title={isEn ? 'No articles in this topic' : 'خبری در این موضوع نیست'} />)}
      </section>
      <details className="note"><summary>{isEn ? `Rule keywords (Taxonomy v${d.taxonomy_version})` : `کلیدواژه‌های قاعده این موضوع (نسخه ${d.taxonomy_version})`}</summary><p dir="ltr" style={{ marginTop: 8 }}>{d.keywords_en.join(' · ')}</p></details>
    </Shell>
  );
}

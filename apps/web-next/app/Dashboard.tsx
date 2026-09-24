'use client';
import Link from 'next/link';
import { ArrowUpLeft, Newspaper, Globe2, Clock3, ShieldCheck, HeartPulse, TrendingUp, TrendingDown, Link2, VolumeX, Hash, Radio } from 'lucide-react';
import { Shell } from './design/Shell';
import { useApi, useNow } from './design/useApi';
import { ErrorState, Skeleton, StatusPill, toHealth } from './design/ui';
import { NewsCard } from './components/NewsCard';
import type { NewsListItem } from './components/news-types';
import { fmt, fmtDateTime } from './design/format';

interface Overview { total_items: number; items_24h: number; items_7d: number; healthy_sources: number; delayed_or_failed_sources: number; last_run: { status: string; finished_at: string | null } | null }
interface Coverage { registered: number; executable: number; monitored: number }
interface CollectionStatus { scheduler_enabled: boolean; collector_health: string; next_run_at: string | null; last_run: { status: string; sources_succeeded: number; sources_planned: number; items_inserted: number; finished_at: string | null } | null }
interface TopicStats { topics: { topic: string; count: number; sources: number }[] }
interface SourceStat { sources: { source_id: string; display_name: string; hostname: string; item_count: number }[] }
interface Brief {
  window: string; items: number; active_sources: number; previous_items: number; change: number;
  categories: [string, number][]; topics: [string, number, number][];
  leading_sources: [string, string, number][]; sources_without_recent_items: [string, string][];
}
interface EventRow { event_id: string; title: string; member_count: number }

export function Dashboard() {
  const now = useNow();
  const overviewQ = useApi<Overview>('stats/overview');
  const coverageQ = useApi<Coverage>('sources/coverage');
  const statusQ = useApi<CollectionStatus>('collection/status');
  const newsQ = useApi<{ items: NewsListItem[]; total: number }>('news?page_size=8');
  const topicsQ = useApi<TopicStats>('stats/topics');
  const sourceStatQ = useApi<SourceStat>('stats/sources');
  const briefQ = useApi<Brief>('stats/brief?window=24h');
  const eventsQ = useApi<{ events: EventRow[] }>('events?page_size=3');
  const categoriesQ = useApi<{ categories: { id: string; label: string; count: number }[] }>('categories?window=30d');

  const error = overviewQ.error;
  const loading = overviewQ.loading;
  const o = overviewQ.data;

  return (
    <Shell title="نمای عملیاتی" breadcrumb="نمای عملیاتی">
      <div className="page-head">
        <div><h1>نبض اخبار و تحولات</h1><p>در منابع تحت پوشش چه اتفاقی افتاده، چه زمانی و ذیل چه موضوعی.</p></div>
        {statusQ.data && (
          <div className="dash-status">
            <StatusPill health={statusQ.data.scheduler_enabled ? toHealth(statusQ.data.collector_health) : 'stopped'}
              label={statusQ.data.scheduler_enabled ? undefined : 'زمان‌بندی متوقف'} />
            <span>{statusQ.data.scheduler_enabled ? `چرخه بعدی ${fmtDateTime(statusQ.data.next_run_at)}` : 'جمع‌آوری غیرفعال'}</span>
          </div>
        )}
      </div>

      {error && <ErrorState onRetry={overviewQ.reload}>دریافت اطلاعات ممکن نشد؛ داده‌های قبلی، در صورت وجود، حفظ شده‌اند.</ErrorState>}
      {loading && <Skeleton height={110} radius={14} />}

      {!loading && !error && o && (
        <>
          <div className="stat-grid" style={{ marginBottom: 'var(--space-5)' }}>
            <div className="stat-card"><span className="stat-label"><Newspaper size={14} />۲۴ ساعت اخیر</span><strong>{fmt(o.items_24h)}</strong><small>خبر تازه</small></div>
            <div className="stat-card"><span className="stat-label"><Newspaper size={14} />۷ روز اخیر</span><strong>{fmt(o.items_7d)}</strong><small>خبر</small></div>
            <div className="stat-card"><span className="stat-label"><Globe2 size={14} />در حال پایش</span><strong>{fmt(coverageQ.data?.monitored)}</strong><small>از {fmt(coverageQ.data?.registered)} منبع ثبت‌شده</small></div>
            <div className="stat-card"><span className="stat-label"><HeartPulse size={14} />نیازمند توجه</span><strong>{fmt(o.delayed_or_failed_sources)}</strong><small>منبع</small></div>
            <div className="stat-card"><span className="stat-label"><Clock3 size={14} />آخرین چرخه موفق</span><strong className="stat-card-time">{fmtDateTime(o.last_run?.finished_at)}</strong></div>
            <div className="stat-card"><span className="stat-label"><ShieldCheck size={14} />کل اخبار</span><strong>{fmt(o.total_items)}</strong><small>در پایگاه داده</small></div>
          </div>

          <section className="brief-section">
            <div className="brief-head">
              <h2>چه اتفاقی افتاده است؟ <span style={{ color: 'var(--text-tertiary)', fontWeight: 400, fontSize: 'var(--text-xs)' }}>(۲۴ ساعت اخیر)</span></h2>
              {briefQ.data && (
                <span className={'brief-change ' + (briefQ.data.change >= 0 ? 'up' : 'down')}>
                  {briefQ.data.change >= 0 ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                  {fmt(briefQ.data.items)} خبر ({briefQ.data.change >= 0 ? '+' : ''}{fmt(briefQ.data.change)} نسبت به روز قبل)
                </span>
              )}
            </div>
            {briefQ.loading && <div className="brief-grid">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height={140} radius={12} />)}</div>}
            {briefQ.error && <ErrorState onRetry={briefQ.reload}>خلاصه وضعیت دریافت نشد.</ErrorState>}
            {!briefQ.loading && !briefQ.error && briefQ.data && (
              <div className="brief-grid">
                <div className="brief-card">
                  <span className="brief-card-title"><Link2 size={13} /> رویدادهای اصلی</span>
                  {eventsQ.data?.events.length ? eventsQ.data.events.map((e) => (
                    <Link key={e.event_id} href={'/events/' + encodeURIComponent(e.event_id)} className="brief-card-row" dir="rtl">
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{e.title}</span>
                      <span>{fmt(e.member_count)}</span>
                    </Link>
                  )) : <span className="brief-card-empty">رویداد مشترکی شناسایی نشده</span>}
                </div>
                <div className="brief-card">
                  <span className="brief-card-title"><Hash size={13} /> موضوعات فعال</span>
                  {briefQ.data.topics.slice(0, 3).map(([topic, count]) => (
                    <Link key={topic} href={'/news?topic=' + encodeURIComponent(topic)} className="brief-card-row" dir="ltr">
                      <span>{topic}</span><span>{fmt(count)}</span>
                    </Link>
                  ))}
                </div>
                <div className="brief-card">
                  <span className="brief-card-title"><Radio size={13} /> منابع فعال</span>
                  {briefQ.data.leading_sources.slice(0, 3).map(([name, hostname, count]) => (
                    <div key={hostname} className="brief-card-row"><span>{name}</span><span>{fmt(count)}</span></div>
                  ))}
                </div>
                <div className="brief-card">
                  <span className="brief-card-title"><VolumeX size={13} /> منابع ساکت (بدون خبر تازه)</span>
                  {briefQ.data.sources_without_recent_items.length ? briefQ.data.sources_without_recent_items.slice(0, 4).map(([name, hostname]) => (
                    <div key={hostname} className="brief-card-row"><span>{name}</span></div>
                  )) : <span className="brief-card-empty">همه منابع در این بازه خبر داشته‌اند</span>}
                </div>
              </div>
            )}
          </section>

          <div className="dash-grid">
            <section className="card dash-feed">
              <div className="card-title"><h2>جریان اخبار</h2><Link href="/news">مشاهده همه <ArrowUpLeft size={14} /></Link></div>
              {newsQ.loading && Array.from({ length: 4 }, (_, i) => <Skeleton key={i} height={116} radius={10} />).map((s, i) => <div key={i} style={{ marginBottom: 12 }}>{s}</div>)}
              {newsQ.data?.items.map((item) => <NewsCard key={item.item_id} item={item} now={now} />)}
            </section>

            <div className="dash-side">
              <section className="card">
                <div className="card-title"><h2>توزیع دسته‌بندی</h2><Link href="/categories">جزئیات</Link></div>
                {categoriesQ.data?.categories.length ? (
                  categoriesQ.data.categories.map((c) => {
                    const max = categoriesQ.data!.categories[0].count || 1;
                    return (
                      <Link key={c.id} href={'/categories/' + encodeURIComponent(c.id)} className="dash-coverage-row" dir="rtl">
                        <span style={{ display: 'grid', gap: 4, flex: 1 }}>
                          {c.label}
                          <span className="topic-track"><i style={{ width: `${(c.count / max) * 100}%` }} /></span>
                        </span>
                        <strong style={{ marginRight: 8 }}>{fmt(c.count)}</strong>
                      </Link>
                    );
                  })
                ) : <span className="brief-card-empty">داده‌ای ثبت نشده</span>}
              </section>

              <section className="card">
                <div className="card-title"><h2>پوشش منابع</h2><Link href="/sources">جزئیات</Link></div>
                <div className="dash-coverage-row"><span>ثبت‌شده</span><strong>{fmt(coverageQ.data?.registered)}</strong></div>
                <div className="dash-coverage-row"><span>قابل اجرا</span><strong>{fmt(coverageQ.data?.executable)}</strong></div>
                <div className="dash-coverage-row"><span>در حال پایش</span><strong>{fmt(coverageQ.data?.monitored)}</strong></div>
              </section>

              <section className="card">
                <div className="card-title"><h2>موضوعات پرتکرار</h2><Link href="/topics">همه</Link></div>
                {topicsQ.data?.topics.slice(0, 6).map((t) => (
                  <Link key={t.topic} href={'/news?topic=' + encodeURIComponent(t.topic)} className="dash-topic-row">
                    <span dir="ltr">{t.topic}</span><span>{fmt(t.count)}</span>
                  </Link>
                ))}
              </section>

              <section className="card">
                <div className="card-title"><h2>فعال‌ترین منابع</h2></div>
                {sourceStatQ.data?.sources.slice().sort((a, b) => b.item_count - a.item_count).slice(0, 5).map((s) => (
                  <Link key={s.source_id} href={'/sources/' + s.source_id} className="dash-topic-row">
                    <span>{s.display_name || s.hostname}</span><span>{fmt(s.item_count)}</span>
                  </Link>
                ))}
              </section>
            </div>
          </div>
        </>
      )}
    </Shell>
  );
}

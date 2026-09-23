'use client';
import Link from 'next/link';
import { ArrowUpLeft, Newspaper, Globe2, Clock3, ShieldCheck, HeartPulse } from 'lucide-react';
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

export function Dashboard() {
  const now = useNow();
  const overviewQ = useApi<Overview>('stats/overview');
  const coverageQ = useApi<Coverage>('sources/coverage');
  const statusQ = useApi<CollectionStatus>('collection/status');
  const newsQ = useApi<{ items: NewsListItem[]; total: number }>('news?page_size=8');
  const topicsQ = useApi<TopicStats>('stats/topics');
  const sourceStatQ = useApi<SourceStat>('stats/sources');

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

          <div className="dash-grid">
            <section className="card dash-feed">
              <div className="card-title"><h2>جریان اخبار</h2><Link href="/news">مشاهده همه <ArrowUpLeft size={14} /></Link></div>
              {newsQ.loading && Array.from({ length: 4 }, (_, i) => <Skeleton key={i} height={116} radius={10} />).map((s, i) => <div key={i} style={{ marginBottom: 12 }}>{s}</div>)}
              {newsQ.data?.items.map((item) => <NewsCard key={item.item_id} item={item} now={now} />)}
            </section>

            <div className="dash-side">
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

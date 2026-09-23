'use client';
import { useState } from 'react';
import Link from 'next/link';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { HeartPulse } from 'lucide-react';
import { Shell } from '../design/Shell';
import { useApi } from '../design/useApi';
import { ErrorState, Skeleton, StatusPill, toHealth } from '../design/ui';
import { fmt, fmtDateTime } from '../design/format';

interface Overview { total_items: number; items_24h: number; items_7d: number; summary_available: number; summary_unavailable_known: number; summary_status_unknown: number; missing_publication_date: number; uncategorized: number; provenance_complete: number; sources: number; healthy_sources: number; not_run_sources: number; delayed_or_failed_sources: number; last_run: unknown }
interface Timeline { series: { bucket: string; count: number }[]; unit: string }
interface Quality { duplicates_prevented: number; rejected: number; classified: number }
interface TopicStats { categories: { label: string; count: number }[]; topics: { topic: string; count: number; sources: number }[] }
interface Collection { scheduler_enabled: boolean; collector_health: string; next_run_at: string | null }

const WINDOWS: [string, string][] = [['24h', '۲۴ ساعت'], ['7d', '۷ روز'], ['30d', '۳۰ روز']];

export function Analytics() {
  const [win, setWin] = useState('24h');
  const overviewQ = useApi<Overview>('stats/overview');
  const timelineQ = useApi<Timeline>('stats/timeline?window=' + win, [win]);
  const topicsQ = useApi<TopicStats>('stats/topics');
  const qualityQ = useApi<Quality>('stats/quality');
  const collectionQ = useApi<Collection>('collection/status');

  const error = overviewQ.error || timelineQ.error;
  const loading = overviewQ.loading || timelineQ.loading;
  const o = overviewQ.data;

  return (
    <Shell title="تحلیل آماری" breadcrumb="تحلیل آماری">
      <div className="page-head">
        <div><h1>تحلیل آماری عملیاتی</h1><p>شمارش توصیفی رکوردهای ذخیره‌شده؛ تحلیل علّی یا پیش‌بینی نیست.</p></div>
        <Link href="/monitoring" className="btn btn-secondary"><HeartPulse size={16} />وضعیت پایش زنده</Link>
      </div>

      {collectionQ.data && (
        <div className="analytics-status-line">
          <StatusPill health={collectionQ.data.scheduler_enabled ? toHealth(collectionQ.data.collector_health) : 'stopped'}
            label={collectionQ.data.scheduler_enabled ? undefined : 'زمان‌بندی متوقف'} />
          <span>{collectionQ.data.scheduler_enabled ? `چرخه بعدی: ${fmtDateTime(collectionQ.data.next_run_at)}` : 'جمع‌آوری خودکار غیرفعال است'}</span>
        </div>
      )}

      {error && <ErrorState onRetry={overviewQ.reload}>دریافت آمار ممکن نشد.</ErrorState>}
      {loading && <Skeleton height={200} radius={14} />}

      {!loading && !error && o && (
        <>
          <div className="stat-grid" style={{ margin: '20px 0' }}>
            <div className="stat-card"><span className="stat-label">کل اخبار</span><strong>{fmt(o.total_items)}</strong></div>
            <div className="stat-card"><span className="stat-label">۲۴ ساعت</span><strong>{fmt(o.items_24h)}</strong></div>
            <div className="stat-card"><span className="stat-label">۷ روز</span><strong>{fmt(o.items_7d)}</strong></div>
            <div className="stat-card"><span className="stat-label">خلاصه موجود</span><strong>{fmt(o.summary_available)}</strong></div>
            <div className="stat-card"><span className="stat-label">منشأ کامل</span><strong>{fmt(o.provenance_complete)}</strong></div>
            <div className="stat-card"><span className="stat-label">منابع سالم</span><strong>{fmt(o.healthy_sources)} / {fmt(o.sources)}</strong></div>
          </div>

          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-title"><h2>انتشار در بازه انتخاب‌شده</h2></div>
            <div className="periods">{WINDOWS.map(([v, t]) => <button key={v} className={win === v ? 'selected' : ''} onClick={() => setWin(v)}>{t}</button>)}</div>
            <div className="chart-box" dir="ltr" style={{ marginTop: 12 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={timelineQ.data?.series || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid stroke="var(--border-subtle)" vertical={false} />
                  <XAxis dataKey="bucket" tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }} tickFormatter={(v) => new Date(v).toLocaleString('fa-IR', { timeZone: 'UTC', hour: '2-digit', day: 'numeric', month: 'short' })} minTickGap={28} />
                  <YAxis allowDecimals={false} tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }} width={28} />
                  <Tooltip contentStyle={{ background: 'var(--surface-3)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="count" name="تعداد خبر" fill="var(--accent)" radius={[3, 3, 0, 0]} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="chart-caption">واحد: {timelineQ.data?.unit === 'hour' ? 'ساعتی' : 'روزانه'} · UTC · بر اساس زمان انتشار یا دریافت</p>
          </div>

          <div className="analytics-grid">
            <div className="card">
              <div className="card-title"><h2>توزیع دسته‌بندی قاعده‌محور</h2></div>
              {topicsQ.data?.categories.slice(0, 10).map((c) => (
                <Link key={c.label} href={'/news?category=' + encodeURIComponent(c.label)} className="topic-row" style={{ gridTemplateColumns: 'minmax(0,1fr) auto' }}>
                  <span>{c.label}</span><span className="topic-count">{fmt(c.count)}</span>
                </Link>
              ))}
            </div>
            <div className="card">
              <div className="card-title"><h2>واژه‌های پرتکرار</h2><Link href="/topics">همه موضوعات</Link></div>
              {topicsQ.data?.topics.slice(0, 10).map((t) => (
                <Link key={t.topic} href={'/news?topic=' + encodeURIComponent(t.topic)} className="topic-row" style={{ gridTemplateColumns: 'minmax(0,1fr) auto' }}>
                  <span dir="ltr" style={{ textAlign: 'left' }}>{t.topic}</span><span className="topic-count">{fmt(t.count)} خبر / {fmt(t.sources)} منبع</span>
                </Link>
              ))}
            </div>
          </div>

          <div className="card" style={{ marginTop: 20 }}>
            <div className="card-title"><h2>کیفیت داده</h2></div>
            <p className="chart-caption" style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
              دسته «سایر»: {fmt(o.uncategorized)} · تاریخ انتشار ناموجود: {fmt(o.missing_publication_date)} ·
              جلوگیری از تکرار: {fmt(qualityQ.data?.duplicates_prevented || 0)} · رد‌شده در دریافت: {fmt(qualityQ.data?.rejected || 0)}
            </p>
          </div>
        </>
      )}
    </Shell>
  );
}

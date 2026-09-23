'use client';
import { useParams } from 'next/navigation';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { ExternalLink } from 'lucide-react';
import { Shell } from '../../design/Shell';
import { useApi, useNow } from '../../design/useApi';
import { EmptyState, ErrorState, Skeleton, SourceMark, StatusPill, toHealth } from '../../design/ui';
import { NewsCard } from '../../components/NewsCard';
import type { NewsListItem } from '../../components/news-types';
import { fmt, fmtDateTime, fmtDateShort, safeUrl, sourceColor } from '../../design/format';

interface SourceDetailData {
  source_id: string; display_name: string | null; canonical_url: string | null; hostname: string | null;
  source_type: string | null; category: string | null; feed_url: string | null; collection_tier: string | null;
  enabled_for_scheduler: boolean; last_attempt_at: string | null; last_success_at: string | null;
  last_http_status: number | null; consecutive_failures: number; health_status: string;
  item_count: number; items_24h: number; items_7d: number; latest_published: string | null;
  provenance: [string, number][]; timeline: [string, number][]; latest_items: NewsListItem[];
}

export function SourceDetail() {
  const params = useParams<{ id?: string }>();
  const id = params?.id || '';
  const { data: s, error, loading, reload } = useApi<SourceDetailData>('sources/' + encodeURIComponent(id), [id]);
  const now = useNow();

  if (loading) return <Shell title="منبع" breadcrumb="منبع"><Skeleton height={200} radius={14} /></Shell>;
  if (error || !s) return <Shell title="منبع" breadcrumb="منبع"><ErrorState onRetry={reload}>دریافت اطلاعات منبع ممکن نشد.</ErrorState></Shell>;

  const name = s.display_name || s.hostname || 'نام ثبت نشده';
  const color = sourceColor(s.source_id);
  const trend = (s.timeline || []).slice().reverse().map(([bucket, count]) => ({ day: fmtDateShort(bucket), count }));

  return (
    <Shell title={name} breadcrumb={name}>
      <div className="source-detail-head">
        <SourceMark name={name} color={color} />
        <div>
          <h1>{name}</h1>
          <p dir="ltr">{s.hostname}{s.feed_url ? ' · ' + s.feed_url : ''}</p>
        </div>
        <StatusPill health={toHealth(s.health_status)} />
        {safeUrl(s.canonical_url || undefined) && <a href={safeUrl(s.canonical_url || undefined)} target="_blank" rel="noopener noreferrer" className="btn btn-secondary">وب‌سایت اصلی <ExternalLink size={14} /></a>}
      </div>

      <div className="stat-grid" style={{ margin: '20px 0' }}>
        <div className="stat-card"><span className="stat-label">کل اخبار</span><strong>{fmt(s.item_count)}</strong></div>
        <div className="stat-card"><span className="stat-label">۲۴ ساعت</span><strong>{fmt(s.items_24h)}</strong></div>
        <div className="stat-card"><span className="stat-label">۷ روز</span><strong>{fmt(s.items_7d)}</strong></div>
        <div className="stat-card"><span className="stat-label">شکست متوالی</span><strong>{fmt(s.consecutive_failures)}</strong></div>
        <div className="stat-card"><span className="stat-label">آخرین دریافت موفق</span><strong className="stat-card-time">{fmtDateTime(s.last_success_at)}</strong></div>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-title"><h2>حجم انتشار روزانه</h2></div>
        {trend.length ? (
          <div className="chart-box" dir="ltr">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs><linearGradient id="src-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--accent-strong)" stopOpacity={0.3} /><stop offset="100%" stopColor="var(--accent-strong)" stopOpacity={0} /></linearGradient></defs>
                <CartesianGrid stroke="var(--border-subtle)" vertical={false} />
                <XAxis dataKey="day" tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }} minTickGap={24} />
                <YAxis allowDecimals={false} tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }} width={28} />
                <Tooltip contentStyle={{ background: 'var(--surface-3)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }} />
                <Area type="monotone" dataKey="count" name="تعداد خبر" stroke="var(--accent-strong)" fill="url(#src-area)" strokeWidth={2} isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : <EmptyState title="برای این منبع سری زمانی ثبت نشده">داده کافی برای رسم نمودار موجود نیست.</EmptyState>}
        <p className="chart-caption">بر اساس تاریخ انتشار یا زمان دریافت ذخیره‌شده؛ این نمودار uptime را نشان نمی‌دهد.</p>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-title"><h2>وضعیت منشأ</h2></div>
        {(s.provenance || []).length ? (s.provenance || []).map(([status, count]) => <p key={status} className="source-provenance-row">{status} <b>{fmt(count)}</b></p>)
          : <EmptyState title="داده منشأ ثبت نشده" />}
      </div>

      <div className="card-title" style={{ marginTop: 24 }}><h2>آخرین خبرهای این منبع</h2></div>
      {(s.latest_items || []).length ? s.latest_items.map((item) => <NewsCard key={item.item_id} item={item} now={now} />)
        : <EmptyState title="خبری برای این منبع ثبت نشده" />}
    </Shell>
  );
}

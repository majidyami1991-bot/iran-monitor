'use client';
import { useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { Newspaper, Link2 } from 'lucide-react';
import { Shell } from '../../design/Shell';
import { useApi } from '../../design/useApi';
import { ErrorState, Skeleton, EmptyState, Badge } from '../../design/ui';
import { fmt, fmtDateShort, fmtDateTime, isPersian } from '../../design/format';

interface LatestItem { item_id: string; title: string; published_at: string | null; source_name: string; confidence: number | null }
interface Data {
  id: string; label: string; is_fallback: boolean; total_items: number; taxonomy_version: string;
  timeline: [string, number][]; main_sources: [string, number][];
  subtopics: { id: string; label: string; count: number }[];
  key_events: { event_id: string; title: string; member_count: number }[];
  latest_items: LatestItem[];
  other_explanation: string | null;
  review_sample: LatestItem[] | null;
}

export function CategoryDetailPage() {
  const params = useParams<{ id?: string }>();
  const id = params?.id || '';
  const [window_, setWindow] = useState('30d');
  const { data, error, loading, reload } = useApi<Data>('categories/' + encodeURIComponent(id) + '?window=' + window_, [id, window_]);

  const trend = (data?.timeline || []).map(([d, n]) => ({ day: fmtDateShort(d), count: n }));

  return (
    <Shell title="دسته‌بندی" breadcrumb={data?.label || 'دسته‌بندی'}>
      {loading && <div style={{ display: 'grid', gap: 12 }}><Skeleton height={28} width={320} /><Skeleton height={220} radius={14} /></div>}
      {error && <ErrorState onRetry={reload}>دریافت اطلاعات دسته ممکن نشد.</ErrorState>}
      {!loading && !error && data && (
        <>
          <div className="page-head">
            <div>
              <h1 dir="rtl">{data.label}</h1>
              <p>{fmt(data.total_items)} خبر · نسخه طبقه‌بندی {data.taxonomy_version}
                {data.is_fallback && ' · دسته آخرین راه (fallback)'}</p>
            </div>
            <Link href={'/news?category=' + encodeURIComponent(data.label)} className="btn btn-secondary">مشاهده همه اخبار این دسته</Link>
          </div>

          {data.is_fallback && data.other_explanation && (
            <div className="card" style={{ marginBottom: 20 }}>
              <div className="card-title"><h2>چرا این خبرها در «سایر» قرار گرفته‌اند؟</h2></div>
              <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.8 }}>{data.other_explanation}</p>
            </div>
          )}

          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-title"><h2>روند زمانی (۹۰ روز اخیر)</h2></div>
            {trend.length ? (
              <div className="chart-box" dir="ltr">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs><linearGradient id="cat-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--accent-strong)" stopOpacity={0.3} /><stop offset="100%" stopColor="var(--accent-strong)" stopOpacity={0} /></linearGradient></defs>
                    <CartesianGrid stroke="var(--border-subtle)" vertical={false} />
                    <XAxis dataKey="day" tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }} minTickGap={24} />
                    <YAxis allowDecimals={false} tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }} width={28} />
                    <Tooltip contentStyle={{ background: 'var(--surface-3)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }} />
                    <Area type="monotone" dataKey="count" name="تعداد خبر" stroke="var(--accent-strong)" fill="url(#cat-area)" strokeWidth={2} isAnimationActive={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : <EmptyState title="داده کافی برای رسم نمودار موجود نیست" />}
          </div>

          {!!data.subtopics.length && (
            <div className="card" style={{ marginBottom: 20 }}>
              <div className="card-title"><h2>زیرموضوع‌ها</h2></div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {data.subtopics.map((s) => (
                  <Link key={s.id} href={'/news?category=' + encodeURIComponent(data.label) + '&topic=' + encodeURIComponent(s.label)}>
                    <Badge>{s.label} ({fmt(s.count)})</Badge>
                  </Link>
                ))}
              </div>
            </div>
          )}

          <div className="analytics-grid" style={{ marginBottom: 20 }}>
            <div className="card">
              <div className="card-title"><h2>منابع اصلی</h2></div>
              {data.main_sources.length ? data.main_sources.map(([name, n]) => (
                <p key={name} className="source-provenance-row">{name} <b>{fmt(n)}</b></p>
              )) : <EmptyState title="منبعی ثبت نشده" />}
            </div>
            <div className="card">
              <div className="card-title"><h2>رویدادهای اصلی</h2></div>
              {data.key_events.length ? (
                <ul className="news-detail-documents">
                  {data.key_events.map((e) => (
                    <li key={e.event_id}>
                      <Link2 size={15} />
                      <Link href={'/events/' + encodeURIComponent(e.event_id)} dir="rtl">{e.title}</Link>
                      <span>{fmt(e.member_count)} خبر</span>
                    </li>
                  ))}
                </ul>
              ) : <EmptyState title="رویداد مشترکی برای این دسته شناسایی نشده" />}
            </div>
          </div>

          <div className="card">
            <div className="card-title"><h2>{data.is_fallback ? 'نمونه برای بازبینی' : 'آخرین خبرها'}</h2></div>
            {(data.is_fallback ? data.review_sample : data.latest_items)?.length ? (
              <ul className="news-detail-documents">
                {(data.is_fallback ? data.review_sample! : data.latest_items).map((it) => (
                  <li key={it.item_id}>
                    <Newspaper size={15} />
                    <Link href={'/news/' + encodeURIComponent(it.item_id)} dir={isPersian(it.title) ? 'rtl' : 'ltr'}>{it.title}</Link>
                    <span>{it.source_name} · {fmtDateTime(it.published_at)}</span>
                    {it.confidence != null && <Badge tone="muted">اطمینان {(it.confidence * 100).toFixed(0)}٪</Badge>}
                  </li>
                ))}
              </ul>
            ) : <EmptyState title="خبری ثبت نشده" />}
          </div>
        </>
      )}
    </Shell>
  );
}

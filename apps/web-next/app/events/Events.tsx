'use client';
import Link from 'next/link';
import { Link2 } from 'lucide-react';
import { Shell } from '../design/Shell';
import { useApi } from '../design/useApi';
import { EmptyState, ErrorState, Skeleton } from '../design/ui';
import { fmt, fmtDateTime } from '../design/format';

interface EventRow {
  event_id: string;
  title: string;
  member_count: number;
  source_count: number;
  first_published_at: string | null;
  last_updated_at: string | null;
  clustering_method: string;
  algorithm_version: string;
}
interface Data { events: EventRow[]; total: number; page: number; page_size: number }

/** Deterministic, keyword-based event clustering — not a semantic model.
 * Two items are grouped only when they share a distinctive proper noun and a
 * close publish time; see the algorithm doc. A news item never disappearing
 * from here means it hasn't matched anything yet, not that it was excluded. */
export function Events() {
  const { data, error, loading, reload } = useApi<Data>('events');

  return (
    <Shell title="رویدادها" breadcrumb="رویدادهای شناسایی‌شده">
      <div className="page-head">
        <div>
          <h1>رویدادهای شناسایی‌شده</h1>
          <p>گروه‌بندی خودکار خبرهای مرتبط با یک رویداد بر اساس نام‌های خاص مشترک و نزدیکی زمانی؛ بدون مدل یادگیری ماشین.</p>
        </div>
      </div>

      {error && <ErrorState onRetry={reload}>فهرست رویدادها دریافت نشد.</ErrorState>}
      {loading && <Skeleton height={280} radius={14} />}

      {!loading && !error && data && (
        !data.events.length ? (
          <EmptyState title="هنوز رویدادی شناسایی نشده">خوشه‌بندی رویداد فقط برای خبرهای پردازش‌شده در پایلوت غنی‌سازی محتوا اجرا شده است.</EmptyState>
        ) : (
          <div className="card">
            <p className="chart-caption" style={{ margin: '0 0 12px' }}>{fmt(data.total)} رویداد</p>
            <div className="topic-list">
              {data.events.map((ev) => (
                <Link className="topic-row" href={'/events/' + encodeURIComponent(ev.event_id)} key={ev.event_id}>
                  <span className="topic-rank"><Link2 size={16} /></span>
                  <div className="topic-info">
                    <strong dir="rtl">{ev.title}</strong>
                    <div className="topic-track"><i style={{ width: '100%' }} /></div>
                  </div>
                  <span className="topic-count">{fmt(ev.member_count)} خبر</span>
                  <span className="topic-meta">{fmt(ev.source_count)} منبع · {fmtDateTime(ev.last_updated_at)}</span>
                </Link>
              ))}
            </div>
          </div>
        )
      )}
    </Shell>
  );
}

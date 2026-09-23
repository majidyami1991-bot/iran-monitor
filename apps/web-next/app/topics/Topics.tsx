'use client';
import { useState } from 'react';
import Link from 'next/link';
import { Shell } from '../design/Shell';
import { useApi } from '../design/useApi';
import { EmptyState, ErrorState, Skeleton, Tabs } from '../design/ui';
import { fmt, fmtDateTime } from '../design/format';

interface Row { label?: string; topic?: string; count: number; sources?: number; categories?: number; latest: string | null; previous_count?: number; source_names?: { name: string }[]; recent_news?: { item_id: string; title: string; source_name: string; observed_at: string | null }[] }
interface Data { window: string; categories: Row[]; topics: Row[]; sources: Row[]; uncategorized: number; latest_observation: string | null }

const WINDOWS: [string, string][] = [['24h', '۲۴ ساعت'], ['7d', '۷ روز'], ['30d', '۳۰ روز'], ['all', 'همه داده‌ها']];

export function Topics() {
  const [window_, setWindow] = useState('30d');
  const [tab, setTab] = useState('categories');
  const { data, error, loading, reload } = useApi<Data>('stats/topics/detailed?window=' + window_, [window_]);

  const rows = tab === 'categories' ? data?.categories : tab === 'topics' ? data?.topics : data?.sources;
  const linkFor = (r: Row) => tab === 'categories' ? '/news?category=' + encodeURIComponent(r.label || '') : tab === 'topics' ? '/news?topic=' + encodeURIComponent(r.topic || '') : undefined;

  return (
    <Shell title="موضوعات" breadcrumb="موضوعات و پوشش منابع">
      <div className="page-head"><div><h1>موضوعات و پوشش منابع</h1><p>دسته‌بندی‌ها و واژه‌ها بر اساس قواعد ذخیره‌شده‌اند؛ این نما تحلیل معنایی یا روند زنده نیست.</p></div></div>

      <div className="periods">{WINDOWS.map(([v, t]) => <button key={v} className={window_ === v ? 'selected' : ''} onClick={() => setWindow(v)}>{t}</button>)}</div>

      {error && <ErrorState onRetry={reload}>آمار موضوعات دریافت نشد.</ErrorState>}
      {loading && <Skeleton height={340} radius={14} />}

      {!loading && !error && data && (
        <div className="card">
          <Tabs value={tab} onChange={setTab} items={[['categories', 'دسته‌بندی‌ها'], ['topics', 'موضوعات'], ['sources', 'منابع درگیر']]} />
          <p className="chart-caption" style={{ margin: '12px 0' }}>بازه: {WINDOWS.find(([v]) => v === window_)?.[1]} · آخرین مشاهده: {fmtDateTime(data.latest_observation)} · دسته «سایر»: {fmt(data.uncategorized)} خبر از کل داده</p>

          {!rows?.length ? <EmptyState title="در این بازه داده‌ای ثبت نشده" /> : (
            <div className="topic-list">
              {rows.map((r, i) => {
                const name = r.label || r.topic || 'نام ثبت نشده';
                const href = linkFor(r);
                const content = (
                  <>
                    <span className="topic-rank">{fmt(i + 1)}</span>
                    <div className="topic-info">
                      <strong>{name}</strong>
                      <div className="topic-track"><i style={{ width: `${(r.count / (rows[0]?.count || 1)) * 100}%` }} /></div>
                    </div>
                    <span className="topic-count">{fmt(r.count)} خبر</span>
                    <span className="topic-meta">{tab === 'sources' ? `${fmt(r.categories || 0)} دسته` : `${fmt(r.sources || 0)} منبع`}</span>
                  </>
                );
                return href ? (
                  <Link className="topic-row" href={href} key={name}>{content}</Link>
                ) : (
                  <div className="topic-row topic-row-static" key={name}>{content}</div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </Shell>
  );
}

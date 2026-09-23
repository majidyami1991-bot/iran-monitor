'use client';
import { useMemo, useState } from 'react';
import Link from 'next/link';
import { Shell } from '../design/Shell';
import { useApi } from '../design/useApi';
import { Chip, ErrorState, Skeleton, SourceMark, StatusPill, toHealth } from '../design/ui';
import { fmt, fmtDateTime, sourceColor } from '../design/format';

interface CoverageSource {
  source_id: string; hostname: string | null; url: string | null; source_type: string; category: string | null;
  x_handle: string | null; coverage_state: string; reason: string; feed_url: string | null;
  in_database: boolean; last_success_at: string | null; health_status: string | null; item_count: number;
}
interface Coverage { registered: number; executable: number; monitored: number; by_state: Record<string, number>; sources: CoverageSource[] }
interface LiveSource { source_id: string; display_name: string; item_count: number; items_24h: number; health_status: string; last_success_at: string | null; consecutive_failures: number }

const STATE_LABEL: Record<string, string> = {
  active_rss: 'فعال (RSS)', feed_candidate: 'نامزد خوراک', sitemap_candidate: 'نامزد Sitemap',
  html_candidate: 'نامزد HTML', blocked: 'مسدود', not_covered: 'بدون پوشش',
};
const TYPE_LABEL: Record<string, string> = { news: 'خبرگزاری', think_tank: 'اندیشکده', x_account: 'حساب X' };
// The API's `reason` field is a fixed, English, one-per-state sentence
// (documentation-oriented). One-to-one with coverage_state, so a Persian
// translation is keyed off the state itself rather than string-matching text.
const REASON_FA: Record<string, string> = {
  active_rss: 'خوراک RSS معتبر در هر چرخه زمان‌بندی‌شده دریافت می‌شود.',
  feed_candidate: 'خوراک کارآمدی پیدا شده اما هنوز برای اجرا اعتبارسنجی نشده است.',
  sitemap_candidate: 'خوراکی وجود ندارد؛ sitemap خوانا هست اما parser آزموده‌ای برای آن نیست.',
  html_candidate: 'نه خوراک و نه sitemap پیدا نشد؛ نیازمند parser اختصاصی فهرست HTML است.',
  blocked: 'ناشر به درخواست خودکار پاسخ ۴۰۳ می‌دهد یا آن را در robots.txt منع کرده است؛ جمع‌آوری نمی‌شود.',
  not_covered: 'حساب X است؛ مسیر دسترسی مجاز یا سیاست استفاده هنوز مشخص نیست.',
};

export function SourcesList() {
  const coverageQ = useApi<Coverage>('sources/coverage');
  const liveQ = useApi<{ sources: LiveSource[] }>('sources?page_size=100');
  const [stateFilter, setStateFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');

  const liveById = useMemo(() => new Map((liveQ.data?.sources || []).map((s) => [s.source_id, s])), [liveQ.data]);

  const rows = useMemo(() => {
    let list = coverageQ.data?.sources || [];
    if (stateFilter) list = list.filter((s) => s.coverage_state === stateFilter);
    if (typeFilter) list = list.filter((s) => s.source_type === typeFilter);
    return list;
  }, [coverageQ.data, stateFilter, typeFilter]);

  if (coverageQ.error) return <Shell title="منابع" breadcrumb="منابع"><ErrorState onRetry={coverageQ.reload}>دریافت فهرست منابع ممکن نشد.</ErrorState></Shell>;

  return (
    <Shell title="منابع" breadcrumb="منابع">
      <div className="page-head"><div><h1>منابع پایش‌شده</h1><p>هر سه عدد پوشش، ثبت‌شده، قابل‌اجرا و درحال‌پایش، جدا از هم گزارش می‌شوند.</p></div></div>

      {coverageQ.loading ? <Skeleton height={110} radius={14} /> : coverageQ.data && (
        <div className="stat-grid" style={{ marginBottom: 'var(--space-5)' }}>
          <div className="stat-card"><span className="stat-label">ثبت‌شده در سند منابع</span><strong>{fmt(coverageQ.data.registered)}</strong><small>کل فهرست مشتری</small></div>
          <div className="stat-card"><span className="stat-label">قابل اجرا</span><strong>{fmt(coverageQ.data.executable)}</strong><small>مسیر جمع‌آوری معتبر</small></div>
          <div className="stat-card"><span className="stat-label">در حال پایش</span><strong>{fmt(coverageQ.data.monitored)}</strong><small>دریافت موفق واقعی</small></div>
        </div>
      )}

      <div className="source-filter-row">
        <Chip active={stateFilter === ''} onClick={() => setStateFilter('')}>همه</Chip>
        {Object.entries(coverageQ.data?.by_state || {}).map(([state, count]) => (
          <Chip key={state} active={stateFilter === state} onClick={() => setStateFilter(stateFilter === state ? '' : state)}>
            {STATE_LABEL[state] || state} ({fmt(count)})
          </Chip>
        ))}
        <span className="source-filter-sep" />
        {Object.entries(TYPE_LABEL).map(([type, label]) => (
          <Chip key={type} active={typeFilter === type} onClick={() => setTypeFilter(typeFilter === type ? '' : type)}>{label}</Chip>
        ))}
      </div>

      {coverageQ.loading ? <Skeleton height={400} radius={14} /> : (
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr>
              <th>منبع</th><th>نوع</th><th>وضعیت پوشش</th><th>سلامت</th><th className="num">خبر</th><th>آخرین دریافت موفق</th><th>دلیل</th>
            </tr></thead>
            <tbody>
              {rows.map((s) => {
                const live = liveById.get(s.source_id);
                const name = s.x_handle || live?.display_name || s.hostname || 'نام ثبت نشده';
                const isLinked = s.coverage_state === 'active_rss';
                return (
                  <tr key={s.source_id}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <SourceMark name={name} color={sourceColor(s.source_id)} />
                        {isLinked ? <Link href={'/sources/' + s.source_id}>{name}</Link> : <span>{name}</span>}
                      </div>
                    </td>
                    <td>{TYPE_LABEL[s.source_type] || s.source_type}</td>
                    <td><StatusPill health={
                      s.coverage_state === 'active_rss' ? 'healthy' :
                      s.coverage_state === 'blocked' ? 'error' :
                      s.coverage_state === 'not_covered' ? 'inactive' : 'attention'
                    } label={STATE_LABEL[s.coverage_state] || s.coverage_state} /></td>
                    <td>{live ? <StatusPill health={toHealth(live.health_status)} /> : '—'}</td>
                    <td className="num">{live ? fmt(live.item_count) : '—'}</td>
                    <td>{live?.last_success_at ? fmtDateTime(live.last_success_at) : 'ثبت نشده'}</td>
                    <td className="source-reason">{REASON_FA[s.coverage_state] || s.reason}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Shell>
  );
}

'use client';
import { Shell } from '../design/Shell';
import { useApi } from '../design/useApi';
import { ErrorState, Skeleton, StatusPill, toHealth } from '../design/ui';
import { fmt, fmtDateTime } from '../design/format';

interface HealthCheck { status: string; problems: string[]; expected_collection: boolean; collector_health: string; last_run_age_seconds: number | null; stale_after_seconds: number; checked_at: string }
interface CollectionStatus { scheduler_enabled: boolean; collector_health: string; interval_seconds: number; next_run_at: string | null; last_run: RunSummary | null; lock: string }
interface RunSummary { run_id: string; started_at: string; finished_at: string | null; status: string; sources_planned: number; sources_attempted: number; sources_succeeded: number; sources_failed: number; http_requests: number; items_inserted: number; duplicates: number; error_summary: string | null; trigger_type?: string; updates?: number }
interface SourceRow { source_id: string; display_name: string; hostname: string; health_status: string; last_attempt_at: string | null; last_success_at: string | null; last_http_status: number | null; consecutive_failures: number }

const PROBLEM_LABEL: Record<string, string> = {
  scheduler_disabled: 'زمان‌بندی غیرفعال است',
  no_run_recorded: 'هیچ چرخه‌ای ثبت نشده است',
  last_run_failed: 'آخرین چرخه ناموفق بوده است',
};
const RUN_STATUS_LABEL: Record<string, string> = {
  succeeded: 'موفق', partial: 'ناقص', failed: 'ناموفق', skipped_locked: 'رد‌شده (قفل)', running: 'درحال‌اجرا',
};
function problemLabel(p: string) {
  if (PROBLEM_LABEL[p]) return PROBLEM_LABEL[p];
  if (p.startsWith('collector_')) return 'وضعیت گردآورنده: ' + p.replace('collector_', '');
  if (p.startsWith('last_run_age_')) return 'آخرین چرخه بیش از حد قدیمی است';
  if (p.startsWith('runs_stuck_in_running')) return 'چرخه‌ای در وضعیت درحال‌اجرا گیر کرده است';
  return p;
}

export function Monitoring() {
  const healthQ = useApi<HealthCheck>('health/collection');
  const statusQ = useApi<CollectionStatus>('collection/status');
  const sourcesQ = useApi<{ sources: SourceRow[] }>('sources?page_size=100');
  const runsQ = useApi<{ runs: RunSummary[] }>('collection/runs?page_size=20');

  const loading = healthQ.loading || statusQ.loading;

  return (
    <Shell title="وضعیت پایش" breadcrumb="وضعیت پایش">
      <div className="page-head"><div><h1>وضعیت پایش</h1><p>سلامت گردآورنده، زمان‌بندی و منابع، مستقل از تحلیل آماری.</p></div></div>

      {healthQ.error && <ErrorState onRetry={healthQ.reload}>دریافت وضعیت پایش ممکن نشد.</ErrorState>}
      {loading && <Skeleton height={140} radius={14} />}

      {!loading && healthQ.data && (
        <div className={healthQ.data.status === 'ok' ? 'monitoring-banner ok' : 'monitoring-banner'}>
          <StatusPill health={healthQ.data.status === 'ok' ? 'healthy' : (healthQ.data.expected_collection ? 'error' : 'stopped')}
            label={healthQ.data.status === 'ok' ? 'پایش سالم' : 'نیازمند بررسی'} />
          {healthQ.data.problems.length > 0 ? (
            <ul className="monitoring-problems">{healthQ.data.problems.map((p) => <li key={p}>{problemLabel(p)}</li>)}</ul>
          ) : (
            <span>هیچ مشکلی در آخرین بررسی ثبت نشده است.</span>
          )}
          <span className="monitoring-checked-at">بررسی‌شده: {fmtDateTime(healthQ.data.checked_at)}</span>
        </div>
      )}

      {statusQ.data && (
        <div className="stat-grid" style={{ margin: '20px 0' }}>
          <div className="stat-card"><span className="stat-label">زمان‌بندی</span><strong className="stat-card-time">{statusQ.data.scheduler_enabled ? 'فعال' : 'متوقف'}</strong></div>
          <div className="stat-card"><span className="stat-label">فاصله چرخه</span><strong className="stat-card-time">{fmt(statusQ.data.interval_seconds / 60)} دقیقه</strong></div>
          <div className="stat-card"><span className="stat-label">چرخه بعدی</span><strong className="stat-card-time">{fmtDateTime(statusQ.data.next_run_at)}</strong></div>
          <div className="stat-card"><span className="stat-label">وضعیت آخرین چرخه</span><strong className="stat-card-time">{statusQ.data.last_run ? (RUN_STATUS_LABEL[statusQ.data.last_run.status] || statusQ.data.last_run.status) : 'ثبت نشده'}</strong></div>
          <div className="stat-card"><span className="stat-label">منابع موفق آخرین چرخه</span><strong>{fmt(statusQ.data.last_run?.sources_succeeded)} / {fmt(statusQ.data.last_run?.sources_planned)}</strong></div>
          <div className="stat-card"><span className="stat-label">خبر تازه آخرین چرخه</span><strong>{fmt(statusQ.data.last_run?.items_inserted)}</strong></div>
        </div>
      )}

      <div className="card-title" style={{ marginTop: 24 }}><h2>وضعیت هر منبع</h2></div>
      {sourcesQ.loading ? <Skeleton height={240} radius={14} /> : (
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>منبع</th><th>سلامت</th><th>آخرین تلاش</th><th>آخرین موفقیت</th><th className="num">HTTP</th><th className="num">شکست متوالی</th></tr></thead>
            <tbody>
              {sourcesQ.data?.sources.map((s) => (
                <tr key={s.source_id}>
                  <td>{s.display_name || s.hostname}</td>
                  <td><StatusPill health={toHealth(s.health_status)} /></td>
                  <td>{fmtDateTime(s.last_attempt_at)}</td>
                  <td>{fmtDateTime(s.last_success_at)}</td>
                  <td className="num">{s.last_http_status ?? '—'}</td>
                  <td className="num">{fmt(s.consecutive_failures)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="card-title" style={{ marginTop: 24 }}><h2>تاریخچه چرخه‌ها</h2></div>
      {runsQ.loading ? <Skeleton height={300} radius={14} /> : (
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>شروع</th><th>نوع اجرا</th><th>وضعیت</th><th className="num">منابع</th><th className="num">درخواست</th><th className="num">تازه</th><th className="num">تکراری</th><th>خطا</th></tr></thead>
            <tbody>
              {runsQ.data?.runs.map((r) => (
                <tr key={r.run_id}>
                  <td>{fmtDateTime(r.started_at)}</td>
                  <td>{r.trigger_type === 'scheduled' ? 'زمان‌بندی‌شده' : r.trigger_type || '—'}</td>
                  <td><StatusPill health={r.status === 'succeeded' ? 'healthy' : r.status === 'partial' ? 'attention' : r.status === 'skipped_locked' ? 'inactive' : 'error'} label={RUN_STATUS_LABEL[r.status] || r.status} /></td>
                  <td className="num">{fmt(r.sources_succeeded)}/{fmt(r.sources_planned)}</td>
                  <td className="num">{fmt(r.http_requests)}</td>
                  <td className="num">{fmt(r.items_inserted)}</td>
                  <td className="num">{fmt(r.duplicates)}</td>
                  <td className="monitoring-error-cell">{r.error_summary || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Shell>
  );
}

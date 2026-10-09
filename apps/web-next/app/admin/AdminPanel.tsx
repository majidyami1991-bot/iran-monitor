'use client';
import { useEffect } from 'react';
import { Shell } from '../design/Shell';
import { useApi, useNow } from '../design/useApi';
import { ErrorState, Skeleton, Tag } from '../design/ui';
import { fmt, fmtDateTime, fmtRelative } from '../design/format';

/** Admin panel of the isolated 3003 lab. Every number comes from
 *  /api/v1/local-ai/ops (database + host status files); a source that is not
 *  available is shown as "unknown", never filled in. Refreshes every 30 s. */
interface Ops {
  checked_at: string;
  news: { items: number; items_24h: number; latest_collected: string | null; latest_published: string | null;
    production_collector_last_run: { started_at: string; status: string } | null };
  sync: { runs: { run_id: string; mode: string; status: string; finished_at: string | null; counts: Record<string, unknown> | null; note: string | null }[];
    last_success: string | null; last_success_age_min: number | null; failures_24h: number | null;
    scheduler: 'unknown' | 'seen' | 'empty'; scheduler_log: { ts: string; event: string; status?: string; reason?: string; inserted_items?: number }[] | null };
  translation: { worker: { state: string; version: string; beat_at: string; detail: Record<string, unknown> } | null; heartbeat_age_min: number | null;
    by_field: Record<string, Record<string, number>>; queue_fields: number; latency_24h: { avg_ms: number | null; calls: number } | null; pipeline: string;
    queue_fresh_items: number | null; queue_archive_items: number | null; items_not_yet_queued: number | null; fields_last_hour: number;
    fields_last_24h: number | null; errors_24h: number | null; eta_hours_queue: number | null;
    progress: { titles_processed: number; summaries_processed: number; items_title_fa_shown: number; items_with_any_fa: number;
      last_accepted_at: string | null; last_processed_at: string | null } | null };
  clustering: { events: number; last_update: string | null; last_update_age_min: number | null; items_without_topic: number };
  assistant: { answers_24h: number; last_answer: string | null; approval: { id: string; state: string; tag: string } | null };
  models: { servable: { id: string; role: string; tag: string; state: string }[]; lab_mode: boolean };
  backup: { status: string; reason?: string; last?: { ts: string; dump?: string; sha256?: string; verify?: string | null }[]; last_age_hours: number | null };
  health_monitor: { status: string; reason?: string; last?: { ts: string; ok: boolean; alerts: string[] }; last_age_min: number | null };
  known_risks: { key: string; severity: string }[];
  alerts: { key: string; severity: string; value: unknown }[];
}

const STATUS_FA: Record<string, string> = {
  translated_auto: 'ترجمه خودکار (بدون ایراد کنترل کیفیت)', qc_warning: 'هشدار کنترل کیفیت', qc_failed: 'رد در کنترل کیفیت',
  translation_pending: 'در صف', processing: 'در حال ترجمه', translation_error: 'خطای موقت (تلاش مجدد)', translation_failed: 'ناموفق دائمی', not_required: 'نیاز ندارد (فارسی)', no_source_text: 'بدون متن منبع',
};
const ALERT_FA: Record<string, string> = {
  sync_stale: 'همگام‌سازی اخبار بیش از ۴۵ دقیقه موفق نبوده است',
  translator_heartbeat_stale: 'سرویس ترجمه بیش از ۱۰ دقیقه گزارش وضعیت نداده است',
  translator_paused: 'سرویس ترجمه متوقف موقت است', translator_error: 'سرویس ترجمه با خطای پایگاه داده روبه‌روست',
  translator_blocked: 'سرویس ترجمه مسدود است', translation_errors: 'ترجمه‌های ناموفق در صف تلاش مجدد',
  clustering_stale: 'خوشه‌بندی رویدادها بیش از ۴۵ دقیقه به‌روز نشده است',
  backup_missing_or_stale: 'پشتیبان پایگاه داده 3003 ثبت نشده یا بیش از ۲۶ ساعت قدیمی است',
  health_monitor_not_running: 'پایشگر سلامت میزبان اجرا نمی‌شود یا خروجی تازه ندارد',
};
const RISK_FA: Record<string, string> = {
  docker_requires_user_sign_in: 'Docker Desktop فقط پس از ورود کاربر Administrator اجرا می‌شود؛ پس از Reboot بدون ورود، همه سرویس‌ها خاموش می‌مانند.',
  host_unclean_resets_16_in_47_days: '۱۶ ریست غیرعادی سرور در ۴۷ روز (Kernel-Power 41) و خطاهای اصلاح‌شده PCIe؛ علت قطعی نامعلوم است.',
  translation_not_human_verified: 'ترجمه‌ها خودکار و تأییدنشده‌اند؛ عبور از کنترل کیفیت به معنی صحت قطعی نیست.',
  assistant_not_human_reviewed: 'دستیار از دروازه‌های ماشینی عبور کرده اما بازبینی انسانی نشده است.',
};
const SEV: Record<string, 'uncertain' | 'info' | 'neutral'> = { high: 'uncertain', medium: 'uncertain', low: 'info' };

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return <><dt>{k}</dt><dd>{v ?? <span className="muted">نامشخص</span>}</dd></>;
}

export function AdminPanel() {
  const q = useApi<Ops>('local-ai/ops');
  const now = useNow(30000);
  useEffect(() => { const t = setInterval(q.reload, 30000); return () => clearInterval(t); }, [q.reload]);
  const d = q.data;
  return (
    <Shell title="پنل مدیریت" breadcrumb="پنل مدیریت">
      <div className="page-head"><div><h1>پنل مدیریت هوش مصنوعی محلی (3003)</h1>
        <p>وضعیت واقعی همگام‌سازی، صف ترجمه، دستیار، خوشه‌بندی، پشتیبان و هشدارها؛ هر ۳۰ ثانیه به‌روز می‌شود. محیط آزمایشی و مستقل از Production.</p></div></div>
      {q.error && <ErrorState onRetry={q.reload}>دریافت وضعیت ممکن نشد.</ErrorState>}
      {!d && !q.error && <Skeleton height={320} />}
      {d && (
        <div className="admin-grid">
          <section className="panel" aria-labelledby="al-h">
            <div className="panel-title"><h3 id="al-h">هشدارهای عملیاتی</h3><Tag tone={d.alerts.length ? 'uncertain' : 'info'}>{fmt(d.alerts.length)} هشدار فعال</Tag></div>
            {d.alerts.length === 0 ? <p className="muted">هشدار فعالی وجود ندارد.</p> : (
              <ul>{d.alerts.map((a) => <li key={a.key}><Tag tone={SEV[a.severity] ?? 'neutral'}>{a.severity}</Tag> {ALERT_FA[a.key] ?? a.key}
                {a.value !== null && a.value !== undefined && <small className="muted"> ({String(a.value)})</small>}</li>)}</ul>)}
            <h4>ریسک‌های باز (رفع‌نشده)</h4>
            <ul>{d.known_risks.map((r) => <li key={r.key}>{RISK_FA[r.key] ?? r.key}</li>)}</ul>
          </section>

          <section className="panel" aria-labelledby="sync-h">
            <div className="panel-title"><h3 id="sync-h">دریافت و همگام‌سازی اخبار</h3></div>
            <dl className="kv">
              <Row k="تعداد اخبار 3003" v={fmt(d.news.items)} />
              <Row k="اخبار ۲۴ ساعت اخیر" v={fmt(d.news.items_24h)} />
              <Row k="آخرین خبر دریافت‌شده" v={d.news.latest_collected && `${fmtDateTime(d.news.latest_collected)} (${fmtRelative(d.news.latest_collected, now)})`} />
              <Row k="آخرین چرخه Collector اصلی (Production)" v={d.news.production_collector_last_run && `${fmtDateTime(d.news.production_collector_last_run.started_at)} · ${d.news.production_collector_last_run.status}`} />
              <Row k="آخرین همگام‌سازی موفق" v={d.sync.last_success && `${fmtDateTime(d.sync.last_success)} (${fmtRelative(d.sync.last_success, now)})`} />
              <Row k="همگام‌سازی ناموفق در ۲۴ ساعت" v={fmt(d.sync.failures_24h ?? 0)} />
              <Row k="زمان‌بند خودکار" v={d.sync.scheduler === 'seen' ? 'فعال (گزارش اجرا موجود است)' : d.sync.scheduler === 'empty' ? 'بدون اجرا' : 'نامشخص'} />
            </dl>
            <table className="tbl"><thead><tr><th>اجرا</th><th>حالت</th><th>وضعیت</th><th>پایان</th></tr></thead>
              <tbody>{d.sync.runs.map((r) => <tr key={r.run_id}><td dir="ltr"><code>{r.run_id}</code></td><td>{r.mode}</td><td>{r.status}</td><td>{r.finished_at ? fmtRelative(r.finished_at, now) : '—'}</td></tr>)}</tbody></table>
          </section>

          <section className="panel" aria-labelledby="tr-h">
            <div className="panel-title"><h3 id="tr-h">صف و کیفیت ترجمه</h3><Tag tone="ai">TranslateGemma 27B · بدون Placeholder</Tag></div>
            <dl className="kv">
              <Row k="وضعیت سرویس ترجمه" v={d.translation.worker && `${d.translation.worker.state} · آخرین گزارش ${fmtRelative(d.translation.worker.beat_at, now)}`} />
              <Row k="نسخه" v={d.translation.worker?.version} />
              <Row k="خط لوله" v={<bdi>{d.translation.pipeline}</bdi>} />
              <Row k="عنوان‌های پردازش‌شده / کل اخبار" v={d.translation.progress && `${fmt(d.translation.progress.titles_processed)} از ${fmt(d.news.items)}`} />
              <Row k="خلاصه‌های پردازش‌شده" v={d.translation.progress && fmt(d.translation.progress.summaries_processed)} />
              <Row k="اخبار با عنوان فارسی قابل نمایش" v={d.translation.progress && `${fmt(d.translation.progress.items_title_fa_shown)} خبر (${fmt(d.translation.progress.items_with_any_fa)} خبر با متن فارسی، شامل هشدار)`} />
              <Row k="آخرین ترجمه پذیرفته‌شده" v={d.translation.progress?.last_accepted_at && `${fmtDateTime(d.translation.progress.last_accepted_at)} (${fmtRelative(d.translation.progress.last_accepted_at, now)})`} />
              <Row k="آخرین خروجی پردازش‌شده" v={d.translation.progress?.last_processed_at && fmtRelative(d.translation.progress.last_processed_at, now)} />
              <Row k="صف اخبار تازه (اولویت بالا)" v={`${fmt(d.translation.queue_fresh_items ?? 0)} خبر`} />
              <Row k="صف آرشیو (پس‌زمینه)" v={`${fmt(d.translation.queue_archive_items ?? 0)} خبر`} />
              <Row k="هنوز وارد صف نشده" v={`${fmt(d.translation.items_not_yet_queued ?? 0)} خبر (هر دقیقه افزوده می‌شود)`} />
              <Row k="طول صف (فیلد)" v={fmt(d.translation.queue_fields)} />
              <Row k="نرخ پردازش" v={`${fmt(d.translation.fields_last_hour)} فیلد در ساعت گذشته · ${fmt(d.translation.fields_last_24h ?? 0)} در ۲۴ ساعت`} />
              <Row k="زمان تقریبی تخلیه صف فعلی" v={d.translation.eta_hours_queue != null ? `حدود ${fmt(d.translation.eta_hours_queue)} ساعت` : 'نامشخص'} />
              <Row k="خطاهای ترجمه (۲۴ ساعت)" v={fmt(d.translation.errors_24h ?? 0)} />
              <Row k="میانگین زمان هر فراخوانی (۲۴ ساعت)" v={d.translation.latency_24h?.avg_ms != null && `${fmt(Math.round(d.translation.latency_24h.avg_ms / 1000))} ثانیه در ${fmt(d.translation.latency_24h.calls)} فراخوانی`} />
            </dl>
            <table className="tbl"><thead><tr><th>وضعیت</th><th>عنوان</th><th>خلاصه</th></tr></thead>
              <tbody>{Object.keys(STATUS_FA).map((s) => <tr key={s}><td>{STATUS_FA[s]}</td><td>{fmt(d.translation.by_field.title?.[s] ?? 0)}</td><td>{fmt(d.translation.by_field.summary?.[s] ?? 0)}</td></tr>)}</tbody></table>
            <p className="bi-note">عبور از کنترل کیفیت خودکار به معنی صحت قطعی ترجمه نیست؛ هیچ ترجمه‌ای بازبینی انسانی نشده است.</p>
          </section>

          <section className="panel" aria-labelledby="as-h">
            <div className="panel-title"><h3 id="as-h">دستیار و مدل‌های فعال</h3></div>
            <dl className="kv">
              <Row k="نسخه دستیار" v={d.assistant.approval && <bdi>{d.assistant.approval.id}</bdi>} />
              <Row k="وضعیت قرارداد" v={d.assistant.approval?.state} />
              <Row k="پاسخ‌های ۲۴ ساعت اخیر" v={fmt(d.assistant.answers_24h ?? 0)} />
              <Row k="حالت آزمایشگاهی" v={d.models.lab_mode ? 'فعال (فقط 3003)' : 'غیرفعال'} />
            </dl>
            <ul>{d.models.servable.map((m) => <li key={m.id}><bdi>{m.tag}</bdi> — {m.role} — <Tag>{m.state}</Tag></li>)}</ul>
          </section>

          <section className="panel" aria-labelledby="cl-h">
            <div className="panel-title"><h3 id="cl-h">خوشه‌بندی و موضوع‌ها</h3></div>
            <dl className="kv">
              <Row k="تعداد رویدادها" v={fmt(d.clustering.events)} />
              <Row k="آخرین خوشه‌بندی" v={d.clustering.last_update && `${fmtDateTime(d.clustering.last_update)} (${fmtRelative(d.clustering.last_update, now)})`} />
              <Row k="اخبار بدون موضوع" v={fmt(d.clustering.items_without_topic)} />
            </dl>
          </section>

          <section className="panel" aria-labelledby="bk-h">
            <div className="panel-title"><h3 id="bk-h">پشتیبان‌گیری و پایش میزبان</h3></div>
            <dl className="kv">
              <Row k="آخرین پشتیبان 3003" v={d.backup.last?.length ? `${fmtDateTime(d.backup.last[d.backup.last.length - 1].ts)} · ${d.backup.last[d.backup.last.length - 1].verify ?? 'بدون آزمون بازیابی'}` : (d.backup.reason ?? 'ثبت نشده')} />
              <Row k="پایشگر سلامت میزبان" v={d.health_monitor.last ? `${d.health_monitor.last.ok ? 'سالم' : 'هشدار'} · ${fmtRelative(d.health_monitor.last.ts, now)}` : (d.health_monitor.reason ?? 'نامشخص')} />
            </dl>
          </section>
        </div>
      )}
      <p className="muted">زمان بررسی: {d ? fmtDateTime(d.checked_at) : '—'}</p>
    </Shell>
  );
}

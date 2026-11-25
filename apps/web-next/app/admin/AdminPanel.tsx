'use client';
import { useCallback, useEffect, useState } from 'react';
import { Shell } from '../design/Shell';
import { useApi, useNow } from '../design/useApi';
import { ErrorState, Skeleton, Tag } from '../design/ui';
import { fmt, fmtDateTime, fmtRelative } from '../design/format';

interface AIConfig {
  provider: string;
  base_url: string;
  model_translation: string;
  model_assistant: string;
  timeout_seconds: number;
  max_concurrency: number;
  enabled_title_translation: boolean;
  enabled_summary_translation: boolean;
  enabled_body_translation: boolean;
  enabled_executive_summary: boolean;
  enabled_why_it_matters: boolean;
  enabled_key_points: boolean;
  enabled_assistant: boolean;
  last_connection_test_at: string | null;
  last_connection_status: string | null;
  last_connection_error: string | null;
}

interface AICapability {
  id: string;
  key: keyof AIConfig;
  label: string;
  label_fa: string;
  enabled: boolean;
}

interface AIAdminData {
  config: AIConfig;
  queues: Record<string, Record<string, number>>;
  translations_completed?: Record<string, number>;
  active_circuit_breakers: {
    domain: string;
    consecutive_failures: number;
    cooldown_until: string;
    last_error: string;
    updated_at: string;
  }[];
  capabilities: AICapability[];
}

interface ConnectionTestResult {
  ok: boolean;
  status: string;
  error?: string | null;
  latency_ms?: number | null;
  version?: string | null;
  available_models?: string[];
  model_found?: boolean;
}

interface TestTranslationResult {
  ok: boolean;
  status: string;
  translation: string;
  latency_ms: number;
  model: string | null;
  error?: string | null;
}

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
  ai?: { state: string; message_fa: string | null };
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
  translation_not_human_verified: 'ترجمه‌ها به‌صورت خودکار انجام می‌شوند.',
  assistant_not_human_reviewed: 'پاسخ‌های دستیار مبتنی بر شواهد استخراج‌شده از منابع هستند.',
};
const SEV: Record<string, 'uncertain' | 'info' | 'neutral'> = { high: 'uncertain', medium: 'uncertain', low: 'info' };

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return <><dt>{k}</dt><dd>{v ?? <span className="muted">نامشخص</span>}</dd></>;
}

function AIControlsSection() {
  const aiApi = useApi<AIAdminData>('admin/ai/config');
  const d = aiApi.data;

  const [baseUrl, setBaseUrl] = useState('');
  const [modelTrans, setModelTrans] = useState('gemma4:e2b');
  const [modelAsst, setModelAsst] = useState('qwen3:8b');
  const [timeoutSec, setTimeoutSec] = useState(60);
  const [maxConc, setMaxConc] = useState(1);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  const [testTesting, setTestTesting] = useState(false);
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null);

  const [snippet, setSnippet] = useState('Defence forces conduct joint military exercises.');
  const [transTesting, setTransTesting] = useState(false);
  const [transResult, setTransResult] = useState<TestTranslationResult | null>(null);

  useEffect(() => {
    if (d?.config) {
      setBaseUrl(d.config.base_url || 'http://host.docker.internal:11434');
      setModelTrans(d.config.model_translation || 'gemma4:e2b');
      setModelAsst(d.config.model_assistant || 'qwen3:8b');
      setTimeoutSec(d.config.timeout_seconds || 60);
      setMaxConc(d.config.max_concurrency || 1);
    }
  }, [d]);

  const saveSettings = async () => {
    setSaveStatus('saving');
    try {
      const res = await fetch('/api/v1/admin/ai/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_url: baseUrl,
          model_translation: modelTrans,
          model_assistant: modelAsst,
          timeout_seconds: timeoutSec,
          max_concurrency: maxConc,
        }),
      });
      if (res.ok) {
        setSaveStatus('saved');
        aiApi.reload();
        setTimeout(() => setSaveStatus(null), 3000);
      } else {
        setSaveStatus('error');
      }
    } catch {
      setSaveStatus('error');
    }
  };

  const toggleCapability = async (key: keyof AIConfig, current: boolean) => {
    try {
      await fetch('/api/v1/admin/ai/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [key]: !current }),
      });
      aiApi.reload();
    } catch (e) {
      console.error('Failed to toggle capability', e);
    }
  };

  const testConnection = async () => {
    setTestTesting(true);
    setTestResult(null);
    try {
      const res = await fetch('/api/v1/admin/ai/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_url: baseUrl, model: modelTrans }),
      });
      const data = await res.json();
      setTestResult(data);
      aiApi.reload();
    } catch (err: unknown) {
      setTestResult({
        ok: false,
        status: 'unreachable',
        error: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setTestTesting(false);
    }
  };

  const runTestTranslation = async () => {
    if (!snippet.trim()) return;
    setTransTesting(true);
    setTransResult(null);
    try {
      const res = await fetch('/api/v1/admin/ai/test-translation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: snippet }),
      });
      const data = await res.json();
      setTransResult(data);
    } catch (err: unknown) {
      setTransResult({
        ok: false,
        status: 'error',
        translation: '',
        latency_ms: 0,
        model: modelTrans,
        error: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setTransTesting(false);
    }
  };

  const getCapabilityStatus = (cap: AICapability) => {
    if (!cap.enabled) {
      return <Tag tone="neutral">غیرفعال (Disabled)</Tag>;
    }
    if (testResult && !testResult.ok) {
      return <Tag tone="urgent">سرویس در دسترس نیست (Unavailable)</Tag>;
    }
    const qKey = cap.id === 'summary' ? 'translation_summary'
      : cap.id === 'title' ? 'translation_title'
      : cap.id === 'body' ? 'translation_body'
      : cap.id === 'executive_summary' ? 'ai_executive_summary'
      : cap.id === 'why_it_matters' ? 'ai_why_it_matters'
      : cap.id === 'key_points' ? 'ai_key_points' : '';
    const processing = d?.queues?.[qKey]?.['processing'] || 0;
    if (processing > 0) {
      return <Tag tone="uncertain">{`در حال پردازش (${fmt(processing)})`}</Tag>;
    }
    return <Tag tone="ok">{'فعال و آماده (Enabled & idle)'}</Tag>;
  };

  return (
    <section className="panel" aria-labelledby="ai-ctrl-h" style={{ gridColumn: 'span 2' }}>
      <div className="panel-title">
        <h3 id="ai-ctrl-h">کنترل‌های عملیاتی هوش مصنوعی (AI Operational Controls)</h3>
        <Tag tone="brand">{'Ollama & LAN Management'}</Tag>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px', marginTop: '12px' }}>
        {/* Connection Settings */}
        <div style={{ background: 'var(--surface-2)', color: 'var(--text-primary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
          <h4 style={{ marginBottom: '12px', fontSize: '1rem', color: 'var(--text-primary)' }}>تنظیمات اتصال سرور Ollama</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 500, color: 'var(--text-secondary)' }}>آدرس سرور Ollama (Local/LAN):</label>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="http://host.docker.internal:11434"
                style={{ width: '100%', padding: '6px 10px', borderRadius: '4px', border: '1px solid var(--border)', background: 'var(--surface-1)', color: 'var(--text-primary)', direction: 'ltr' }}
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 500, color: 'var(--text-secondary)' }}>مدل ترجمه (Translation):</label>
                <input
                  type="text"
                  value={modelTrans}
                  onChange={(e) => setModelTrans(e.target.value)}
                  style={{ width: '100%', padding: '6px 10px', borderRadius: '4px', border: '1px solid var(--border)', background: 'var(--surface-1)', color: 'var(--text-primary)', direction: 'ltr' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 500, color: 'var(--text-secondary)' }}>مدل دستیار (Assistant):</label>
                <input
                  type="text"
                  value={modelAsst}
                  onChange={(e) => setModelAsst(e.target.value)}
                  style={{ width: '100%', padding: '6px 10px', borderRadius: '4px', border: '1px solid var(--border)', background: 'var(--surface-1)', color: 'var(--text-primary)', direction: 'ltr' }}
                />
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 500, color: 'var(--text-secondary)' }}>مهلت زمانی (ثانیه):</label>
                <input
                  type="number"
                  value={timeoutSec}
                  onChange={(e) => setTimeoutSec(Number(e.target.value))}
                  style={{ width: '100%', padding: '6px 10px', borderRadius: '4px', border: '1px solid var(--border)', background: 'var(--surface-1)', color: 'var(--text-primary)', direction: 'ltr' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 500, color: 'var(--text-secondary)' }}>حداکثر همزمانی GPU:</label>
                <input
                  type="number"
                  value={maxConc}
                  onChange={(e) => setMaxConc(Number(e.target.value))}
                  style={{ width: '100%', padding: '6px 10px', borderRadius: '4px', border: '1px solid var(--border)', background: 'var(--surface-1)', color: 'var(--text-primary)', direction: 'ltr' }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px', marginTop: '8px' }}>
              <button
                type="button"
                onClick={testConnection}
                disabled={testTesting}
                style={{ padding: '8px 14px', borderRadius: '4px', cursor: 'pointer', background: '#3b82f6', color: '#fff', border: 'none', fontWeight: 500 }}
              >
                {testTesting ? 'در حال بررسی...' : 'آزمون اتصال (Test Connection)'}
              </button>
              <button
                type="button"
                onClick={saveSettings}
                style={{ padding: '8px 14px', borderRadius: '4px', cursor: 'pointer', background: '#10b981', color: '#fff', border: 'none', fontWeight: 500 }}
              >
                ذخیره تنظیمات
              </button>
            </div>
            {saveStatus === 'saved' && <p style={{ color: '#10b981', fontSize: '0.85rem' }}>تنظیمات با موفقیت در پایگاه داده ذخیره شد.</p>}
            {saveStatus === 'error' && <p style={{ color: '#ef4444', fontSize: '0.85rem' }}>خطا در ذخیره تنظیمات.</p>}

            {/* Test Connection Output */}
            {testResult && (
              <div style={{
                marginTop: '10px',
                padding: '10px',
                borderRadius: '6px',
                background: testResult.ok ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                border: `1px solid ${testResult.ok ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                color: 'var(--text-primary)'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong>وضعیت اتصال:</strong>
                  {testResult.ok && testResult.status === 'connected' ? (
                    <Tag tone="ok">{`متصل (${testResult.latency_ms} ms)`}</Tag>
                  ) : testResult.status === 'model_missing' ? (
                    <Tag tone="uncertain">مدل یافت نشد</Tag>
                  ) : (
                    <Tag tone="urgent">قطع ارتباط</Tag>
                  )}
                </div>
                {testResult.version && <p style={{ fontSize: '0.8rem', marginTop: '4px', color: 'var(--text-secondary)' }}>نسخه سرور: {testResult.version}</p>}
                {testResult.available_models && testResult.available_models.length > 0 && (
                  <p style={{ fontSize: '0.8rem', marginTop: '4px', color: 'var(--text-secondary)' }}>مدل‌های موجود: {testResult.available_models.join(', ')}</p>
                )}
                {testResult.error && <p style={{ color: '#ef4444', fontSize: '0.8rem', marginTop: '4px' }}>{testResult.error}</p>}
              </div>
            )}
          </div>
        </div>

        {/* Safe Manual Testing */}
        <div style={{ background: 'var(--surface-2)', color: 'var(--text-primary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
          <h4 style={{ marginBottom: '8px', fontSize: '1rem', color: 'var(--text-primary)' }}>آزمون دستی و ایمن ترجمه (Safe Manual Testing)</h4>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)', marginBottom: '10px' }}>
            ترجمه آزمایشی یک عبارت کوتاه بدون صف‌بندی پس‌زمینه و بدون تغییر مقالات در پایگاه داده.
          </p>
          <textarea
            value={snippet}
            onChange={(e) => setSnippet(e.target.value)}
            rows={3}
            placeholder="Enter English text to translate..."
            style={{ width: '100%', padding: '6px 10px', borderRadius: '4px', border: '1px solid var(--border)', background: 'var(--surface-1)', color: 'var(--text-primary)', direction: 'ltr', fontSize: '0.9rem' }}
          />
          <div style={{ marginTop: '8px' }}>
            <button
              type="button"
              onClick={runTestTranslation}
              disabled={transTesting || !snippet.trim()}
              style={{ padding: '8px 16px', borderRadius: '4px', cursor: 'pointer', background: '#6366f1', color: '#fff', border: 'none', fontWeight: 500 }}
            >
              {transTesting ? 'در حال ترجمه...' : 'ترجمه آزمایشی'}
            </button>
          </div>
          {transResult && (
            <div style={{
              marginTop: '12px',
              padding: '10px',
              borderRadius: '6px',
              background: transResult.ok ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
              border: `1px solid ${transResult.ok ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
              color: 'var(--text-primary)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  مدل: {transResult.model || modelTrans} · زمان: {transResult.latency_ms} ms
                </span>
                <Tag tone={transResult.ok ? 'ok' : 'urgent'}>{transResult.ok ? 'موفق' : 'خطا'}</Tag>
              </div>
              {transResult.translation && (
                <p style={{ fontSize: '0.95rem', fontWeight: 500, marginTop: '6px', lineHeight: 1.5, color: 'var(--text-primary)' }}>
                  {transResult.translation}
                </p>
              )}
              {transResult.error && (
                <p style={{ color: '#ef4444', fontSize: '0.8rem', marginTop: '4px' }}>
                  {transResult.error}
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 7 AI Capabilities Controls */}
      <div style={{ marginTop: '20px' }}>
        <h4 style={{ marginBottom: '10px', fontSize: '1rem' }}>کنترل مستقل قابلیت‌های هفت‌گانه هوش مصنوعی</h4>
        <p style={{ fontSize: '0.85rem', color: '#666', marginBottom: '12px' }}>
          تمامی قابلیت‌ها به‌صورت پیش‌فرض غیرفعال هستند و وضعیت آن‌ها در پایگاه داده ذخیره می‌شود. غیرفعال‌سازی سرویس را فوراً متوقف می‌کند.
        </p>

        {/* Translation & Job Queue Summary Cards */}
        {(() => {
          const totalJobsDone = Object.values(d?.queues || {}).reduce((acc, q) => acc + (q['succeeded'] || 0), 0);
          const totalPending = Object.values(d?.queues || {}).reduce((acc, q) => acc + (q['pending'] || 0), 0);
          const totalProcessing = Object.values(d?.queues || {}).reduce((acc, q) => acc + (q['processing'] || 0), 0);
          const totalCompletedStored = Object.values(d?.translations_completed || {}).reduce((acc, c) => acc + c, 0);

          return (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '16px' }}>
              <div style={{ background: 'var(--surface-2)', padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>کل ترجمه‌های ذخیره‌شده (سامانه)</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#10b981', marginTop: '4px' }}>{fmt(totalCompletedStored)}</div>
              </div>
              <div style={{ background: 'var(--surface-2)', padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>کارهای موفق در صف هوش مصنوعی</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#3b82f6', marginTop: '4px' }}>{fmt(totalJobsDone)}</div>
              </div>
              <div style={{ background: 'var(--surface-2)', padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>کل موارد در صف انتظار (Pending)</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 'bold', color: 'var(--text-primary)', marginTop: '4px' }}>{fmt(totalPending)}</div>
              </div>
              <div style={{ background: 'var(--surface-2)', padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>در حال پردازش زنده (Processing)</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 'bold', color: totalProcessing > 0 ? '#f59e0b' : 'var(--text-secondary)', marginTop: '4px' }}>{fmt(totalProcessing)}</div>
              </div>
            </div>
          );
        })()}

        <div style={{ overflowX: 'auto' }}>
          <table className="tbl" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th style={{ width: '40px' }}>فعال</th>
                <th>قابلیت</th>
                <th>نام سیستمی</th>
                <th>وضعیت زنده</th>
                <th>آمار کارها (انجام‌شده / در صف / در حال پردازش / خطا)</th>
              </tr>
            </thead>
            <tbody>
              {d?.capabilities?.map((cap) => {
                const qKey = cap.id === 'summary' ? 'translation_summary'
                  : cap.id === 'title' ? 'translation_title'
                  : cap.id === 'body' ? 'translation_body'
                  : cap.id === 'executive_summary' ? 'ai_executive_summary'
                  : cap.id === 'why_it_matters' ? 'ai_why_it_matters'
                  : cap.id === 'key_points' ? 'ai_key_points' : '';
                const qDone = qKey ? (d?.queues?.[qKey]?.['succeeded'] || 0) : 0;
                const qPending = qKey ? (d?.queues?.[qKey]?.['pending'] || 0) : 0;
                const qProc = qKey ? (d?.queues?.[qKey]?.['processing'] || 0) : 0;
                const qDead = qKey ? (d?.queues?.[qKey]?.['dead_letter'] || 0) : 0;
                const storedDone = qKey ? (d?.translations_completed?.[cap.id] ?? null) : null;

                return (
                  <tr key={cap.id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={cap.enabled}
                        onChange={() => toggleCapability(cap.key, cap.enabled)}
                        style={{ cursor: 'pointer', transform: 'scale(1.2)' }}
                      />
                    </td>
                    <td>
                      <strong>{cap.label_fa}</strong>
                      {cap.id === 'body' && <small style={{ color: '#b45309', marginRight: '6px' }}>(غیرفعال به‌صورت پیش‌فرض)</small>}
                    </td>
                    <td dir="ltr"><code>{cap.id}</code></td>
                    <td>{getCapabilityStatus(cap)}</td>
                    <td>
                      {qKey ? (
                        <span style={{ fontSize: '0.85rem' }}>
                          {'انجام‌شده: '}
                          <strong style={{ color: '#10b981' }}>{fmt(qDone)}</strong>
                          {storedDone !== null && (
                            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginRight: '4px' }}>
                              {` (${fmt(storedDone)} رکورد)`}
                            </span>
                          )}
                          {' | در صف: '}<strong>{fmt(qPending)}</strong>
                          {' | در حال پردازش: '}<strong>{fmt(qProc)}</strong>
                          {' | خطا: '}<strong style={{ color: qDead > 0 ? '#ef4444' : 'inherit' }}>{fmt(qDead)}</strong>
                        </span>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Circuit Breakers */}
      {d?.active_circuit_breakers && d.active_circuit_breakers.length > 0 && (
        <div style={{ marginTop: '20px', padding: '12px', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '8px' }}>
          <h4 style={{ color: '#f59e0b', marginBottom: '8px' }}>قطع‌کننده‌های مدار فعال (Circuit Breakers Active)</h4>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
            دامنه‌های زیر به دلیل خطاهای متوالی (۴۰۳ یا مسدودسازی) در دوره استراحت (Cooldown) قرار دارند:
          </p>
          <ul style={{ margin: 0, paddingRight: '20px', fontSize: '0.85rem', color: 'var(--text-primary)' }}>
            {d.active_circuit_breakers.map((cb) => (
              <li key={cb.domain}>
                <strong>{cb.domain}</strong>: {cb.consecutive_failures} خطای متوالی ({cb.last_error}) · پایان استراحت: {cb.cooldown_until}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
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
          {/* AI Operational Controls & Configuration */}
          <AIControlsSection />

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
            <div className="panel-title"><h3 id="tr-h">صف و کیفیت ترجمه</h3><Tag tone="ai">TranslateGemma 27B</Tag></div>
            {d.ai && d.ai.state !== 'enabled' && <p className="note" role="status" data-testid="admin-ai-off">{d.ai.message_fa} (<bdi dir="ltr">{d.ai.state}</bdi>) — ترجمه و دستیار متوقف‌اند؛ داده‌های ذخیره‌شده فقط‌خواندنی نمایش داده می‌شوند.</p>}
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

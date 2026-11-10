'use client';
import { useState } from 'react';
import { Cpu } from 'lucide-react';
import { fmt, fmtDateTime } from '../design/format';
import { useApi } from '../design/useApi';
import { AiTag, Tag } from '../design/ui';
import type { XPost } from './lib';

/** Local (Ollama) machine translation of an X post. Everything here is read
 *  from the API/PostgreSQL; the page never triggers a translation and never
 *  talks to the model. Only an `available` translation carries text. */
export const TRANSLATION_STATE_FA: Record<string, string> = {
  pending: 'ترجمه فارسی در صف پردازش محلی است.',
  stale: 'متن اصلی تغییر کرده است؛ ترجمه تازه در صف پردازش محلی است.',
  processing: 'در حال ترجمه با مدل محلی',
  needs_review: 'ترجمه ماشینی نیازمند بازبینی است.',
  failed: 'ترجمه محلی انجام نشد؛ متن اصلی همچنان در دسترس است.',
  not_required: 'متن اصلی فارسی است.',
};

// URLs, @mentions and #hashtags inside Persian text are isolated as LTR runs;
// without this the bidi algorithm moves '@', ':' and '/' to the wrong end.
const LTR_TOKEN = /(https?:\/\/[^\s]+|@[A-Za-z0-9_]{1,15}|#[A-Za-z0-9_]+)/g;
function withLtrRuns(text: string) {
  return text.split(LTR_TOKEN).map((part, i) => (i % 2 === 1 ? <bdi key={i} dir="ltr">{part}</bdi> : part));
}

export function TranslatedPost({ p, full = false }: { p: XPost; full?: boolean }) {
  const t = p.translation;
  const status = t?.status ?? 'pending';
  const available = status === 'available' && !!t?.translated_text;
  const [showOriginal, setShowOriginal] = useState(false);
  const persianSource = status === 'not_required';
  const clamp = full ? undefined : { WebkitLineClamp: 5 };

  if (!p.original_text) {
    return <p className="muted">متن محلی ثبت نشده است؛ فقط پیوند رسمی پست نگه داشته شده است.</p>;
  }
  const original = (
    <blockquote className="x-original" dir={persianSource ? 'rtl' : 'ltr'} lang={persianSource ? 'fa' : undefined} style={clamp}
      data-testid="x-original">{p.original_text}</blockquote>
  );

  if (!available) {
    return (
      <div className="x-translation" data-state={status}>
        <p className={`x-tr-state x-tr-${status}`} role="status" data-testid="x-tr-state">
          {status === 'processing' && <span className="x-tr-spinner" aria-hidden="true" />}
          {TRANSLATION_STATE_FA[status] ?? TRANSLATION_STATE_FA.pending}
        </p>
        {original}
      </div>
    );
  }
  return (
    <div className="x-translation" data-state="available">
      <div className="x-tr-bar">
        <AiTag>ترجمه ماشینی محلی</AiTag>
        <button type="button" className="btn-ghost x-tr-toggle" aria-pressed={showOriginal} onClick={() => setShowOriginal(!showOriginal)}
          data-testid="x-tr-toggle">
          {showOriginal ? 'نمایش ترجمه' : 'نمایش متن اصلی'}
        </button>
      </div>
      {showOriginal ? original : (
        <p className="x-tr-text" dir="rtl" lang="fa" style={clamp} data-testid="x-tr-text">{withLtrRuns(t!.translated_text!)}</p>
      )}
      <details className="x-tr-prov">
        <summary>جزئیات ترجمه</summary>
        <dl className="kv">
          <dt>مدل</dt><dd dir="ltr">{t!.model ?? '—'}</dd>
          <dt>اجرا</dt><dd>محلی روی همین سامانه (Ollama · CPU) · بدون سرویس ابری</dd>
          <dt>زمان ترجمه</dt><dd>{t!.translated_at ? fmtDateTime(t!.translated_at) : '—'}</dd>
          <dt>بازبینی</dt><dd>{t!.reviewed_at ? `بازبینی‌شده توسط ${t!.reviewed_by ?? '—'} · ${fmtDateTime(t!.reviewed_at)}` : 'بازبینی انسانی نشده'}</dd>
          <dt>نسخه دستور</dt><dd dir="ltr">{t!.prompt_version ?? '—'}</dd>
          {typeof t!.latency_ms === 'number' && <><dt>مدت پردازش</dt><dd>{fmt(Math.round(t!.latency_ms / 1000))} ثانیه</dd></>}
        </dl>
      </details>
    </div>
  );
}

interface TranslationStatus {
  enabled: boolean; ollama_reachable: boolean; model_found: boolean; configured_model: string | null;
  worker_running: boolean; config_errors: string[];
}
interface TranslationStats {
  pending: number; processing: number; available: number; needs_review: number; failed: number; not_required: number;
  stale: number; translatable: number;
}

export function TranslationStatusNote() {
  const st = useApi<TranslationStatus>('social/translation/status');
  const stats = useApi<TranslationStats>('social/translations/stats');
  if (!st.data || !stats.data) return null;
  const s = st.data, c = stats.data;
  const queued = c.pending + c.stale;
  return (
    <section className="panel x-tr-panel" aria-label="ترجمه محلی پست‌ها" data-testid="x-tr-panel">
      <div className="panel-title"><h3><Cpu size={15} aria-hidden="true" /> ترجمه محلی پست‌ها</h3>
        <Tag tone={s.ollama_reachable && s.model_found ? 'ok' : 'warn'}>
          {s.ollama_reachable ? (s.model_found ? 'مدل محلی در دسترس' : 'مدل پیکربندی‌شده یافت نشد') : 'مدل محلی خاموش است'}
        </Tag>
      </div>
      <p className="muted">
        ترجمه به‌صورت دسته‌ای و غیربلادرنگ با مدل محلی <bdi dir="ltr">{s.configured_model ?? '—'}</bdi> انجام می‌شود؛ هیچ سرویس ابری استفاده نمی‌شود و بازکردن صفحه ترجمه‌ای اجرا نمی‌کند.
        {!s.ollama_reachable && ' تا روشن‌شدن مدل محلی، پست‌ها با متن اصلی نمایش داده می‌شوند.'}
      </p>
      <div className="x-tr-counts">
        <span>ترجمه‌شده: <b>{fmt(c.available)}</b></span>
        <span>در صف: <b>{fmt(queued)}</b></span>
        <span>نیازمند بازبینی: <b>{fmt(c.needs_review)}</b></span>
        <span>ناموفق: <b>{fmt(c.failed)}</b></span>
        <span>فارسی (بی‌نیاز): <b>{fmt(c.not_required)}</b></span>
        {s.worker_running && <Tag tone="info">پردازش در حال اجرا</Tag>}
      </div>
    </section>
  );
}

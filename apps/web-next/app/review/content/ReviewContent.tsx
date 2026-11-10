'use client';
import { useState } from 'react';
import Link from 'next/link';
import { CheckCircle2, XCircle, Pencil, RefreshCw, ShieldAlert, ExternalLink } from 'lucide-react';
import { Shell } from '../../design/Shell';
import { useApi } from '../../design/useApi';
import { Badge, EmptyState, ErrorState, Skeleton, FieldStatus } from '../../design/ui';
import { fmt, fmtDateTime, isPersian } from '../../design/format';

interface QueueItem {
  item_id: string; title: string; field: string; text: string | null;
  provider: string | null; model: string | null; prompt_version: string | null;
  quality_score: number | null; quality_flags: string[]; review_status: string;
  reviewed_by: string | null; reviewed_at: string | null; updated_at: string; source_name: string;
}
interface QueueData { items: QueueItem[]; total: number; page: number; page_size: number; status_filter: string }

interface KeyPoint { point_id: number; point_index: number; text_fa: string; evidence_span: string; evidence_verified: boolean }
interface CIDetail {
  item_id: string; original_title: string; original_language: string | null;
  original_summary: string | null; original_content_excerpt: string | null;
  translation: Record<string, { field: string; status: string; text: string | null }>;
  summary: { status: string; text: string | null } | null;
  executive_summary: { status: string; text: string | null } | null;
  why_it_matters: { status: string; text: string | null } | null;
  key_points: KeyPoint[];
}

const STATUS_TABS: [string, string][] = [
  ['needs_review', 'نیازمند بازبینی'], ['pending_review', 'در صف بازبینی'],
  ['approved', 'تأییدشده'], ['rejected', 'ردشده'],
];
const REVIEWER_NAME = 'reviewer'; // single-operator context; no auth layer exists yet in this phase

async function postAction(path: string, params: Record<string, string>): Promise<{ ok: boolean; body: any }> {
  const qs = new URLSearchParams(params).toString();
  // The API proxy accepts writes only as JSON (cross-site form posts are refused).
  const res = await fetch(`/api/v1${path}?${qs}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{}' });
  const body = await res.json().catch(() => ({}));
  return { ok: res.ok, body };
}

export function ReviewContent() {
  const [status, setStatus] = useState('needs_review');
  const [selected, setSelected] = useState<QueueItem | null>(null);
  const [editText, setEditText] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const { data, error, loading, reload } = useApi<QueueData>('review/content?status=' + status, [status]);
  const detailQ = useApi<CIDetail>(selected ? 'news/' + encodeURIComponent(selected.item_id) + '/content-intelligence' : null, [selected?.item_id]);

  function openRow(row: QueueItem) {
    setSelected(row);
    setEditText(row.text || '');
    setRejectReason('');
    setNotice(null);
  }

  async function act(action: 'approve' | 'reject' | 'edit' | 'regenerate') {
    if (!selected) return;
    setBusy(true);
    setNotice(null);
    try {
      const params: Record<string, string> = { field: selected.field };
      if (action !== 'regenerate') params.reviewed_by = REVIEWER_NAME;
      if (action === 'reject') params.reason = rejectReason || 'no reason given';
      if (action === 'edit') params.text = editText;
      const { ok, body } = await postAction(`/review/content/${encodeURIComponent(selected.item_id)}/${action}`, params);
      if (!ok) { setNotice('خطا: ' + (body.detail || 'عملیات ناموفق بود')); return; }
      if (action === 'regenerate' && body.status === 'provider_not_configured') {
        setNotice('ارائه‌دهنده هوش مصنوعی تنظیم نشده است؛ بازتولید انجام نشد و متنی ساخته نشد.');
      } else {
        setNotice('انجام شد: ' + action);
      }
      reload();
      if (action !== 'regenerate') setSelected(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell title="بازبینی محتوا" breadcrumb="صف بازبینی ترجمه و خلاصه">
      <div className="page-head">
        <div>
          <h1>بازبینی محتوای هوش مصنوعی</h1>
          <p>هیچ خروجی مدل بدون بازبینی یا تأیید انسانی به‌عنوان محتوای قطعی نمایش داده نمی‌شود.</p>
        </div>
      </div>

      <div className="periods">
        {STATUS_TABS.map(([v, t]) => (
          <button key={v} className={status === v ? 'selected' : ''} onClick={() => { setStatus(v); setSelected(null); }}>{t}</button>
        ))}
      </div>

      {error && <ErrorState onRetry={reload}>صف بازبینی دریافت نشد.</ErrorState>}
      {loading && <Skeleton height={280} radius={14} />}

      {!loading && !error && data && (
        <div className="dash-grid">
          <section className="card">
            <div className="card-title"><h2>{fmt(data.total)} مورد</h2></div>
            {!data.items.length ? (
              <EmptyState title="موردی در این وضعیت نیست">
                {status === 'needs_review' ? 'هیچ خروجی‌ای اکنون رد اعتبارسنجی نشده — یا هنوز چیزی تولید نشده (ارائه‌دهنده هوش مصنوعی فعال نیست).' : 'فهرست خالی است.'}
              </EmptyState>
            ) : (
              <div className="topic-list">
                {data.items.map((row) => (
                  <button key={row.item_id + row.field} className="topic-row topic-row-static" style={{ width: '100%', textAlign: 'right', cursor: 'pointer' }}
                    onClick={() => openRow(row)}>
                    <span className="topic-rank">{row.quality_score != null ? Math.round(row.quality_score * 100) + '٪' : '—'}</span>
                    <div className="topic-info">
                      <strong dir={isPersian(row.title) ? 'rtl' : 'ltr'}>{row.title}</strong>
                      <span className="chart-caption">{row.field} · {row.source_name} · {fmtDateTime(row.updated_at)}</span>
                    </div>
                    <span className="topic-count">{row.provider || '—'}</span>
                    <span className="topic-meta">{row.quality_flags?.length ? <Badge tone="error">{row.quality_flags.length} پرچم</Badge> : <Badge tone="muted">بدون پرچم</Badge>}</span>
                  </button>
                ))}
              </div>
            )}
          </section>

          <div className="dash-side">
            {!selected ? (
              <section className="card"><EmptyState title="موردی را برای بازبینی انتخاب کنید" /></section>
            ) : (
              <section className="card">
                <div className="card-title"><h2>بازبینی: {selected.field}</h2>
                  <Link href={'/news/' + encodeURIComponent(selected.item_id)} target="_blank">مشاهده خبر <ExternalLink size={12} /></Link>
                </div>

                <FieldStatus label="وضعیت" status={selected.review_status} />
                {selected.quality_score != null && <p className="chart-caption">امتیاز کیفیت: {(selected.quality_score * 100).toFixed(0)}٪</p>}
                {!!selected.quality_flags?.length && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, margin: '8px 0' }}>
                    {selected.quality_flags.map((f) => <Badge key={f} tone="error"><ShieldAlert size={11} /> {f}</Badge>)}
                  </div>
                )}
                <p className="chart-caption">ارائه‌دهنده: {selected.provider || '—'} · مدل: {selected.model || '—'} · نسخه prompt: {selected.prompt_version || '—'}</p>

                {detailQ.loading && <Skeleton height={120} radius={10} />}
                {detailQ.data && (
                  <div className="news-detail-fields" style={{ margin: '12px 0' }}>
                    <div className="news-detail-text-ltr" dir="ltr" style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', maxHeight: 100, overflow: 'auto', marginBottom: 8 }}>
                      {detailQ.data.original_title}
                      {detailQ.data.original_content_excerpt ? ' — ' + detailQ.data.original_content_excerpt.slice(0, 300) : ''}
                    </div>
                  </div>
                )}

                <label className="field">متن فارسی (قابل ویرایش)
                  <textarea value={editText} onChange={(e) => setEditText(e.target.value)} rows={5} dir="rtl"
                    style={{ width: '100%', background: 'var(--surface-2)', color: 'var(--text-primary)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: 8 }} />
                </label>

                {notice && <p className="chart-caption" role="status">{notice}</p>}

                <div className="news-filters-actions" style={{ marginTop: 12, flexWrap: 'wrap' }}>
                  <button className="btn btn-primary" disabled={busy} onClick={() => act('approve')}><CheckCircle2 size={14} /> تأیید</button>
                  <button className="btn btn-secondary" disabled={busy} onClick={() => act('edit')}><Pencil size={14} /> ذخیره ویرایش</button>
                  <button className="btn btn-secondary" disabled={busy} onClick={() => act('regenerate')}><RefreshCw size={14} /> بازتولید</button>
                </div>
                <label className="field" style={{ marginTop: 8 }}>دلیل رد (اختیاری)
                  <input value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} dir="rtl" />
                </label>
                <button className="btn btn-secondary" disabled={busy} onClick={() => act('reject')} style={{ marginTop: 8 }}>
                  <XCircle size={14} /> رد
                </button>
              </section>
            )}
          </div>
        </div>
      )}
    </Shell>
  );
}

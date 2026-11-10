'use client';
import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Shell } from '../../../design/Shell';
import { useApi, useNow } from '../../../design/useApi';
import { fmtDateTime } from '../../../design/format';
import { AiTag, Bone, Failure, PageHead, RuleTag, Tag } from '../../../design/ui';
import { PostCard } from '../../PostCard';
import { XEmbed } from '../../XEmbed';
import { useTopicLabels } from '../../Social';
import { AVAILABILITY_FA, errorText, VERIFICATION_FA, writeSocial, type SocialStatus, type XPost } from '../../lib';

const ACTIONS: [string, string, 'ai' | 'rule'][] = [
  // Translation is not an on-demand action: the local offline batch owns it.
  ['summarize', 'خلاصه فارسی', 'ai'],
  ['classify', 'پیشنهاد موضوع', 'rule'], ['entities', 'استخراج نام‌ها', 'rule'], ['suggest_event', 'پیشنهاد رویداد', 'rule'],
];
const STATUS_FA: Record<string, string> = {
  suggested: 'پیشنهاد', available: 'انجام شد', needs_review: 'ردشده در کنترل کیفیت', provider_not_configured: 'ارائه‌دهنده پیکربندی نشده',
  error: 'خطا', circuit_open: 'متوقف (قطع‌کننده)', budget_exceeded: 'سقف بودجه',
};
const ACTION_FA: Record<string, string> = {
  created: 'ثبت', updated: 'ویرایش', availability_changed: 'تغییر وضعیت', ai_translate: 'ترجمه هوش مصنوعی',
  ai_summarize: 'خلاصه هوش مصنوعی', ai_classify: 'پیشنهاد موضوع', ai_entities: 'استخراج نام', ai_suggest_event: 'پیشنهاد رویداد',
};

export default function Page() {
  const { postId } = useParams<{ postId: string }>();
  const q = useApi<XPost>('social/posts/' + encodeURIComponent(postId), [postId]);
  const status = useApi<SocialStatus>('social/status');
  const now = useNow();
  const { label } = useTopicLabels();
  const [analyst, setAnalyst] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (q.error) return <Shell><Failure onRetry={q.reload}>این پست پیدا نشد.</Failure></Shell>;
  if (!q.data) return <Shell><Bone h={28} w="40%" /><Bone h={160} /></Shell>;
  const p = q.data;
  const canWrite = status.data?.manual_ingest_enabled;

  const act = async (fn: () => Promise<{ ok: boolean; data: unknown }>, okText: string) => {
    setBusy(true); setMsg(null);
    const r = await fn();
    setBusy(false);
    setMsg(r.ok ? okText : errorText((r.data as { detail?: unknown }).detail));
    q.reload();
  };
  const runAi = (action: string) => act(() => writeSocial(`social/posts/${p.post_id}/ai`, 'POST', { analyst, action }), 'اقدام اجرا و در تاریخچه ثبت شد.');
  const setField = (patch: Record<string, string>) => act(() => writeSocial(`social/manual-posts/${p.post_id}`, 'PATCH', { analyst, ...patch }), 'تغییر ثبت شد.');

  return (
    <Shell>
      <nav className="muted" aria-label="مسیر"><Link href="/social">شبکه‌های اجتماعی</Link> / <Link href={`/social/accounts/${p.source_id}`} dir="ltr">{p.author_handle}</Link></nav>
      <PageHead eyebrow="پست X · ثبت دستی" title={`پست ثبت‌شده از حساب ${p.author_handle.replace(/^@/, '')}`} />
      <div className="detail">
        <div className="detail-main">
          <PostCard p={p} now={now} topicLabel={label} full />
          {p.event_id && <p className="muted">رویداد مرتبط: <Link href={`/events/${p.event_id}`} className="sec-link" dir="ltr">{p.event_title}</Link></p>}
          {p.related_item_id && <p className="muted">خبر مرتبط: <Link href={`/news/${p.related_item_id}`} className="sec-link" dir="ltr">{p.related_item_title}</Link></p>}
          {p.media && p.media.length > 0 && (
            <section className="panel"><div className="panel-title"><h3>رسانه ثبت‌شده</h3></div>
              <ul className="prov">{p.media.map((m, i) => <li key={i}><span /><div><a href={m.external_url} target="_blank" rel="noopener noreferrer nofollow" dir="ltr" className="sec-link">{m.media_type}</a><small>{m.alt_text ?? 'بدون توضیح'} · ثبت‌شده توسط تحلیلگر</small></div></li>)}</ul>
            </section>
          )}
          <XEmbed postId={p.post_id} postUrl={p.post_url} />
          {p.provenance_json?.ai && Object.keys(p.provenance_json.ai).length > 0 && (
            <section className="panel"><div className="panel-title"><h3>خروجی‌های کمکی</h3></div>
              <ul className="prov">
                {Object.entries(p.provenance_json.ai).map(([k, v]) => (
                  <li key={k}><span />
                    <div>{v.kind === 'ai' ? <AiTag>{String(v.label_fa ?? 'هوش مصنوعی')}</AiTag> : <RuleTag>{String(v.label_fa ?? 'قاعده‌محور')}</RuleTag>}
                      <small>{ACTION_FA['ai_' + k] ?? k} · وضعیت {STATUS_FA[String(v.status)] ?? String(v.status)} {v.response_model ? `· مدل ${String(v.response_model)}` : ''} {v.error ? `· ${String(v.error)}` : ''} · {fmtDateTime(String(v.at))}</small>
                      {k === 'classify' && <small>پیشنهاد: {label(String(v.suggested_topic))}</small>}
                      {k === 'entities' && <small dir="ltr">{(v.entities as string[] | undefined)?.join(', ') || '—'}</small>}
                      {k === 'suggest_event' && <small>{(v.events as { event_id: string; title: string }[] | undefined)?.map((e) => <Link key={e.event_id} href={`/events/${e.event_id}`} className="sec-link" dir="ltr" style={{ display: 'block' }}>{e.title}</Link>) ?? '—'}</small>}
                    </div></li>
                ))}
              </ul>
            </section>
          )}
        </div>
        <aside className="side">
          {canWrite && (
            <section className="panel">
              <div className="panel-title"><h3>اقدام تحلیلگر</h3></div>
              <label className="field">نام تحلیلگر *<input value={analyst} onChange={(e) => setAnalyst(e.target.value)} maxLength={60} /></label>
              <p className="muted">اقدام‌های هوش مصنوعی فقط با درخواست شما و فقط روی متنی که تحلیلگر ثبت کرده اجرا می‌شوند. اگر ارائه‌دهنده در دسترس نباشد، پست بدون تغییر می‌ماند.</p>
              <div className="x-actions">
                {ACTIONS.map(([k, l, kind]) => (
                  <button key={k} type="button" className="btn-ghost" disabled={busy || !analyst || !p.original_text} onClick={() => runAi(k)}
                    title={p.original_text ? undefined : 'متن محلی ثبت نشده است'}>{l}{kind === 'ai' ? ' · AI' : ' · قاعده'}</button>
                ))}
              </div>
              <label className="field">راستی‌آزمایی
                <select value={p.verification_status} disabled={busy || !analyst} onChange={(e) => setField({ verification_status: e.target.value })}>
                  {Object.entries(VERIFICATION_FA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </label>
              <label className="field">وضعیت دسترسی (حذف فیزیکی انجام نمی‌شود)
                <select value={p.availability_status} disabled={busy || !analyst} onChange={(e) => setField({ availability_status: e.target.value })}>
                  {Object.entries(AVAILABILITY_FA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </label>
              {msg && <p className="note" role="status">{msg}</p>}
            </section>
          )}
          <section className="panel">
            <div className="panel-title"><h3>تاریخچه</h3><Tag>{p.history?.length ?? 0}</Tag></div>
            <ul className="prov">
              {p.history?.map((h, i) => <li key={i}><span /><div>{ACTION_FA[h.action] ?? h.action}<small><bdi>{h.actor}</bdi> · {fmtDateTime(h.created_at)}</small></div></li>)}
            </ul>
          </section>
          <section className="panel">
            <div className="panel-title"><h3>منشأ</h3></div>
            <dl className="kv">
              <dt>روش</dt><dd>ثبت دستی · از X چیزی دریافت نشده</dd>
              <dt>ثبت‌کننده</dt><dd><bdi>{String(p.provenance_json?.registered_by ?? '—')}</bdi></dd>
              <dt>زمان ثبت</dt><dd>{fmtDateTime(p.manually_registered_at)}</dd>
              <dt>متن</dt><dd>{String(p.provenance_json?.note_fa ?? '')}</dd>
            </dl>
          </section>
        </aside>
      </div>
    </Shell>
  );
}

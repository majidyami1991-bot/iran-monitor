'use client';
import { useState } from 'react';
import { useApi, useNow } from '../design/useApi';
import { Failure, Tag } from '../design/ui';
import { PostCard } from './PostCard';
import { errorText, IMPORTANCE_FA, VERIFICATION_FA, writeSocial, type XAccount, type XPost } from './lib';

interface EventRow { event_id: string; title: string }

const EMPTY = { url: '', analyst: '', original_text: '', published_at: '', topic_id: '', importance: 'medium',
  verification_status: 'unverified', analyst_note: '', event_id: '', related_item_id: '' };

/** Manual registration of one specific X post. "Preview" runs the same server
 *  validation with dry_run=true and shows exactly what would be stored;
 *  nothing is written until "Save". */
export function RegisterForm({ accounts, topics, onDone }: {
  accounts: XAccount[]; topics: { id: string; label: string; subtopics: { id: string; label: string }[] }[]; onDone: () => void;
}) {
  const [f, setF] = useState(EMPTY);
  const [preview, setPreview] = useState<XPost | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const events = useApi<{ events: EventRow[] }>('timeline/events?sort=latest&page_size=60');
  const now = useNow();
  const upd = (k: keyof typeof EMPTY) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setF({ ...f, [k]: e.target.value }); setPreview(null);
  };
  const body = (dry: boolean) => ({
    url: f.url, analyst: f.analyst, original_text: f.original_text || null,
    published_at: f.published_at ? new Date(f.published_at).toISOString() : null,
    topic_id: f.topic_id || null, importance: f.importance, verification_status: f.verification_status,
    analyst_note: f.analyst_note || null, event_id: f.event_id || null, related_item_id: f.related_item_id.trim() || null,
    dry_run: dry,
  });
  const submit = async (dry: boolean) => {
    setBusy(true); setError(null);
    const r = await writeSocial<{ would_create?: XPost } & XPost>('social/manual-posts', 'POST', body(dry));
    setBusy(false);
    if (!r.ok) { setError(errorText((r.data as { detail?: unknown }).detail)); return; }
    if (dry) {
      const w = (r.data as { would_create: XPost }).would_create;
      setPreview({ ...w, manually_registered_at: new Date().toISOString(), profile_url: '', display_name: null, event_title: null, related_item_title: null, translated_text_fa: null, summary_fa: null });
    } else { setF(EMPTY); setPreview(null); onDone(); }
  };

  return (
    <section className="panel x-form" aria-labelledby="xform-h">
      <div className="panel-title"><h3 id="xform-h">ثبت پست X</h3><Tag tone="info">فقط ثبت دستی · چیزی از X دریافت نمی‌شود</Tag></div>
      <form onSubmit={(e) => { e.preventDefault(); submit(true); }} noValidate>
        <div className="grid-2">
          <label className="field">نشانی پست (x.com یا twitter.com) *
            <input name="url" dir="ltr" value={f.url} onChange={upd('url')} required placeholder="https://x.com/handle/status/1234567890" inputMode="url" />
          </label>
          <label className="field">نام تحلیلگر *
            <input name="analyst" value={f.analyst} onChange={upd('analyst')} required maxLength={60} />
          </label>
        </div>
        <label className="field">متن اصلی پست (اختیاری؛ دقیقاً همان‌طور که در X آمده، توسط شما وارد می‌شود)
          <textarea name="original_text" dir="auto" rows={4} maxLength={4000} value={f.original_text} onChange={upd('original_text')} />
        </label>
        <div className="grid-3">
          <label className="field">تاریخ و زمان انتشار (اختیاری)
            <input type="datetime-local" name="published_at" value={f.published_at} onChange={upd('published_at')} />
          </label>
          <label className="field">موضوع
            <select name="topic_id" value={f.topic_id} onChange={upd('topic_id')}>
              <option value="">بدون موضوع</option>
              {topics.map((c) => <optgroup key={c.id} label={c.label}><option value={c.id}>{c.label}</option>{c.subtopics.map((s) => <option key={s.id} value={s.id}>— {s.label}</option>)}</optgroup>)}
            </select>
          </label>
          <label className="field">اهمیت
            <select name="importance" value={f.importance} onChange={upd('importance')}>{Object.entries(IMPORTANCE_FA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
          </label>
          <label className="field">راستی‌آزمایی
            <select name="verification_status" value={f.verification_status} onChange={upd('verification_status')}>{Object.entries(VERIFICATION_FA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
          </label>
          <label className="field">اتصال به رویداد
            <select name="event_id" value={f.event_id} onChange={upd('event_id')}>
              <option value="">بدون رویداد</option>
              {events.data?.events.map((e) => <option key={e.event_id} value={e.event_id}>{e.title.slice(0, 80)}</option>)}
            </select>
          </label>
          <label className="field">شناسه خبر مرتبط (اختیاری)
            <input name="related_item_id" dir="ltr" value={f.related_item_id} onChange={upd('related_item_id')} />
          </label>
        </div>
        <label className="field">توضیح تحلیلگر
          <textarea name="analyst_note" rows={2} maxLength={2000} value={f.analyst_note} onChange={upd('analyst_note')} />
        </label>
        <p className="muted">حساب نویسنده از نشانی استخراج و با ۳۶ حساب فهرست منابع تطبیق داده می‌شود. نشانی کوتاه (t.co)، دامنه مشابه یا حساب خارج از فهرست پذیرفته نمی‌شود.</p>
        {error && <Failure>{error}</Failure>}
        <div className="x-form-actions">
          <button type="submit" className="btn-ghost" disabled={busy}>پیش‌نمایش پیش از ثبت</button>
          <button type="button" className="btn-primary" disabled={busy || !preview} onClick={() => submit(false)}
            title={preview ? undefined : 'ابتدا پیش‌نمایش را ببینید'}>ثبت نهایی</button>
        </div>
      </form>
      {preview && (
        <div className="x-preview" aria-live="polite">
          <h4 className="brief-sub">پیش‌نمایش آنچه ذخیره می‌شود</h4>
          <PostCard p={preview} now={now} full />
        </div>
      )}
      {accounts.length === 0 && <p className="muted">فهرست حساب‌ها در دسترس نیست.</p>}
    </section>
  );
}

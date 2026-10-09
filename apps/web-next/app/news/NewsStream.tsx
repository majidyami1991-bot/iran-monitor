'use client';
import { useMemo, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { SlidersHorizontal, X } from 'lucide-react';
import { Shell } from '../design/Shell';
import { useApi, useNow } from '../design/useApi';
import type { FeedResponse } from '../design/types';
import { fmt, qs } from '../design/format';
import { CardBones, Empty, Failure, PageHead, Pager, Segmented } from '../design/ui';
import { NewsCard } from '../components/NewsCard';

interface Topics { categories: { id: string; label: string; count: number; subtopics: { id: string; label: string; count: number }[] }[] }
interface Sources { sources: { source_id: string; name: string; item_count: number }[] }

const KEYS = ['q', 'source_id', 'category', 'topic', 'window', 'date_from', 'date_to', 'lang', 'importance', 'translation', 'sort', 'page'] as const;
type Key = (typeof KEYS)[number];

const LABELS: Partial<Record<Key, Record<string, string>>> = {
  window: { '1h': 'یک ساعت', '24h': '۲۴ ساعت', '7d': '۷ روز', '30d': '۳۰ روز' },
  lang: { en: 'انگلیسی', fa: 'فارسی', unknown: 'زبان نامشخص' },
  importance: { high: 'اهمیت زیاد', medium: 'اهمیت متوسط', low: 'اهمیت کم' },
  translation: { available: 'ترجمه خودکار بدون ایراد کیفیت', warning: 'ترجمه با هشدار کیفیت', failed: 'ترجمه ردشده در کنترل کیفیت', pending: 'ترجمه در انتظار', error: 'خطای ترجمه' },
};

/** All filter state lives in the URL, so every view is shareable and the
 *  back button works; the API receives exactly the same parameters. */
export function NewsStream() {
  const sp = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const now = useNow();
  const [open, setOpen] = useState(false);
  const p = useMemo(() => Object.fromEntries(KEYS.map((k) => [k, sp.get(k) ?? ''])) as Record<Key, string>, [sp]);
  const sort = (p.sort || 'newest') as 'newest' | 'important' | 'coverage' | 'oldest';
  const page = Math.max(1, Number(p.page) || 1);

  const set = (patch: Partial<Record<Key, string>>) => {
    const next = { ...p, ...patch };
    if (!('page' in patch)) next.page = '';
    router.push(pathname + qs(next), { scroll: 'page' in patch });
  };

  const apiQs = qs({ ...p, sort, page, page_size: 24 });
  const q = useApi<FeedResponse>('feed' + apiQs, [apiQs]);
  const topics = useApi<Topics>('topics?window=all');
  const sources = useApi<Sources>('source-profiles');

  const catLabel = (id: string) => topics.data?.categories.find((c) => c.id === id)?.label ?? (id === 'other' ? 'سایر' : id);
  const subLabel = (id: string) => topics.data?.categories.flatMap((c) => c.subtopics).find((s) => s.id === id)?.label ?? id;
  const srcLabel = (id: string) => sources.data?.sources.find((s) => s.source_id === id)?.name ?? 'منبع';
  const active = (KEYS.filter((k) => p[k] && !['sort', 'page'].includes(k)) as Key[]).map((k) => ({
    k, label: k === 'category' ? catLabel(p[k]) : k === 'topic' ? subLabel(p[k]) : k === 'source_id' ? srcLabel(p[k])
      : k === 'q' ? `«${p[k]}»` : k === 'date_from' ? `از ${p[k]}` : k === 'date_to' ? `تا ${p[k]}` : LABELS[k]?.[p[k]] ?? p[k],
  }));

  return (
    <Shell>
      <PageHead eyebrow="جریان خبر" title="اخبار" lede="همه خبرهای گردآوری‌شده از منابع فعال. عنوان فارسی فقط وقتی نمایش داده می‌شود که ترجمه ماشینی واقعاً ذخیره شده باشد؛ در غیر این صورت متن اصلی منبع نمایش داده می‌شود." />
      <div className="stream">
        <aside className="filters" data-open={open ? 'true' : 'false'} aria-label="فیلترها">
          <h2>فیلترها</h2>
          <form onSubmit={(e) => { e.preventDefault(); const f = new FormData(e.currentTarget); set({ q: String(f.get('q') || '') }); }}>
            <label className="field">جست‌وجو<input name="q" defaultValue={p.q} key={p.q} placeholder="واژه در عنوان یا خلاصه" /></label>
          </form>
          <label className="field">منبع
            <select name="source_id" value={p.source_id} onChange={(e) => set({ source_id: e.target.value })}>
              <option value="">همه منابع</option>
              {sources.data?.sources.map((s) => <option key={s.source_id} value={s.source_id}>{s.name} ({fmt(s.item_count)})</option>)}
            </select>
          </label>
          <label className="field">موضوع
            <select name="category" value={p.category} onChange={(e) => set({ category: e.target.value, topic: '' })}>
              <option value="">همه موضوعات</option>
              {topics.data?.categories.map((c) => <option key={c.id} value={c.id}>{c.label} ({fmt(c.count)})</option>)}
              <option value="other">سایر (با دلیل مشخص)</option>
            </select>
          </label>
          {p.category && topics.data?.categories.find((c) => c.id === p.category)?.subtopics.length ? (
            <label className="field">زیرموضوع
              <select name="topic" value={p.topic} onChange={(e) => set({ topic: e.target.value })}>
                <option value="">همه زیرموضوع‌ها</option>
                {topics.data.categories.find((c) => c.id === p.category)!.subtopics.map((s) => <option key={s.id} value={s.id}>{s.label} ({fmt(s.count)})</option>)}
              </select>
            </label>
          ) : null}
          <label className="field">بازه زمانی
            <select name="window" value={p.window} onChange={(e) => set({ window: e.target.value })}>
              <option value="">همه زمان‌ها</option>
              {Object.entries(LABELS.window!).map(([k, v]) => <option key={k} value={k}>{v} اخیر</option>)}
            </select>
          </label>
          <div className="grid-2">
            <label className="field">از تاریخ<input type="date" name="date_from" value={p.date_from} onChange={(e) => set({ date_from: e.target.value })} /></label>
            <label className="field">تا تاریخ<input type="date" name="date_to" value={p.date_to} onChange={(e) => set({ date_to: e.target.value })} /></label>
          </div>
          <label className="field">زبان محتوا
            <select name="lang" value={p.lang} onChange={(e) => set({ lang: e.target.value })}>
              <option value="">همه</option>
              {Object.entries(LABELS.lang!).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label className="field">اهمیت (قاعده importance_v1)
            <select name="importance" value={p.importance} onChange={(e) => set({ importance: e.target.value })}>
              <option value="">همه</option>
              {Object.entries(LABELS.importance!).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label className="field">وضعیت ترجمه
            <select name="translation" value={p.translation} onChange={(e) => set({ translation: e.target.value })}>
              <option value="">همه</option>
              {Object.entries(LABELS.translation!).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          {active.length > 0 && <button type="button" className="btn-ghost" onClick={() => router.push(pathname)}>پاک کردن همه فیلترها</button>}
        </aside>

        <section aria-labelledby="stream-h" style={{ minWidth: 0 }}>
          <h2 id="stream-h" className="sr-only">نتایج</h2>
          <div className="stream-head">
            <button type="button" className="btn-ghost filter-toggle" aria-expanded={open} onClick={() => setOpen(!open)}><SlidersHorizontal size={15} />فیلترها{active.length ? ` (${fmt(active.length)})` : ''}</button>
            <span className="stream-count" role="status">{q.data ? `${fmt(q.data.total)} خبر` : 'در حال شمارش…'}</span>
            <Segmented label="مرتب‌سازی" value={sort} onChange={(v) => set({ sort: v })}
              items={[['newest', 'جدیدترین'], ['important', 'مهم‌ترین'], ['coverage', 'پربازتاب‌ترین'], ['oldest', 'قدیمی‌ترین']]} />
          </div>
          {active.length > 0 && (
            <div className="active-filters" aria-label="فیلترهای فعال">
              {active.map((a) => <button key={a.k} type="button" onClick={() => set({ [a.k]: '' })} aria-label={`حذف فیلتر ${a.label}`}>{a.label}<X size={12} /></button>)}
            </div>
          )}
          {q.error && <Failure onRetry={q.reload} />}
          {!q.data && !q.error && <CardBones n={6} />}
          {q.data && q.data.items.length === 0 && (
            <Empty title="هیچ خبری با این فیلترها پیدا نشد">فیلترها را کمتر کنید یا بازه زمانی را گسترش دهید.{p.translation === 'available' && ' تاکنون هیچ ترجمه فارسی موفقی در پایگاه داده ذخیره نشده است.'}</Empty>
          )}
          {q.data && q.data.items.length > 0 && (
            <>
              <div style={{ opacity: q.loading ? 0.6 : 1, transition: 'opacity 150ms' }}>
                {q.data.items.map((i) => <NewsCard key={i.item_id} item={i} now={now} variant="row" />)}
              </div>
              <Pager page={page} hasNext={q.data.has_next} total={q.data.total} onPage={(n) => set({ page: String(n) })} />
            </>
          )}
        </section>
      </div>
    </Shell>
  );
}

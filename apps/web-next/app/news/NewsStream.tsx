'use client';
import { useEffect, useMemo, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { SlidersHorizontal, X } from 'lucide-react';
import { Shell } from '../design/Shell';
import { useApi, useNow } from '../design/useApi';
import { usePrefs } from '../design/prefs';
import type { FeedResponse } from '../design/types';
import { fmt, qs } from '../design/format';
import { CardBones, Empty, Failure, PageHead, Pager, Segmented } from '../design/ui';
import { NewsCard } from '../components/NewsCard';
import { useAiState } from '../design/aiState';

interface Topics { categories: { id: string; label: string; count: number; subtopics: { id: string; label: string; count: number }[] }[] }
interface Sources { sources: { source_id: string; name: string; item_count: number }[] }

const KEYS = ['q', 'source_id', 'category', 'topic', 'window', 'date_from', 'date_to', 'lang', 'importance', 'translation', 'sort', 'page'] as const;
type Key = (typeof KEYS)[number];

/** All filter state lives in the URL, so every view is shareable and the
 *  back button works; the API receives exactly the same parameters. */
export function NewsStream() {
  const sp = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const now = useNow();
  const { t, isEn } = usePrefs();
  const [open, setOpen] = useState(false);
  const p = useMemo(() => Object.fromEntries(KEYS.map((k) => [k, sp.get(k) ?? ''])) as Record<Key, string>, [sp]);
  const sort = (p.sort || 'newest') as 'newest' | 'important' | 'coverage' | 'oldest';
  const page = Math.max(1, Number(p.page) || 1);

  const labels: Partial<Record<Key, Record<string, string>>> = {
    window: { '1h': t.filterWindow1h, '24h': t.filterWindow24h, '7d': t.filterWindow7d, '30d': t.filterWindow30d },
    lang: { en: t.filterLangEn, fa: t.filterLangFa, unknown: t.filterLangUnknown },
    importance: { high: t.filterImportanceHigh, medium: t.filterImportanceMed, low: t.filterImportanceLow },
    translation: {
      available: t.filterTransAvailable,
      warning: t.filterTransWarning,
      failed: t.filterTransFailed,
      pending: t.filterTransPending,
      error: t.filterTransError,
    },
  };

  const set = (patch: Partial<Record<Key, string>>) => {
    const next = { ...p, ...patch };
    if (!('page' in patch)) next.page = '';
    router.push(pathname + qs(next), { scroll: 'page' in patch });
  };

  const apiQs = qs({ ...p, sort, page, page_size: 24 });
  const q = useApi<FeedResponse>('feed' + apiQs, [apiQs]);
  const awaiting = (q.data?.items ?? []).some((it) => ['translation_pending', 'processing', 'pending'].includes(it.title_fa_status));
  const ai = useAiState();
  useEffect(() => {
    if (!awaiting || ai.off !== false) return;
    const timer = setInterval(q.reload, 60000);
    return () => clearInterval(timer);
  }, [awaiting, q.reload, ai.off]);
  const topics = useApi<Topics>('topics?window=all');
  const sources = useApi<Sources>('source-profiles');

  const catLabel = (id: string) => topics.data?.categories.find((c) => c.id === id)?.label ?? (id === 'other' ? t.filterOtherCategory : id);
  const subLabel = (id: string) => topics.data?.categories.flatMap((c) => c.subtopics).find((s) => s.id === id)?.label ?? id;
  const srcLabel = (id: string) => sources.data?.sources.find((s) => s.source_id === id)?.name ?? t.filterSourceLabel;
  const active = (KEYS.filter((k) => p[k] && !['sort', 'page'].includes(k)) as Key[]).map((k) => ({
    k, label: k === 'category' ? catLabel(p[k]) : k === 'topic' ? subLabel(p[k]) : k === 'source_id' ? srcLabel(p[k])
      : k === 'q' ? `«${p[k]}»` : k === 'date_from' ? t.filterDateFrom.replace('{val}', p[k]) : k === 'date_to' ? t.filterDateTo.replace('{val}', p[k]) : labels[k]?.[p[k]] ?? p[k],
  }));

  return (
    <Shell>
      <PageHead eyebrow={t.newsStreamEyebrow} title={t.newsStreamTitle} lede={t.newsStreamLede} />
      <div className="stream">
        <aside className="filters" data-open={open ? 'true' : 'false'} aria-label={t.filtersTitle}>
          <h2>{t.filtersTitle}</h2>
          <form onSubmit={(e) => { e.preventDefault(); const f = new FormData(e.currentTarget); set({ q: String(f.get('q') || '') }); }}>
            <label className="field">{t.filterSearchLabel}<input name="q" defaultValue={p.q} key={p.q} placeholder={t.filterSearchPlaceholder} /></label>
          </form>
          <label className="field">{t.filterSourceLabel}
            <select name="source_id" value={p.source_id} onChange={(e) => set({ source_id: e.target.value })}>
              <option value="">{t.filterAllSources}</option>
              {sources.data?.sources.map((s) => <option key={s.source_id} value={s.source_id}>{s.name} ({fmt(s.item_count)})</option>)}
            </select>
          </label>
          <label className="field">{t.filterCategoryLabel}
            <select name="category" value={p.category} onChange={(e) => set({ category: e.target.value, topic: '' })}>
              <option value="">{t.filterAllCategories}</option>
              {topics.data?.categories.map((c) => <option key={c.id} value={c.id}>{c.label} ({fmt(c.count)})</option>)}
              <option value="other">{t.filterOtherCategory}</option>
            </select>
          </label>
          {p.category && topics.data?.categories.find((c) => c.id === p.category)?.subtopics.length ? (
            <label className="field">{t.filterSubtopicLabel}
              <select name="topic" value={p.topic} onChange={(e) => set({ topic: e.target.value })}>
                <option value="">{t.filterAllSubtopics}</option>
                {topics.data.categories.find((c) => c.id === p.category)!.subtopics.map((s) => <option key={s.id} value={s.id}>{s.label} ({fmt(s.count)})</option>)}
              </select>
            </label>
          ) : null}
          <label className="field">{t.filterWindowLabel}
            <select name="window" value={p.window} onChange={(e) => set({ window: e.target.value })}>
              <option value="">{t.filterAllTimes}</option>
              <option value="1h">{t.filterWindow1h}</option>
              <option value="24h">{t.filterWindow24h}</option>
              <option value="7d">{t.filterWindow7d}</option>
              <option value="30d">{t.filterWindow30d}</option>
            </select>
          </label>
          <div className="grid-2">
            <label className="field">{isEn ? "From date" : "از تاریخ"}<input type="date" name="date_from" value={p.date_from} onChange={(e) => set({ date_from: e.target.value })} /></label>
            <label className="field">{isEn ? "To date" : "تا تاریخ"}<input type="date" name="date_to" value={p.date_to} onChange={(e) => set({ date_to: e.target.value })} /></label>
          </div>
          <label className="field">{t.filterLangLabel}
            <select name="lang" value={p.lang} onChange={(e) => set({ lang: e.target.value })}>
              <option value="">{t.filterAllLangs}</option>
              <option value="en">{t.filterLangEn}</option>
              <option value="fa">{t.filterLangFa}</option>
            </select>
          </label>
          <label className="field">{t.filterImportanceLabel}
            <select name="importance" value={p.importance} onChange={(e) => set({ importance: e.target.value })}>
              <option value="">{t.filterImportanceAll}</option>
              <option value="high">{t.filterImportanceHigh}</option>
              <option value="medium">{t.filterImportanceMed}</option>
              <option value="low">{t.filterImportanceLow}</option>
            </select>
          </label>
          {active.length > 0 && <button type="button" className="btn-ghost" onClick={() => router.push(pathname)}>{t.clearFilters}</button>}
        </aside>

        <section aria-labelledby="stream-h" style={{ minWidth: 0 }}>
          <h2 id="stream-h" className="sr-only">{t.showingResults}</h2>
          <div className="stream-head">
            <button type="button" className="btn-ghost filter-toggle" aria-expanded={open} onClick={() => setOpen(!open)}><SlidersHorizontal size={15} />{t.filtersTitle}{active.length ? ` (${fmt(active.length)})` : ''}</button>
            <span className="stream-count" role="status">{q.data ? `${fmt(q.data.total)} ${t.newsUnit}` : t.loadingText}</span>
            <Segmented label={t.filterSortLabel} value={sort} onChange={(v) => set({ sort: v })}
              items={[['newest', t.sortNewest], ['important', t.sortImportant7d], ['coverage', t.sortCoverage7d], ['oldest', t.filterOldest]]} />
          </div>
          {active.length > 0 && (
            <div className="active-filters" aria-label={isEn ? "Active Filters" : "فیلترهای فعال"}>
              {active.map((a) => <button key={a.k} type="button" onClick={() => set({ [a.k]: '' })} aria-label={isEn ? `Remove filter ${a.label}` : `حذف فیلتر ${a.label}`}>{a.label}<X size={12} /></button>)}
            </div>
          )}
          {q.error && <Failure onRetry={q.reload} />}
          {!q.data && !q.error && <CardBones n={6} />}
          {q.data && q.data.items.length === 0 && (
            <Empty title={t.emptyResults}>{isEn ? "Try broadening the time window or clearing selected filters." : "فیلترها را کمتر کنید یا بازه زمانی را گسترش دهید."}</Empty>
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

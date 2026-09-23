'use client';
import { useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { SlidersHorizontal, X } from 'lucide-react';
import { Shell } from '../design/Shell';
import { useApi, useNow } from '../design/useApi';
import { Chip, EmptyState, ErrorState, Pagination, Skeleton } from '../design/ui';
import { NewsCard } from '../components/NewsCard';
import type { NewsListItem } from '../components/news-types';
import { fmt } from '../design/format';

const WINDOWS: [string, string][] = [['all', 'همه'], ['24h', '۲۴ ساعت'], ['7d', '۷ روز'], ['30d', '۳۰ روز']];
const TRANSLATIONS: [string, string][] = [['', 'همه'], ['available', 'ترجمه‌شده'], ['pending', 'در صف'], ['unavailable', 'ناموجود']];

interface Filters {
  search: string; source_id: string; category: string; topic: string;
  window: string; sort: string; translation: string; has_image: string; has_document: string;
}
const EMPTY: Filters = { search: '', source_id: '', category: '', topic: '', window: 'all', sort: 'newest', translation: '', has_image: '', has_document: '' };

function filtersFromParams(sp: URLSearchParams): Filters {
  return {
    search: sp.get('search') || sp.get('q') || '', source_id: sp.get('source_id') || '', category: sp.get('category') || '',
    topic: sp.get('topic') || '', window: sp.get('window') || 'all', sort: sp.get('sort') || 'newest',
    translation: sp.get('translation') || '', has_image: sp.get('has_image') || '', has_document: sp.get('has_document') || '',
  };
}

export function NewsStream() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initial = useMemo(() => filtersFromParams(new URLSearchParams(searchParams?.toString() || '')), [searchParams]);
  const [filters, setFilters] = useState<Filters>(initial);
  const [searchDraft, setSearchDraft] = useState(initial.search);
  const [page, setPage] = useState(1);
  const [panelOpen, setPanelOpen] = useState(false);
  const now = useNow();

  const query = useMemo(() => {
    const p = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => { if (v && !(k === 'window' && v === 'all') && !(k === 'sort' && v === 'newest')) p.set(k, v); });
    return p;
  }, [filters]);

  const newsPath = useMemo(() => {
    const p = new URLSearchParams(query);
    p.set('page', String(page)); p.set('page_size', '20');
    return 'news?' + p.toString();
  }, [query, page]);
  const { data, error, loading, reload } = useApi<{ items: NewsListItem[]; total: number }>(newsPath, [newsPath]);

  const sourcesQ = useApi<{ sources: { source_id: string; display_name: string }[] }>('sources?page_size=100');
  const topicsQ = useApi<{ categories: { label: string; count: number }[] }>('stats/topics');

  function applyFilters(next: Partial<Filters>) {
    const merged = { ...filters, ...next };
    setFilters(merged); setPage(1);
    const p = new URLSearchParams();
    Object.entries(merged).forEach(([k, v]) => { if (v && !(k === 'window' && v === 'all') && !(k === 'sort' && v === 'newest')) p.set(k, v); });
    router.replace('/news' + (p.toString() ? '?' + p.toString() : ''), { scroll: false });
  }
  function clearAll() { setSearchDraft(''); applyFilters(EMPTY); }

  const activeCount = Object.values(filters).filter((v, i) => v && !(Object.keys(filters)[i] === 'window' && v === 'all') && !(Object.keys(filters)[i] === 'sort' && v === 'newest')).length;

  return (
    <Shell title="جریان اخبار" breadcrumb="جریان اخبار">
      <div className="page-head">
        <div><h1>جریان اخبار</h1><p>زمان‌ها به وقت هماهنگ جهانی (UTC) نمایش داده می‌شوند.</p></div>
        <button type="button" className="btn btn-secondary news-filter-toggle" onClick={() => setPanelOpen(!panelOpen)}>
          <SlidersHorizontal size={16} />فیلتر و جست‌وجو{activeCount > 0 && <span className="filter-count">{fmt(activeCount)}</span>}
        </button>
      </div>

      <form className={panelOpen ? 'news-filters open' : 'news-filters'} onSubmit={(e) => { e.preventDefault(); applyFilters({ search: searchDraft }); }}>
        <div className="news-filters-head"><strong>فیلترها</strong><button type="button" onClick={() => setPanelOpen(false)}><X size={16} /></button></div>
        <label className="field">جست‌وجو
          <input value={searchDraft} onChange={(e) => setSearchDraft(e.target.value)} placeholder="عبارت جست‌وجو…" />
        </label>
        <label className="field">منبع
          <select value={filters.source_id} onChange={(e) => applyFilters({ source_id: e.target.value })}>
            <option value="">همه منابع</option>
            {sourcesQ.data?.sources.map((s) => <option key={s.source_id} value={s.source_id}>{s.display_name}</option>)}
          </select>
        </label>
        <label className="field">دسته‌بندی
          <select value={filters.category} onChange={(e) => applyFilters({ category: e.target.value })}>
            <option value="">همه دسته‌ها</option>
            {topicsQ.data?.categories.map((c) => <option key={c.label} value={c.label}>{c.label}</option>)}
          </select>
        </label>
        <label className="field">بازه زمانی
          <select value={filters.window} onChange={(e) => applyFilters({ window: e.target.value })}>
            {WINDOWS.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
          </select>
        </label>
        <label className="field">ترجمه فارسی
          <select value={filters.translation} onChange={(e) => applyFilters({ translation: e.target.value })}>
            {TRANSLATIONS.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
          </select>
        </label>
        <label className="field">مرتب‌سازی
          <select value={filters.sort} onChange={(e) => applyFilters({ sort: e.target.value })}>
            <option value="newest">جدیدترین</option><option value="oldest">قدیمی‌ترین</option>
          </select>
        </label>
        <div className="news-filters-toggles">
          <Chip active={filters.has_image === 'true'} onClick={() => applyFilters({ has_image: filters.has_image === 'true' ? '' : 'true' })}>دارای تصویر</Chip>
          <Chip active={filters.has_document === 'true'} onClick={() => applyFilters({ has_document: filters.has_document === 'true' ? '' : 'true' })}>دارای سند</Chip>
        </div>
        <div className="news-filters-actions">
          <button type="submit" className="btn btn-primary">اعمال جست‌وجو</button>
          <button type="button" className="btn btn-secondary" onClick={clearAll}>پاک‌کردن فیلترها</button>
        </div>
      </form>

      {error && <ErrorState onRetry={reload}>دریافت داده از API ممکن نشد؛ داده‌ای ساخته نشده است.</ErrorState>}

      {!error && (
        <>
          <p className="news-count">{loading ? 'در حال دریافت…' : `${fmt(data?.total || 0)} خبر · صفحه ${fmt(page)}`}
            {filters.topic && <span> · موضوع: {filters.topic}</span>}
          </p>
          <div>
            {loading && Array.from({ length: 6 }, (_, i) => <Skeleton key={i} height={116} radius={10} />).map((s, i) => <div key={i} style={{ marginBottom: 12 }}>{s}</div>)}
            {!loading && data?.items.length === 0 && (
              <EmptyState title={filters.window === '24h' ? 'در ۲۴ ساعت گذشته خبری با این فیلتر ثبت نشده' : 'خبری با این فیلترها یافت نشد'}>
                {filters.window === '24h' ? (
                  <button className="btn btn-secondary" onClick={() => applyFilters({ window: '7d' })}>نمایش ۷ روز گذشته</button>
                ) : 'فیلترها را تغییر دهید یا پاک کنید.'}
              </EmptyState>
            )}
            {!loading && data?.items.map((item) => <NewsCard key={item.item_id} item={item} now={now} />)}
          </div>
          {!loading && data && data.total > 20 && <Pagination page={page} hasNext={page * 20 < data.total} onPage={setPage} />}
        </>
      )}
    </Shell>
  );
}

'use client';
import { useMemo, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { Plus, X as Close } from 'lucide-react';
import { Shell } from '../design/Shell';
import { useApi, useNow } from '../design/useApi';
import { fmt, fmtDateTime, fmtRelative, qs } from '../design/format';
import { CardBones, Empty, Failure, PageHead, Pager, Stat, Tag } from '../design/ui';
import { PostCard } from './PostCard';
import { TranslationStatusNote } from './Translation';
import { RegisterForm } from './RegisterForm';
import { IMPORTANCE_FA, VERIFICATION_FA, type SocialStatus, type XAccount, type XPost } from './lib';

interface Stats { accounts: number; posts: number; posts_today: number; accounts_without_posts: number; active_topics_7d: number; last_registered_at: string | null }
interface Topics { categories: { id: string; label: string; subtopics: { id: string; label: string }[] }[] }
const KEYS = ['source_id', 'topic', 'date_from', 'date_to', 'importance', 'verification', 'has_translation', 'has_event', 'page'] as const;
type Key = (typeof KEYS)[number];

export function useTopicLabels() {
  const t = useApi<Topics>('topics?window=all');
  return useMemo(() => {
    const m = new Map<string, string>();
    t.data?.categories.forEach((c) => { m.set(c.id, c.label); c.subtopics.forEach((s) => m.set(s.id, s.label)); });
    return { label: (id: string) => m.get(id) ?? id, topics: t.data?.categories ?? [] };
  }, [t.data]);
}

export function Social() {
  const sp = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const now = useNow();
  const [formOpen, setFormOpen] = useState(false);
  const p = useMemo(() => Object.fromEntries(KEYS.map((k) => [k, sp.get(k) ?? ''])) as Record<Key, string>, [sp]);
  const page = Math.max(1, Number(p.page) || 1);
  const set = (patch: Partial<Record<Key, string>>) => router.push(pathname + qs({ ...p, ...patch, ...('page' in patch ? {} : { page: '' }) }), { scroll: false });

  const status = useApi<SocialStatus>('social/status');
  const stats = useApi<Stats>('social/stats');
  const accounts = useApi<{ accounts: XAccount[]; total: number }>('social/accounts');
  const apiQs = qs({ ...p, page, page_size: 20 });
  const posts = useApi<{ posts: XPost[]; total: number; has_next: boolean }>('social/posts' + apiQs, [apiQs]);
  const { label, topics } = useTopicLabels();
  const reload = () => { posts.reload(); stats.reload(); accounts.reload(); status.reload(); };
  const active = KEYS.filter((k) => p[k] && k !== 'page');

  return (
    <Shell>
      <PageHead eyebrow="شبکه‌های اجتماعی" title="پایش دستی حساب‌های X"
        lede="۳۶ حساب X از فهرست منابع مشتری به‌صورت دستی پایش می‌شوند: تحلیلگر نشانی پست مشخص را ثبت می‌کند. هیچ API پولی، scraping، ربات یا زمان‌بندی به X متصل نیست و هیچ پستی به‌طور خودکار دریافت نمی‌شود.">
        {status.data && <Tag tone="info">پایش دستی · API رسمی خاموش · زمان‌بند خاموش</Tag>}
        {status.data?.manual_ingest_enabled && (
          <button type="button" className="btn-primary" onClick={() => setFormOpen(!formOpen)} aria-expanded={formOpen}>
            {formOpen ? <Close size={15} /> : <Plus size={15} />}ثبت پست X
          </button>
        )}
      </PageHead>

      {stats.error && <Failure onRetry={stats.reload} />}
      {stats.data && (
        <div className="stat-row x-stats">
          <Stat label="حساب ثبت‌شده" value={stats.data.accounts} note={status.data ? `از ${fmt(status.data.manifest_summary.raw_occurrences)} مورد خام در سند منابع` : undefined} />
          <Stat label="پست ثبت‌شده دستی" value={stats.data.posts} note={`امروز: ${fmt(stats.data.posts_today)}`} />
          <Stat label="حساب بدون پست" value={stats.data.accounts_without_posts} />
          <Stat label="موضوعات فعال (۷ روز)" value={stats.data.active_topics_7d}
            note={stats.data.last_registered_at ? `آخرین ثبت: ${fmtRelative(stats.data.last_registered_at, now)}` : 'هنوز ثبتی انجام نشده'} />
        </div>
      )}
      <TranslationStatusNote />
      {status.data && !status.data.manual_ingest_enabled && (
        <p className="note">ثبت دستی در این محیط غیرفعال است (SOCIAL_MANUAL_INGEST_ENABLED=false). پست‌های ثبت‌شده فقط نمایش داده می‌شوند.</p>
      )}

      {formOpen && status.data?.manual_ingest_enabled && (
        <RegisterForm accounts={accounts.data?.accounts ?? []} topics={topics} onDone={() => { setFormOpen(false); reload(); }} />
      )}

      <div className="stream">
        <aside className="filters" data-open="true" aria-label="فیلتر پست‌ها">
          <h2>فیلترها</h2>
          <label className="field">حساب
            <select name="source_id" value={p.source_id} onChange={(e) => set({ source_id: e.target.value })}>
              <option value="">همه حساب‌ها</option>
              {accounts.data?.accounts.map((a) => <option key={a.source_id} value={a.source_id}>{a.handle} ({fmt(a.post_count)})</option>)}
            </select>
          </label>
          <label className="field">موضوع
            <select name="topic" value={p.topic} onChange={(e) => set({ topic: e.target.value })}>
              <option value="">همه موضوعات</option>
              {topics.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
            </select>
          </label>
          <div className="grid-2">
            <label className="field">از تاریخ<input type="date" name="date_from" value={p.date_from} onChange={(e) => set({ date_from: e.target.value })} /></label>
            <label className="field">تا تاریخ<input type="date" name="date_to" value={p.date_to} onChange={(e) => set({ date_to: e.target.value })} /></label>
          </div>
          <label className="field">اهمیت
            <select name="importance" value={p.importance} onChange={(e) => set({ importance: e.target.value })}>
              <option value="">همه</option>{Object.entries(IMPORTANCE_FA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label className="field">راستی‌آزمایی
            <select name="verification" value={p.verification} onChange={(e) => set({ verification: e.target.value })}>
              <option value="">همه</option>{Object.entries(VERIFICATION_FA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label className="field">ترجمه
            <select name="has_translation" value={p.has_translation} onChange={(e) => set({ has_translation: e.target.value })}>
              <option value="">همه</option><option value="true">دارای ترجمه</option><option value="false">بدون ترجمه</option>
            </select>
          </label>
          <label className="field">رویداد
            <select name="has_event" value={p.has_event} onChange={(e) => set({ has_event: e.target.value })}>
              <option value="">همه</option><option value="true">متصل به رویداد</option><option value="false">بدون رویداد</option>
            </select>
          </label>
          {active.length > 0 && <button type="button" className="btn-ghost" onClick={() => router.push(pathname)}>پاک کردن فیلترها</button>}
        </aside>

        <section aria-labelledby="xposts-h" style={{ minWidth: 0 }}>
          <div className="stream-head">
            <h2 id="xposts-h" className="brief-sub">جریان پست‌های ثبت‌شده</h2>
            <span className="stream-count" role="status">{posts.data ? `${fmt(posts.data.total)} پست` : 'در حال شمارش…'}</span>
          </div>
          {posts.error && <Failure onRetry={posts.reload} />}
          {!posts.data && !posts.error && <CardBones n={3} image={false} />}
          {posts.data && posts.data.posts.length === 0 && (
            <Empty title={active.length ? 'هیچ پستی با این فیلترها ثبت نشده است' : 'هنوز هیچ پستی به‌صورت دستی ثبت نشده است'}>
              پست‌ها فقط وقتی اینجا ظاهر می‌شوند که تحلیلگر نشانی یک پست مشخص از یکی از ۳۶ حساب را ثبت کند. هیچ پست نمونه یا نمایشی ساخته نمی‌شود.
            </Empty>
          )}
          {posts.data && posts.data.posts.length > 0 && (
            <>
              <div className="x-list">{posts.data.posts.map((x) => <PostCard key={x.post_id} p={x} now={now} topicLabel={label} />)}</div>
              <Pager page={page} hasNext={posts.data.has_next} total={posts.data.total} onPage={(n) => set({ page: String(n) })} />
            </>
          )}
        </section>
      </div>

      <section aria-labelledby="xacc-h">
        <h2 id="xacc-h" className="sec-head" style={{ marginBottom: 12 }}>حساب‌های ثبت‌شده ({fmt(accounts.data?.total ?? 0)})</h2>
        {accounts.error && <Failure onRetry={accounts.reload} />}
        {accounts.data && (
          <div className="table-scroll panel">
            <table className="data">
              <thead><tr><th>حساب</th><th>نام ثبت‌شده</th><th>دسته</th><th>پست ثبت‌شده</th><th>آخرین ثبت</th><th>وضعیت</th><th /></tr></thead>
              <tbody>
                {accounts.data.accounts.map((a) => (
                  <tr key={a.source_id}>
                    <td><a href={a.profile_url} target="_blank" rel="noopener noreferrer nofollow" dir="ltr" className="sec-link">{a.handle}</a></td>
                    <td>{a.display_name ?? <span className="muted">ثبت نشده</span>}</td>
                    <td>{a.category ?? <span className="muted">ثبت نشده</span>}</td>
                    <td>{fmt(a.post_count)}</td>
                    <td>{a.last_manual_post_at ? fmtDateTime(a.last_manual_post_at) : <span className="muted">—</span>}</td>
                    <td><Tag tone="info">پایش دستی</Tag></td>
                    <td><Link href={`/social/accounts/${a.source_id}`} className="sec-link">جزئیات</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </Shell>
  );
}

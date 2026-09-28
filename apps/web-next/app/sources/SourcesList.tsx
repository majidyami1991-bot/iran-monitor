'use client';
import { useState } from 'react';
import Link from 'next/link';
import { Shell } from '../design/Shell';
import { useApi, useNow } from '../design/useApi';
import { fmt, fmtPercent, fmtRelative, sourceColor } from '../design/format';
import { CardBones, Failure, PageHead, Segmented, SourceMark, Tag } from '../design/ui';

export interface Profile {
  source_id: string; name: string; has_official_name: boolean; hostname: string; canonical_url: string | null; source_type: string | null;
  category: string | null; language: string | null; feed_url: string | null; collection_tier: string | null; enabled_for_scheduler: boolean;
  last_attempt_at: string | null; last_success_at: string | null; last_http_status: number | null; consecutive_failures: number; health_status: string;
  item_count: number; items_24h: number; items_7d: number; last_published: string | null; last_received: string | null;
  provenance_complete: number; translated: number; with_summary: number; runs_7d: number; runs_ok_7d: number; success_rate_7d: number | null;
  coverage_share: number; translation_pct: number | null; provenance_pct: number | null; country: string | null; country_status: string;
  language_provenance: string; channels: { rss: string; html: string; x: string }; freshness_minutes: number | null;
}
interface Resp { sources: Profile[]; total: number; metadata_completeness: { pct: number | null; filled: number; possible: number } }

export const TYPE_FA: Record<string, string> = { news: 'رسانه خبری', think_tank: 'اندیشکده', x_account: 'حساب X' };
export function health(p: Profile) {
  if (p.consecutive_failures >= 3) return ['خطای پیاپی', 'error'] as const;
  if (p.consecutive_failures > 0) return ['نیازمند توجه', 'warn'] as const;
  if (!p.last_success_at) return ['اجرا نشده', 'uncertain'] as const;
  return ['سالم', 'ok'] as const;
}
export function freshness(min: number | null) {
  if (min == null) return ['بدون دریافت', 'uncertain'] as const;
  if (min <= 60) return ['تازه', 'ok'] as const;
  if (min <= 60 * 24) return ['امروز', 'info'] as const;
  return ['کهنه', 'warn'] as const;
}

export function SourcesList() {
  const q = useApi<Resp>('source-profiles');
  const now = useNow();
  const [sort, setSort] = useState<'items' | 'recent' | 'name'>('items');
  const list = [...(q.data?.sources ?? [])].sort((a, b) =>
    sort === 'items' ? b.item_count - a.item_count : sort === 'recent' ? Date.parse(b.last_received ?? '0') - Date.parse(a.last_received ?? '0') : a.name.localeCompare(b.name));
  return (
    <Shell>
      <PageHead eyebrow="منابع" title="منابع تحت پایش"
        lede="هر منبع با نام رسمی ثبت‌شده در خوراک خودش، وضعیت گردآورنده، تازگی، نرخ موفقیت و کیفیت داده. کشور و مالکیت فقط با شواهد مستند ثبت می‌شود و هنوز ثبت نشده است.">
        {q.data && <Tag tone="info">کامل بودن فراداده: {fmtPercent(q.data.metadata_completeness.pct, 1)}</Tag>}
        <Link href="/monitoring" className="btn-ghost">پوشش ۶۲ منبع ثبت‌شده</Link>
      </PageHead>
      <Segmented label="مرتب‌سازی منابع" value={sort} onChange={setSort} items={[['items', 'بیشترین خبر'], ['recent', 'تازه‌ترین دریافت'], ['name', 'نام']]} />
      {q.error && <Failure onRetry={q.reload} />}
      {!q.data && !q.error && <CardBones n={4} image={false} />}
      <div className="src-grid">
        {list.map((s) => {
          const [hl, ht] = health(s);
          const [fl, ft] = freshness(s.freshness_minutes);
          return (
            <article key={s.source_id} className="src-card">
              <div className="src-head">
                <SourceMark name={s.name} color={sourceColor(s.source_id)} size={40} />
                <div style={{ minWidth: 0 }}>
                  <h3><Link href={`/sources/${s.source_id}`}><bdi>{s.name}</bdi></Link></h3>
                  <small dir="ltr">{s.hostname}</small>
                </div>
              </div>
              <div className="card-flags">
                <Tag>{TYPE_FA[s.source_type ?? ''] ?? 'نوع ثبت نشده'}</Tag>
                <Tag tone={ht}>{hl}</Tag>
                <Tag tone={ft}>{fl}</Tag>
                {!s.has_official_name && <Tag tone="uncertain">نام رسمی ثبت نشده؛ نام میزبان نمایش داده می‌شود</Tag>}
              </div>
              <div className="src-metrics">
                <div><span>کل خبرها</span><strong>{fmt(s.item_count)}</strong></div>
                <div><span>۲۴ ساعت</span><strong>{fmt(s.items_24h)}</strong></div>
                <div><span>موفقیت ۷ روز</span><strong>{s.success_rate_7d == null ? '—' : fmtPercent(s.success_rate_7d)}</strong></div>
                <div><span>سهم پوشش</span><strong>{fmtPercent(s.coverage_share, 1)}</strong></div>
                <div><span>منشأ کامل</span><strong>{fmtPercent(s.provenance_pct)}</strong></div>
                <div><span>ترجمه</span><strong>{fmtPercent(s.translation_pct)}</strong></div>
              </div>
              <p className="muted">آخرین دریافت: {fmtRelative(s.last_received, now)} · زبان: {s.language ? <bdi>{s.language}</bdi> : 'اعلام نشده'}{s.language ? ' (اعلام‌شده در خوراک)' : ''}</p>
            </article>
          );
        })}
      </div>
    </Shell>
  );
}

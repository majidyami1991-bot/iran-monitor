'use client';
import { useState } from 'react';
import Link from 'next/link';
import { Shell } from '../design/Shell';
import { useApi } from '../design/useApi';
import { catVar, fmt, fmtPercent, fmtSigned } from '../design/format';
import { CardBones, Failure, PageHead, Segmented, Tag } from '../design/ui';
import { Bars, Figure } from '../design/charts';

export interface TopicsResp {
  taxonomy_version: string; method: string; window: string; total: number;
  categories: { id: string; label: string; label_en: string; count: number; share: number; last_7d: number; prev_7d: number; subtopics: { id: string; label: string; count: number }[] }[];
  other: { count: number; share: number; reasons: { id: string; label: string; n: number }[] };
  legacy_v2_other_share: number | null;
}

export function Topics() {
  const [win, setWin] = useState<'24h' | '7d' | '30d' | 'all'>('all');
  const q = useApi<TopicsResp>('topics?window=' + win, [win]);
  const d = q.data;
  return (
    <Shell>
      <PageHead eyebrow="موضوعات" title="موضوعات و دسته‌بندی‌ها"
        lede="طبقه‌بندی چندسطحی و نسخه‌دار: هر خبر یک دسته اصلی، موضوعات فرعی، زیرموضوع‌ها و شواهد متنی دارد. «سایر» فقط با دلیل مشخص استفاده می‌شود.">
        {d && <Tag tone="info">طبقه‌بندی نسخه {d.taxonomy_version}</Tag>}
      </PageHead>
      <Segmented label="بازه" value={win} onChange={setWin} items={[['24h', '۲۴ ساعت'], ['7d', '۷ روز'], ['30d', '۳۰ روز'], ['all', 'همه']]} />
      {q.error && <Failure onRetry={q.reload} />}
      {!d && !q.error && <CardBones n={4} image={false} />}
      {d && (
        <>
          <div className="topic-grid">
            {d.categories.filter((c) => c.count > 0 || win === 'all').map((c) => {
              const delta = c.last_7d - c.prev_7d;
              return (
                <article key={c.id} className="topic-card" style={{ ['--art' as string]: catVar(c.id) }}>
                  <h3><Link href={`/topics/${c.id}`}>{c.label}</Link></h3>
                  <div className="topic-num"><strong>{fmt(c.count)}</strong><span className="muted">خبر · {fmtPercent(c.share, 1)} از کل</span></div>
                  <span className={delta > 0 ? 'delta delta-up' : delta < 0 ? 'delta delta-down' : 'muted'} style={{ fontSize: 12 }}>
                    {fmtSigned(delta)} در ۷ روز اخیر نسبت به ۷ روز قبل ({fmt(c.prev_7d)} ← {fmt(c.last_7d)})
                  </span>
                  {c.subtopics.length > 0 && (
                    <div className="topic-subs">{c.subtopics.filter((s) => s.count > 0).map((s) => <Link key={s.id} href={`/topics/${s.id}`}>{s.label} · {fmt(s.count)}</Link>)}</div>
                  )}
                  <Link href={`/news?category=${c.id}${win !== 'all' ? `&window=${win}` : ''}`} className="sec-link">خبرهای این دسته</Link>
                </article>
              );
            })}
          </div>
          <div className="grid-2">
            <Figure title="سهم هر دسته از پوشش" question="بیشترین پوشش خبری به کدام موضوع اختصاص دارد؟" unit="خبر" range={win === 'all' ? 'همه زمان‌ها' : win} source={`طبقه‌بندی قاعده‌محور نسخه ${d.taxonomy_version}`}
              table={{ head: ['دسته', 'تعداد', 'سهم'], rows: d.categories.map((c) => [c.label, c.count, fmtPercent(c.share, 1)]) }}>
              <Bars data={[...d.categories].sort((a, b) => b.count - a.count).map((c) => ({ key: c.id, label: c.label, value: c.count, note: fmtPercent(c.share, 1) }))} href={(k) => `/topics/${k}`} />
            </Figure>
            <Figure title="«سایر» و دلیل آن" question="چه بخشی از خبرها در هیچ دسته موضوعی جای نگرفت و چرا؟" unit="خبر" source="کد دلیل ثبت‌شده برای هر خبر"
              table={{ head: ['دلیل', 'تعداد'], rows: d.other.reasons.map((r) => [r.label, r.n]) }}>
              <p className="muted">سهم «سایر»: <b>{fmtPercent(d.other.share, 1)}</b> ({fmt(d.other.count)} خبر){d.legacy_v2_other_share != null && <> — در طبقه‌بندی قبلی (نسخه ۲.۱): {fmtPercent(d.legacy_v2_other_share, 1)}</>}</p>
              <Bars data={d.other.reasons.map((r) => ({ key: r.id, label: r.label, value: r.n, color: 'var(--uncertain)' }))} href={() => '/news?category=other'} />
            </Figure>
          </div>
          <p className="note">روش: {d.method}</p>
        </>
      )}
    </Shell>
  );
}

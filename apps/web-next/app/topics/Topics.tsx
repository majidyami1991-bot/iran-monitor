'use client';
import { useState } from 'react';
import Link from 'next/link';
import { Shell } from '../design/Shell';
import { useApi } from '../design/useApi';
import { usePrefs } from '../design/prefs';
import { catVar, fmt, fmtPercent, fmtSigned } from '../design/format';
import { getCategoryLabel, getSubtopicLabel, getOtherReasonLabel } from '../design/taxonomy';
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
  const { isEn } = usePrefs();
  const d = q.data;
  return (
    <Shell>
      <PageHead eyebrow={isEn ? "Taxonomy" : "موضوعات"} title={isEn ? "Topics & Categories" : "موضوعات و دسته‌بندی‌ها"}
        lede={isEn ? "Multi-level versioned taxonomy: each news item has a primary category, secondary topics, subtopics and keyword evidence." : "طبقه‌بندی چندسطحی و نسخه‌دار: هر خبر یک دسته اصلی، موضوعات فرعی، زیرموضوع‌ها و شواهد متنی دارد. «سایر» فقط با دلیل مشخص استفاده می‌شود."}>
        {d && <Tag tone="info">{isEn ? `Taxonomy version ${d.taxonomy_version}` : `طبقه‌بندی نسخه ${d.taxonomy_version}`}</Tag>}
      </PageHead>
      <Segmented label={isEn ? "Window" : "بازه"} value={win} onChange={setWin} items={[['24h', isEn ? '24 Hours' : '۲۴ ساعت'], ['7d', isEn ? '7 Days' : '۷ روز'], ['30d', isEn ? '30 Days' : '۳۰ روز'], ['all', isEn ? 'All' : 'همه']]} />
      {q.error && <Failure onRetry={q.reload} />}
      {!d && !q.error && <CardBones n={4} image={false} />}
      {d && (
        <>
          <div className="topic-grid">
            {d.categories.filter((c) => c.count > 0 || win === 'all').map((c) => {
              const delta = c.last_7d - c.prev_7d;
              return (
                <article key={c.id} className="topic-card" style={{ ['--art' as string]: catVar(c.id) }}>
                  <h3><Link href={`/topics/${c.id}`}>{getCategoryLabel(c.id, isEn)}</Link></h3>
                  <div className="topic-num"><strong>{fmt(c.count)}</strong><span className="muted">{isEn ? `articles · ${fmtPercent(c.share, 1)} of total` : `خبر · ${fmtPercent(c.share, 1)} از کل`}</span></div>
                  <span className={delta > 0 ? 'delta delta-up' : delta < 0 ? 'delta delta-down' : 'muted'} style={{ fontSize: 12 }}>
                    {isEn ? `${fmtSigned(delta)} in last 7d vs prior 7d (${fmt(c.prev_7d)} ← ${fmt(c.last_7d)})` : `${fmtSigned(delta)} در ۷ روز اخیر نسبت به ۷ روز قبل (${fmt(c.prev_7d)} ← ${fmt(c.last_7d)})`}
                  </span>
                  {c.subtopics.length > 0 && (
                    <div className="topic-subs">{c.subtopics.filter((s) => s.count > 0).map((s) => <Link key={s.id} href={`/topics/${s.id}`}>{getSubtopicLabel(s.id, isEn)} · {fmt(s.count)}</Link>)}</div>
                  )}
                  <Link href={`/news?category=${c.id}${win !== 'all' ? `&window=${win}` : ''}`} className="sec-link">{isEn ? 'News in this category' : 'خبرهای این دسته'}</Link>
                </article>
              );
            })}
          </div>
          <div className="grid-2">
            <Figure title={isEn ? "Coverage Share by Category" : "سهم هر دسته از پوشش"} question={isEn ? "Which categories have the most coverage?" : "بیشترین پوشش خبری به کدام موضوع اختصاص دارد؟"} unit={isEn ? "article" : "خبر"} range={win === 'all' ? (isEn ? 'All time' : 'همه زمان‌ها') : win} source={isEn ? `Rule-based taxonomy v${d.taxonomy_version}` : `طبقه‌بندی قاعده‌محور نسخه ${d.taxonomy_version}`}
              table={{ head: isEn ? ['Category', 'Count', 'Share'] : ['دسته', 'تعداد', 'سهم'], rows: d.categories.map((c) => [getCategoryLabel(c.id, isEn), c.count, fmtPercent(c.share, 1)]) }}>
              <Bars data={[...d.categories].sort((a, b) => b.count - a.count).map((c) => ({ key: c.id, label: getCategoryLabel(c.id, isEn), value: c.count, note: fmtPercent(c.share, 1) }))} href={(k) => `/topics/${k}`} />
            </Figure>
            <Figure title={isEn ? "'Other' and Assigned Reason" : "«سایر» و دلیل آن"} question={isEn ? "What portion of news fell outside predefined topics and why?" : "چه بخشی از خبرها در هیچ دسته موضوعی جای نگرفت و چرا؟"} unit={isEn ? "article" : "خبر"} source={isEn ? "Recorded reason code per article" : "کد دلیل ثبت‌شده برای هر خبر"}
              table={{ head: isEn ? ['Reason', 'Count'] : ['دلیل', 'تعداد'], rows: d.other.reasons.map((r) => [getOtherReasonLabel(r.id, isEn), r.n]) }}>
              <p className="muted">{isEn ? "Share of 'Other': " : "سهم «سایر»: "}<b>{fmtPercent(d.other.share, 1)}</b> ({fmt(d.other.count)} {isEn ? "articles" : "خبر"}){d.legacy_v2_other_share != null && <> — {isEn ? `in prior taxonomy (v2.1): ${fmtPercent(d.legacy_v2_other_share, 1)}` : `در طبقه‌بندی قبلی (نسخه ۲.۱): ${fmtPercent(d.legacy_v2_other_share, 1)}`}</>}</p>
              <Bars data={d.other.reasons.map((r) => ({ key: r.id, label: getOtherReasonLabel(r.id, isEn), value: r.n, color: 'var(--uncertain)' }))} href={() => '/news?category=other'} />
            </Figure>
          </div>
          <p className="note">{isEn ? `Method: ${d.method}` : `روش: ${d.method}`}</p>
        </>
      )}
    </Shell>
  );
}

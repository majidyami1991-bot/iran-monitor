'use client';
import { useState } from 'react';
import Link from 'next/link';
import { Shell } from '../design/Shell';
import { useApi, useNow } from '../design/useApi';
import { fmt, fmtDateLong, fmtDateTime, fmtRelative, fmtSigned } from '../design/format';
import { AiTag, CategoryTag, Empty, Failure, ImportanceTag, PageHead, RuleTag, Tag, Bone } from '../design/ui';
import { AI_STATUS, FRESH, TopicDeltaList, type BriefingResponse } from '../components/Briefing';
import { ItemImage } from '../components/Visual';

export function Briefing() {
  const [date, setDate] = useState<string>('');
  const q = useApi<BriefingResponse>('briefing/daily' + (date ? '?date=' + date : ''), [date]);
  const now = useNow();
  if (q.error) return <Shell><Failure onRetry={q.reload}>خلاصه روزانه دریافت نشد.</Failure></Shell>;
  if (!q.data) return <Shell><Bone h={30} w="40%" /><Bone h={120} /></Shell>;
  const b = q.data.briefing;
  const [fl, ft] = FRESH[q.data.status];
  return (
    <Shell>
      <PageHead eyebrow="گزارش روزانه" title="امروز چه اتفاقی افتاد؟"
        lede={b ? <>خلاصه ۲۴ ساعت از {fmtDateTime(b.window_start)} تا {fmtDateTime(b.window_end)} — {fmtDateLong(b.generated_at)}</> : undefined}>
        <RuleTag>قاعده‌محور · {b?.generator_version ?? '—'}</RuleTag>
        <Tag tone={ft}>{fl}</Tag>
        {q.data.history && q.data.history.length > 1 && (
          <label className="field" style={{ minWidth: 180 }}>نسخه‌های ذخیره‌شده
            <select value={date} onChange={(e) => setDate(e.target.value)}>
              <option value="">آخرین نسخه</option>
              {[...new Set(q.data.history.map((h) => h.briefing_date))].map((d) => <option key={d} value={d}>{fmtDateLong(d)}</option>)}
            </select>
          </label>
        )}
      </PageHead>
      {!b ? <Empty title="هنوز خلاصه‌ای تولید نشده است">اولین خلاصه پس از اجرای زمان‌بند ساخته می‌شود. خلاصه ساختگی نمایش داده نمی‌شود.</Empty> : (
        <>
          <div className="note note-ai">
            <AiTag>خلاصه مدیریتی هوش مصنوعی</AiTag>{' '}
            {b.ai_generated && b.executive_summary_fa
              ? <><p style={{ marginTop: 8 }}>{b.executive_summary_fa}</p><small>مدل {b.ai_model} · نسخه دستور {b.ai_prompt_version} · تولیدشده با هوش مصنوعی، نیازمند بازبینی؛ واقعیت قطعی نیست.</small></>
              : <span>{AI_STATUS[q.data.ai.status] ?? q.data.ai.status} بخش‌های زیر فقط از شمارش‌ها و قواعد قطعی ساخته شده‌اند و هیچ متن تفسیری تولید نشده است.</span>}
          </div>
          <section className="brief-panel">
            <p className="brief-narrative" style={{ fontSize: 17 }}>{b.payload.narrative_fa}</p>
            <small className="muted">{b.payload.narrative_method}</small>
            <div className="brief-stats" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
              <div><strong>{fmt(b.payload.totals.items_24h)}</strong><span>خبر در ۲۴ ساعت</span></div>
              <div><strong>{fmt(b.payload.totals.items_prev_24h)}</strong><span>۲۴ ساعت قبل از آن</span></div>
              <div><strong className={(b.payload.totals.change_pct ?? 0) < 0 ? 'down' : 'up'}>{b.payload.totals.change_pct == null ? '—' : fmtSigned(b.payload.totals.change_pct) + '٪'}</strong><span>تغییر</span></div>
              <div><strong>{fmt(b.payload.totals.active_sources)}</strong><span>منبع فعال</span></div>
            </div>
          </section>

          <section aria-labelledby="dev-h">
            <h2 id="dev-h" className="brief-sub" style={{ fontSize: 18 }}>تحولات کلیدی ({fmt(b.payload.key_developments.length)})</h2>
            <p className="muted">انتخاب با قاعده اهمیت ({b.payload.rules.importance})؛ از هر رویداد فقط یک خبر.</p>
            {b.payload.key_developments.length === 0 ? <Empty title="تحول موضوعی در این بازه ثبت نشده است" /> : (
              <ol className="timeline" style={{ marginTop: 12 }}>
                {b.payload.key_developments.map((d, i) => (
                  <li key={d.item_id} className="tl-item">
                    <div className="tl-when"><time>{fmt(i + 1)}</time><small>{fmtRelative(d.published_at, now)}</small></div>
                    <span className="tl-dot" aria-hidden="true" />
                    <div className="tl-body" style={{ display: 'grid', gridTemplateColumns: d.image_url ? '1fr 132px' : '1fr', gap: 12 }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 0 }}>
                        <div className="card-flags"><CategoryTag id={d.category_id} label={d.category_label} /><ImportanceTag level={d.importance_level} />{d.event_sources >= 2 && <Tag tone="brand">{fmt(d.event_sources)} منبع</Tag>}</div>
                        <h3 dir={d.headline_lang === 'en' ? 'ltr' : 'rtl'}><Link href={d.href}>{d.headline}</Link></h3>
                        {d.summary && <p className="card-summary" dir={d.summary_lang === 'en' ? 'ltr' : 'rtl'} style={{ WebkitLineClamp: 3 }}>{d.summary}</p>}
                        <span className="tl-meta"><bdi>{d.source_name}</bdi> · شاهد: <Link href={d.href} className="sec-link">خبر</Link>{d.event_id && <> · <Link href={`/events/${d.event_id}`} className="sec-link">رویداد</Link></>}</span>
                      </div>
                      {d.image_url && <div style={{ borderRadius: 8, overflow: 'hidden', aspectRatio: '4/3' }}><ItemImage src={d.image_url} categoryId={d.category_id} compact credit={false} /></div>}
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </section>

          <div className="grid-3">
            <section className="panel"><div className="panel-title"><h3>موضوعات صعودی</h3></div><TopicDeltaList items={b.payload.rising_topics} dir="up" /></section>
            <section className="panel"><div className="panel-title"><h3>موضوعات نزولی</h3></div><TopicDeltaList items={b.payload.falling_topics} dir="down" /></section>
            <section className="panel"><div className="panel-title"><h3>مهم‌ترین منابع</h3></div>
              <ul className="delta-list">{b.payload.top_sources.map((s) => <li key={s.source_id}><Link href={`/sources/${s.source_id}`}><bdi>{s.name}</bdi></Link><small>{fmt(s.n)} خبر</small></li>)}</ul>
            </section>
          </div>

          <section className="panel" aria-labelledby="gap-h">
            <div className="panel-title"><h3 id="gap-h">نقاط ابهام و پوشش ناکافی</h3></div>
            <ul className="prov">
              <li><span /><div>منابع بدون خبر در ۲۴ ساعت: {b.payload.coverage_gaps.silent_sources.length ? b.payload.coverage_gaps.silent_sources.map((s) => <Link key={s.source_id} href={`/sources/${s.source_id}`} className="tag" style={{ marginInlineEnd: 4 }}><bdi>{s.name}</bdi></Link>) : 'هیچ'}</div></li>
              <li><span /><div>خبرهای بدون ترجمه فارسی: {fmt(b.payload.coverage_gaps.untranslated_24h)} از {fmt(b.payload.coverage_gaps.items_24h)}</div></li>
              <li><span /><div>خبرهای بدون خلاصه منبع: {fmt(b.payload.coverage_gaps.without_summary_24h)}</div></li>
              <li><span /><div>خبرهای خارج از دسته‌های موضوعی («سایر»): {fmt(b.payload.coverage_gaps.other_category_24h)}</div></li>
              <li><span /><div>منابع با خطای دریافت: {b.payload.coverage_gaps.sources_with_failures.length ? b.payload.coverage_gaps.sources_with_failures.map((s) => `${s.name} (${fmt(s.consecutive_failures)})`).join('، ') : 'هیچ'}</div></li>
            </ul>
          </section>
          <p className="muted">زمان تولید: {fmtDateTime(b.generated_at)} · مولد: {b.generator} {b.generator_version} · طبقه‌بندی {b.payload.rules.taxonomy} · خوشه‌بندی {b.payload.rules.clustering}. هر نسخه جدا ذخیره می‌شود و بازنویسی نمی‌شود.</p>
        </>
      )}
    </Shell>
  );
}

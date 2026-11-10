'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ChevronRight, ChevronLeft, Pause, Play, Zap, Clock3 } from 'lucide-react';
import { useApi, useNow } from '../design/useApi';
import type { FeedItem } from '../design/types';
import { fmt, fmtRelative } from '../design/format';
import { usePrefs } from '../design/prefs';

interface Breaking { mode: 'breaking' | 'latest_fallback'; rule: { id: string; description_fa: string }; items: FeedItem[] }

/** One headline at a time, advancing every 7s — never a marquee. Pauses on
 *  hover/focus and with the pause button; users who prefer reduced motion
 *  get no auto-advance at all. Items come only from the audited rule; when
 *  nothing qualifies, the bar says so and shows the latest items labelled
 *  as "latest", not as breaking. */
export function BreakingTicker() {
  const q = useApi<Breaking>('breaking?limit=12');
  const now = useNow();
  const { contentLang } = usePrefs();
  const [i, setI] = useState(0);
  const [paused, setPaused] = useState(false);
  const [hover, setHover] = useState(false);
  const [reduced, setReduced] = useState(false);
  const items = q.data?.items ?? [];
  useEffect(() => { setReduced(window.matchMedia('(prefers-reduced-motion: reduce)').matches); }, []);
  useEffect(() => {
    if (paused || hover || reduced || items.length < 2) return;
    const t = setInterval(() => setI((x) => (x + 1) % items.length), 7000);
    return () => clearInterval(t);
  }, [paused, hover, reduced, items.length]);

  if (q.error) return <div className="ticker ticker-muted" role="status">نوار خبر فوری در دسترس نیست (خطای ارتباط با سرور).</div>;
  if (!q.data) return <div className="ticker" aria-hidden="true"><span className="bone" style={{ height: 14, width: '60%' }} /></div>;
  if (!items.length) return <div className="ticker ticker-muted" role="status">هنوز خبری ثبت نشده است.</div>;

  const it = items[i % items.length];
  const title = contentLang === 'fa' && it.title_fa ? it.title_fa : it.title;
  const isBreaking = q.data.mode === 'breaking';
  return (
    <section className={isBreaking ? 'ticker ticker-live' : 'ticker'} aria-label={isBreaking ? 'خبرهای فوری' : 'تازه‌ترین خبرها'}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)} onFocus={() => setHover(true)} onBlur={() => setHover(false)}>
      <span className="ticker-label" title={q.data.rule.description_fa}>
        {isBreaking ? <><Zap size={14} />فوری</> : <><Clock3 size={14} />تازه‌ترین</>}
      </span>
      <div className="ticker-track" aria-live={paused || hover ? 'polite' : 'off'}>
        <Link key={it.item_id} href={`/news/${it.item_id}`} className="ticker-item">
          <span className="ticker-title" dir={title === it.title ? 'ltr' : 'rtl'}>{title}</span>
          <span className="ticker-meta"><bdi>{it.source_name}</bdi> · {fmtRelative(it.published_at, now)}
            {it.importance_level === 'high' && <> · <b>اهمیت زیاد</b></>}
            {it.event_sources >= 2 && <> · {fmt(it.event_sources)} منبع</>}
          </span>
        </Link>
      </div>
      <div className="ticker-ctrl">
        <span className="ticker-pos" aria-hidden="true">{fmt((i % items.length) + 1)}/{fmt(items.length)}</span>
        <button type="button" onClick={() => setI((x) => (x - 1 + items.length) % items.length)} aria-label="خبر قبلی"><ChevronRight size={16} /></button>
        <button type="button" onClick={() => setPaused(!paused)} aria-label={paused ? 'ادامه چرخش خودکار' : 'توقف چرخش خودکار'} aria-pressed={paused}>
          {paused ? <Play size={14} /> : <Pause size={14} />}
        </button>
        <button type="button" onClick={() => setI((x) => (x + 1) % items.length)} aria-label="خبر بعدی"><ChevronLeft size={16} /></button>
      </div>
    </section>
  );
}

'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { ChevronLeft, ChevronRight, Pause, Play, X, ExternalLink } from 'lucide-react';
import { useApi, useNow } from '../design/useApi';
import type { Story, StorySummary } from '../design/types';
import { catVar, fmt, fmtRelative, safeUrl } from '../design/format';
import { usePrefs } from '../design/prefs';
import { Empty, Failure } from '../design/ui';

const FRAME_MS = 6500;

function Avatar({ s }: { s: StorySummary }) {
  const [broken, setBroken] = useState(false);
  const img = safeUrl(s.visual.image_url);
  return (
    <span className="story-avatar" style={{ ['--art' as string]: catVar(s.visual.category_id) }}>
      {img && !broken
        // eslint-disable-next-line @next/next/no-img-element
        ? <img src={img} alt="" loading="lazy" referrerPolicy="no-referrer" onError={() => setBroken(true)} />
        : <span className="story-mono" aria-hidden="true">{s.visual.monogram}</span>}
    </span>
  );
}

export function useStories() {
  return useApi<{ stories: StorySummary[]; total: number; rule_version: string }>('stories');
}

/** Horizontal rail. Each bubble is a real button (keyboard, mouse, touch);
 *  arrow keys move between bubbles; the ring shows new vs seen content. */
export function StoriesRail({ layout = 'rail' }: { layout?: 'rail' | 'grid' }) {
  const q = useStories();
  const now = useNow();
  const { seen } = usePrefs();
  const [open, setOpen] = useState<number | null>(null);
  const railRef = useRef<HTMLDivElement>(null);
  const lastFocus = useRef<HTMLElement | null>(null);
  const stories = q.data?.stories ?? [];

  const onKey = (e: React.KeyboardEvent, idx: number) => {
    const next = e.key === 'ArrowLeft' ? idx + 1 : e.key === 'ArrowRight' ? idx - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? stories.length - 1 : null;
    if (next == null || next < 0 || next >= stories.length) return;
    e.preventDefault();
    (railRef.current?.querySelectorAll<HTMLButtonElement>('.story-btn')[next])?.focus();
  };
  const scroll = (dir: 1 | -1) => railRef.current?.scrollBy({ left: dir * -320, behavior: 'smooth' });

  if (q.error) return <Failure onRetry={q.reload}>استوری‌ها دریافت نشد.</Failure>;
  if (!q.data) return <div className="stories-rail" aria-hidden="true">{Array.from({ length: 7 }).map((_, i) => <span key={i} className="story-bone" />)}</div>;
  if (!stories.length) return <Empty title="هنوز استوری‌ای ساخته نشده است">استوری‌ها هر ۱۵ دقیقه از داده‌های واقعی پایگاه داده ساخته می‌شوند؛ اگر در بازه اخیر خبری نباشد، استوری‌ای هم ساخته نمی‌شود.</Empty>;

  return (
    <div className={layout === 'grid' ? 'stories stories-grid' : 'stories'}>
      {layout === 'rail' && <button type="button" className="rail-arrow rail-prev" onClick={() => scroll(-1)} aria-label="استوری‌های قبلی"><ChevronRight size={18} /></button>}
      <div className="stories-rail" ref={railRef} role="list" aria-label="استوری‌ها">
        {stories.map((s, idx) => {
          const isNew = seen[s.story_id] !== (s.content_updated_at ?? s.generated_at);
          return (
            <div role="listitem" key={s.story_id} className="story">
              <button type="button" className={isNew ? 'story-btn story-new' : 'story-btn'} onKeyDown={(e) => onKey(e, idx)}
                onClick={(e) => { lastFocus.current = e.currentTarget; setOpen(idx); }}
                aria-label={`${s.title_fa}، ${s.collection_label}، ${fmt(s.frame_count)} بخش${isNew ? '، جدید' : '، دیده‌شده'}`}>
                <Avatar s={s} />
                <span className="story-title">{s.title_fa}</span>
                <span className="story-sub">{s.collection_label} · {fmtRelative(s.content_updated_at ?? s.generated_at, now)}</span>
              </button>
            </div>
          );
        })}
      </div>
      {layout === 'rail' && <button type="button" className="rail-arrow rail-next" onClick={() => scroll(1)} aria-label="استوری‌های بعدی"><ChevronLeft size={18} /></button>}
      {open != null && (
        <StoryViewer stories={stories} index={open} onIndex={setOpen}
          onClose={() => { setOpen(null); setTimeout(() => lastFocus.current?.focus(), 0); }} />
      )}
    </div>
  );
}

export function StoryViewer({ stories, index, onIndex, onClose }: { stories: StorySummary[]; index: number; onIndex: (i: number) => void; onClose: () => void }) {
  const summary = stories[index];
  const q = useApi<Story>('stories/' + encodeURIComponent(summary.story_id), [summary.story_id]);
  const { markSeen, contentLang } = usePrefs();
  const now = useNow();
  const [frame, setFrame] = useState(0);
  const [paused, setPaused] = useState(false);
  const [hold, setHold] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const closeRef = useRef<HTMLButtonElement>(null);
  const frames = q.data?.frames ?? [];

  useEffect(() => { setFrame(0); setElapsed(0); }, [index]);
  useEffect(() => { closeRef.current?.focus(); const prev = document.body.style.overflow; document.body.style.overflow = 'hidden'; return () => { document.body.style.overflow = prev; }; }, []);
  useEffect(() => { if (q.data) markSeen(summary.story_id, summary.content_updated_at ?? summary.generated_at); }, [q.data, summary, markSeen]);

  const next = useCallback(() => {
    setElapsed(0);
    if (frame < frames.length - 1) setFrame(frame + 1);
    else if (index < stories.length - 1) onIndex(index + 1);
    else onClose();
  }, [frame, frames.length, index, stories.length, onIndex, onClose]);
  const prev = useCallback(() => {
    setElapsed(0);
    if (frame > 0) setFrame(frame - 1);
    else if (index > 0) onIndex(index - 1);
  }, [frame, index, onIndex]);

  const running = !paused && !hold && frames.length > 0;
  useEffect(() => {
    if (!running) return;
    const t0 = Date.now() - elapsed;
    const t = setInterval(() => {
      const e = Date.now() - t0;
      if (e >= FRAME_MS) { clearInterval(t); next(); } else setElapsed(e);
    }, 100);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running, frame, index, frames.length]);

  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      else if (e.key === 'ArrowLeft') { e.preventDefault(); next(); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); prev(); }
      else if (e.key === ' ' && (e.target as HTMLElement)?.tagName !== 'A') { e.preventDefault(); setPaused((p) => !p); }
      else if (e.key === 'Tab') {
        const nodes = document.querySelectorAll<HTMLElement>('.viewer button, .viewer a[href]');
        if (!nodes.length) return;
        const first = nodes[0], last = nodes[nodes.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [next, prev, onClose]);

  const f = frames[frame];
  const img = safeUrl(f?.image_url);
  return (
    <div className="viewer" role="dialog" aria-modal="true" aria-label={`استوری: ${summary.title_fa}`}>
      <div className="viewer-card" style={{ ['--art' as string]: catVar(f?.category_id ?? summary.visual.category_id) }}>
        <div className="viewer-progress" aria-hidden="true">
          {(frames.length ? frames : [null]).map((_, i) => (
            <span key={i}><i style={{ width: i < frame ? '100%' : i === frame ? `${Math.min(100, (elapsed / FRAME_MS) * 100)}%` : '0%' }} /></span>
          ))}
        </div>
        <div className="viewer-head">
          <div>
            <strong>{summary.title_fa}</strong>
            <small>{summary.collection_label} · {summary.subtitle_fa}</small>
          </div>
          <div className="viewer-tools">
            <button type="button" onClick={() => setPaused(!paused)} aria-pressed={paused} aria-label={paused ? 'ادامه' : 'توقف'}>{paused ? <Play size={16} /> : <Pause size={16} />}</button>
            <button type="button" ref={closeRef} onClick={onClose} aria-label="بستن استوری"><X size={18} /></button>
          </div>
        </div>

        <div className="viewer-stage" onPointerDown={(e) => { if (e.pointerType === 'touch') setHold(true); }}
          onPointerUp={() => setHold(false)} onPointerCancel={() => setHold(false)}>
          {q.error && <Failure>بخش‌های این استوری دریافت نشد.</Failure>}
          {!q.data && !q.error && <span className="bone" style={{ height: 200, width: '100%' }} />}
          {f && (
            <div className="viewer-frame" aria-live="polite">
              <div className="viewer-visual">
                {img
                  // eslint-disable-next-line @next/next/no-img-element
                  ? <img src={img} alt="" referrerPolicy="no-referrer" />
                  : <span className="viewer-mono" aria-hidden="true">{summary.visual.monogram}</span>}
              </div>
              <div className="viewer-text" onMouseEnter={() => setHold(true)} onMouseLeave={() => setHold(false)}
                onFocus={() => setHold(true)} onBlur={() => setHold(false)}>
                {f.category_label && <span className="viewer-kicker">{f.category_label}</span>}
                <h2 dir={f.headline_lang === 'en' ? 'ltr' : 'rtl'}>{f.headline}</h2>
                {f.subline && <p dir={f.subline_lang === 'en' ? 'ltr' : 'rtl'}>{f.subline}</p>}
                <div className="viewer-meta">
                  {f.source_name && <bdi>{f.source_name}</bdi>}
                  {f.published_at && <span>{fmtRelative(f.published_at, now)}</span>}
                  {f.headline_lang === 'en' && contentLang === 'fa' && <span className="viewer-note">متن اصلی منبع؛ ترجمه فارسی هنوز ذخیره نشده</span>}
                </div>
                <Link href={f.href} className="btn-primary" onClick={onClose}>مشاهده جزئیات<ExternalLink size={14} /></Link>
              </div>
            </div>
          )}
          <button type="button" className="viewer-zone viewer-zone-prev" onClick={prev} aria-label="بخش قبلی"><ChevronRight size={28} /></button>
          <button type="button" className="viewer-zone viewer-zone-next" onClick={next} aria-label="بخش بعدی"><ChevronLeft size={28} /></button>
        </div>

        <div className="viewer-foot">
          <span>{fmt(frame + 1)} از {fmt(Math.max(frames.length, 1))} · استوری {fmt(index + 1)} از {fmt(stories.length)}</span>
          <Link href={summary.target_href} onClick={onClose}>همه موارد این مجموعه</Link>
          <span className="viewer-rule" title="استوری‌ها با قواعد نسخه‌دار از داده پایگاه داده ساخته می‌شوند">قاعده {summary.rule_version}</span>
        </div>
      </div>
    </div>
  );
}

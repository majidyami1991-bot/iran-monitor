'use client';
import { useEffect, useRef, useState } from 'react';
import { ExternalLink, ShieldAlert } from 'lucide-react';
import { safeUrl } from '../design/format';

/** Official X embed, loaded only when the reader clicks. It renders the one
 *  registered post by id through X's own widget (an iframe X controls) — no
 *  HTML from X or from users is ever injected into this page, and the embed
 *  is never a data source. If X is blocked or the post is gone, the reader
 *  keeps the internal card and the "view on X" link. */
declare global {
  interface Window { twttr?: { widgets?: { createTweet: (id: string, el: HTMLElement, opts?: Record<string, unknown>) => Promise<HTMLElement | undefined> } } }
}

type State = 'idle' | 'loading' | 'loaded' | 'unavailable' | 'blocked';
const SCRIPT = 'https://platform.twitter.com/widgets.js';
let scriptPromise: Promise<void> | null = null;

function loadScript(): Promise<void> {
  if (window.twttr?.widgets) return Promise.resolve();
  if (!scriptPromise) {
    scriptPromise = new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = SCRIPT; s.async = true; s.charset = 'utf-8';
      s.onload = () => (window.twttr?.widgets ? resolve() : reject(new Error('no_widgets')));
      s.onerror = () => { scriptPromise = null; reject(new Error('blocked')); };
      document.head.appendChild(s);
    });
  }
  return scriptPromise;
}

export function XEmbed({ postId, postUrl }: { postId: string; postUrl: string }) {
  const [state, setState] = useState<State>('idle');
  const box = useRef<HTMLDivElement>(null);
  const url = safeUrl(postUrl);

  useEffect(() => {
    if (state !== 'loading' || !box.current) return;
    let done = false;
    const timer = setTimeout(() => { if (!done) { done = true; setState('blocked'); } }, 12000);
    loadScript()
      .then(() => window.twttr!.widgets!.createTweet(postId, box.current!, { dnt: true, lang: 'fa', theme: 'dark', conversation: 'none' }))
      .then((el) => { if (!done) { done = true; clearTimeout(timer); setState(el ? 'loaded' : 'unavailable'); } })
      .catch(() => { if (!done) { done = true; clearTimeout(timer); setState('blocked'); } });
    return () => { done = true; clearTimeout(timer); };
  }, [state, postId]);

  return (
    <section className="panel x-embed" aria-labelledby={`emb-${postId}`}>
      <div className="panel-title"><h3 id={`emb-${postId}`}>نمایش رسمی X</h3></div>
      {state === 'idle' && (
        <div className="x-embed-consent">
          <p className="muted"><ShieldAlert size={14} /> با بارگذاری، مرورگر شما مستقیماً به platform.twitter.com متصل می‌شود و X ممکن است آن را ثبت کند. این نمایش منبع داده سامانه نیست.</p>
          <button type="button" className="btn-ghost" onClick={() => setState('loading')}>بارگذاری نمایش رسمی این پست</button>
        </div>
      )}
      {state === 'loading' && <p className="muted" role="status">در حال بارگذاری از X…</p>}
      {state === 'blocked' && <p className="x-embed-msg" role="status">X در دسترس نیست یا بارگذاری آن مسدود شد (فیلترینگ، شبکه یا سیاست محتوایی مرورگر). اطلاعات ثبت‌شده در این صفحه همچنان معتبر است.</p>}
      {state === 'unavailable' && <p className="x-embed-msg" role="status">X این پست را نمایش نداد؛ ممکن است حذف، محدود یا خصوصی شده باشد. وضعیت پست را در صورت لزوم به «در X در دسترس نیست» تغییر دهید.</p>}
      <div ref={box} className="x-embed-box" hidden={state !== 'loading' && state !== 'loaded'} />
      {url && <a href={url} target="_blank" rel="noopener noreferrer nofollow" className="sec-link">مشاهده در X<ExternalLink size={13} /></a>}
    </section>
  );
}

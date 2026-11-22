'use client';
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';

/** Per-viewer conveniences only (browser storage):
 *  - contentLang: 'fa' (Persian interface & RTL) or 'en' (English interface & LTR).
 *  - seen stories: story id -> content_updated_at, for the new/seen ring. */
type Lang = 'fa' | 'en';

interface PrefsValue {
  contentLang: Lang;
  setContentLang: (l: Lang) => void;
  seen: Record<string, string>;
  markSeen: (id: string, stamp: string) => void;
}

const Ctx = createContext<PrefsValue>({ contentLang: 'fa', setContentLang: () => {}, seen: {}, markSeen: () => {} });

function read<T>(key: string, fallback: T): T {
  try { const v = localStorage.getItem(key); return v ? (JSON.parse(v) as T) : fallback; } catch { return fallback; }
}
function write(key: string, value: unknown) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* per-viewer only */ }
}

export function Prefs({ children }: { children: ReactNode }) {
  const [contentLang, setLang] = useState<Lang>('fa');
  const [seen, setSeen] = useState<Record<string, string>>({});

  useEffect(() => {
    const l = read<Lang>('im.contentLang', 'fa');
    const validLang: Lang = l === 'en' ? 'en' : 'fa';
    setLang(validLang);
    if (typeof document !== 'undefined') {
      document.documentElement.dir = validLang === 'en' ? 'ltr' : 'rtl';
      document.documentElement.lang = validLang;
    }
    setSeen(read('im.storiesSeen', {}));
  }, []);

  const setContentLang = useCallback((l: Lang) => {
    const validLang: Lang = l === 'en' ? 'en' : 'fa';
    setLang(validLang);
    write('im.contentLang', validLang);
    if (typeof document !== 'undefined') {
      document.documentElement.dir = validLang === 'en' ? 'ltr' : 'rtl';
      document.documentElement.lang = validLang;
    }
  }, []);

  const markSeen = useCallback((id: string, stamp: string) => {
    setSeen((s) => { const n = { ...s, [id]: stamp }; write('im.storiesSeen', n); return n; });
  }, []);

  return <Ctx.Provider value={{ contentLang, setContentLang, seen, markSeen }}>{children}</Ctx.Provider>;
}

export const usePrefs = () => useContext(Ctx);

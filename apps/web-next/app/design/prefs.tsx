'use client';
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';

/** Per-viewer conveniences only (browser storage; safe to lose):
 *  - contentLang: which text leads on cards — the stored Persian machine
 *    translation when one exists ('fa'), or the publisher's original ('en').
 *    Interface chrome stays Persian; this only changes content order.
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
  useEffect(() => { setLang(read<Lang>('im.contentLang', 'fa')); setSeen(read('im.storiesSeen', {})); }, []);
  const setContentLang = useCallback((l: Lang) => { setLang(l); write('im.contentLang', l); }, []);
  const markSeen = useCallback((id: string, stamp: string) => {
    setSeen((s) => { const n = { ...s, [id]: stamp }; write('im.storiesSeen', n); return n; });
  }, []);
  return <Ctx.Provider value={{ contentLang, setContentLang, seen, markSeen }}>{children}</Ctx.Provider>;
}

export const usePrefs = () => useContext(Ctx);

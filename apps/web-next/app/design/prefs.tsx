'use client';
import { createContext, useCallback, useContext, useEffect, useState, useMemo, type ReactNode } from 'react';
import { getT, type Lang, type Translations } from './i18n';

export type { Lang };

interface PrefsValue {
  contentLang: Lang;
  setContentLang: (l: Lang) => void;
  seen: Record<string, string>;
  markSeen: (id: string, stamp: string) => void;
  t: Translations;
  isEn: boolean;
}

const defaultT = getT('fa');
const Ctx = createContext<PrefsValue>({ 
  contentLang: 'fa', 
  setContentLang: () => {}, 
  seen: {}, 
  markSeen: () => {},
  t: defaultT,
  isEn: false
});

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

  const t = useMemo(() => getT(contentLang), [contentLang]);
  const isEn = contentLang === 'en';

  return <Ctx.Provider value={{ contentLang, setContentLang, seen, markSeen, t, isEn }}>{children}</Ctx.Provider>;
}

export const usePrefs = () => useContext(Ctx);

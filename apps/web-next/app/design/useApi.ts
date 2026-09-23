'use client';
import { useCallback, useEffect, useState } from 'react';

interface ApiState<T> { data: T | null; error: boolean; loading: boolean; }

/** Fetch one /api/v1/... path, re-running when `deps` change. Never fabricates
 * a value on failure: `data` stays whatever it last was (or null) and `error`
 * is set, so callers can show a real error state instead of a stale guess. */
export function useApi<T>(path: string | null, deps: unknown[] = []): ApiState<T> & { reload: () => void } {
  const [state, setState] = useState<ApiState<T>>({ data: null, error: false, loading: true });
  const load = useCallback(() => {
    if (!path) return;
    setState((s) => ({ ...s, loading: true }));
    fetch('/api/v1/' + path, { cache: 'no-store' })
      .then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json(); })
      .then((data) => setState({ data, error: false, loading: false }))
      .catch(() => setState((s) => ({ ...s, error: true, loading: false })));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps]);
  useEffect(() => { load(); }, [load]);
  return { ...state, reload: load };
}

/** now() re-rendered once a minute, for relative-time display without a
 * per-second re-render cost. */
export function useNow(intervalMs = 60000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(t);
  }, [intervalMs]);
  return now;
}

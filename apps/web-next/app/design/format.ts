// Shared formatting helpers. One implementation of each, used everywhere, so
// number/date formatting cannot drift between pages. All wall-clock times are
// shown in Tehran time with the Persian (Jalali) calendar; the header states it.
export const TZ = 'Asia/Tehran';
const nf = new Intl.NumberFormat('fa-IR');

export const fmt = (n: number | null | undefined): string => (n == null ? '—' : nf.format(n));

export const fmtPercent = (n: number | null | undefined, digits = 0): string =>
  n == null ? '—' : new Intl.NumberFormat('fa-IR', { maximumFractionDigits: digits }).format(n) + '٪';

export const fmtSigned = (n: number): string => (n > 0 ? '+' : n < 0 ? '−' : '') + nf.format(Math.abs(n));

function parse(value: string | Date | null | undefined): Date | null {
  if (!value) return null;
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function fmtDateTime(value: string | null | undefined): string {
  const d = parse(value);
  return d ? d.toLocaleString('fa-IR', { timeZone: TZ, dateStyle: 'medium', timeStyle: 'short' }) : 'ثبت نشده';
}

export function fmtDateShort(value: string | null | undefined): string {
  const d = parse(value);
  return d ? d.toLocaleDateString('fa-IR', { timeZone: TZ, month: 'short', day: 'numeric' }) : 'ثبت نشده';
}

export function fmtDateLong(value: string | Date | null | undefined): string {
  const d = parse(value);
  return d ? d.toLocaleDateString('fa-IR', { timeZone: TZ, weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) : 'ثبت نشده';
}

export function fmtTime(value: string | Date | null | undefined): string {
  const d = parse(value);
  return d ? d.toLocaleTimeString('fa-IR', { timeZone: TZ, hour: '2-digit', minute: '2-digit' }) : '—';
}

export function fmtClock(d: Date): string {
  return d.toLocaleTimeString('fa-IR', { timeZone: TZ, hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function fmtDay(value: string | null | undefined): string {
  const d = parse(value);
  return d ? d.toLocaleDateString('fa-IR', { timeZone: TZ, month: 'numeric', day: 'numeric' }) : '—';
}

/** Relative "چند دقیقه پیش" phrasing; absolute date once relative stops helping. */
export function fmtRelative(value: string | null | undefined, nowMs: number): string {
  const d = parse(value);
  if (!d) return 'ثبت نشده';
  const diffMin = Math.round((nowMs - d.getTime()) / 60000);
  if (diffMin < -5) return fmtDateTime(value ?? null); // future-dated by the publisher
  if (diffMin < 1) return 'همین الان';
  if (diffMin < 60) return `${fmt(diffMin)} دقیقه پیش`;
  const h = Math.round(diffMin / 60);
  if (h < 24) return `${fmt(h)} ساعت پیش`;
  const days = Math.round(h / 24);
  if (days < 14) return `${fmt(days)} روز پیش`;
  return fmtDateShort(value);
}

/** Only ever return a URL that is safe for an href/src: http(s), no credentials. */
export function safeUrl(u: string | null | undefined): string | undefined {
  if (!u) return undefined;
  try {
    const x = new URL(u);
    return ['http:', 'https:'].includes(x.protocol) && !x.username && !x.password ? u : undefined;
  } catch {
    return undefined;
  }
}

export function hostOf(u: string | null | undefined): string | null {
  try { return u ? new URL(u).hostname.replace(/^www\./, '') : null; } catch { return null; }
}

export function isPersian(text: string | null | undefined): boolean {
  return !!text && /[؀-ۿ]/.test(text);
}

/** Deterministic per-source accent colour, so each publisher keeps one identity. */
export function sourceColor(sourceId: string): string {
  const hue = 190 + ([...sourceId].reduce((a, c) => a + c.charCodeAt(0), 0) % 140);
  return `hsl(${hue} 45% 55%)`;
}

export function catVar(categoryId: string | null | undefined): string {
  return `var(--cat-${categoryId || 'other'}, var(--cat-other))`;
}

export function qs(params: Record<string, string | number | boolean | null | undefined>): string {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== null && v !== undefined && v !== '') u.set(k, String(v));
  const s = u.toString();
  return s ? '?' + s : '';
}

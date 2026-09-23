// Shared formatting helpers. One implementation of each, used everywhere, so
// number/date formatting cannot drift between pages.
const nf = new Intl.NumberFormat('fa-IR');

export const fmt = (n: number | null | undefined): string => (n == null ? '—' : nf.format(n));

export const fmtPercent = (n: number | null | undefined): string => (n == null ? '—' : nf.format(Math.round(n)) + '٪');

export function fmtDateTime(value: string | null | undefined): string {
  if (!value) return 'ثبت نشده';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return 'ثبت نشده';
  return d.toLocaleString('fa-IR', { timeZone: 'UTC' });
}

export function fmtDateShort(value: string | null | undefined): string {
  if (!value) return 'ثبت نشده';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return 'ثبت نشده';
  return d.toLocaleDateString('fa-IR', { timeZone: 'UTC', month: 'short', day: 'numeric' });
}

export function fmtTime(value: string | null | undefined): string {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleTimeString('fa-IR', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit' });
}

/** Relative "چند دقیقه پیش" phrasing for freshness indicators. Falls back to an
 * absolute timestamp once the gap is large enough that relative time stops
 * being useful. */
export function fmtRelative(value: string | null | undefined, nowMs: number): string {
  if (!value) return 'ثبت نشده';
  const t = Date.parse(value);
  if (Number.isNaN(t)) return 'ثبت نشده';
  const diffMin = Math.round((nowMs - t) / 60000);
  if (diffMin < 1) return 'همین الان';
  if (diffMin < 60) return `${fmt(diffMin)} دقیقه پیش`;
  const diffHour = Math.round(diffMin / 60);
  if (diffHour < 24) return `${fmt(diffHour)} ساعت پیش`;
  const diffDay = Math.round(diffHour / 24);
  if (diffDay < 14) return `${fmt(diffDay)} روز پیش`;
  return fmtDateShort(value);
}

/** Only ever return a URL that is safe to place in an href: http(s), no
 * embedded credentials. Anything else (data:, javascript:, malformed) yields
 * undefined so the caller can omit the link rather than render a bad one. */
export function safeUrl(u: string | null | undefined): string | undefined {
  if (!u) return undefined;
  try {
    const x = new URL(u);
    return ['http:', 'https:'].includes(x.protocol) && !x.username && !x.password ? u : undefined;
  } catch {
    return undefined;
  }
}

export function isPersian(text: string): boolean {
  return /[؀-ۿ]/.test(text);
}

/** Deterministic per-source accent color from the source id, so each
 * publisher gets a stable identity color without maintaining a manual map. */
export function sourceColor(sourceId: string): string {
  const hue = 165 + ([...sourceId].reduce((a, c) => a + c.charCodeAt(0), 0) % 90);
  return `hsl(${hue} 55% 56%)`;
}

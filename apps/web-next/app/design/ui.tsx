'use client';
import type { ReactNode } from 'react';
import { AlertTriangle, Inbox } from 'lucide-react';

/** The six monitoring states named in the design system. Every health value
 * the API returns maps to exactly one of these — never invent a color. */
export type Health = 'healthy' | 'fresh' | 'attention' | 'stopped' | 'error' | 'inactive';

const HEALTH_LABEL: Record<Health, string> = {
  healthy: 'سالم', fresh: 'تازه', attention: 'نیازمند توجه',
  stopped: 'متوقف', error: 'خطادار', inactive: 'غیرفعال',
};

/** Maps API health_status / collector_health strings to one of the six design
 * states. This is the single place that translation happens — never inline
 * a color decision at a call site. */
export function toHealth(apiValue: string | null | undefined): Health {
  switch (apiValue) {
    case 'healthy': return 'healthy';
    case 'delayed': case 'degraded': return 'attention';
    case 'failing': case 'stopped_stale_heartbeat': return 'error';
    case 'stopped': case 'not_running': return 'stopped';
    case 'not_run': return 'inactive';
    default: return 'inactive';
  }
}

export function StatusPill({ health, label, title }: { health: Health; label?: string; title?: string }) {
  return <span className={'status-pill status-' + health} title={title}><i />{label ?? HEALTH_LABEL[health]}</span>;
}

export function Badge({ children, tone = 'default', title }: { children: ReactNode; tone?: 'default' | 'accent' | 'error' | 'muted'; title?: string }) {
  const cls = tone === 'default' ? 'badge' : `badge badge-${tone}`;
  return <span className={cls} title={title}>{children}</span>;
}

export function Chip({ children, active = false, onClick, href }: { children: ReactNode; active?: boolean; onClick?: () => void; href?: string }) {
  if (href) return <a href={href} className="chip" aria-pressed={active}>{children}</a>;
  return <button type="button" className="chip" aria-pressed={active} onClick={onClick}>{children}</button>;
}

export function Tabs({ value, onChange, items }: { value: string; onChange: (v: string) => void; items: [string, string][] }) {
  return (
    <div className="tabs" role="tablist">
      {items.map(([key, label]) => (
        <button key={key} type="button" role="tab" aria-selected={value === key} onClick={() => onChange(key)}>{label}</button>
      ))}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="state-block" role="status">
      <Inbox size={26} color="var(--text-disabled)" />
      <strong>{title}</strong>
      {children && <p>{children}</p>}
    </div>
  );
}

export function ErrorState({ children, onRetry }: { children: ReactNode; onRetry?: () => void }) {
  return (
    <div className="state-error" role="alert">
      <AlertTriangle size={18} />
      <span>{children}</span>
      {onRetry && <button type="button" className="btn btn-secondary" onClick={onRetry} style={{ marginRight: 'auto' }}>تلاش دوباره</button>}
    </div>
  );
}

export function StaleNotice({ children }: { children: ReactNode }) {
  return <span className="state-stale"><AlertTriangle size={13} />{children}</span>;
}

export function Skeleton({ height = 16, width = '100%', radius }: { height?: number; width?: number | string; radius?: number }) {
  return <div className="skeleton" style={{ height, width, borderRadius: radius }} />;
}

export function SourceMark({ name, color }: { name: string; color: string }) {
  const letter = (name || '؟').trim().slice(0, 1).toUpperCase();
  return <span className="source-mark" style={{ ['--mark-color' as string]: color }}>{letter}</span>;
}

/** Small, consistent per-field status indicator: replaces the
 * "field_name: field_value" pill dumps that read as a debug panel. Shows an
 * icon + label only; hover reveals the full explanation via `title`. */
const FIELD_LABEL: Record<string, string> = {
  available: 'موجود', pending: 'در صف', unavailable: 'ناموجود',
  error: 'خطا', not_processed: 'پردازش‌نشده', summary_only: 'فقط خلاصه',
  full_syndicated: 'متن کامل', link_only: 'فقط پیوند',
  not_generated: 'تولید نشده', provider_not_configured: 'ارائه‌دهنده تنظیم نشده',
  needs_review: 'نیازمند بازبینی', pending_review: 'در صف بازبینی',
  approved: 'تأییدشده', rejected: 'ردشده', not_applicable: '—',
  source_summary_missing: 'خلاصه منبع موجود نیست',
};
const FIELD_TONE: Record<string, 'accent' | 'default' | 'muted' | 'error'> = {
  available: 'accent', full_syndicated: 'accent', approved: 'accent',
  pending: 'default', summary_only: 'default', pending_review: 'default',
  unavailable: 'muted', not_processed: 'muted', link_only: 'muted',
  not_generated: 'muted', provider_not_configured: 'muted', not_applicable: 'muted',
  source_summary_missing: 'muted',
  error: 'error', rejected: 'error', needs_review: 'error',
};
export function FieldStatus({ label, status, title }: { label: string; status?: string | null; title?: string }) {
  const key = status || 'unavailable';
  return <Badge tone={FIELD_TONE[key] ?? 'muted'} title={title}>{label} · {FIELD_LABEL[key] ?? key}</Badge>;
}

export function Pagination({ page, hasNext, onPage }: { page: number; hasNext: boolean; onPage: (p: number) => void }) {
  return (
    <div style={{ display: 'flex', gap: 'var(--space-3)', justifyContent: 'center', margin: 'var(--space-6) 0' }}>
      <button type="button" className="btn btn-secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>صفحه قبل</button>
      <button type="button" className="btn btn-secondary" disabled={!hasNext} onClick={() => onPage(page + 1)}>صفحه بعد</button>
    </div>
  );
}

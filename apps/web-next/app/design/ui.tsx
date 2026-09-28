'use client';
import type { ReactNode } from 'react';
import Link from 'next/link';
import { AlertTriangle, Inbox, PlugZap, Sparkles, Languages, Zap, CircleDashed, ChevronLeft } from 'lucide-react';
import { catVar, fmt } from './format';
import type { Importance, Integration } from './types';

/* ------------------------------------------------------------------ v2 primitives */

export function Tag({ children, tone = 'neutral', title, icon }: {
  children: ReactNode; tone?: 'neutral' | 'brand' | 'urgent' | 'warn' | 'ok' | 'error' | 'ai' | 'info' | 'uncertain';
  title?: string; icon?: ReactNode;
}) {
  return <span className={`tag tag-${tone}`} title={title}>{icon}{children}</span>;
}

export function CategoryTag({ id, label, href = true }: { id: string | null | undefined; label: string | null | undefined; href?: boolean }) {
  const text = label || 'دسته‌بندی‌نشده';
  const inner = <><i style={{ background: catVar(id) }} />{text}</>;
  if (href && id) return <Link href={`/topics/${id}`} className="cat-tag">{inner}</Link>;
  return <span className="cat-tag">{inner}</span>;
}

const IMP_LABEL: Record<Importance, string> = { high: 'اهمیت زیاد', medium: 'اهمیت متوسط', low: 'اهمیت کم' };
export function ImportanceTag({ level, showLow = false }: { level: Importance; showLow?: boolean }) {
  if (level === 'low' && !showLow) return null;
  return <span className={`imp imp-${level}`} title="بر اساس قاعده importance_v1 — صفحه «درباره» را ببینید"><i />{IMP_LABEL[level]}</span>;
}

export function BreakingTag() {
  return <Tag tone="urgent" icon={<Zap size={12} />}>فوری</Tag>;
}

/** The client's rule: a machine translation is always visibly labelled, with
 *  its review state. Absent translations say why, never show a guess. */
export function TranslationTag({ status, review }: { status: string | null | undefined; review?: string | null }) {
  if (status === 'available') {
    const reviewed = review === 'approved' ? ' · بازبینی‌شده' : review === 'pending_review' ? ' · در صف بازبینی' : ' · بازبینی‌نشده';
    return <Tag tone="ai" icon={<Languages size={12} />} title="ترجمه ماشینی؛ متن اصلی منبع حفظ شده است">ترجمه ماشینی{reviewed}</Tag>;
  }
  const label = status === 'error' ? 'ترجمه ناموفق' : status === 'unavailable' ? 'ترجمه ناموجود' : 'ترجمه در انتظار';
  return <Tag tone="uncertain" icon={<Languages size={12} />} title="هنوز ترجمه فارسی ذخیره نشده؛ متن اصلی نمایش داده می‌شود">{label}</Tag>;
}

export function AiTag({ children = 'تولیدشده با هوش مصنوعی' }: { children?: ReactNode }) {
  return <Tag tone="ai" icon={<Sparkles size={12} />}>{children}</Tag>;
}

export function RuleTag({ children }: { children: ReactNode }) {
  return <Tag tone="info" icon={<CircleDashed size={12} />}>{children}</Tag>;
}

export function SectionHead({ title, kicker, action, id }: { title: string; kicker?: ReactNode; action?: { href: string; label: string }; id?: string }) {
  return (
    <div className="sec-head">
      <div>
        <h2 id={id}>{title}</h2>
        {kicker && <p>{kicker}</p>}
      </div>
      {action && <Link href={action.href} className="sec-link">{action.label}<ChevronLeft size={15} /></Link>}
    </div>
  );
}

export function PageHead({ title, lede, children, eyebrow }: { title: string; lede?: ReactNode; children?: ReactNode; eyebrow?: string }) {
  return (
    <header className="page-hero">
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        {lede && <p>{lede}</p>}
      </div>
      {children && <div className="page-hero-side">{children}</div>}
    </header>
  );
}

export function Empty({ title, children, icon }: { title: string; children?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="empty" role="status">
      {icon ?? <Inbox size={24} />}
      <strong>{title}</strong>
      {children && <div className="empty-body">{children}</div>}
    </div>
  );
}

export function Failure({ children, onRetry }: { children?: ReactNode; onRetry?: () => void }) {
  return (
    <div className="failure" role="alert">
      <AlertTriangle size={18} />
      <span>{children ?? 'دریافت داده از سرور ناموفق بود. داده‌ای حدس زده یا جایگزین نشده است.'}</span>
      {onRetry && <button type="button" className="btn-ghost" onClick={onRetry}>تلاش دوباره</button>}
    </div>
  );
}

export function Bone({ h = 14, w = '100%', r }: { h?: number; w?: number | string; r?: number }) {
  return <span className="bone" style={{ height: h, width: w, borderRadius: r }} aria-hidden="true" />;
}

export function CardBones({ n = 4, image = true }: { n?: number; image?: boolean }) {
  return (
    <div className="bones" role="status" aria-label="در حال بارگذاری">
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} className="bone-card">
          {image && <Bone h={84} w={120} r={8} />}
          <div style={{ flex: 1, display: 'grid', gap: 8 }}><Bone h={12} w="30%" /><Bone h={16} /><Bone h={16} w="75%" /></div>
        </div>
      ))}
    </div>
  );
}

const INTEGRATION_STATUS: Record<string, [string, 'ok' | 'warn' | 'error' | 'uncertain']> = {
  active: ['فعال', 'ok'], configured: ['پیکربندی‌شده', 'ok'], stale: ['متوقف یا با تأخیر', 'warn'],
  blocked: ['مسدود', 'error'], not_configured: ['اتصال پیکربندی نشده', 'uncertain'],
};

/** Honest state for a capability whose data source is not connected: which
 *  integration, its live status, why — and never a placeholder number. */
export function IntegrationNotice({ integration, title, children }: { integration: Integration | null | undefined; title?: string; children?: ReactNode }) {
  const [label, tone] = INTEGRATION_STATUS[integration?.live_status ?? 'not_configured'] ?? [integration?.live_status ?? '—', 'uncertain'];
  return (
    <div className={`integration integration-${tone}`}>
      <div className="integration-head">
        <PlugZap size={18} />
        <strong>{title ?? integration?.name_fa ?? 'اتصال داده'}</strong>
        <Tag tone={tone}>{label}</Tag>
      </div>
      {integration?.reason_fa && <p>{integration.reason_fa}</p>}
      {children}
      {tone !== 'ok' && <small>هیچ داده نمایشی یا ساختگی در این بخش نشان داده نمی‌شود.</small>}
    </div>
  );
}

export function Stat({ label, value, note, tone }: { label: string; value: ReactNode; note?: ReactNode; tone?: 'up' | 'down' | 'flat' }) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{typeof value === 'number' ? fmt(value) : value}</strong>
      {note && <span className={`stat-note ${tone ? 'stat-' + tone : ''}`}>{note}</span>}
    </div>
  );
}

export function Segmented<T extends string>({ value, onChange, items, label }: { value: T; onChange: (v: T) => void; items: [T, string][]; label: string }) {
  return (
    <div className="segmented" role="radiogroup" aria-label={label}>
      {items.map(([k, l]) => (
        <button key={k} type="button" role="radio" aria-checked={value === k} onClick={() => onChange(k)}>{l}</button>
      ))}
    </div>
  );
}

export function Pager({ page, hasNext, onPage, total }: { page: number; hasNext: boolean; onPage: (p: number) => void; total?: number }) {
  return (
    <nav className="pager" aria-label="صفحه‌بندی">
      <button type="button" className="btn-ghost" disabled={page <= 1} onClick={() => onPage(page - 1)}>صفحه قبل</button>
      <span>صفحه {fmt(page)}{total != null ? ` · ${fmt(total)} مورد` : ''}</span>
      <button type="button" className="btn-ghost" disabled={!hasNext} onClick={() => onPage(page + 1)}>صفحه بعد</button>
    </nav>
  );
}

export function SourceMark({ name, color, size = 28 }: { name: string; color: string; size?: number }) {
  const letter = (name || '؟').trim().replace(/^the\s+/i, '').slice(0, 1).toUpperCase();
  return <span className="mark" style={{ ['--mark' as string]: color, width: size, height: size, fontSize: size * 0.45 }} aria-hidden="true">{letter}</span>;
}

/* ------------------------------------------------------------------ v1 primitives
   (kept so the retained review and monitoring pages compile unchanged) */

export type Health = 'healthy' | 'fresh' | 'attention' | 'stopped' | 'error' | 'inactive';
const HEALTH_LABEL: Record<Health, string> = {
  healthy: 'سالم', fresh: 'تازه', attention: 'نیازمند توجه', stopped: 'متوقف', error: 'خطادار', inactive: 'غیرفعال',
};
export function toHealth(apiValue: string | null | undefined): Health {
  switch (apiValue) {
    case 'healthy': return 'healthy';
    case 'delayed': case 'degraded': return 'attention';
    case 'failing': case 'stopped_stale_heartbeat': return 'error';
    case 'stopped': case 'not_running': return 'stopped';
    default: return 'inactive';
  }
}
export function StatusPill({ health, label, title }: { health: Health; label?: string; title?: string }) {
  return <span className={'status-pill status-' + health} title={title}><i />{label ?? HEALTH_LABEL[health]}</span>;
}
export function Badge({ children, tone = 'default', title }: { children: ReactNode; tone?: 'default' | 'accent' | 'error' | 'muted'; title?: string }) {
  return <span className={tone === 'default' ? 'badge' : `badge badge-${tone}`} title={title}>{children}</span>;
}
export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return <Empty title={title}>{children}</Empty>;
}
export function ErrorState({ children, onRetry }: { children: ReactNode; onRetry?: () => void }) {
  return <Failure onRetry={onRetry}>{children}</Failure>;
}
export function Skeleton({ height = 16, width = '100%', radius }: { height?: number; width?: number | string; radius?: number }) {
  return <Bone h={height} w={width} r={radius} />;
}
const FIELD_LABEL: Record<string, string> = {
  available: 'موجود', pending: 'در صف', unavailable: 'ناموجود', error: 'خطا', not_processed: 'پردازش‌نشده',
  summary_only: 'فقط خلاصه', full_syndicated: 'متن کامل', link_only: 'فقط پیوند', not_generated: 'تولید نشده',
  provider_not_configured: 'ارائه‌دهنده تنظیم نشده', needs_review: 'نیازمند بازبینی', pending_review: 'در صف بازبینی',
  approved: 'تأییدشده', rejected: 'ردشده', not_applicable: '—', source_summary_missing: 'خلاصه منبع موجود نیست',
};
const FIELD_TONE: Record<string, 'accent' | 'default' | 'muted' | 'error'> = {
  available: 'accent', full_syndicated: 'accent', approved: 'accent', pending: 'default', summary_only: 'default',
  pending_review: 'default', error: 'error', rejected: 'error', needs_review: 'error',
};
export function FieldStatus({ label, status, title }: { label: string; status?: string | null; title?: string }) {
  const key = status || 'unavailable';
  return <Badge tone={FIELD_TONE[key] ?? 'muted'} title={title}>{label} · {FIELD_LABEL[key] ?? key}</Badge>;
}

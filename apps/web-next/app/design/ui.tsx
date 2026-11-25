'use client';
import type { ReactNode } from 'react';
import Link from 'next/link';
import { AlertTriangle, Inbox, PlugZap, Sparkles, Languages, Zap, CircleDashed, ChevronLeft } from 'lucide-react';
import { catVar, fmt } from './format';
import { getCategoryLabel } from './taxonomy';
import type { Importance, Integration } from './types';
import { usePrefs } from './prefs';

/* ------------------------------------------------------------------ v2 primitives */

export function Tag({ children, tone = 'neutral', title, icon }: {
  children: ReactNode; tone?: 'neutral' | 'brand' | 'urgent' | 'warn' | 'ok' | 'error' | 'ai' | 'info' | 'uncertain';
  title?: string; icon?: ReactNode;
}) {
  return <span className={`tag tag-${tone}`} title={title}>{icon}{children}</span>;
}

export function CategoryTag({ id, label, href = true }: { id: string | null | undefined; label: string | null | undefined; href?: boolean }) {
  const { t, isEn } = usePrefs();
  const text = getCategoryLabel(id || label, isEn) || label || t.tagUncategorized;
  const inner = <><i style={{ background: catVar(id) }} />{text}</>;
  if (href && id) return <Link href={`/topics/${id}`} className="cat-tag">{inner}</Link>;
  return <span className="cat-tag">{inner}</span>;
}

export function ImportanceTag({ level, showLow = false }: { level: Importance; showLow?: boolean }) {
  const { t } = usePrefs();
  if (level === 'low' && !showLow) return null;
  const labels: Record<Importance, string> = {
    high: t.importanceHigh,
    medium: t.importanceMed,
    low: t.importanceLow,
  };
  return <span className={`imp imp-${level}`} title={t.importanceTitle}><i />{labels[level]}</span>;
}

export function BreakingTag() {
  const { t } = usePrefs();
  return <Tag tone="urgent" icon={<Zap size={12} />}>{t.tagBreaking}</Tag>;
}

/** The client's rule: a machine translation is always visibly labelled, with
 *  its review state. Absent translations say why, never show a guess. */
export const MACHINE_LABEL = 'ترجمه خودکار ـ تأیید انسانی نشده';

export function TranslationTag({ status, review }: { status: string | null | undefined; review?: string | null }) {
  const { t } = usePrefs();
  // 3003 lab pipeline (TranslateGemma 27B + QC v2.1): passing QC is not proof of correctness.
  if (status === 'translated_auto')
    return <Tag tone="ai" icon={<Languages size={12} />} title={t.translationQcPassTitle}>{t.tagMachineLabel}</Tag>;
  if (status === 'qc_warning')
    return <Tag tone="uncertain" icon={<Languages size={12} />} title={t.translationQcWarnTitle}>{t.translationQcWarnLabel}</Tag>;
  if (status === 'qc_failed')
    return <Tag tone="uncertain" icon={<Languages size={12} />} title={t.translationQcFailedTitle}>{t.translationQcFailedLabel}</Tag>;
  if (status === 'translation_pending' || status === 'processing')
    return <Tag tone="uncertain" icon={<Languages size={12} />} title={t.translationPendingTitle}>{status === 'processing' ? t.translationProcessingLabel : t.translationPendingLabel}</Tag>;
  if (status === 'translation_failed')
    return <Tag tone="uncertain" icon={<Languages size={12} />} title={t.translationFailedTitle}>{t.translationFailedLabel}</Tag>;
  if (status === 'no_source_text')
    return <Tag tone="neutral" icon={<Languages size={12} />} title={t.translationNoTextTitle}>{t.translationNoTextLabel}</Tag>;
  if (status === 'translation_error')
    return <Tag tone="uncertain" icon={<Languages size={12} />} title={t.translationErrorTitle}>{t.translationErrorLabel}</Tag>;
  if (status === 'available') {
    const reviewed = review === 'approved' ? ` · ${t.translationReviewed}` : review === 'pending_review' ? ` · ${t.translationPendingReview}` : ` · ${t.translationUnreviewed}`;
    return <Tag tone="ai" icon={<Languages size={12} />} title={t.tagMachineLabel}>{t.translationMachine}{reviewed}</Tag>;
  }
  const label = status === 'error' || status === 'failed' ? t.translationFailedLabel : status === 'unavailable' ? t.translationUnavailable
    : status === 'needs_review' ? t.translationQcRejected : status === 'processing' ? t.translationProcessingLabel
    : status === 'stale' ? t.translationStale : status === 'not_required' ? t.translationNotRequired : t.translationPendingLabel;
  return <Tag tone="uncertain" icon={<Languages size={12} />} title={t.translationPendingTitle}>{label}</Tag>;
}

export function AiTag({ children }: { children?: ReactNode }) {
  const { t } = usePrefs();
  return <Tag tone="ai" icon={<Sparkles size={12} />}>{children ?? t.tagAiGenerated}</Tag>;
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
  const { t } = usePrefs();
  return (
    <div className="failure" role="alert">
      <AlertTriangle size={18} />
      <span>{children ?? t.failureDefault}</span>
      {onRetry && <button type="button" className="btn-ghost" onClick={onRetry}>{t.retryAction}</button>}
    </div>
  );
}

export function Bone({ h = 14, w = '100%', r }: { h?: number; w?: number | string; r?: number }) {
  return <span className="bone" style={{ height: h, width: w, borderRadius: r }} aria-hidden="true" />;
}

export function CardBones({ n = 4, image = true }: { n?: number; image?: boolean }) {
  const { t } = usePrefs();
  return (
    <div className="bones" role="status" aria-label={t.loadingText}>
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} className="bone-card">
          {image && <Bone h={84} w={120} r={8} />}
          <div style={{ flex: 1, display: 'grid', gap: 8 }}><Bone h={12} w="30%" /><Bone h={16} /><Bone h={16} w="75%" /></div>
        </div>
      ))}
    </div>
  );
}

/** Honest state for a capability whose data source is not connected: which
 *  integration, its live status, why — and never a placeholder number. */
export function IntegrationNotice({ integration, title, children }: { integration: Integration | null | undefined; title?: string; children?: ReactNode }) {
  const { t, isEn } = usePrefs();
  const statusMap: Record<string, [string, 'ok' | 'warn' | 'error' | 'uncertain']> = {
    active: [t.statusActive, 'ok'],
    configured: [t.statusConfigured, 'ok'],
    stale: [t.statusStale, 'warn'],
    blocked: [t.statusBlocked, 'error'],
    not_configured: [t.statusNotConfigured, 'uncertain'],
    manual_only: [t.statusManualOnly, 'ok'],
  };
  const [label, tone] = statusMap[integration?.live_status ?? 'not_configured'] ?? [integration?.live_status ?? '—', 'uncertain'];
  const displayTitle = title ?? (isEn && integration?.name ? integration.name : (integration?.name_fa ?? t.dataConnection));
  const displayReason = (isEn && integration?.reason ? integration.reason : null) || integration?.reason_fa;

  return (
    <div className={`integration integration-${tone}`}>
      <div className="integration-head">
        <PlugZap size={18} />
        <strong>{displayTitle}</strong>
        <Tag tone={tone}>{label}</Tag>
      </div>
      {displayReason && <p>{displayReason}</p>}
      {children}
      {tone !== 'ok' && <small>{t.noMockDataNote}</small>}
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
  const { t } = usePrefs();
  return (
    <nav className="pager" aria-label={t.pagerAria}>
      <button type="button" className="btn-ghost" disabled={page <= 1} onClick={() => onPage(page - 1)}>{t.pagerPrev}</button>
      <span>{t.pagerPage} {fmt(page)}{total != null ? ` · ${fmt(total)} ${t.pagerItems}` : ''}</span>
      <button type="button" className="btn-ghost" disabled={!hasNext} onClick={() => onPage(page + 1)}>{t.pagerNext}</button>
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
  const { isEn } = usePrefs();
  const healthLabel: Record<Health, string> = {
    healthy: isEn ? 'Healthy' : 'سالم',
    fresh: isEn ? 'Fresh' : 'تازه',
    attention: isEn ? 'Attention' : 'نیازمند توجه',
    stopped: isEn ? 'Stopped' : 'متوقف',
    error: isEn ? 'Error' : 'خطادار',
    inactive: isEn ? 'Inactive' : 'غیرفعال',
  };
  return <span className={'status-pill status-' + health} title={title}><i />{label ?? healthLabel[health]}</span>;
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

const FIELD_TONE: Record<string, 'accent' | 'default' | 'muted' | 'error'> = {
  available: 'accent', full_syndicated: 'accent', approved: 'accent', pending: 'default', summary_only: 'default',
  pending_review: 'default', error: 'error', rejected: 'error', needs_review: 'error',
};

export function FieldStatus({ label, status, title }: { label: string; status?: string | null; title?: string }) {
  const { isEn } = usePrefs();
  const fieldLabels: Record<string, string> = {
    available: isEn ? 'Available' : 'موجود',
    pending: isEn ? 'Pending' : 'در صف',
    unavailable: isEn ? 'Unavailable' : 'ناموجود',
    error: isEn ? 'Error' : 'خطا',
    not_processed: isEn ? 'Not processed' : 'پردازش‌نشده',
    summary_only: isEn ? 'Summary only' : 'فقط خلاصه',
    full_syndicated: isEn ? 'Full text' : 'متن کامل',
    link_only: isEn ? 'Link only' : 'فقط پیوند',
    not_generated: isEn ? 'Not generated' : 'تولید نشده',
    provider_not_configured: isEn ? 'Provider not configured' : 'ارائه‌دهنده تنظیم نشده',
    needs_review: isEn ? 'Needs review' : 'نیازمند بازبینی',
    pending_review: isEn ? 'In review queue' : 'در صف بازبینی',
    approved: isEn ? 'Approved' : 'تأییدشده',
    rejected: isEn ? 'Rejected' : 'ردشده',
    not_applicable: '—',
    source_summary_missing: isEn ? 'Source summary missing' : 'خلاصه منبع موجود نیست',
  };
  const key = status || 'unavailable';
  return <Badge tone={FIELD_TONE[key] ?? 'muted'} title={title}>{label} · {fieldLabels[key] ?? key}</Badge>;
}

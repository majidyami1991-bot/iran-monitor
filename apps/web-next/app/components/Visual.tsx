'use client';
import { useState } from 'react';
import { catVar, hostOf, safeUrl } from '../design/format';

const GLYPH: Record<string, string> = {
  security_defense: 'ام', defense_industry: 'صد', regional_geopolitics: 'من', politics_governance: 'سی',
  diplomacy_international: 'دی', economy_trade_sanctions: 'اق', energy_infrastructure: 'ان', technology_cyber_ai: 'فن',
  aerospace_maritime: 'هو', society_human_rights: 'جا', environment_crisis: 'مح', other: '؟',
};

/** Neutral, generated placeholder used whenever no valid source image exists
 *  (or the publisher refuses it). Never a stock, random or AI-generated
 *  picture; it says plainly that the source image is unavailable. */
export function CategoryArt({ categoryId, label, monogram, compact = false, reason }: {
  categoryId?: string | null; label?: string | null; monogram?: string; compact?: boolean; reason?: string;
}) {
  const id = categoryId || 'other';
  const text = reason ?? 'تصویر منبع موجود نیست';
  return (
    <div className={compact ? 'art art-compact' : 'art'} style={{ ['--art' as string]: catVar(id) }} role="img"
      aria-label={label ? `${text} — نگاره دسته ${label}` : text} data-placeholder="true">
      <span className="art-glyph" aria-hidden="true">{monogram ?? GLYPH[id] ?? '؟'}</span>
      {!compact && <span className="art-label">{text}</span>}
    </div>
  );
}

/** The item's primary image, loaded from the publisher (never proxied or
 *  stored here). The frame keeps a fixed aspect ratio so nothing shifts while
 *  it loads (skeleton) or if it fails (placeholder). Alt text is the
 *  publisher's own, or empty — never invented. */
export function ItemImage({ src, alt, categoryId, categoryLabel, compact, credit = true, priority = false, width, height }: {
  src: string | null | undefined; alt?: string | null; categoryId?: string | null; categoryLabel?: string | null;
  compact?: boolean; credit?: boolean; priority?: boolean; width?: number | null; height?: number | null;
}) {
  const [state, setState] = useState<'loading' | 'loaded' | 'failed'>('loading');
  const url = safeUrl(src);
  if (!url || !url.startsWith('https://')) {
    return <CategoryArt categoryId={categoryId} label={categoryLabel} compact={compact} />;
  }
  if (state === 'failed') {
    return <CategoryArt categoryId={categoryId} label={categoryLabel} compact={compact} reason="تصویر منبع بارگذاری نشد" />;
  }
  return (
    <figure className={state === 'loading' ? 'img img-loading' : 'img'} aria-busy={state === 'loading' || undefined}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={url} alt={alt || ''} loading={priority ? 'eager' : 'lazy'} decoding="async" referrerPolicy="no-referrer"
        {...(priority ? { fetchPriority: 'high' as const } : {})}
        width={width ?? undefined} height={height ?? undefined}
        onLoad={() => setState('loaded')} onError={() => setState('failed')} />
      {credit && state === 'loaded' && <figcaption dir="ltr">© {hostOf(url)}</figcaption>}
    </figure>
  );
}

'use client';
import { useState } from 'react';
import { catVar, hostOf, safeUrl } from '../design/format';

const GLYPH: Record<string, string> = {
  security_defense: 'ام', defense_industry: 'صد', regional_geopolitics: 'من', politics_governance: 'سی',
  diplomacy_international: 'دی', economy_trade_sanctions: 'اق', energy_infrastructure: 'ان', technology_cyber_ai: 'فن',
  aerospace_maritime: 'هو', society_human_rights: 'جا', environment_crisis: 'مح', other: '؟',
};

/** Internal, generated artwork used whenever no verified article image
 *  exists. Never a stock photo or an unrelated image. */
export function CategoryArt({ categoryId, label, monogram, compact = false }: { categoryId?: string | null; label?: string | null; monogram?: string; compact?: boolean }) {
  const id = categoryId || 'other';
  return (
    <div className={compact ? 'art art-compact' : 'art'} style={{ ['--art' as string]: catVar(id) }} role="img"
      aria-label={label ? `نگاره دسته ${label} (تصویر خبر در دسترس نیست)` : 'تصویر خبر در دسترس نیست'}>
      <span className="art-glyph" aria-hidden="true">{monogram ?? GLYPH[id] ?? '؟'}</span>
      {!compact && label && <span className="art-label">{label}</span>}
    </div>
  );
}

/** A verified-or-unverified article image served from the publisher (never
 *  downloaded or proxied), with attribution; falls back to CategoryArt if the
 *  URL is unsafe or the publisher refuses the request. */
export function ItemImage({ src, alt, categoryId, categoryLabel, compact, credit = true }: {
  src: string | null | undefined; alt?: string | null; categoryId?: string | null; categoryLabel?: string | null; compact?: boolean; credit?: boolean;
}) {
  const [broken, setBroken] = useState(false);
  const url = safeUrl(src);
  if (!url || broken) return <CategoryArt categoryId={categoryId} label={categoryLabel} compact={compact} />;
  return (
    <figure className="img">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={url} alt={alt || ''} loading="lazy" decoding="async" referrerPolicy="no-referrer" onError={() => setBroken(true)} />
      {credit && <figcaption dir="ltr">© {hostOf(url)}</figcaption>}
    </figure>
  );
}

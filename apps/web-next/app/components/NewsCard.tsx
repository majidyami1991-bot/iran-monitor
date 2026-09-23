'use client';
import Link from 'next/link';
import { ShieldCheck, Image as ImageIcon } from 'lucide-react';
import type { NewsListItem } from './news-types';
import { fmtRelative, isPersian, safeUrl, sourceColor } from '../design/format';
import { Badge, SourceMark } from '../design/ui';

/** The one news-item card used in every list context: the dashboard's
 * "جریان اخبار" panel, the news stream, and a source's "latest items". Shows
 * a short excerpt only — never the full extracted body, which belongs on the
 * detail page. This is deliberate: a stream the reader must scan in seconds
 * cannot be built from stacked full articles. */
export function NewsCard({ item, now }: { item: NewsListItem; now: number }) {
  const href = '/news/' + encodeURIComponent(item.item_id);
  const sourceHref = '/sources/' + encodeURIComponent(item.source_id);
  const color = sourceColor(item.source_id);
  const sourceLabel = item.source_name || item.hostname || 'نام منبع ثبت نشده';
  const isNew = item.published_at != null && now - Date.parse(item.published_at) < 86400000 && now >= Date.parse(item.published_at);

  const faSummary = item.summary_fa;
  const faStatus = item.summary_fa_status || 'pending';
  const enSummary = item.summary;

  return (
    <article className="news-card">
      {item.lead_image_url ? (
        <img className="news-card-thumb" src={item.lead_image_url} alt={item.lead_image_alt || ''} loading="lazy" referrerPolicy="no-referrer"
          onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />
      ) : (
        <div className="news-card-thumb news-card-thumb-empty" aria-hidden><ImageIcon size={18} strokeWidth={1.5} /></div>
      )}
      <div className="news-card-body">
        <div className="news-card-meta">
          <Link href={sourceHref} className="news-card-source">
            <SourceMark name={sourceLabel} color={color} />
            <span>{sourceLabel}</span>
          </Link>
          <time dateTime={item.published_at || item.fetched_at || undefined}>{fmtRelative(item.published_at || item.fetched_at, now)}</time>
          {isNew && <Badge tone="accent">جدید</Badge>}
        </div>
        <h3 dir={isPersian(item.title) ? 'rtl' : 'ltr'}><Link href={href}>{item.title}</Link></h3>
        {faSummary ? (
          <p className="news-card-excerpt" dir="rtl">{faSummary}</p>
        ) : (
          <p className="news-card-excerpt news-card-excerpt-pending" dir="ltr">
            {enSummary || (item.summary_available === false ? 'این منبع خلاصه‌ای در خوراک منتشر نکرده است.' : 'خلاصه در دسترس نیست.')}
          </p>
        )}
        <footer className="news-card-footer">
          {item.category && <Badge>{item.category}</Badge>}
          <span className="news-card-provenance"><ShieldCheck size={12} />{item.provenance_status === 'COMPLETE' ? 'منشأ کامل' : 'منشأ ناقص'}</span>
          <Link href={href} className="news-card-detail">جزئیات</Link>
          {safeUrl(item.canonical_url) && <a href={safeUrl(item.canonical_url)} target="_blank" rel="noopener noreferrer">منبع اصلی</a>}
        </footer>
      </div>
    </article>
  );
}

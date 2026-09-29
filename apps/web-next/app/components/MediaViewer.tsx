'use client';
import { useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { useApi } from '../design/useApi';
import { fmt, hostOf, safeUrl } from '../design/format';
import { ItemImage, CategoryArt } from './Visual';

interface M {
  id: string; url: string; width: number | null; height: number | null; alt_text: string | null; caption: string | null;
  credit: string | null; source_method: string | null; source_field: string | null; source_hostname: string | null;
  is_primary: boolean; validation_status: string | null;
}

const METHOD_FA: Record<string, string> = {
  rss_media_content: 'خوراک RSS · media:content', rss_media_thumbnail: 'خوراک RSS · media:thumbnail',
  rss_enclosure: 'خوراک RSS · enclosure', rss_content_html: 'خوراک RSS · تصویر داخل متن', rss_description_html: 'خوراک RSS · تصویر خلاصه',
  article_open_graph: 'فراداده صفحه مقاله · Open Graph', article_json_ld: 'فراداده صفحه مقاله · JSON-LD', article_html: 'صفحه مقاله', manual: 'ثبت دستی',
};
const STATUS_FA: Record<string, string> = { valid: 'راستی‌آزمایی‌شده', unknown: 'اعلام‌شده توسط ناشر، راستی‌آزمایی‌نشده', pending: 'در انتظار راستی‌آزمایی' };

/** Primary image + accessible gallery for one item, from /news/{id}/media.
 *  Rejected, blocked and unreachable media are never shown; when the item's
 *  only image is blocked or unreachable the reader is told so and gets the
 *  article link instead. */
export function MediaViewer({ itemId, categoryId, categoryLabel, mediaStatus, articleUrl }: {
  itemId: string; categoryId: string | null; categoryLabel: string | null; mediaStatus: string; articleUrl?: string;
}) {
  const q = useApi<{ primary_media: M | null; media: M[] }>(`news/${encodeURIComponent(itemId)}/media`, [itemId]);
  const [sel, setSel] = useState<string | null>(null);
  const media = q.data?.media ?? [];
  const current = media.find((m) => m.id === sel) ?? q.data?.primary_media ?? null;
  const link = safeUrl(articleUrl);

  if (!q.data) return <div className="detail-hero"><span className="bone" style={{ height: '100%' }} /></div>;
  if (!current) {
    const reason = mediaStatus === 'blocked' ? 'منبع اجازه نمایش تصویر را نمی‌دهد' : mediaStatus === 'unreachable' ? 'تصویر منبع در دسترس نیست' : 'تصویر منبع موجود نیست';
    return (
      <figure className="media-figure">
        <div className="detail-hero"><CategoryArt categoryId={categoryId} label={categoryLabel} reason={reason} /></div>
        {(mediaStatus === 'blocked' || mediaStatus === 'unreachable') && link && (
          <figcaption className="media-caption">{reason}. <a href={link} target="_blank" rel="noopener noreferrer nofollow" className="sec-link">دیدن تصویر در مقاله اصلی<ExternalLink size={13} /></a></figcaption>
        )}
      </figure>
    );
  }
  return (
    <figure className="media-figure">
      <div className="detail-hero">
        <ItemImage key={current.id} src={current.url} alt={current.alt_text} categoryId={categoryId} categoryLabel={categoryLabel}
          priority width={current.width} height={current.height} credit={false} />
      </div>
      <figcaption className="media-caption">
        {current.caption && <span>{current.caption}</span>}
        {current.credit && <span>اعتبار تصویر: <bdi>{current.credit}</bdi></span>}
        <small>
          منبع تصویر: <bdi dir="ltr">{current.source_hostname ?? hostOf(current.url)}</bdi>
          {current.source_method && <> · {METHOD_FA[current.source_method] ?? current.source_method}</>}
          {current.width && current.height ? <> · {fmt(current.width)}×{fmt(current.height)}</> : null}
          {' · '}{STATUS_FA[current.validation_status ?? 'unknown'] ?? current.validation_status}
          {!current.alt_text && ' · متن جایگزین توسط ناشر ثبت نشده'}
        </small>
      </figcaption>
      {media.length > 1 && (
        <ul className="gallery" aria-label={`گالری تصاویر خبر (${fmt(media.length)})`}>
          {media.map((m, i) => (
            <li key={m.id}>
              <button type="button" aria-pressed={m.id === current.id} onClick={() => setSel(m.id)}
                aria-label={`تصویر ${fmt(i + 1)} از ${fmt(media.length)}${m.alt_text ? `: ${m.alt_text}` : ''}`}>
                <span className="media-thumb"><ItemImage src={m.url} alt="" categoryId={categoryId} compact credit={false} /></span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </figure>
  );
}

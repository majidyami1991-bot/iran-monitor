'use client';
import Link from 'next/link';
import { ExternalLink, Layers, Newspaper } from 'lucide-react';
import { fmtDateTime, fmtRelative, safeUrl } from '../design/format';
import { AiTag, CategoryTag, Tag } from '../design/ui';
import { AVAILABILITY_FA, IMPORTANCE_FA, VERIFICATION_FA, VERIFICATION_TONE, type XPost } from './lib';

/** All user- or X-originated text is rendered as React text nodes (escaped);
 *  nothing here uses dangerouslySetInnerHTML. */
export function PostCard({ p, now, topicLabel, full = false }: { p: XPost; now: number; topicLabel?: (id: string) => string; full?: boolean }) {
  const when = p.published_at ?? p.manually_registered_at;
  const url = safeUrl(p.post_url);
  return (
    <article className="x-post">
      <header className="x-post-head">
        <Link href={`/social/accounts/${p.source_id}`} className="x-handle" dir="ltr">{p.author_handle}</Link>
        <time dateTime={when} title={p.published_at ? `انتشار: ${fmtDateTime(p.published_at)}` : `ثبت دستی: ${fmtDateTime(p.manually_registered_at)}`}>
          {p.published_at ? fmtRelative(p.published_at, now) : `ثبت ${fmtRelative(p.manually_registered_at, now)} (زمان انتشار ثبت نشده)`}
        </time>
      </header>
      <div className="card-flags">
        {p.importance !== 'low' && <Tag tone={p.importance === 'high' ? 'urgent' : 'warn'}>{IMPORTANCE_FA[p.importance]}</Tag>}
        {p.topic_id && <CategoryTag id={p.topic_id} label={topicLabel ? topicLabel(p.topic_id) : p.topic_id} />}
        <Tag tone={VERIFICATION_TONE[p.verification_status] ?? 'uncertain'}>{VERIFICATION_FA[p.verification_status] ?? p.verification_status}</Tag>
        <Tag tone={p.availability_status === 'text_recorded' ? 'info' : 'uncertain'}>{AVAILABILITY_FA[p.availability_status] ?? p.availability_status}</Tag>
      </div>
      {p.translated_text_fa && (
        <div className="x-text">
          <p>{p.translated_text_fa}</p>
          <AiTag>ترجمه ماشینی · بازبینی انسانی نشده</AiTag>
        </div>
      )}
      {p.summary_fa && <div className="x-text"><p className="muted">{p.summary_fa}</p><AiTag>خلاصه هوش مصنوعی</AiTag></div>}
      {p.original_text
        ? <blockquote className="x-original" dir="auto" style={full ? undefined : { WebkitLineClamp: 5 }}>{p.original_text}</blockquote>
        : <p className="muted">متن محلی ثبت نشده است؛ فقط پیوند رسمی پست نگه داشته شده است.</p>}
      {p.analyst_note && <p className="x-note"><b>توضیح تحلیلگر:</b> {p.analyst_note}</p>}
      <footer className="x-post-foot">
        <span className="muted">منشأ: ثبت دستی توسط <bdi>{p.provenance_json?.registered_by ?? '—'}</bdi>{p.original_text ? ' · متن واردشده توسط تحلیلگر (خروجی مستقیم X نیست)' : ''}</span>
        <span className="x-links">
          {p.event_id && <Link href={`/events/${p.event_id}`} className="tag tag-info"><Layers size={12} />رویداد</Link>}
          {p.related_item_id && <Link href={`/news/${p.related_item_id}`} className="tag tag-info"><Newspaper size={12} />خبر مرتبط</Link>}
          {!full && <Link href={`/social/posts/${p.post_id}`} className="sec-link">جزئیات</Link>}
          {url && <a href={url} target="_blank" rel="noopener noreferrer nofollow" className="sec-link">مشاهده در X<ExternalLink size={12} /></a>}
        </span>
      </footer>
    </article>
  );
}

'use client';
import Link from 'next/link';
import { Layers } from 'lucide-react';
import type { FeedItem } from '../design/types';
import { fmt, fmtRelative, fmtDateTime, sourceColor } from '../design/format';
import { usePrefs } from '../design/prefs';
import { BreakingTag, CategoryTag, ImportanceTag, SourceMark, TranslationTag } from '../design/ui';
import { ItemImage } from './Visual';

/** Which text leads. Persian leads only when a stored translation exists and
 *  the viewer prefers Persian; otherwise the publisher's original, marked LTR. */
export function useHeadline(item: FeedItem) {
  const { contentLang } = usePrefs();
  const fa = contentLang === 'fa' && item.title_fa;
  return {
    title: fa ? item.title_fa! : item.title,
    titleDir: fa ? 'rtl' : 'ltr',
    original: fa ? item.title : null,
    summary: contentLang === 'fa' && item.summary_fa ? item.summary_fa : item.summary,
    summaryDir: contentLang === 'fa' && item.summary_fa ? 'rtl' : 'ltr',
  } as const;
}

function Meta({ item, now, withSource = true }: { item: FeedItem; now: number; withSource?: boolean }) {
  return (
    <div className="card-meta">
      {withSource && (
        <Link href={`/sources/${item.source_id}`} className="card-source">
          <SourceMark name={item.source_name} color={sourceColor(item.source_id)} size={20} />
          <bdi>{item.source_name}</bdi>
        </Link>
      )}
      <time dateTime={item.published_at ?? undefined} title={item.published_at ? `انتشار: ${fmtDateTime(item.published_at)}` : 'زمان انتشار در خوراک منبع ثبت نشده'}>
        {item.published_at ? fmtRelative(item.published_at, now) : 'زمان انتشار ثبت نشده'}
      </time>
    </div>
  );
}

function Summary({ item, text, dir, lines = 3 }: { item: FeedItem; text: string | null; dir: 'ltr' | 'rtl'; lines?: number }) {
  if (!text) {
    return <p className="card-summary card-summary-missing">{item.summary_available === false ? 'منبع برای این خبر خلاصه‌ای منتشر نکرده است.' : 'خلاصه‌ای برای این خبر ثبت نشده است.'}</p>;
  }
  return <p className="card-summary" dir={dir} style={{ WebkitLineClamp: lines }}>{text}</p>;
}

export function NewsCard({ item, now, variant = 'standard' }: { item: FeedItem; now: number; variant?: 'lead' | 'standard' | 'compact' | 'row' }) {
  const h = useHeadline(item);
  const href = `/news/${item.item_id}`;

  if (variant === 'compact') {
    return (
      <article className="card-compact">
        <div className="card-flags">{item.breaking && <BreakingTag />}<CategoryTag id={item.category_id} label={item.category_label} /></div>
        <h3 dir={h.titleDir}><Link href={href}>{h.title}</Link></h3>
        <Meta item={item} now={now} />
      </article>
    );
  }

  if (variant === 'row') {
    return (
      <article className="card-row">
        <Link href={href} className="card-row-media" tabIndex={-1} aria-hidden="true">
          <ItemImage src={item.primary_media?.url} alt={item.primary_media?.alt_text} categoryId={item.category_id} categoryLabel={item.category_label}
            compact credit={false} width={item.primary_media?.width} height={item.primary_media?.height} />
        </Link>
        <div className="card-row-body">
          <div className="card-flags">
            {item.breaking && <BreakingTag />}
            <CategoryTag id={item.category_id} label={item.category_label} />
            <ImportanceTag level={item.importance_level} />
            {item.event_members > 1 && <Link href={`/events/${item.event_id}`} className="tag tag-info"><Layers size={12} />{fmt(item.event_members)} خبر در رویداد</Link>}
          </div>
          <h3 dir={h.titleDir}><Link href={href}>{h.title}</Link></h3>
          {h.original && <p className="card-original" dir="ltr">{h.original}</p>}
          <Summary item={item} text={h.summary} dir={h.summaryDir} lines={2} />
          <div className="card-foot">
            <Meta item={item} now={now} />
            <TranslationTag status={item.title_fa_status} review={item.title_fa_review} />
          </div>
        </div>
      </article>
    );
  }

  return (
    <article className={variant === 'lead' ? 'card card-lead' : 'card'}>
      <Link href={href} className="card-media" tabIndex={-1} aria-hidden="true">
        <ItemImage src={item.primary_media?.url} alt={item.primary_media?.alt_text} categoryId={item.category_id} categoryLabel={item.category_label}
          priority={variant === 'lead'} width={item.primary_media?.width} height={item.primary_media?.height} />
      </Link>
      <div className="card-body">
        <div className="card-flags">
          {item.breaking && <BreakingTag />}
          <CategoryTag id={item.category_id} label={item.category_label} />
          <ImportanceTag level={item.importance_level} />
        </div>
        <h3 dir={h.titleDir}><Link href={href}>{h.title}</Link></h3>
        {h.original && <p className="card-original" dir="ltr">{h.original}</p>}
        <Summary item={item} text={h.summary} dir={h.summaryDir} lines={variant === 'lead' ? 4 : 3} />
        <div className="card-foot">
          <Meta item={item} now={now} />
          <TranslationTag status={item.title_fa_status} review={item.title_fa_review} />
        </div>
        {item.event_members > 1 && (
          <Link href={`/events/${item.event_id}`} className="card-event"><Layers size={14} />بخشی از رویدادی با {fmt(item.event_members)} خبر از {fmt(item.event_sources)} منبع</Link>
        )}
      </div>
    </article>
  );
}

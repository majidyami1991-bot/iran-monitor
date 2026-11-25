'use client';
import Link from 'next/link';
import { Layers } from 'lucide-react';
import type { FeedItem } from '../design/types';
import { fmt, fmtRelative, fmtDateTime, sourceColor } from '../design/format';
import { usePrefs } from '../design/prefs';
import { BreakingTag, CategoryTag, ImportanceTag, SourceMark, TranslationTag } from '../design/ui';
import { ItemImage } from './Visual';

/** Which text leads. 'fa': the stored Persian translation when it passed QC
 *  (translated_auto / reviewed), else the publisher's original. 'en': the
 *  original. 'bi': the original leads and the Persian follows — a QC-warning
 *  translation only here, visibly marked. A QC-failed translation never
 *  reaches the client. The original is always kept and shown. */
export function useHeadline(item: FeedItem) {
  const { contentLang } = usePrefs();
  const fa = contentLang === 'fa' && item.title_fa;
  const bi = false;
  return {
    title: fa ? item.title_fa! : item.title,
    titleDir: fa ? 'rtl' : 'ltr',
    original: fa ? item.title : null,
    summary: contentLang === 'fa' && item.summary_fa ? item.summary_fa : item.summary,
    summaryDir: contentLang === 'fa' && item.summary_fa ? 'rtl' : 'ltr',
    bi,
    biTitle: null,
    biTitleWarn: false,
  } as const;
}

/** Persian line under the original in bilingual mode (or the reason it is absent). */
export function BiLine({ text, warn, status }: { text: string | null; warn: boolean; status: string }) {
  const { t } = usePrefs();
  if (text) return <p className={warn ? 'card-fa card-fa-warn' : 'card-fa'} dir="rtl">{warn && <span className="fa-warn-mark" title={t.cardFaWarnTitle}>⚠</span>}{text}</p>;
  const why = status === 'qc_failed' ? t.cardFaQcFailed
    : status === 'translation_error' ? t.cardFaTranslationError
    : status === 'not_required' ? null : t.cardFaPending;
  return why ? <p className="card-fa card-fa-missing" dir="rtl">{why}</p> : null;
}

function Meta({ item, now, withSource = true }: { item: FeedItem; now: number; withSource?: boolean }) {
  const { t } = usePrefs();
  return (
    <div className="card-meta">
      {withSource && (
        <Link href={`/sources/${item.source_id}`} className="card-source">
          <SourceMark name={item.source_name} color={sourceColor(item.source_id)} size={20} />
          <bdi>{item.source_name}</bdi>
        </Link>
      )}
      <time dateTime={item.published_at ?? undefined} title={item.published_at ? `${t.cardPublishedAt}${fmtDateTime(item.published_at)}` : t.cardPubNotRecorded}>
        {item.published_at ? fmtRelative(item.published_at, now) : t.cardPubNotRecordedShort}
      </time>
    </div>
  );
}

function Summary({ item, text, dir, lines = 3 }: { item: FeedItem; text: string | null; dir: 'ltr' | 'rtl'; lines?: number }) {
  const { t } = usePrefs();
  if (!text) {
    return <p className="card-summary card-summary-missing">{item.summary_available === false ? t.cardSummaryMissingPublisher : t.cardSummaryMissingGeneric}</p>;
  }
  return <p className="card-summary" dir={dir} style={{ WebkitLineClamp: lines }}>{text}</p>;
}

export function NewsCard({ item, now, variant = 'standard' }: { item: FeedItem; now: number; variant?: 'lead' | 'standard' | 'compact' | 'row' }) {
  const { t } = usePrefs();
  const h = useHeadline(item);
  const href = `/news/${item.item_id}`;

  if (variant === 'compact') {
    return (
      <article className="card-compact">
        <div className="card-flags">{item.breaking && <BreakingTag />}<CategoryTag id={item.category_id} label={item.category_label} /></div>
        <h3 dir={h.titleDir}><Link href={href}>{h.title}</Link></h3>
        {h.bi && <BiLine text={h.biTitle} warn={h.biTitleWarn} status={item.title_fa_status} />}
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
            {item.event_members > 1 && <Link href={`/events/${item.event_id}`} className="tag tag-info"><Layers size={12} />{fmt(item.event_members)} {t.cardEventArticles}</Link>}
          </div>
          <h3 dir={h.titleDir}><Link href={href}>{h.title}</Link></h3>
          {h.original && <p className="card-original" dir="ltr">{h.original}</p>}
          {h.bi && <BiLine text={h.biTitle} warn={h.biTitleWarn} status={item.title_fa_status} />}
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
        {h.bi && <BiLine text={h.biTitle} warn={h.biTitleWarn} status={item.title_fa_status} />}
        <Summary item={item} text={h.summary} dir={h.summaryDir} lines={variant === 'lead' ? 4 : 3} />
        <div className="card-foot">
          <Meta item={item} now={now} />
          <TranslationTag status={item.title_fa_status} review={item.title_fa_review} />
        </div>
        {item.event_members > 1 && (
          <Link href={`/events/${item.event_id}`} className="card-event"><Layers size={14} />{t.cardEventPartPrefix} {fmt(item.event_members)} {t.cardEventArticlesWord} {fmt(item.event_sources)} {t.cardEventSourcesWord}</Link>
        )}
      </div>
    </article>
  );
}

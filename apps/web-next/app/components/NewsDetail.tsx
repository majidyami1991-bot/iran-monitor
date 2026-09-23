'use client';
import { useState } from 'react';
import Link from 'next/link';
import { ShieldCheck, ExternalLink, FileText } from 'lucide-react';
import type { NewsDetailItem } from './news-types';
import { fmtDateTime, isPersian, safeUrl, sourceColor } from '../design/format';
import { Badge, EmptyState, FieldStatus, SourceMark, Tabs } from '../design/ui';

function SafeImage({ url, alt }: { url: string; alt?: string | null }) {
  const [broken, setBroken] = useState(false);
  if (broken) return <div className="news-image-broken">تصویر در دسترس نیست.</div>;
  return <img className="news-detail-image" src={url} alt={alt || ''} loading="lazy" referrerPolicy="no-referrer" onError={() => setBroken(true)} />;
}

export function NewsDetail({ item }: { item: NewsDetailItem }) {
  const [tab, setTab] = useState('translation');
  const sourceLabel = item.source_name || item.hostname || 'نام منبع ثبت نشده';
  const color = sourceColor(item.source_id);
  const images = item.media?.images || [];
  const documents = item.media?.documents || [];
  const lead = images[0];
  const gallery = images.slice(1);
  const titleFa = item.translations?.title;
  const summaryFa = item.translations?.summary;
  const bodyFa = item.translations?.body;
  const content = item.content;
  const bodyAvailable = content?.display_policy === 'full_syndicated' && content.original_text;

  return (
    <article>
      <div className="news-detail-meta">
        <Link href={'/sources/' + encodeURIComponent(item.source_id)} className="news-card-source">
          <SourceMark name={sourceLabel} color={color} />
          <span>{sourceLabel}</span>
        </Link>
        {item.category && <Badge>{item.category}</Badge>}
        <span className="news-detail-time">انتشار: {fmtDateTime(item.published_at)}</span>
        <span className="news-detail-time">دریافت: {fmtDateTime(item.fetched_at)}</span>
      </div>

      {titleFa?.status === 'available' && titleFa.text && (
        <h2 className="news-detail-title-fa" dir="rtl">{titleFa.text} <span className="machine-tag">ترجمه ماشینی</span></h2>
      )}
      <h1 className="news-detail-title-en" dir={isPersian(item.title) ? 'rtl' : 'ltr'}>{item.title}</h1>

      {lead && (
        <figure className="news-detail-figure">
          <SafeImage url={lead.url} alt={lead.alt_text} />
          <figcaption>
            {lead.alt_text || 'بدون توضیح ثبت‌شده از منبع'}
            <span className="news-image-verify">{lead.verification_status === 'unverified' ? 'راستی‌آزمایی‌نشده' : 'راستی‌آزمایی‌شده'}</span>
          </figcaption>
        </figure>
      )}

      <div className="news-detail-fields">
        <FieldStatus label="عنوان فارسی" status={titleFa?.status} title="ترجمه ماشینی عنوان" />
        <FieldStatus label="خلاصه فارسی" status={summaryFa?.status} title="ترجمه یا تولید ماشینی خلاصه" />
        <FieldStatus label="متن اصلی" status={content?.extraction_status} title="متن استخراج‌شده از خوراک منبع" />
      </div>

      <Tabs value={tab} onChange={setTab} items={[
        ['translation', 'ترجمه فارسی'],
        ['original', 'متن اصلی'],
        ['media', `تصاویر و اسناد${images.length + documents.length ? ' (' + (images.length + documents.length) + ')' : ''}`],
        ['evidence', 'منشأ و شواهد'],
      ]} />

      <div className="news-detail-panel">
        {tab === 'translation' && (
          bodyFa?.status === 'available' && bodyFa.text ? (
            <div dir="rtl" className="news-detail-text">
              {bodyFa.text.split('\n').filter(Boolean).map((p, i) => <p key={i}>{p}</p>)}
              <p className="news-detail-provider">ارائه‌دهنده: {bodyFa.provider} · مدل: {bodyFa.model} <span className="machine-tag">ترجمه ماشینی</span></p>
            </div>
          ) : summaryFa?.status === 'available' && summaryFa.text ? (
            <div dir="rtl" className="news-detail-text">
              <p>{summaryFa.text} <span className="machine-tag">ترجمه ماشینی</span></p>
              <p className="chart-caption">ترجمه کامل متن هنوز تولید نشده؛ فقط خلاصه فارسی در دسترس است.</p>
            </div>
          ) : (
            <EmptyState title="ترجمه فارسی هنوز آماده نیست">
              {bodyFa?.error ? `خطای ثبت‌شده: ${bodyFa.error}` : 'ارائه‌دهنده ترجمه هنوز فعال نشده است؛ تا فعال‌سازی متنی تولید نمی‌شود.'}
            </EmptyState>
          )
        )}
        {tab === 'original' && (
          bodyAvailable ? (
            <div dir="ltr" className="news-detail-text news-detail-text-ltr">
              {content!.original_text!.split('\n').filter(Boolean).map((p, i) => <p key={i}>{p}</p>)}
              <p className="news-detail-provider">{content!.text_chars} نویسه · روش استخراج: {content!.extraction_method || 'ثبت نشده'}</p>
            </div>
          ) : (
            <EmptyState title={content?.display_policy === 'summary_only' ? 'متن کامل در این پلتفرم نمایش داده نمی‌شود' : 'متن کامل برای این رکورد ذخیره نشده است'}>
              {content?.display_policy === 'summary_only'
                ? 'منبع فقط خلاصه را در خوراک منتشر کرده است؛ برای متن کامل به نشانی اصلی مراجعه کنید.'
                : content?.note || 'این رکورد پیش از افزودن استخراج متن ثبت شده است.'}
            </EmptyState>
          )
        )}
        {tab === 'media' && (
          gallery.length || documents.length ? (
            <>
              {gallery.length > 0 && (
                <div className="news-detail-gallery">
                  {gallery.map((m) => <SafeImage key={m.media_id} url={m.url} alt={m.alt_text} />)}
                </div>
              )}
              {documents.length > 0 && (
                <ul className="news-detail-documents">
                  {documents.map((d) => (
                    <li key={d.media_id}>
                      <FileText size={15} />
                      <a href={safeUrl(d.url)} target="_blank" rel="noopener noreferrer" dir="ltr">{d.url.split('/').pop()}</a>
                      <span>{d.mime_type}</span>
                      <Badge tone="muted">{d.verification_status === 'unverified' ? 'راستی‌آزمایی‌نشده' : 'راستی‌آزمایی‌شده'}</Badge>
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <EmptyState title="رسانه اضافی برای این خبر ثبت نشده">تصاویر و اسناد فقط از محتوای خوراک منبع استخراج می‌شوند.</EmptyState>
          )
        )}
        {tab === 'evidence' && (
          <div className="news-detail-evidence">
            <p><ShieldCheck size={14} /> وضعیت منشأ: {item.provenance_status === 'COMPLETE' ? 'کامل' : 'نیازمند بررسی'}</p>
            <p>شناسه فنی خبر: <span className="mono">{item.item_id}</span></p>
            <p>شناسه منبع: <span className="mono">{item.source_id}</span></p>
            {item.feed_url && <p>خوراک منبع: <span className="mono" dir="ltr">{item.feed_url}</span></p>}
            {safeUrl(item.canonical_url) && (
              <p><a href={safeUrl(item.canonical_url)} target="_blank" rel="noopener noreferrer" className="btn btn-secondary">مشاهده منبع اصلی <ExternalLink size={14} /></a></p>
            )}
          </div>
        )}
      </div>
    </article>
  );
}

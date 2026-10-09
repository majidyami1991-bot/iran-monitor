'use client';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ExternalLink, FileText, Rss, Clock3, Database, ShieldCheck, Link2, History, Layers } from 'lucide-react';
import { Shell } from '../../design/Shell';
import { useApi, useNow } from '../../design/useApi';
import type { FeedItem } from '../../design/types';
import { fmt, fmtDateTime, fmtPercent, fmtRelative, hostOf, safeUrl, sourceColor } from '../../design/format';
import { usePrefs } from '../../design/prefs';
import { BreakingTag, CategoryTag, Empty, Failure, ImportanceTag, SourceMark, Tag, TranslationTag, Bone, CardBones, MACHINE_LABEL } from '../../design/ui';
import { useEffect, useState } from 'react';
import type { TranslationQc } from '../../design/types';
import { MediaViewer } from '../../components/MediaViewer';
import { NewsCard } from '../../components/NewsCard';

interface Media { media_id: string; kind: string; url: string; mime_type: string | null; byte_size: number | null; alt_text: string | null; relevance: string; verification_status: string }
interface Detail {
  item_id: string; title: string; summary: string | null; canonical_url: string; published_at: string | null; fetched_at: string | null; first_seen_at: string | null;
  source_name: string | null; hostname: string; source_type: string; feed_url: string | null; provenance_status: string; content_language: string | null; external_guid: string | null;
  content: { extraction_status: string; display_policy: string; original_text: string | null; text_chars: number; original_text_withheld_reason?: string; extraction_method: string | null };
  translations: Record<string, { status: string; text: string | null; provider: string | null; model: string | null; updated_at: string | null }>;
  media: { images: Media[]; documents: Media[]; filtered_out: { url: string; relevance: string }[] };
  key_points: { point_index: number; text_fa: string; evidence_span: string | null; evidence_verified: boolean }[];
  provenance: { feed_url: string | null; execution_reference: string | null; evidence_status: string }[];
}
interface Context {
  item: FeedItem;
  assignment: null | { category_id: string; category_label: string; confidence: number | null; secondary: { id: string; label: string; score: number }[];
    subtopics: { id: string; label: string; parent: string }[]; evidence: string[]; other_reason_code: string | null; method: string; human_locked: boolean; taxonomy_version: string };
  other_reason_label: string | null;
  history: { taxonomy_version: string; category_label: string; change_kind: string; recorded_at: string; confidence: number | null }[];
  legacy_classification: { category_label: string; taxonomy_version: string } | null;
  event_items: { item_id: string; title: string; published_at: string | null; source_name: string }[];
  same_topic: FeedItem[];
  importance_rule: { id: string; description_fa: string };
}

const POLICY: Record<string, string> = {
  full_syndicated: 'متن کامل در خوراک خود ناشر منتشر شده است.',
  summary_only: 'ناشر فقط خلاصه را در خوراک منتشر کرده است؛ متن کامل بازنشر نمی‌شود.',
  link_only: 'ناشر متن را در خوراک منتشر نکرده است؛ فقط پیوند به منبع نمایش داده می‌شود.',
};
const CHANGE: Record<string, string> = { assigned: 'تخصیص اولیه', reclassified: 'بازطبقه‌بندی', human_override: 'اصلاح انسانی' };

function sizeLabel(n: number | null) {
  if (!n) return 'حجم نامشخص';
  return n > 1048576 ? `${fmt(Math.round(n / 104857.6) / 10)} مگابایت` : `${fmt(Math.round(n / 1024))} کیلوبایت`;
}

export function NewsDetailPage() {
  const { id } = useParams<{ id: string }>();
  const d = useApi<Detail>('news/' + encodeURIComponent(id), [id]);
  const c = useApi<Context>(`feed/${encodeURIComponent(id)}/context`, [id]);
  const now = useNow();
  const { contentLang } = usePrefs();
  // The translation appears without a manual refresh: poll while it is queued or running.
  const waiting = ['translation_pending', 'processing', 'pending'].includes(c.data?.item.title_fa_status ?? '')
    || ['translation_pending', 'processing', 'pending'].includes(c.data?.item.summary_fa_status ?? '');
  useEffect(() => {
    if (!waiting) return;
    const t = setInterval(() => { c.reload(); }, 20000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [waiting, id]);

  if (d.error || c.error) return <Shell><Failure onRetry={() => { d.reload(); c.reload(); }}>این خبر پیدا نشد یا دریافت آن ناموفق بود.</Failure></Shell>;
  // Loading skeleton mirrors the final layout (breadcrumb, flags, title,
  // meta, 16:9 hero, side panels) so content arriving does not shift it.
  if (!d.data || !c.data) return (
    <Shell>
      <Bone h={16} w="18%" />
      <div className="detail" aria-busy="true">
        <div className="detail-main">
          <Bone h={20} w="40%" /><Bone h={34} w="85%" /><Bone h={34} w="55%" /><Bone h={16} w="60%" />
          <div className="detail-hero"><span className="bone" /></div>
          <div className="bilingual"><Bone h={180} /><Bone h={180} /></div>
        </div>
        <aside className="side"><Bone h={320} r={14} /><Bone h={260} r={14} /></aside>
      </div>
    </Shell>
  );
  const x = d.data, ctx = c.data, it = ctx.item, a = ctx.assignment;
  const faTitle = it.title_fa, faSummary = it.summary_fa;
  const leadFa = contentLang === 'fa' && !!faTitle;
  const original = safeUrl(x.canonical_url);

  return (
    <Shell>
      <nav className="muted" aria-label="مسیر"><Link href="/news">اخبار</Link> / {a && <Link href={`/topics/${a.category_id}`}>{a.category_label}</Link>}</nav>
      <div className="detail">
        <article className="detail-main">
          <div className="card-flags">
            {it.breaking && <BreakingTag />}
            <CategoryTag id={it.category_id} label={it.category_label} />
            <ImportanceTag level={it.importance_level} showLow />
            <TranslationTag status={it.title_fa_status} review={it.title_fa_review} />
          </div>
          <h1 className="detail-title" dir={leadFa ? 'rtl' : 'ltr'}>{leadFa ? faTitle : x.title}</h1>
          {leadFa && <p className="card-original" dir="ltr">{x.title}</p>}
          <div className="card-meta">
            <Link href={`/sources/${it.source_id}`} className="card-source"><SourceMark name={it.source_name} color={sourceColor(it.source_id)} size={22} /><bdi>{it.source_name}</bdi></Link>
            <span>انتشار: {x.published_at ? fmtDateTime(x.published_at) : 'در خوراک ثبت نشده'}</span>
            <span>{fmtRelative(x.published_at, now)}</span>
            {original && <a href={original} target="_blank" rel="noopener noreferrer nofollow" className="sec-link">خبر در سایت منبع<ExternalLink size={13} /></a>}
          </div>

          <MediaViewer itemId={it.item_id} categoryId={it.category_id} categoryLabel={it.category_label} mediaStatus={it.media_status} articleUrl={x.canonical_url} />

          <section aria-labelledby="bi-h">
            <h2 id="bi-h" className="sr-only">متن دوزبانه</h2>
            <div className="bilingual">
              <div className="lang-col">
                <h4>فارسی <TranslationTag status={it.title_fa_status} review={it.title_fa_review} /></h4>
                <FaField label="عنوان" cls="t" text={faTitle} unverified={it.title_fa_unverified ?? null} status={it.title_fa_status} qc={it.title_fa_qc ?? null} />
                <FaField label="خلاصه" cls="s" text={faSummary} unverified={it.summary_fa_unverified ?? null} status={it.summary_fa_status} qc={it.summary_fa_qc ?? null} />
                {(it.title_fa_status === 'translation_pending' || it.title_fa_status === 'pending') && <RequestTranslation id={it.item_id} />}
                {(it.machine_translated || it.title_fa_unverified || it.summary_fa_unverified) && (
                  <small className="muted">{MACHINE_LABEL} · ترجمه محلی <bdi>{it.translation_provider}</bdi> · مدل <bdi>{it.translation_model}</bdi>
                    {it.title_fa_qc?.pipeline && <> · کنترل کیفیت <bdi>{it.title_fa_qc.pipeline}</bdi></>} · عبور از کنترل کیفیت به معنی صحت قطعی نیست؛ متن اصلی ملاک است.</small>
                )}
              </div>
              <div className="lang-col" dir="ltr" lang="en">
                <h4 dir="rtl">متن اصلی منبع (انگلیسی) <Tag>{x.content_language || 'زبان اعلام‌نشده'}</Tag></h4>
                <p className="t">{x.title}</p>
                {x.summary ? <p className="s">{x.summary}</p> : <p className="muted" dir="rtl">ناشر برای این خبر خلاصه‌ای منتشر نکرده است.</p>}
              </div>
            </div>
          </section>

          <section className="panel" aria-labelledby="body-h">
            <div className="panel-title"><FileText size={16} /><h3 id="body-h">متن خبر</h3></div>
            {x.content.display_policy === 'full_syndicated' && x.content.original_text
              ? <div className="body-text" dir="ltr" lang="en">{x.content.original_text}</div>
              : <p className="muted">{POLICY[x.content.display_policy] ?? 'متن کامل نمایش داده نمی‌شود.'} {original && <a href={original} target="_blank" rel="noopener noreferrer nofollow" className="sec-link">خواندن در سایت ناشر</a>}</p>}
          </section>

          {x.key_points.length > 0 && (
            <section className="panel"><div className="panel-title"><h3>نکات کلیدی</h3><Tag tone="ai">تولیدشده با هوش مصنوعی · نیازمند بازبینی</Tag></div>
              <ul>{x.key_points.map((k) => <li key={k.point_index}>{k.text_fa}{k.evidence_span && <small className="muted" dir="ltr"> — «{k.evidence_span}»</small>}</li>)}</ul>
            </section>
          )}

          {x.media.documents.length > 0 && (
            <section className="panel" aria-labelledby="media-h">
              <div className="panel-title"><h3 id="media-h">اسناد پیوست خبر</h3></div>
              {x.media.documents.length > 0 && (
                <ul className="prov" style={{ marginTop: 12 }}>
                  {x.media.documents.map((doc) => {
                    const u = safeUrl(doc.url);
                    return (
                      <li key={doc.media_id}><FileText size={15} />
                        <div>{u ? <a href={u} target="_blank" rel="noopener noreferrer nofollow" dir="ltr">{decodeURIComponent(u.split('/').pop() || u).slice(0, 80)}</a> : 'نشانی نامعتبر'}
                          <small>{doc.mime_type || 'نوع نامشخص'} · {sizeLabel(doc.byte_size)} · {hostOf(doc.url)} · {doc.verification_status === 'verified' ? 'بررسی‌شده' : 'بررسی‌نشده'} — دانلود خودکار نمی‌شود</small></div>
                      </li>
                    );
                  })}
                </ul>
              )}

            </section>
          )}

          {ctx.event_items.length > 0 && (
            <section className="panel" aria-labelledby="ev-h">
              <div className="panel-title"><Layers size={16} /><h3 id="ev-h">همین رویداد در منابع دیگر</h3>{it.event_id && <Link href={`/events/${it.event_id}`} className="sec-link" style={{ marginInlineStart: 'auto' }}>صفحه رویداد</Link>}</div>
              <ul className="prov">{ctx.event_items.map((e) => <li key={e.item_id}><Link2 size={14} /><div><Link href={`/news/${e.item_id}`} dir="ltr">{e.title}</Link><small><bdi>{e.source_name}</bdi> · {fmtDateTime(e.published_at)}</small></div></li>)}</ul>
            </section>
          )}

          {ctx.same_topic.length > 0 && (
            <section aria-labelledby="rel-h">
              <h2 id="rel-h" className="brief-sub">خبرهای دیگر در «{it.category_label}»</h2>
              {ctx.same_topic.map((s) => <NewsCard key={s.item_id} item={s} now={now} variant="row" />)}
            </section>
          )}
        </article>

        <aside className="side" aria-label="منشأ و طبقه‌بندی">
          <section className="panel">
            <div className="panel-title"><ShieldCheck size={16} /><h3>منشأ و مسیر دریافت</h3></div>
            <ul className="prov">
              <li><Database size={14} /><div>منبع<small><bdi>{it.source_name}</bdi> · {x.hostname}</small></div></li>
              <li><Rss size={14} /><div>روش گردآوری<small>خوراک RSS ناشر، یک درخواست در هر چرخه{x.feed_url ? <> · <span dir="ltr">{hostOf(x.feed_url)}</span></> : ''}</small></div></li>
              <li><Clock3 size={14} /><div>زمان انتشار<small>{x.published_at ? fmtDateTime(x.published_at) : 'در خوراک ثبت نشده'}</small></div></li>
              <li><Clock3 size={14} /><div>زمان دریافت<small>{x.fetched_at ? fmtDateTime(x.fetched_at) : 'ثبت نشده (رکورد پیش از ثبت زمان دریافت)'}</small></div></li>
              <li><ShieldCheck size={14} /><div>وضعیت منشأ<small>{x.provenance_status === 'COMPLETE' ? 'کامل' : x.provenance_status || 'نامشخص'}{x.provenance[0]?.execution_reference ? ` · اجرای ${x.provenance[0].execution_reference.slice(0, 18)}` : ''}</small></div></li>
              <li><FileText size={14} /><div>متن<small>{POLICY[x.content.display_policy] ?? x.content.display_policy} ({fmt(x.content.text_chars)} نویسه)</small></div></li>
            </ul>
          </section>
          <section className="panel">
            <div className="panel-title"><h3>طبقه‌بندی موضوعی</h3>{a && <Tag>{`نسخه ${a.taxonomy_version}`}</Tag>}</div>
            {!a ? <Empty title="هنوز طبقه‌بندی نشده" /> : (
              <dl className="kv">
                <dt>دسته اصلی</dt><dd><CategoryTag id={a.category_id} label={a.category_label} /></dd>
                {a.other_reason_code && <><dt>دلیل «سایر»</dt><dd>{ctx.other_reason_label}</dd></>}
                <dt>اطمینان</dt><dd>{a.confidence != null && a.category_id !== 'other' ? fmtPercent(a.confidence * 100) : '—'} <small className="muted">(شمارش شواهد، نه احتمال)</small></dd>
                <dt>موضوعات فرعی</dt><dd>{a.secondary.length ? a.secondary.map((s) => <CategoryTag key={s.id} id={s.id} label={s.label} />) : '—'}</dd>
                <dt>زیرموضوع‌ها</dt><dd>{a.subtopics.length ? a.subtopics.map((s) => <Link key={s.id + s.parent} href={`/topics/${s.id}`} className="tag" style={{ marginInlineEnd: 4 }}>{s.label}</Link>) : '—'}</dd>
                <dt>شواهد</dt><dd dir="ltr" style={{ textAlign: 'right' }}>{a.evidence.length ? a.evidence.join('، ') : '—'}</dd>
                <dt>روش</dt><dd>{a.human_locked ? 'اصلاح انسانی (قفل‌شده)' : 'قواعد کلیدواژه‌ای قطعی'}</dd>
                {ctx.legacy_classification && <><dt>طبقه‌بندی قبلی</dt><dd>{ctx.legacy_classification.category_label} <small className="muted">(نسخه {ctx.legacy_classification.taxonomy_version})</small></dd></>}
              </dl>
            )}
            {ctx.history.length > 0 && (
              <details style={{ marginTop: 10 }}><summary className="muted"><History size={13} /> تاریخچه طبقه‌بندی ({fmt(ctx.history.length)})</summary>
                <ul className="prov" style={{ marginTop: 8 }}>{ctx.history.map((h, i) => <li key={i}><History size={13} /><div>{h.category_label}<small>{CHANGE[h.change_kind] ?? h.change_kind} · نسخه {h.taxonomy_version} · {fmtDateTime(h.recorded_at)}</small></div></li>)}</ul>
              </details>
            )}
          </section>
          <section className="panel">
            <div className="panel-title"><h3>اهمیت</h3><ImportanceTag level={it.importance_level} showLow /></div>
            <p className="muted">امتیاز {fmt(it.importance)} · {ctx.importance_rule.description_fa}</p>
          </section>
        </aside>
      </div>
    </Shell>
  );
}

/** One Persian field: shown as a translation only when QC found no objection;
 *  a QC-warning text only with a warning; a rejected one never. */
function FaField({ label, cls, text, unverified, status, qc }: { label: string; cls: string; text: string | null; unverified: string | null; status: string; qc: TranslationQc | null }) {
  const scope = qc?.scope === 'lead' && qc.lead_chars && qc.full_chars
    ? <p className="bi-note">ترجمه بخش آغازین {label} ({fmt(qc.lead_chars)} از {fmt(qc.full_chars)} نویسه)؛ متن کامل در ستون انگلیسی است.</p> : null;
  if (text) return <><p className={cls}>{text}</p>{scope}</>;
  if (unverified) return (
    <><p className={cls}>{unverified}</p>
      <p className="bi-warn">هشدار کنترل کیفیت: {qc ? `${fmt(qc.uncertain)} مورد (عدد، نام، اصطلاح یا رابطه)` : 'برخی موارد'} به‌طور خودکار قابل تأیید نبود. این ترجمه فقط در کنار متن اصلی نمایش داده می‌شود و متن اصلی ملاک است.</p>{scope}</>);
  if (status === 'qc_failed') return <p className="bi-fail">ترجمه {label} در کنترل کیفیت خطای بحرانی داشت{qc?.critical ? ` (${fmt(qc.critical)} مورد)` : ''} و نمایش داده نمی‌شود؛ متن اصلی انگلیسی معتبر است.</p>;
  if (status === 'translation_failed') return <p className="muted">ترجمه {label} پس از چند تلاش ناموفق ماند؛ متن اصلی انگلیسی معتبر است.</p>;
  if (status === 'no_source_text') return <p className="muted">منبع برای {label} متنی منتشر نکرده است.</p>;
  if (status === 'translation_error') return <p className="muted">ترجمه {label} ناموفق بود و خودکار با تأخیر دوباره تلاش می‌شود.</p>;
  if (status === 'not_required') return <p className="muted">متن اصلی {label} فارسی است.</p>;
  if (status === 'processing') return <p className="muted">ترجمه {label} در حال انجام است…</p>;
  if (status === 'needs_review') return <p className="muted">ترجمه {label} در کنترل کیفیت رد شد و نمایش داده نمی‌شود.</p>;
  return <p className="muted">{label} فارسی هنوز آماده نیست (در انتظار ترجمه خودکار). متنی حدس زده یا جایگزین نمی‌شود.</p>;
}

function RequestTranslation({ id }: { id: string }) {
  const [state, setState] = useState<'idle' | 'sent' | 'error'>('idle');
  if (state === 'sent') return <p className="bi-note">در صف ترجمه قرار گرفت؛ پس از آماده شدن، بدون نیاز به بارگذاری دوباره نمایش داده می‌شود.</p>;
  return (
    <button type="button" className="btn-ghost" onClick={() => fetch(`/api/v1/news/${encodeURIComponent(id)}/translation/request`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{}' })
      .then((r) => setState(r.ok ? 'sent' : 'error')).catch(() => setState('error'))}>
      {state === 'error' ? 'ثبت درخواست ناموفق بود؛ دوباره تلاش کنید' : 'اولویت دادن به ترجمه این خبر'}
    </button>
  );
}

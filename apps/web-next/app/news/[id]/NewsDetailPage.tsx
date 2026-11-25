'use client';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ExternalLink, FileText, Rss, Clock3, Database, ShieldCheck, Link2, History, Layers } from 'lucide-react';
import { Shell } from '../../design/Shell';
import { useApi, useNow } from '../../design/useApi';
import type { FeedItem } from '../../design/types';
import { fmt, fmtDateTime, fmtPercent, fmtRelative, hostOf, safeUrl, sourceColor } from '../../design/format';
import { usePrefs } from '../../design/prefs';
import { useAiState } from '../../design/aiState';
import { BreakingTag, CategoryTag, Empty, Failure, ImportanceTag, SourceMark, Tag, TranslationTag, Bone, CardBones, MACHINE_LABEL } from '../../design/ui';
import { useEffect, useState } from 'react';
import type { TranslationQc } from '../../design/types';
import { getCategoryLabel, getSubtopicLabel, getOtherReasonLabel } from '../../design/taxonomy';
import { MediaViewer } from '../../components/MediaViewer';
import { NewsCard } from '../../components/NewsCard';

interface Media { media_id: string; kind: string; url: string; mime_type: string | null; byte_size: number | null; alt_text: string | null; relevance: string; verification_status: string }
interface Detail {
  item_id: string; title: string; summary: string | null; canonical_url: string; published_at: string | null; fetched_at: string | null; first_seen_at: string | null;
  source_name: string | null; hostname: string; source_type: string; feed_url: string | null; provenance_status: string; content_language: string | null; external_guid: string | null;
  content: { extraction_status: string; display_policy: string; original_text: string | null; text_chars: number; original_text_withheld_reason?: string; extraction_method: string | null };
  translations: Record<string, { status: string; text: string | null; provider: string | null; model: string | null; updated_at: string | null; text_unverified?: string | null; qc?: TranslationQc | null }>;
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

function sizeLabel(n: number | null, mbText = 'مگابایت', kbText = 'کیلوبایت', unknownText = 'حجم نامشخص') {
  if (!n) return unknownText;
  return n > 1048576 ? `${fmt(Math.round(n / 104857.6) / 10)} ${mbText}` : `${fmt(Math.round(n / 1024))} ${kbText}`;
}

export function NewsDetailPage() {
  const { id } = useParams<{ id: string }>();
  const d = useApi<Detail>('news/' + encodeURIComponent(id), [id]);
  const c = useApi<Context>(`feed/${encodeURIComponent(id)}/context`, [id]);
  const now = useNow();
  const { contentLang, t, isEn } = usePrefs();
  const ai = useAiState();

  const policyMap: Record<string, string> = {
    full_syndicated: t.policyFullSyndicated,
    summary_only: t.policySummaryOnly,
    link_only: t.policyLinkOnly,
  };
  const changeMap: Record<string, string> = {
    assigned: t.changeAssigned,
    reclassified: t.changeReclassified,
    human_override: t.changeHumanOverride,
  };

  // The translation appears without a manual refresh: poll while it is queued or running.
  const waiting = ['translation_pending', 'processing', 'pending'].includes(c.data?.item.title_fa_status ?? '')
    || ['translation_pending', 'processing', 'pending'].includes(c.data?.item.summary_fa_status ?? '');
  useEffect(() => {
    if (!waiting || ai.off !== false) return;   // nothing will arrive while local AI is disabled
    const timer = setInterval(() => { c.reload(); }, 20000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [waiting, id, ai.off]);

  if (d.error || c.error) return <Shell><Failure onRetry={() => { d.reload(); c.reload(); }}>{t.newsDetailNotFound}</Failure></Shell>;
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
      <nav className="muted" aria-label={t.navBreadcrumb}><Link href="/news">{t.navNews}</Link> / {a && <Link href={`/topics/${a.category_id}`}>{a.category_label}</Link>}</nav>
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
            <span>{t.publishedLabel}{x.published_at ? fmtDateTime(x.published_at) : t.feedNotRecorded}</span>
            <span>{fmtRelative(x.published_at, now)}</span>
            {original && <a href={original} target="_blank" rel="noopener noreferrer nofollow" className="sec-link">{t.viewOnSource}<ExternalLink size={13} /></a>}
          </div>

          <MediaViewer itemId={it.item_id} categoryId={it.category_id} categoryLabel={it.category_label} mediaStatus={it.media_status} articleUrl={x.canonical_url} />

          <section aria-labelledby="bi-h">
            <h2 id="bi-h" className="sr-only">{t.bilingualTextHeading}</h2>
            {(() => {
              const hasSummary = Boolean(x.summary && x.summary.trim() && (!x.content?.original_text || x.summary.trim() !== x.content.original_text.trim()));
              const summaryTrans = x.translations?.['summary'];
              const bodyTrans = x.translations?.['body'];
              const summaryFaText = summaryTrans?.text ?? (it.summary_fa_status === 'available' ? it.summary_fa : null);
              const summaryFaUnverified = summaryTrans?.text_unverified ?? it.summary_fa_unverified;
              const summaryFaStatus = summaryTrans?.status ?? it.summary_fa_status;
              const summaryFaQc = summaryTrans?.qc ?? it.summary_fa_qc;
              const bodyFaText = bodyTrans?.text ?? null;
              const bodyFaUnverified = bodyTrans?.text_unverified ?? null;
              const bodyFaStatus = bodyTrans?.status ?? (x.content?.original_text ? 'pending' : 'no_source_text');
              const bodyFaQc = bodyTrans?.qc ?? null;

              return (
                <div className="bilingual">
                  <div className="lang-col">
                    <h4>{t.persianColHeading} <TranslationTag status={it.title_fa_status} review={it.title_fa_review} /></h4>
                    <FaField label={t.fieldTitleLabel} cls="t" text={faTitle} unverified={it.title_fa_unverified ?? null} status={it.title_fa_status} qc={it.title_fa_qc ?? null} />

                    {hasSummary && (
                      <div className="section-summary" style={{ marginTop: 10, padding: '10px 12px', background: 'var(--surface, rgba(0,0,0,0.02))', borderRadius: 8, border: '1px solid var(--line)' }}>
                        <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--ink-3)', marginBottom: 4 }}>
                          {t.fieldPublisherSummaryLabel}
                        </div>
                        <FaField label={t.fieldPublisherSummaryLabel} cls="s" text={summaryFaText} unverified={summaryFaUnverified ?? null} status={summaryFaStatus} qc={summaryFaQc ?? null} />
                      </div>
                    )}

                    <div className="section-body" style={{ marginTop: 12 }}>
                      <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--ink-3)', marginBottom: 6 }}>
                        {t.fieldArticleBodyLabel}
                      </div>
                      {x.content?.original_text ? (
                        <FaField label={t.fieldArticleBodyLabel} cls="body-text" text={bodyFaText} unverified={bodyFaUnverified ?? null} status={bodyFaStatus} qc={bodyFaQc ?? null} />
                      ) : (
                        <p className="muted">{t.noBodyTextPublished}</p>
                      )}
                    </div>

                    {ai.off && waiting && <p className="bi-note" role="status" data-testid="ai-off-note">{ai.message} {t.aiOffEnglishNotice}</p>}
                    {ai.off === false && (it.title_fa_status === 'translation_pending' || it.title_fa_status === 'pending') && <RequestTranslation id={it.item_id} />}
                    {(it.machine_translated || it.title_fa_unverified || it.summary_fa_unverified) && (
                      <small className="muted">{t.tagMachineLabel} · {t.aiNoticeLocalProvider} <bdi>{it.translation_provider}</bdi> · {t.aiNoticeModel} <bdi>{it.translation_model}</bdi>
                        {it.title_fa_qc?.pipeline && <> · {t.aiNoticeQc} <bdi>{it.title_fa_qc.pipeline}</bdi></>} · {t.aiNoticeDisclaimer}</small>
                    )}
                  </div>

                  <div className="lang-col" dir="ltr" lang="en">
                    <h4 dir={isEn ? 'ltr' : 'rtl'}>{t.englishColHeading} <Tag>{x.content_language || t.unspecifiedLanguage}</Tag></h4>
                    <p className="t">{x.title}</p>

                    {hasSummary && (
                      <div className="section-summary" style={{ marginTop: 10, padding: '10px 12px', background: 'var(--surface, rgba(0,0,0,0.02))', borderRadius: 8, border: '1px solid var(--line)' }}>
                        <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--ink-3)', marginBottom: 4 }} dir={isEn ? 'ltr' : 'rtl'}>
                          {t.fieldPublisherSummaryLabel}
                        </div>
                        <p className="s" style={{ whiteSpace: 'pre-line' }}>{x.summary}</p>
                      </div>
                    )}

                    <div className="section-body" style={{ marginTop: 12 }}>
                      <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--ink-3)', marginBottom: 6 }} dir={isEn ? 'ltr' : 'rtl'}>
                        {t.fieldArticleBodyLabel}
                      </div>
                      {x.content?.original_text ? (
                        <p className="body-text">{x.content.original_text}</p>
                      ) : (
                        <p className="muted" dir={isEn ? 'ltr' : 'rtl'}>{t.noBodyTextPublished}</p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })()}
          </section>

          {x.key_points.length > 0 && (
            <section className="panel"><div className="panel-title"><h3>{t.keyPointsTitle}</h3><Tag tone="ai">{t.keyPointsAiTag}</Tag></div>
              <ul>{x.key_points.map((k) => <li key={k.point_index}>{k.text_fa}{k.evidence_span && <small className="muted" dir="ltr"> — «{k.evidence_span}»</small>}</li>)}</ul>
            </section>
          )}

          {x.media.documents.length > 0 && (
            <section className="panel" aria-labelledby="media-h">
              <div className="panel-title"><h3 id="media-h">{t.attachedDocsTitle}</h3></div>
              {x.media.documents.length > 0 && (
                <ul className="prov" style={{ marginTop: 12 }}>
                  {x.media.documents.map((doc) => {
                    const u = safeUrl(doc.url);
                    return (
                      <li key={doc.media_id}><FileText size={15} />
                        <div>{u ? <a href={u} target="_blank" rel="noopener noreferrer nofollow" dir="ltr">{decodeURIComponent(u.split('/').pop() || u).slice(0, 80)}</a> : t.invalidUrl}
                          <small>{doc.mime_type || t.unknownType} · {sizeLabel(doc.byte_size, t.unitMB, t.unitKB, t.unknownSize)} · {hostOf(doc.url)} · {doc.verification_status === 'verified' ? t.verified : t.unverified} — {t.noAutoDownload}</small></div>
                      </li>
                    );
                  })}
                </ul>
              )}

            </section>
          )}

          {ctx.event_items.length > 0 && (
            <section className="panel" aria-labelledby="ev-h">
              <div className="panel-title"><Layers size={16} /><h3 id="ev-h">{t.sameEventTitle}</h3>{it.event_id && <Link href={`/events/${it.event_id}`} className="sec-link" style={{ marginInlineStart: 'auto' }}>{t.eventPageLink}</Link>}</div>
              <ul className="prov">{ctx.event_items.map((e) => <li key={e.item_id}><Link2 size={14} /><div><Link href={`/news/${e.item_id}`} dir="ltr">{e.title}</Link><small><bdi>{e.source_name}</bdi> · {fmtDateTime(e.published_at)}</small></div></li>)}</ul>
            </section>
          )}

          {ctx.same_topic.length > 0 && (
            <section aria-labelledby="rel-h">
              <h2 id="rel-h" className="brief-sub">{t.otherNewsInCategory} «{getCategoryLabel(it.category_id || it.category_label, isEn)}»</h2>
              {ctx.same_topic.map((s) => <NewsCard key={s.item_id} item={s} now={now} variant="row" />)}
            </section>
          )}
        </article>

        <aside className="side" aria-label={t.provenanceAndClassification}>
          <section className="panel">
            <div className="panel-title"><ShieldCheck size={16} /><h3>{t.provenanceHeading}</h3></div>
            <ul className="prov">
              <li><Database size={14} /><div>{t.sourceProvenanceLabel}<small><bdi>{it.source_name}</bdi> · {x.hostname}</small></div></li>
              <li><Rss size={14} /><div>{t.ingestionMethodLabel}<small>{x.source_type === 'html' ? t.ingestionHtmlDesc : t.ingestionRssDesc}{x.feed_url ? <> · <span dir="ltr">{hostOf(x.feed_url)}</span></> : ''}</small></div></li>
              <li><Clock3 size={14} /><div>{t.publishedAtLabel}<small>{x.published_at ? fmtDateTime(x.published_at, isEn) : t.feedNotRecorded}</small></div></li>
              <li><Clock3 size={14} /><div>{t.receivedAtLabel}<small>{x.fetched_at ? fmtDateTime(x.fetched_at, isEn) : t.notRecordedLegacy}</small></div></li>
              <li><ShieldCheck size={14} /><div>{t.provenanceStatusLabel}<small>{x.provenance_status === 'COMPLETE' ? t.statusComplete : (x.provenance_status || t.statusUnknown)}{x.provenance[0]?.execution_reference ? ` · ${t.executionRefPrefix} ${x.provenance[0].execution_reference.slice(0, 18)}` : ''}</small></div></li>
              <li><FileText size={14} /><div>{t.textProvenanceLabel}<small>{policyMap[x.content.display_policy] ?? x.content.display_policy} ({fmt(x.content.text_chars)} {t.charsCount})</small></div></li>
            </ul>
          </section>
          <section className="panel">
            <div className="panel-title"><h3>{t.thematicClassification}</h3>{a && <Tag>{`${t.versionPrefix} ${a.taxonomy_version}`}</Tag>}</div>
            {!a ? <Empty title={t.notClassifiedYet} /> : (
              <dl className="kv">
                <dt>{t.primaryCategory}</dt><dd><CategoryTag id={a.category_id} label={a.category_label} /></dd>
                {a.other_reason_code && <><dt>{t.otherReasonLabel}</dt><dd>{getOtherReasonLabel(a.other_reason_code || ctx.other_reason_label, isEn)}</dd></>}
                <dt>{t.confidenceLabel}</dt><dd>{a.confidence != null && a.category_id !== 'other' ? fmtPercent(a.confidence * 100) : '—'} <small className="muted">{t.evidenceCountNote}</small></dd>
                <dt>{t.secondaryTopics}</dt><dd>{a.secondary.length ? a.secondary.map((s) => <CategoryTag key={s.id} id={s.id} label={s.label} />) : '—'}</dd>
                <dt>{t.subtopicsLabel}</dt><dd>{a.subtopics.length ? a.subtopics.map((s) => <Link key={s.id + s.parent} href={`/topics/${s.id}`} className="tag" style={{ marginInlineEnd: 4 }}>{getSubtopicLabel(s.id || s.label, isEn)}</Link>) : '—'}</dd>
                <dt>{t.evidenceLabel}</dt><dd dir="ltr" style={{ textAlign: isEn ? 'left' : 'right' }}>{a.evidence.length ? a.evidence.join('، ') : '—'}</dd>
                <dt>{t.methodLabel}</dt><dd>{a.human_locked ? t.methodHumanLocked : t.methodRules}</dd>
                {ctx.legacy_classification && <><dt>{t.previousClassification}</dt><dd>{getCategoryLabel(ctx.legacy_classification.category_label, isEn)} <small className="muted">({t.versionPrefix} {ctx.legacy_classification.taxonomy_version})</small></dd></>}
              </dl>
            )}
            {ctx.history.length > 0 && (
              <details style={{ marginTop: 10 }}><summary className="muted"><History size={13} /> {t.classificationHistory} ({fmt(ctx.history.length)})</summary>
                <ul className="prov" style={{ marginTop: 8 }}>{ctx.history.map((h, i) => <li key={i}><History size={13} /><div>{getCategoryLabel(h.category_label, isEn)}<small>{changeMap[h.change_kind] ?? h.change_kind} · {t.versionPrefix} {h.taxonomy_version} · {fmtDateTime(h.recorded_at, isEn)}</small></div></li>)}</ul>
              </details>
            )}
          </section>
          <section className="panel">
            <div className="panel-title"><h3>{t.importanceHeading}</h3><ImportanceTag level={it.importance_level} showLow /></div>
            <p className="muted">{t.importanceScore} {fmt(it.importance)} · {isEn ? ctx.importance_rule.id : ctx.importance_rule.description_fa}</p>
          </section>
        </aside>
      </div>
    </Shell>
  );
}

/** One Persian field: shown as a translation only when QC found no objection;
 *  a QC-warning text only with a warning; a rejected one never. */
function FaField({ label, cls, text, unverified, status, qc }: { label: string; cls: string; text: string | null; unverified: string | null; status: string; qc: TranslationQc | null }) {
  const { isEn } = usePrefs();
  const scope = qc?.scope === 'lead' && qc.lead_chars && qc.full_chars
    ? <p className="bi-note">{isEn ? `Lead translation (${fmt(qc.lead_chars)} of ${fmt(qc.full_chars)} chars); full text is in the English column.` : `ترجمه بخش آغازین ${label} (${fmt(qc.lead_chars)} از ${fmt(qc.full_chars)} نویسه)؛ متن کامل در ستون انگلیسی است.`}</p> : null;
  if (text) return <><p className={cls}>{text}</p>{scope}</>;
  if (unverified) return (
    <><p className={cls}>{unverified}</p>
      <p className="bi-warn">{isEn ? `QC Warning: ${qc ? `${fmt(qc.uncertain)} items` : 'Some items'} could not be auto-verified.` : `هشدار کنترل کیفیت: ${qc ? `${fmt(qc.uncertain)} مورد` : 'برخی موارد'} به‌طور خودکار قابل تأیید نبود.`}</p>{scope}</>);
  if (status === 'qc_failed') return <p className="bi-fail">{isEn ? `Translation rejected in QC${qc?.critical ? ` (${fmt(qc.critical)} critical errors)` : ''}.` : `ترجمه ${label} در کنترل کیفیت خطای بحرانی داشت${qc?.critical ? ` (${fmt(qc.critical)} مورد)` : ''} و نمایش داده نمی‌شود.`}</p>;
  if (status === 'translation_failed') return <p className="muted">{isEn ? `Translation failed after multiple attempts.` : `ترجمه ${label} پس از چند تلاش ناموفق ماند.`}</p>;
  if (status === 'no_source_text') return <p className="muted">{isEn ? `Publisher provided no text for ${label}.` : `منبع برای ${label} متنی منتشر نکرده است.`}</p>;
  if (status === 'translation_error') return <p className="muted">{isEn ? `Translation error; will retry automatically.` : `ترجمه ${label} ناموفق بود و خودکار با تأخیر دوباره تلاش می‌شود.`}</p>;
  if (status === 'not_required') return <p className="muted">{isEn ? `Original ${label} is in Persian.` : `متن اصلی ${label} فارسی است.`}</p>;
  if (status === 'processing') return <p className="muted">{isEn ? `Translating ${label}…` : `ترجمه ${label} در حال انجام است…`}</p>;
  if (status === 'needs_review') return <p className="muted">{isEn ? `Translation rejected by QC.` : `ترجمه ${label} در کنترل کیفیت رد شد و نمایش داده نمی‌شود.`}</p>;
  return <p className="muted">{isEn ? `Persian ${label} not ready yet (awaiting automated translation).` : `${label} فارسی هنوز آماده نیست (در انتظار ترجمه خودکار).`}</p>;
}

function RequestTranslation({ id }: { id: string }) {
  const { t } = usePrefs();
  const [state, setState] = useState<'idle' | 'sent' | 'error'>('idle');
  if (state === 'sent') return <p className="bi-note">{t.requestTranslationSent}</p>;
  return (
    <button type="button" className="btn-ghost" onClick={() => fetch(`/api/v1/news/${encodeURIComponent(id)}/translation/request`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{}' })
      .then((r) => setState(r.ok ? 'sent' : 'error')).catch(() => setState('error'))}>
      {state === 'error' ? t.requestTranslationError : t.requestTranslationBtn}
    </button>
  );
}

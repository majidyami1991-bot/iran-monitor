'use client';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Shell } from '../../design/Shell';
import { useApi, useNow } from '../../design/useApi';
import type { FeedItem } from '../../design/types';
import { fmt, fmtDateTime, fmtPercent, fmtRelative, sourceColor } from '../../design/format';
import { CategoryTag, Failure, PageHead, SourceMark, Tag, TranslationTag, Bone, CardBones } from '../../design/ui';
import { ConfidenceTag, Pulse } from '../../components/EventTimeline';
import { ItemImage } from '../../components/Visual';

type Member = FeedItem & { similarity_score: number | null; membership_reason: { shared_entities?: string[]; shared_words?: string[]; hours_apart?: number; weighted_jaccard?: number } | null };
interface Resp {
  event: { event_id: string; title: string; first_published_at: string | null; last_updated_at: string | null; source_count: number; member_count: number;
    clustering_method: string; algorithm_version: string; primary_category: string | null; primary_category_label: string | null; confidence: number | null; confidence_level: 'high' | 'medium' | 'low' | null };
  items: Member[]; sources: [string, string][]; method_note_fa: string;
}

export function EventDetailPage() {
  const { id } = useParams<{ id: string }>();
  const q = useApi<Resp>('timeline/events/' + encodeURIComponent(id), [id]);
  const now = useNow();
  if (q.error) return <Shell><Failure onRetry={q.reload}>این رویداد پیدا نشد یا دریافت آن ناموفق بود.</Failure></Shell>;
  if (!q.data) return <Shell><Bone h={28} w="60%" /><CardBones n={3} /></Shell>;
  const { event: e, items, sources } = q.data;
  return (
    <Shell>
      <nav className="muted" aria-label="مسیر"><Link href="/events">رویدادها</Link></nav>
      <PageHead eyebrow="داستان رویداد" title={e.title}>
        <div className="card-flags">
          <CategoryTag id={e.primary_category} label={e.primary_category_label ?? 'دسته غالب ندارد'} href={!!e.primary_category} />
          <ConfidenceTag level={e.confidence_level} />
          <Tag tone="brand">{fmt(e.source_count)} منبع · {fmt(e.member_count)} خبر</Tag>
        </div>
      </PageHead>
      <div className="grid-3">
        <div className="stat"><span className="stat-label">نخستین گزارش</span><strong className="stat-value" style={{ fontSize: 16 }}>{fmtDateTime(e.first_published_at)}</strong></div>
        <div className="stat"><span className="stat-label">آخرین تحول</span><strong className="stat-value" style={{ fontSize: 16 }}>{fmtDateTime(e.last_updated_at)}</strong><span className="stat-note">{fmtRelative(e.last_updated_at, now)}</span></div>
        <div className="stat"><span className="stat-label">اطمینان گروه‌بندی</span><strong className="stat-value" style={{ fontSize: 16 }}>{e.confidence != null ? fmtPercent(e.confidence * 100) : 'نامشخص'}</strong><span className="stat-note">میانگین امتیاز شباهت دوبه‌دو</span></div>
      </div>
      <section className="panel">
        <h2 className="brief-sub">شدت پوشش در طول زمان</h2>
        <Pulse pulses={items.map((i) => ({ t: i.published_at, item_id: i.item_id }))} label="انتشار خبرهای این رویداد" />
        <p className="fig-note">هر خط، انتشار یک خبر است؛ از نخستین تا آخرین گزارش.</p>
        <div className="channels" style={{ marginTop: 10 }}>
          {sources.map(([sid, name]) => <Link key={sid} href={`/sources/${sid}`} className="cat-chip"><SourceMark name={name} color={sourceColor(sid)} size={18} /><bdi>{name}</bdi></Link>)}
        </div>
      </section>
      <section aria-labelledby="story-h">
        <h2 id="story-h" className="sec-head" style={{ marginBottom: 12 }}>روایت به ترتیب زمان</h2>
        <ol className="timeline">
          {items.map((it, idx) => (
            <li key={it.item_id} className="tl-item">
              <div className="tl-when"><time dateTime={it.published_at ?? undefined}>{fmtDateTime(it.published_at).split('،').pop()}</time><small>{idx === 0 ? 'نخستین گزارش' : fmtRelative(it.published_at, now)}</small></div>
              <span className="tl-dot" aria-hidden="true" />
              <div className="tl-body" style={{ display: 'grid', gridTemplateColumns: it.image_url ? '1fr 120px' : '1fr', gap: 12 }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 0 }}>
                  <div className="card-flags"><span className="card-source"><SourceMark name={it.source_name} color={sourceColor(it.source_id)} size={18} /><bdi>{it.source_name}</bdi></span><TranslationTag status={it.title_fa_status} /></div>
                  <h3 dir="ltr"><Link href={`/news/${it.item_id}`}>{it.title}</Link></h3>
                  {it.title_fa && <p>{it.title_fa}</p>}
                  {it.summary && <p className="card-summary" dir="ltr" style={{ WebkitLineClamp: 3 }}>{it.summary}</p>}
                  {it.membership_reason?.shared_entities && (
                    <p className="tl-meta">دلیل عضویت: نام‌های مشترک <span dir="ltr">{it.membership_reason.shared_entities.join(', ')}</span>
                      {it.membership_reason.hours_apart != null && <> · فاصله {fmt(it.membership_reason.hours_apart)} ساعت</>}
                      {it.similarity_score != null && <> · امتیاز {fmt(Math.round(it.similarity_score * 100) / 100)}</>}</p>
                  )}
                </div>
                {it.image_url && <div style={{ borderRadius: 8, overflow: 'hidden', aspectRatio: '4/3' }}><ItemImage src={it.image_url} categoryId={it.category_id} compact credit={false} /></div>}
              </div>
            </li>
          ))}
        </ol>
      </section>
      <p className="note">{q.data.method_note_fa} روش: {e.clustering_method} نسخه {e.algorithm_version}.</p>
    </Shell>
  );
}

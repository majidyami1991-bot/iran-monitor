'use client';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { FileText, Link2 } from 'lucide-react';
import { Shell } from '../../design/Shell';
import { useApi } from '../../design/useApi';
import { ErrorState, Skeleton, Badge } from '../../design/ui';
import { fmt, fmtDateTime, isPersian, safeUrl } from '../../design/format';

interface Member {
  item_id: string;
  title: string;
  published_at: string | null;
  canonical_url: string;
  hostname: string | null;
  similarity_score: number | null;
  membership_reason: { shared_entities?: string[] } | null;
}
interface EventData {
  event_id: string; title: string; member_count: number; source_count: number;
  first_published_at: string | null; last_updated_at: string | null;
  clustering_method: string; algorithm_version: string; members: Member[];
}

export function EventDetailPage() {
  const params = useParams<{ id?: string }>();
  const id = params?.id || '';
  const { data, error, loading, reload } = useApi<EventData>('events/' + encodeURIComponent(id), [id]);

  return (
    <Shell title="جزئیات رویداد" breadcrumb={data?.title || 'جزئیات رویداد'}>
      {loading && <div style={{ display: 'grid', gap: 12 }}><Skeleton height={28} width={480} /><Skeleton height={260} radius={14} /></div>}
      {error && <ErrorState onRetry={reload}>دریافت رویداد ممکن نشد؛ داده‌ای ساخته نشده است.</ErrorState>}
      {!loading && !error && data && (
        <article>
          <div className="news-detail-meta">
            <Badge tone="accent"><Link2 size={12} /> رویداد خودکار</Badge>
            <span className="news-detail-time">اولین انتشار: {fmtDateTime(data.first_published_at)}</span>
            <span className="news-detail-time">آخرین بروزرسانی: {fmtDateTime(data.last_updated_at)}</span>
          </div>
          <h1 className="news-detail-title-en" dir={isPersian(data.title) ? 'rtl' : 'ltr'}>{data.title}</h1>
          <p className="chart-caption">
            {fmt(data.member_count)} خبر از {fmt(data.source_count)} منبع · روش: {data.clustering_method} نسخه {data.algorithm_version}
          </p>

          <div className="news-detail-panel">
            <ul className="news-detail-documents">
              {data.members.map((m) => (
                <li key={m.item_id}>
                  <FileText size={15} />
                  <Link href={'/news/' + encodeURIComponent(m.item_id)} dir={isPersian(m.title) ? 'rtl' : 'ltr'}>{m.title}</Link>
                  <span>{m.hostname} · {fmtDateTime(m.published_at)}</span>
                  {m.similarity_score != null && <Badge tone="muted">تشابه {(m.similarity_score * 100).toFixed(0)}٪</Badge>}
                  {m.membership_reason?.shared_entities?.length ? (
                    <Badge tone="muted">اشتراک: {m.membership_reason.shared_entities.join('، ')}</Badge>
                  ) : null}
                  {safeUrl(m.canonical_url) && (
                    <a href={safeUrl(m.canonical_url)} target="_blank" rel="noopener noreferrer" dir="ltr">منبع اصلی</a>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </article>
      )}
    </Shell>
  );
}

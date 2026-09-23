'use client';
import { useParams } from 'next/navigation';
import { Shell } from '../../design/Shell';
import { useApi } from '../../design/useApi';
import { ErrorState, Skeleton } from '../../design/ui';
import { NewsDetail } from '../../components/NewsDetail';
import type { NewsDetailItem } from '../../components/news-types';

export function NewsDetailPage() {
  const params = useParams<{ id?: string }>();
  const id = params?.id || '';
  const { data, error, loading, reload } = useApi<NewsDetailItem>('news/' + encodeURIComponent(id), [id]);

  return (
    <Shell title="جزئیات خبر" breadcrumb={data?.title || 'جزئیات خبر'}>
      {loading && <div style={{ display: 'grid', gap: 12 }}><Skeleton height={28} width={480} /><Skeleton height={320} radius={14} /><Skeleton height={200} /></div>}
      {error && <ErrorState onRetry={reload}>دریافت خبر ممکن نشد؛ داده‌ای ساخته نشده است.</ErrorState>}
      {!loading && !error && data && <NewsDetail item={data} />}
    </Shell>
  );
}

import { Suspense } from 'react';
import { NewsDetailPage } from './NewsDetailPage';

export default function Page() {
  return (
    <Suspense fallback={<p className="loading-fallback" role="status">در حال دریافت داده…</p>}>
      <NewsDetailPage />
    </Suspense>
  );
}

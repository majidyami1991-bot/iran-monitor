import { Suspense } from 'react';
import { CategoryDetailPage } from './CategoryDetailPage';

export default function Page() {
  return (
    <Suspense fallback={<p className="loading-fallback" role="status">در حال دریافت داده…</p>}>
      <CategoryDetailPage />
    </Suspense>
  );
}

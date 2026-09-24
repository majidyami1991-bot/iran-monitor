import { Suspense } from 'react';
import { EventDetailPage } from './EventDetailPage';

export default function Page() {
  return (
    <Suspense fallback={<p className="loading-fallback" role="status">در حال دریافت داده…</p>}>
      <EventDetailPage />
    </Suspense>
  );
}

import { Suspense } from 'react';
import { NewsStream } from './NewsStream';

export default function Page() {
  return (
    <Suspense fallback={<p className="loading-fallback" role="status">در حال دریافت داده…</p>}>
      <NewsStream />
    </Suspense>
  );
}

import { Suspense } from 'react';
import { Social } from './Social';

export default function Page() {
  return (
    <Suspense fallback={<p className="muted" role="status">در حال دریافت داده…</p>}>
      <Social />
    </Suspense>
  );
}

'use client';
import { Compass } from 'lucide-react';

/** Every foresight page opens with the same scope statement, so descriptive
 *  counts are never read as forecasts. */
export function ForesightNote({ children }: { children: React.ReactNode }) {
  return (
    <div className="note" role="note" style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
      <Compass size={18} style={{ marginTop: 3 }} />
      <div>
        <strong>دامنه این صفحه: </strong>{children}
        <div className="muted" style={{ marginTop: 4 }}>بخش آینده‌پژوهی در این نسخه فقط نشانه‌های توصیفی از داده‌های گردآوری‌شده را نمایش می‌دهد؛ پیش‌بینی، سناریو یا ارزیابی راهبردی ارائه نمی‌کند.</div>
      </div>
    </div>
  );
}

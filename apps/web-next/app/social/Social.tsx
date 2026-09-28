'use client';
import { Shell } from '../design/Shell';
import { useApi } from '../design/useApi';
import type { Integration } from '../design/types';
import { fmt } from '../design/format';
import { Failure, IntegrationNotice, PageHead, Tag, Bone } from '../design/ui';

interface Social { integration: Integration; registered_accounts: { handle: string; collection_status: string; enabled: boolean }[]; posts: unknown[]; total_posts: number }

export function Social() {
  const q = useApi<Social>('social');
  return (
    <Shell>
      <PageHead eyebrow="تحلیل" title="شبکه‌های اجتماعی"
        lede="پست‌های شبکه‌های اجتماعی فقط از مسیر مجاز و رسمی گردآوری می‌شوند. تا وقتی چنین مسیری پیکربندی نشده، هیچ پست نمایشی، نمونه یا خراشیده‌شده‌ای نشان داده نمی‌شود." />
      {q.error && <Failure onRetry={q.reload} />}
      {!q.data && !q.error && <Bone h={160} />}
      {q.data && (
        <>
          <IntegrationNotice integration={q.data.integration} title="گردآوری X (توییتر)">
            <p className="muted">پست‌های ذخیره‌شده در پایگاه داده: {fmt(q.data.total_posts)}</p>
          </IntegrationNotice>
          <section className="panel">
            <div className="panel-title"><h3>حساب‌های ثبت‌شده در فهرست منابع مشتری</h3><Tag>{fmt(q.data.registered_accounts.length)} حساب</Tag></div>
            <p className="muted" style={{ marginBottom: 12 }}>این حساب‌ها در سند منابع (sites.docx) آمده‌اند و در شمارش «منابع تحت پایش» حساب نمی‌شوند، چون هیچ داده‌ای از آن‌ها گردآوری نمی‌شود.</p>
            <div className="channels">
              {q.data.registered_accounts.map((a) => <span key={a.handle} className="cat-chip" dir="ltr">{a.handle}</span>)}
            </div>
          </section>
        </>
      )}
    </Shell>
  );
}

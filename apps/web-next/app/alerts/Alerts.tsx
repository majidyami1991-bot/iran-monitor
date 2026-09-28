'use client';
import Link from 'next/link';
import { Shell } from '../design/Shell';
import { useApi, useNow } from '../design/useApi';
import type { Integration } from '../design/types';
import { fmtRelative } from '../design/format';
import { Empty, Failure, IntegrationNotice, PageHead, Tag, Bone } from '../design/ui';

interface Alerts { rules: unknown[]; integration: Integration; system_notifications: { kind: string; severity: string; title: string; title_lang?: string; at: string | null; href: string }[] }
const SEV: Record<string, ['error' | 'warn' | 'urgent', string]> = { error: ['error', 'خطا'], warning: ['warn', 'هشدار'], info: ['urgent', 'فوری'] };

export function Alerts() {
  const q = useApi<Alerts>('alerts');
  const now = useNow();
  return (
    <Shell>
      <PageHead eyebrow="پایش سامانه" title="هشدارها" lede="دو نوع اعلان جدا نگه داشته می‌شوند: اعلان‌های سامانه (سلامت منابع، چرخه گردآوری، قاعده خبر فوری) که همین حالا فعال‌اند، و قواعد هشدار موضوعی که باید توسط کاربر تعریف شوند." />
      {q.error && <Failure onRetry={q.reload} />}
      {!q.data && !q.error && <Bone h={160} />}
      {q.data && (
        <div className="grid-2">
          <section className="panel">
            <div className="panel-title"><h3>اعلان‌های فعال سامانه</h3></div>
            {q.data.system_notifications.length === 0 ? <Empty title="اعلان فعالی نیست" /> : (
              <ul className="prov">
                {q.data.system_notifications.map((n, i) => (
                  <li key={i}><Tag tone={SEV[n.severity]?.[0] ?? 'warn'}>{SEV[n.severity]?.[1] ?? n.severity}</Tag>
                    <div><Link href={n.href} dir={n.title_lang === 'en' ? 'ltr' : undefined}>{n.title}</Link><small>{fmtRelative(n.at, now)}</small></div></li>
                ))}
              </ul>
            )}
          </section>
          <section>
            <IntegrationNotice integration={q.data.integration} title="قواعد هشدار موضوعی">
              <p className="muted">قواعد تعریف‌شده: {q.data.rules.length}. ساختار ذخیره قاعده (جدول <code>alert_rules</code>) آماده است؛ رابط تعریف قاعده و ارسال اعلان هنوز ساخته نشده است.</p>
            </IntegrationNotice>
          </section>
        </div>
      )}
    </Shell>
  );
}

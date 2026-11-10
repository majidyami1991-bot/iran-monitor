'use client';
import Link from 'next/link';
import { ArrowDownLeft, ArrowUpLeft, FileText } from 'lucide-react';
import { useApi, useNow } from '../design/useApi';
import { fmt, fmtDateTime, fmtRelative, fmtSigned } from '../design/format';
import { AiTag, CategoryTag, Empty, Failure, ImportanceTag, RuleTag, Tag, Bone } from '../design/ui';

export interface Dev {
  item_id: string; href: string; headline: string; headline_lang: 'fa' | 'en'; summary: string | null; summary_lang: 'fa' | 'en';
  source_name: string; published_at: string | null; category_id: string | null; category_label: string | null;
  event_id: string | null; event_sources: number; importance: number; importance_level: 'high' | 'medium' | 'low'; image_url: string | null;
}
interface TopicDelta { id: string; label: string; now_n: number; prev_n: number; delta: number }
export interface BriefingPayload {
  narrative_fa: string; narrative_method: string;
  totals: { items_24h: number; items_prev_24h: number; change_pct: number | null; active_sources: number; events_in_window: number };
  key_developments: Dev[]; rising_topics: TopicDelta[]; falling_topics: TopicDelta[];
  top_sources: { source_id: string; name: string; n: number }[];
  coverage_gaps: { silent_sources: { source_id: string; name: string }[]; untranslated_24h: number; without_summary_24h: number;
    other_category_24h: number; items_24h: number; sources_with_failures: { name: string; consecutive_failures: number }[] };
  rules: Record<string, string>;
}
export interface BriefingResponse {
  status: 'fresh' | 'stale' | 'outdated' | 'not_generated'; age_hours?: number;
  ai: { status: string; provider: string | null; api_key_configured: boolean; last_request_status: string | null; last_request_error_class: string | null };
  briefing: null | { briefing_id: number; briefing_date: string; generated_at: string; window_start: string; window_end: string; generator: string; generator_version: string;
    ai_generated: boolean; ai_status: string; ai_model: string | null; ai_prompt_version: string | null; executive_summary_fa: string | null; payload: BriefingPayload };
  history?: { briefing_id: number; briefing_date: string; generated_at: string }[];
}

export const FRESH: Record<string, [string, 'ok' | 'warn' | 'error' | 'uncertain']> = {
  fresh: ['به‌روز', 'ok'], stale: ['قدیمی‌تر از یک ساعت', 'warn'], outdated: ['قدیمی‌تر از ۲۴ ساعت', 'error'], not_generated: ['تولید نشده', 'uncertain'],
};
export const AI_STATUS: Record<string, string> = {
  provider_not_configured: 'ارائه‌دهنده هوش مصنوعی پیکربندی نشده است؛ خلاصه مدیریتی هوش مصنوعی تولید نمی‌شود.',
  provider_unavailable: 'ارائه‌دهنده هوش مصنوعی پیکربندی شده اما آخرین درخواست ناموفق بوده است؛ خلاصه هوش مصنوعی تولید نمی‌شود.',
  configured: 'ارائه‌دهنده پیکربندی شده است؛ تولید خلاصه هوش مصنوعی هنوز فعال نشده است.',
};

export function TopicDeltaList({ items, dir }: { items: TopicDelta[]; dir: 'up' | 'down' }) {
  if (!items.length) return <p className="muted">{dir === 'up' ? 'هیچ موضوعی نسبت به ۲۴ ساعت قبل افزایش نداشته است.' : 'هیچ موضوعی کاهش نداشته است.'}</p>;
  return (
    <ul className="delta-list">
      {items.map((t) => (
        <li key={t.id}>
          <CategoryTag id={t.id} label={t.label} />
          <span className={dir === 'up' ? 'delta delta-up' : 'delta delta-down'}>
            {dir === 'up' ? <ArrowUpLeft size={13} /> : <ArrowDownLeft size={13} />}{fmtSigned(t.delta)}
          </span>
          <small>{fmt(t.prev_n)} ← {fmt(t.now_n)}</small>
        </li>
      ))}
    </ul>
  );
}

export function BriefingCard() {
  const q = useApi<BriefingResponse>('briefing/daily');
  const now = useNow();
  if (q.error) return <section className="brief-panel"><Failure onRetry={q.reload}>خلاصه روزانه دریافت نشد.</Failure></section>;
  if (!q.data) return <section className="brief-panel" aria-busy="true"><Bone h={20} w="50%" /><Bone h={14} /><Bone h={14} /><Bone h={14} w="70%" /></section>;
  const b = q.data.briefing;
  if (!b) return <section className="brief-panel"><Empty title="خلاصه روزانه هنوز تولید نشده است" icon={<FileText size={24} />}>نخستین خلاصه پس از اولین اجرای زمان‌بند (هر ۱۵ دقیقه) ساخته می‌شود.</Empty></section>;
  const p = b.payload;
  const [fl, ft] = FRESH[q.data.status];
  return (
    <section className="brief-panel" aria-labelledby="brief-h">
      <div className="brief-top">
        <span className="eyebrow">خلاصه روزانه</span>
        <h2 id="brief-h">امروز چه اتفاقی افتاد؟</h2>
        <div className="card-flags"><RuleTag>قاعده‌محور، بدون هوش مصنوعی</RuleTag><Tag tone={ft}>{fl}</Tag></div>
      </div>
      <p className="brief-narrative">{p.narrative_fa}</p>
      <div className="brief-stats">
        <div><strong>{fmt(p.totals.items_24h)}</strong><span>خبر در ۲۴ ساعت</span></div>
        <div><strong className={p.totals.change_pct != null && p.totals.change_pct < 0 ? 'down' : 'up'}>{p.totals.change_pct == null ? '—' : fmtSigned(p.totals.change_pct) + '٪'}</strong><span>نسبت به ۲۴ ساعت قبل</span></div>
        <div><strong>{fmt(p.totals.active_sources)}</strong><span>منبع فعال</span></div>
      </div>
      <h3 className="brief-sub">تحولات کلیدی</h3>
      {p.key_developments.length === 0 ? <p className="muted">در ۲۴ ساعت گذشته خبر موضوعی ثبت نشده است.</p> : (
        <ol className="brief-devs">
          {p.key_developments.slice(0, 6).map((d) => (
            <li key={d.item_id}>
              <Link href={d.href} dir={d.headline_lang === 'en' ? 'ltr' : 'rtl'}>{d.headline}</Link>
              <span><bdi>{d.source_name}</bdi> · {fmtRelative(d.published_at, now)} <ImportanceTag level={d.importance_level} /></span>
            </li>
          ))}
        </ol>
      )}
      <div className="brief-foot">
        <span>تولید: {fmtDateTime(b.generated_at)} · {b.generator_version}</span>
        <Link href="/briefing" className="sec-link">گزارش کامل و شواهد</Link>
      </div>
      <div className="brief-ai">
        <AiTag>خلاصه مدیریتی هوش مصنوعی</AiTag>
        <span>{AI_STATUS[q.data.ai.status] ?? q.data.ai.status}</span>
      </div>
    </section>
  );
}

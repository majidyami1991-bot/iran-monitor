'use client';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Shell } from '../../design/Shell';
import { useApi, useNow } from '../../design/useApi';
import type { FeedItem } from '../../design/types';
import { fmt, fmtDateTime, fmtDay, fmtPercent, fmtRelative, safeUrl, sourceColor } from '../../design/format';
import { Failure, PageHead, SourceMark, Tag, Bone, CardBones, Empty } from '../../design/ui';
import { Bars, Columns, Figure } from '../../design/charts';
import { NewsCard } from '../../components/NewsCard';
import { freshness, health, type Profile, TYPE_FA } from '../SourcesList';

interface Detail extends Profile {
  topics: { category_id: string; category_label: string; n: number }[];
  timeline_30d: { day: string; n: number }[];
  runs: { run_id: string; started_at: string; status: string; http_status: number | null; observed: number; inserted: number; duplicates: number; error_class: string | null }[];
  hours: { h: number; n: number }[];
  recent: FeedItem[];
}
const CH: Record<string, [string, 'ok' | 'uncertain']> = { active: ['فعال', 'ok'], inactive: ['غیرفعال', 'uncertain'], not_configured: ['پیکربندی نشده', 'uncertain'] };

export function SourceDetail() {
  const { id } = useParams<{ id: string }>();
  const q = useApi<Detail>('source-profiles/' + encodeURIComponent(id), [id]);
  const now = useNow();
  if (q.error) return <Shell><Failure onRetry={q.reload}>این منبع پیدا نشد.</Failure></Shell>;
  if (!q.data) return <Shell><Bone h={28} w="40%" /><CardBones n={3} /></Shell>;
  const s = q.data;
  const [hl, ht] = health(s);
  const [fl, ft] = freshness(s.freshness_minutes);
  const byDay = new Map(s.timeline_30d.map((x) => [x.day.slice(0, 10), x.n]));
  const days = Array.from({ length: 30 }, (_, i) => { const d = new Date(Date.now() - (29 - i) * 86400000).toISOString().slice(0, 10); return { key: d, label: fmtDay(d), value: byDay.get(d) ?? 0 }; });
  const hours = Array.from({ length: 24 }, (_, h) => ({ key: String(h), label: `${fmt(h)}:۰۰`, value: s.hours.find((x) => x.h === h)?.n ?? 0 }));
  const site = safeUrl(s.canonical_url);
  return (
    <Shell>
      <nav className="muted" aria-label="مسیر"><Link href="/sources">منابع</Link></nav>
      <PageHead eyebrow={TYPE_FA[s.source_type ?? ''] ?? 'منبع'} title={s.name}>
        <SourceMark name={s.name} color={sourceColor(s.source_id)} size={48} />
      </PageHead>
      <div className="card-flags"><Tag tone={ht}>{hl}</Tag><Tag tone={ft}>{fl}</Tag>
        {Object.entries(s.channels).map(([k, v]) => <Tag key={k} tone={CH[v]?.[1] ?? 'uncertain'}>{k.toUpperCase()}: {CH[v]?.[0] ?? v}</Tag>)}
      </div>
      <div className="detail">
        <div className="detail-main">
          <div className="stat-row">
            <div className="stat"><span className="stat-label">کل خبرها</span><strong className="stat-value">{fmt(s.item_count)}</strong><span className="stat-note">{fmtPercent(s.coverage_share, 1)} از کل پوشش</span></div>
            <div className="stat"><span className="stat-label">۲۴ ساعت / ۷ روز</span><strong className="stat-value">{fmt(s.items_24h)} / {fmt(s.items_7d)}</strong></div>
            <div className="stat"><span className="stat-label">موفقیت دریافت ۷ روز</span><strong className="stat-value">{s.success_rate_7d == null ? '—' : fmtPercent(s.success_rate_7d)}</strong><span className="stat-note">{fmt(s.runs_ok_7d)} از {fmt(s.runs_7d)} اجرا</span></div>
            <div className="stat"><span className="stat-label">آخرین دریافت</span><strong className="stat-value" style={{ fontSize: 16 }}>{fmtRelative(s.last_received, now)}</strong></div>
          </div>
          <div className="grid-2">
            <Figure title="خط زمانی انتشار" question="این منبع در ۳۰ روز اخیر هر روز چند خبر منتشر کرده است؟" unit="خبر" range="۳۰ روز" source="زمان انتشار در خوراک">
              <Columns data={days} height={130} />
            </Figure>
            <Figure title="ساعت‌های انتشار" question="این منبع معمولاً در چه ساعتی منتشر می‌کند؟" unit="خبر" range="همه زمان‌ها" source="به وقت تهران">
              <Columns data={hours} height={130} />
            </Figure>
          </div>
          <Figure title="توزیع موضوعی" question="این منبع بیشتر درباره چه موضوعاتی می‌نویسد؟" unit="خبر" source="طبقه‌بندی نسخه ۳"
            empty={s.topics.length ? undefined : <Empty title="خبری طبقه‌بندی نشده" />}>
            <Bars data={s.topics.map((t) => ({ key: t.category_id, label: t.category_label, value: t.n }))} href={(k) => `/news?source_id=${s.source_id}&category=${k}`} />
          </Figure>
          <section>
            <h2 className="brief-sub">خبرهای اخیر</h2>
            {s.recent.length ? s.recent.map((i) => <NewsCard key={i.item_id} item={i} now={now} variant="row" />) : <Empty title="خبری ثبت نشده" />}
            <Link href={`/news?source_id=${s.source_id}`} className="sec-link">همه خبرهای این منبع</Link>
          </section>
        </div>
        <aside className="side">
          <section className="panel">
            <div className="panel-title"><h3>شناسنامه منبع</h3></div>
            <dl className="kv">
              <dt>نام رسمی</dt><dd>{s.has_official_name ? <bdi>{s.name}</bdi> : <span className="muted">ثبت نشده</span>}</dd>
              <dt>میزبان</dt><dd dir="ltr">{s.hostname}</dd>
              <dt>وب‌سایت</dt><dd>{site ? <a href={site} target="_blank" rel="noopener noreferrer nofollow" dir="ltr" className="sec-link">{site}</a> : '—'}</dd>
              <dt>نوع</dt><dd>{TYPE_FA[s.source_type ?? ''] ?? 'ثبت نشده'}</dd>
              <dt>زبان</dt><dd>{s.language ? <><bdi>{s.language}</bdi> <small className="muted">(اعلام‌شده در خوراک)</small></> : 'اعلام نشده'}</dd>
              <dt>کشور</dt><dd className="muted">ثبت نشده — بدون منبع مستند ثبت نمی‌شود</dd>
              <dt>ردیف گردآوری</dt><dd dir="ltr">{s.collection_tier ?? '—'}</dd>
              <dt>آخرین تلاش</dt><dd>{fmtDateTime(s.last_attempt_at)}{s.last_http_status ? ` · HTTP ${s.last_http_status}` : ''}</dd>
              <dt>آخرین موفقیت</dt><dd>{fmtDateTime(s.last_success_at)}</dd>
              <dt>خطای پیاپی</dt><dd>{fmt(s.consecutive_failures)}</dd>
              <dt>منشأ کامل</dt><dd>{fmtPercent(s.provenance_pct)} ({fmt(s.provenance_complete)} خبر)</dd>
              <dt>دارای خلاصه</dt><dd>{fmt(s.with_summary)} خبر</dd>
            </dl>
          </section>
          <section className="panel">
            <div className="panel-title"><h3>آخرین اجراها</h3></div>
            <div className="table-scroll"><table className="data">
              <thead><tr><th>زمان</th><th>وضعیت</th><th>مشاهده</th><th>جدید</th></tr></thead>
              <tbody>{s.runs.slice(0, 12).map((r) => <tr key={r.run_id}><td>{fmtRelative(r.started_at, now)}</td><td>{r.status === 'succeeded' ? <Tag tone="ok">موفق</Tag> : <Tag tone="error">{r.error_class ?? r.status}</Tag>}</td><td>{fmt(r.observed)}</td><td>{fmt(r.inserted)}</td></tr>)}</tbody>
            </table></div>
          </section>
        </aside>
      </div>
    </Shell>
  );
}

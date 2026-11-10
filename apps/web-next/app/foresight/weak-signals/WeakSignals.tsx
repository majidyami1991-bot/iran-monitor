'use client';
import Link from 'next/link';
import { Shell } from '../../design/Shell';
import { useApi, useNow } from '../../design/useApi';
import { fmt, fmtRelative } from '../../design/format';
import { CardBones, Empty, Failure, PageHead } from '../../design/ui';
import { Figure } from '../../design/charts';
import { ForesightNote } from '../ForesightNote';

interface Signal { term: string; count_7d: number; sources_7d: number; first_seen: string; last_seen: string; example_item_id: string; example_title: string; item_ids: string[] }
interface Resp { method_fa: string; signals: Signal[]; total: number }

/** Quadrant: x = frequency in the last 7 days, y = number of independent
 *  sources. Top-right = recurring and corroborated; bottom-left = faint. */
function Quadrant({ signals }: { signals: Signal[] }) {
  const maxX = Math.max(3, ...signals.map((s) => s.count_7d));
  const maxY = Math.max(2, ...signals.map((s) => s.sources_7d));
  const W = 560, H = 300, P = 36;
  const x = (v: number) => P + ((v - 1) / Math.max(1, maxX - 1)) * (W - 2 * P);
  const y = (v: number) => H - P - ((v - 1) / Math.max(1, maxY - 1)) * (H - 2 * P);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="نمودار ربعی سیگنال‌های ضعیف: بسامد در برابر تعداد منابع" style={{ maxHeight: 340, direction: 'ltr' }}>
      <line x1={P} y1={H - P} x2={W - P} y2={H - P} stroke="var(--line-3)" />
      <line x1={P} y1={P} x2={P} y2={H - P} stroke="var(--line-3)" />
      <line x1={(W) / 2} y1={P} x2={W / 2} y2={H - P} stroke="var(--grid)" strokeDasharray="4 4" />
      <line x1={P} y1={H / 2} x2={W - P} y2={H / 2} stroke="var(--grid)" strokeDasharray="4 4" />
      <text x={W - P} y={H - 8} fill="var(--ink-3)" fontSize="11" textAnchor="end">بسامد در ۷ روز ←</text>
      <text x={8} y={P - 12} fill="var(--ink-3)" fontSize="11">↑ منابع مستقل</text>
      {signals.map((s, i) => (
        <a key={s.term} href={`/news/${s.example_item_id}`}>
          <circle cx={x(s.count_7d) + ((i % 3) - 1) * 4} cy={y(s.sources_7d) + ((i % 2) * 2 - 1) * 3} r="6" fill="var(--series-1)" stroke="var(--panel)" strokeWidth="2">
            <title>{`${s.term}: ${s.count_7d} خبر، ${s.sources_7d} منبع`}</title>
          </circle>
          {i < 8 && <text x={x(s.count_7d) + 9} y={y(s.sources_7d) + 4} fill="var(--ink-2)" fontSize="11">{s.term}</text>}
        </a>
      ))}
    </svg>
  );
}

export function WeakSignals() {
  const q = useApi<Resp>('foresight/weak-signals');
  const now = useNow();
  const d = q.data;
  return (
    <Shell>
      <PageHead eyebrow="آینده‌پژوهی" title="سیگنال‌های ضعیف" />
      <ForesightNote>{d?.method_fa ?? 'نام‌های تازه کم‌بسامد.'}</ForesightNote>
      {q.error && <Failure onRetry={q.reload} />}
      {!d && !q.error && <CardBones n={3} image={false} />}
      {d && d.signals.length === 0 && <Empty title="در ۷ روز اخیر نام تازه‌ای با دست‌کم دو خبر ظاهر نشده است" />}
      {d && d.signals.length > 0 && (
        <>
          <Figure title="بسامد در برابر تأیید منابع" question="کدام نام‌های تازه هم تکرار شده‌اند و هم در چند منبع مستقل آمده‌اند؟" unit="خبر / منبع" range="۷ روز در برابر ۳۰ روز قبل" source="عنوان خبرها"
            table={{ head: ['نام', 'خبر', 'منبع'], rows: d.signals.map((s) => [s.term, s.count_7d, s.sources_7d]) }}>
            <Quadrant signals={d.signals} />
          </Figure>
          <div className="table-scroll panel">
            <table className="data">
              <thead><tr><th>نام</th><th>خبر در ۷ روز</th><th>منبع مستقل</th><th>نخستین ظهور</th><th>نمونه خبر</th></tr></thead>
              <tbody>{d.signals.map((s) => (
                <tr key={s.term}><td dir="ltr"><b>{s.term}</b></td><td>{fmt(s.count_7d)}</td><td>{fmt(s.sources_7d)}</td><td>{fmtRelative(s.first_seen, now)}</td>
                  <td style={{ whiteSpace: 'normal', minWidth: 260 }}><Link href={`/news/${s.example_item_id}`} dir="ltr" className="sec-link">{s.example_title}</Link></td></tr>
              ))}</tbody>
            </table>
          </div>
        </>
      )}
    </Shell>
  );
}

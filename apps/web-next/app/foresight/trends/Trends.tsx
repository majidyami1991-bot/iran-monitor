'use client';
import Link from 'next/link';
import { Shell } from '../../design/Shell';
import { useApi } from '../../design/useApi';
import { catVar, fmt, fmtSigned } from '../../design/format';
import { CardBones, Empty, Failure, PageHead } from '../../design/ui';
import { Figure, Sparkline } from '../../design/charts';
import { ForesightNote } from '../ForesightNote';

interface Trends { method_fa: string; category_daily: { category_id: string; category_label: string; day: string; n: number }[]; subtopic_momentum: { id: string; label: string; n7: number; p7: number; momentum: number }[] }

export function Trends() {
  const q = useApi<Trends>('foresight/trends');
  const d = q.data;
  const cats = d ? [...new Map(d.category_daily.map((c) => [c.category_id, c.category_label])).entries()] : [];
  const series = (id: string) => Array.from({ length: 28 }, (_, i) => {
    const day = new Date(Date.now() - (27 - i) * 86400000).toISOString().slice(0, 10);
    return d!.category_daily.find((c) => c.category_id === id && c.day.slice(0, 10) === day)?.n ?? 0;
  });
  return (
    <Shell>
      <PageHead eyebrow="آینده‌پژوهی" title="روندهای پوشش" />
      <ForesightNote>{d?.method_fa ?? 'مقایسه توصیفی حجم پوشش خبری.'}</ForesightNote>
      {q.error && <Failure onRetry={q.reload} />}
      {!d && !q.error && <CardBones n={3} image={false} />}
      {d && (
        <div className="grid-2">
          <Figure title="حجم روزانه هر موضوع" question="پوشش هر موضوع در چهار هفته اخیر چه شکلی داشته است؟" unit="خبر در روز" range="۲۸ روز" source="طبقه‌بندی نسخه ۳"
            empty={cats.length ? undefined : <Empty title="داده کافی نیست" />}>
            <ul className="bars">
              {cats.map(([id, label]) => {
                const s = series(id);
                return <li key={id}><Link href={`/topics/${id}`} className="bars-row"><span className="bars-label"><i style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 2, background: catVar(id), marginInlineEnd: 6 }} />{label}</span><Sparkline values={s} width={200} height={28} label={`${label}: ${fmt(s.reduce((a, b) => a + b, 0))} خبر در ۲۸ روز`} /><span className="bars-value">{fmt(s.reduce((a, b) => a + b, 0))}</span></Link></li>;
              })}
            </ul>
          </Figure>
          <Figure title="شتاب زیرموضوع‌ها" question="پوشش کدام زیرموضوع‌ها در ۷ روز اخیر نسبت به ۷ روز قبل بیشترین تغییر را داشته است؟" unit="خبر" range="۱۴ روز" source="زیرموضوع‌های طبقه‌بندی نسخه ۳"
            table={{ head: ['زیرموضوع', '۷ روز قبل', '۷ روز اخیر', 'تغییر'], rows: d.subtopic_momentum.map((s) => [s.label, s.p7, s.n7, fmtSigned(s.momentum)]) }}>
            <ul className="delta-list">
              {[...d.subtopic_momentum].sort((a, b) => Math.abs(b.momentum) - Math.abs(a.momentum)).slice(0, 14).map((s) => (
                <li key={s.id}><Link href={`/topics/${s.id}`}>{s.label}</Link>
                  <span className={s.momentum >= 0 ? 'delta delta-up' : 'delta delta-down'}>{fmtSigned(s.momentum)}</span>
                  <small>{fmt(s.p7)} ← {fmt(s.n7)}</small></li>
              ))}
            </ul>
          </Figure>
        </div>
      )}
    </Shell>
  );
}

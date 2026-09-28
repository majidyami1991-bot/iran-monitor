'use client';
import Link from 'next/link';
import { Shell } from '../../design/Shell';
import { useApi } from '../../design/useApi';
import { catVar, fmt } from '../../design/format';
import { CardBones, Empty, Failure, PageHead } from '../../design/ui';
import { Figure, Matrix, SeqLegend } from '../../design/charts';
import { ForesightNote } from '../ForesightNote';

interface Resp {
  scope_fa: string;
  steep: { key: string; label: string; categories: { id: string; label: string; n30: number; total: number }[] }[];
  co_occurrence: { a: string; b: string; n: number }[];
  labels: Record<string, string>;
  drivers: unknown[];
}

export function Drivers() {
  const q = useApi<Resp>('foresight/drivers');
  const d = q.data;
  const ids = d ? Object.keys(d.labels) : [];
  const co = (r: string, c: string) => d?.co_occurrence.filter((x) => (x.a === r && x.b === c) || (x.a === c && x.b === r)).reduce((a, x) => a + x.n, 0) ?? 0;
  const max = d ? Math.max(1, ...ids.flatMap((r) => ids.map((c) => (r === c ? 0 : co(r, c))))) : 1;
  return (
    <Shell>
      <PageHead eyebrow="آینده‌پژوهی" title="پیشران‌ها و STEEP" />
      <ForesightNote>{d?.scope_fa ?? 'نگاشت موضوعی.'}</ForesightNote>
      {q.error && <Failure onRetry={q.reload} />}
      {!d && !q.error && <CardBones n={3} image={false} />}
      {d && (
        <>
          <div className="topic-grid">
            {d.steep.map((s) => (
              <article key={s.key} className="topic-card" style={{ ['--art' as string]: 'var(--brand)' }}>
                <h3>{s.label} <small className="muted" dir="ltr">({s.key})</small></h3>
                <div className="topic-num"><strong>{fmt(s.categories.reduce((a, c) => a + c.n30, 0))}</strong><span className="muted">خبر در ۳۰ روز</span></div>
                <ul className="delta-list">{s.categories.map((c) => <li key={c.id}><Link href={`/topics/${c.id}`} className="cat-tag"><i style={{ background: catVar(c.id) }} />{c.label}</Link><small>{fmt(c.n30)}</small></li>)}</ul>
              </article>
            ))}
          </div>
          <Figure title="هم‌رخدادی موضوعات در یک خبر" question="کدام موضوعات بیشتر با هم در یک خبر دیده می‌شوند؟" unit="خبر" source="دسته اصلی × موضوع فرعی، طبقه‌بندی نسخه ۳"
            legend={<SeqLegend max={max} unit="خبر" />}>
            <Matrix rows={ids} cols={ids} value={(r, c) => (r === c ? 0 : co(r, c))} rowLabel={(r) => d.labels[r]} colLabel={(c) => d.labels[c]} />
            <p className="fig-note">این ماتریس هم‌رخدادی است، نه اثر متقابل: نشان می‌دهد موضوعات چقدر با هم گزارش می‌شوند، نه اینکه بر هم اثر می‌گذارند.</p>
          </Figure>
          <Empty title="پیشرانی ثبت نشده است">شناسایی پیشران و ارزیابی اهمیت و عدم‌قطعیت آن کار تحلیلگر است. هیچ پیشرانی به‌صورت خودکار یا نمایشی ساخته نمی‌شود.</Empty>
        </>
      )}
    </Shell>
  );
}

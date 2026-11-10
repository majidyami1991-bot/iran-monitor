'use client';
import type { ReactNode } from 'react';
import { fmt } from './format';

/* Chart kit. Rules (docs/COMMERCIAL DESIGN SYSTEM.md, dataviz method):
   - every chart answers one question, stated in its title;
   - one hue for one series (sequential blue), status colours never used as series;
   - thin marks, rounded data-ends on the baseline, recessive grid;
   - hover/focus tooltip on every mark, plus a table view for keyboard and
     screen-reader users (<details>), so nothing is colour- or hover-only;
   - time runs left→right inside the plot (dir=ltr), labelled at the ends. */

export function Figure({ title, question, unit, range, source, children, table, legend, empty }: {
  title: string; question?: string; unit?: string; range?: string; source?: string;
  children: ReactNode; table?: { head: string[]; rows: (string | number)[][] }; legend?: ReactNode; empty?: ReactNode;
}) {
  return (
    <figure className="fig">
      <figcaption>
        <h3>{title}</h3>
        {question && <p>{question}</p>}
        <div className="fig-meta">
          {unit && <span>واحد: {unit}</span>}
          {range && <span>بازه: {range}</span>}
          {source && <span>منبع: {source}</span>}
        </div>
      </figcaption>
      {legend && <div className="fig-legend">{legend}</div>}
      {empty ?? children}
      {table && table.rows.length > 0 && !empty && (
        <details className="fig-table">
          <summary>نمایش جدول داده</summary>
          <div className="table-scroll">
            <table>
              <thead><tr>{table.head.map((h) => <th key={h}>{h}</th>)}</tr></thead>
              <tbody>{table.rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{typeof c === 'number' ? fmt(c) : c}</td>)}</tr>)}</tbody>
            </table>
          </div>
        </details>
      )}
    </figure>
  );
}

export function LegendKey({ items }: { items: { label: string; color: string; pattern?: boolean }[] }) {
  return (
    <ul className="legend">
      {items.map((i) => <li key={i.label}><i style={{ background: i.color }} className={i.pattern ? 'hatch' : undefined} />{i.label}</li>)}
    </ul>
  );
}

/** Vertical columns over time. `data` oldest first. */
export function Columns({ data, height = 150, unit = 'خبر', color = 'var(--series-1)', highlightLast = false }: {
  data: { key: string; label: string; value: number; tip?: string }[]; height?: number; unit?: string; color?: string; highlightLast?: boolean;
}) {
  const max = Math.max(1, ...data.map((d) => d.value));
  const ticks = [max, Math.round(max / 2), 0];
  return (
    <div className="cols" style={{ height }} dir="ltr">
      <div className="cols-axis" aria-hidden="true">{ticks.map((t, i) => <span key={i}>{fmt(t)}</span>)}</div>
      <div className="cols-plot">
        <div className="cols-grid" aria-hidden="true"><i /><i /><i /></div>
        {data.map((d, i) => (
          <div key={d.key} className="col" aria-label={`${d.label}: ${fmt(d.value)} ${unit}`}>
            <span className="col-bar" style={{ height: `${(d.value / max) * 100}%`, background: highlightLast && i === data.length - 1 ? 'var(--seq-300)' : color }} />
            <span className="tip" dir="rtl"><b>{fmt(d.value)} {unit}</b>{d.tip ?? d.label}</span>
          </div>
        ))}
      </div>
      <div className="cols-x" aria-hidden="true">
        <span>{data[0]?.label}</span>
        {data.length > 2 && <span>{data[Math.floor(data.length / 2)]?.label}</span>}
        <span>{data[data.length - 1]?.label}</span>
      </div>
    </div>
  );
}

/** Horizontal bars for ranked categories (reads naturally in RTL). */
export function Bars({ data, unit = 'خبر', max: forcedMax, href }: {
  data: { key: string; label: ReactNode; value: number; note?: ReactNode; color?: string }[];
  unit?: string; max?: number; href?: (key: string) => string;
}) {
  const max = forcedMax ?? Math.max(1, ...data.map((d) => d.value));
  return (
    <ul className="bars">
      {data.map((d) => {
        const body = (
          <>
            <span className="bars-label">{d.label}</span>
            <span className="bars-track"><span className="bars-fill" style={{ width: `${Math.max(d.value ? 1.5 : 0, (d.value / max) * 100)}%`, background: d.color ?? 'var(--series-1)' }} /></span>
            <span className="bars-value">{fmt(d.value)}{d.note && <small>{d.note}</small>}</span>
          </>
        );
        return (
          <li key={d.key} title={`${fmt(d.value)} ${unit}`}>
            {href ? <a href={href(d.key)} className="bars-row">{body}</a> : <div className="bars-row">{body}</div>}
          </li>
        );
      })}
    </ul>
  );
}

export function Sparkline({ values, width = 120, height = 32, label }: { values: number[]; width?: number; height?: number; label: string }) {
  if (values.length < 2) return <span className="spark-empty">داده کافی نیست</span>;
  const max = Math.max(1, ...values);
  const step = width / (values.length - 1);
  const pts = values.map((v, i) => `${(i * step).toFixed(1)},${(height - 2 - (v / max) * (height - 4)).toFixed(1)}`).join(' ');
  return (
    <svg className="spark" width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={label}>
      <polyline points={pts} fill="none" stroke="var(--series-1)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={(values.length - 1) * step} cy={height - 2 - (values[values.length - 1] / max) * (height - 4)} r="3" fill="var(--series-1)" />
    </svg>
  );
}

const SEQ = ['var(--panel-2)', 'var(--seq-700)', 'var(--seq-600)', 'var(--seq-500)', 'var(--seq-400)', 'var(--seq-300)', 'var(--seq-200)'];
export function seqColor(v: number, max: number) {
  if (!v) return SEQ[0];
  return SEQ[Math.min(SEQ.length - 1, 1 + Math.floor((v / Math.max(1, max)) * (SEQ.length - 1.001)))];
}

/** Rows × columns of counts on one sequential ramp. */
export function Matrix({ rows, cols, value, rowLabel, colLabel, unit = 'خبر', rowHref }: {
  rows: string[]; cols: string[]; value: (r: string, c: string) => number;
  rowLabel: (r: string) => ReactNode; colLabel: (c: string) => string; unit?: string; rowHref?: (r: string) => string;
}) {
  let max = 1;
  for (const r of rows) for (const c of cols) max = Math.max(max, value(r, c));
  return (
    <div className="table-scroll">
      <table className="matrix">
        <thead><tr><th />{cols.map((c) => <th key={c} scope="col"><span>{colLabel(c)}</span></th>)}</tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r}>
              <th scope="row">{rowHref ? <a href={rowHref(r)}>{rowLabel(r)}</a> : rowLabel(r)}</th>
              {cols.map((c) => {
                const v = value(r, c);
                return <td key={c} style={{ background: seqColor(v, max), color: v / max > 0.55 ? 'var(--ink-inverse)' : 'var(--ink-2)' }}
                  title={`${colLabel(c)}: ${fmt(v)} ${unit}`}>{v ? fmt(v) : ''}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SeqLegend({ max, unit }: { max: number; unit: string }) {
  return (
    <div className="seq-legend" aria-hidden="true">
      <span>۰</span>{SEQ.map((c, i) => <i key={i} style={{ background: c }} />)}<span>{fmt(max)} {unit}</span>
    </div>
  );
}

/** Stacked share bar with labelled segments (2px surface gaps). */
export function ShareBar({ parts }: { parts: { key: string; label: string; value: number; color: string }[] }) {
  const total = parts.reduce((a, p) => a + p.value, 0) || 1;
  return (
    <div>
      <div className="share" role="img" aria-label={parts.map((p) => `${p.label}: ${fmt(p.value)}`).join('، ')}>
        {parts.filter((p) => p.value > 0).map((p) => (
          <span key={p.key} style={{ width: `${(p.value / total) * 100}%`, background: p.color }} title={`${p.label}: ${fmt(p.value)}`} />
        ))}
      </div>
      <LegendKey items={parts.map((p) => ({ label: `${p.label} (${fmt(p.value)})`, color: p.color }))} />
    </div>
  );
}

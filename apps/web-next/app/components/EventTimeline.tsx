'use client';
import Link from 'next/link';
import type { EventRow } from '../design/types';
import { fmt, fmtDateTime, fmtRelative, fmtTime } from '../design/format';
import { CategoryTag, Tag } from '../design/ui';

const CONF: Record<string, [string, 'ok' | 'warn' | 'uncertain']> = {
  high: ['اطمینان زیاد', 'ok'], medium: ['اطمینان متوسط', 'warn'], low: ['اطمینان کم', 'uncertain'],
};

export function ConfidenceTag({ level }: { level: EventRow['confidence_level'] }) {
  const [label, tone] = CONF[level ?? ''] ?? ['اطمینان نامشخص', 'uncertain'];
  return <Tag tone={tone} title="میانگین امتیاز شباهت دوبه‌دوی اعضای رویداد (خوشه‌بندی قطعی)">{label}</Tag>;
}

/** Coverage intensity: each member article as a tick on the event's own time
 *  span — shows whether coverage came in one burst or kept developing. */
export function Pulse({ pulses, label }: { pulses: EventRow['pulses']; label: string }) {
  const ts = (pulses ?? []).map((p) => (p.t ? Date.parse(p.t) : NaN)).filter((x) => !Number.isNaN(x));
  if (ts.length < 2) return null;
  const min = Math.min(...ts), max = Math.max(...ts), span = Math.max(1, max - min);
  const hours = Math.round(span / 3600000);
  return (
    <div className="pulse" role="img" aria-label={`${label}: ${fmt(ts.length)} خبر در ${fmt(hours)} ساعت`} dir="ltr">
      <span className="pulse-line" />
      {ts.map((t, i) => <i key={i} style={{ left: `${((t - min) / span) * 100}%` }} />)}
      <small className="pulse-span">{hours < 1 ? 'کمتر از یک ساعت' : `${fmt(hours)} ساعت`}</small>
    </div>
  );
}

export function EventTimeline({ events, now, compact = false }: { events: EventRow[]; now: number; compact?: boolean }) {
  return (
    <ol className={compact ? 'timeline timeline-compact' : 'timeline'}>
      {events.map((e) => (
        <li key={e.event_id} className="tl-item">
          <div className="tl-when">
            <time dateTime={e.last_updated_at ?? undefined} title={`آخرین تحول: ${fmtDateTime(e.last_updated_at)}`}>{fmtTime(e.last_updated_at)}</time>
            <small>{fmtRelative(e.last_updated_at, now)}</small>
          </div>
          <span className="tl-dot" aria-hidden="true" />
          <div className="tl-body">
            <div className="card-flags">
              <CategoryTag id={e.primary_category} label={e.primary_category_label ?? (e.primary_category ? null : 'دسته غالب ندارد')} href={!!e.primary_category} />
              <ConfidenceTag level={e.confidence_level} />
              {e.source_count >= 2 && <Tag tone="brand">{fmt(e.source_count)} منبع مستقل</Tag>}
            </div>
            <h3 dir="ltr"><Link href={`/events/${e.event_id}`}>{e.title}</Link></h3>
            <p className="tl-meta">
              {fmt(e.member_count)} خبر · شروع {fmtRelative(e.first_published_at, now)}
              {e.sources && e.sources.length > 0 && <> · <span className="tl-sources">{e.sources.map((s, i) => <span key={s.source_id}>{i > 0 && '، '}<bdi>{s.name}</bdi></span>)}</span></>}
            </p>
            {!compact && <Pulse pulses={e.pulses} label="روند پوشش" />}
          </div>
        </li>
      ))}
    </ol>
  );
}

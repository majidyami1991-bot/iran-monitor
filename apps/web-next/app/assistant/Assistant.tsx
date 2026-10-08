'use client';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { Cpu, ExternalLink, Newspaper, Send, Square, Trash2 } from 'lucide-react';
import { Shell } from '../design/Shell';
import { useApi } from '../design/useApi';
import { fmt, fmtDateTime, safeUrl } from '../design/format';
import { Empty, PageHead, Segmented, Tag } from '../design/ui';

/** «دستیار هوشمند» — answers only from Defence Monitor's own records, with the
 *  local model. The page talks to /api/v1/assistant/* only; it never calls
 *  Ollama, never triggers a translation, and renders every model or collected
 *  string as a React text node (never HTML). */

type Window = '24h' | '7d' | '30d' | 'all';
type Kind = 'all' | 'news' | 'x';
interface Citation {
  evidence_id: string; type: 'news' | 'x'; record_id: string; title: string; title_original: string | null;
  source_name: string | null; published_at: string | null; canonical_url: string | null; internal_url: string;
  category_label: string | null;
}
interface Result {
  answer: string; confidence: 'high' | 'medium' | 'low'; citations: Citation[]; limitations: string[];
  follow_up_suggestions: string[]; kind: 'answer' | 'no_evidence' | 'rejected'; model: string; latency_ms: number;
  context_record_count: number; tokens_in: number | null; tokens_out: number | null; cache_hit: boolean; window: string;
}
interface Msg { id: string; role: 'user' | 'assistant'; content: string; result?: Result }
interface ReqView { request_id: string; session_id: string; status: string; queue_position: number; error: string | null; result?: Result }
interface Status {
  enabled: boolean; ollama_reachable: boolean; model_found: boolean; model: string; model_busy: boolean;
  translation_batch_running: boolean; queue_length: number; generating: boolean;
  limits: { max_records: number; history_turns: number; max_output_tokens: number; retention_days: number };
}
interface Usage {
  inferences: number; translation_inferences: number; assistant_inferences: number; cache_hits: number;
  input_tokens: number; output_tokens: number; average_latency_ms: number | null; assistant_average_latency_ms: number | null;
  queue_length: number; failed: number; translation_pending: number; translation_failed_jobs: number;
  model_available: boolean; reported_cost_usd: number;
}

const SESSION_KEY = 'dm.assistant.session';
const TERMINAL = ['done', 'rejected', 'cancelled', 'error'];
const SUGGESTIONS = [
  'در ۲۴ ساعت گذشته چه اتفاقاتی افتاده است؟',
  'مهم‌ترین اخبار امروز چیست؟',
  'درباره F-35 چه خبرهایی منتشر شده است؟',
  'کدام منابع درباره پهپادها نوشته‌اند و روایتشان چه تفاوتی دارد؟',
  'آیا اطلاعات موجود درباره آزمایش موشکی کافی است؟',
];
const CONF_FA: Record<string, [string, 'ok' | 'warn' | 'uncertain']> = {
  high: ['اطمینان زیاد', 'ok'], medium: ['اطمینان متوسط', 'warn'], low: ['اطمینان کم', 'uncertain'],
};
const STATUS_FA: Record<string, string> = {
  queued: 'در صف پردازش محلی', retrieving: 'در حال جست‌وجو در داده‌های سامانه',
  waiting_for_model: 'مدل محلی مشغول است؛ درخواست شما در صف است', generating: 'در حال تولید پاسخ با مدل محلی',
};
const ERROR_FA: Record<string, string> = {
  queue_full: 'صف دستیار پر است؛ کمی بعد دوباره تلاش کنید.', rate_limited: 'تعداد درخواست‌ها زیاد است؛ یک دقیقه صبر کنید.',
  session_busy: 'پاسخ قبلی هنوز در حال آماده‌شدن است.', assistant_disabled: 'دستیار در این محیط غیرفعال است.',
  origin_not_allowed: 'درخواست از مبدأ مجاز ارسال نشده است.', provider_unreachable: 'مدل محلی در دسترس نیست.',
  model_busy: 'مدل محلی مشغول است؛ زمان انتظار به پایان رسید.', transient_timeout: 'زمان پاسخ مدل محلی به پایان رسید.',
  internal_error: 'خطای داخلی؛ هیچ پاسخی ساخته نشد.',
};

function readSession(): string | null {
  try { return window.localStorage.getItem(SESSION_KEY); } catch { return null; }
}
function writeSession(id: string | null) {
  try { if (id) window.localStorage.setItem(SESSION_KEY, id); else window.localStorage.removeItem(SESSION_KEY); } catch { /* storage unavailable */ }
}
async function post<T>(path: string, body: unknown, method = 'POST'): Promise<{ ok: boolean; status: number; data: T & { detail?: unknown } }> {
  const r = await fetch('/api/v1/' + path, { method, cache: 'no-store', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body ?? {}) });
  return { ok: r.ok, status: r.status, data: await r.json().catch(() => ({})) };
}

/** Answer text with [E1]-style markers turned into links to the citation cards. */
function AnswerText({ text, cites }: { text: string; cites: Map<string, number> }) {
  const parts = text.split(/(\[E\d{1,2}\])/g);
  return (
    <p className="as-answer prose-justify" dir="rtl" lang="fa">
      {parts.map((p, i) => {
        const m = /^\[(E\d{1,2})\]$/.exec(p);
        if (!m) return <span key={i}>{p}</span>;
        const n = cites.get(m[1]);
        return n ? <a key={i} href={`#cite-${m[1]}`} className="as-cite" aria-label={`سند ${fmt(n)}`}>[{fmt(n)}]</a> : null;
      })}
    </p>
  );
}

function CitationCard({ c, n }: { c: Citation; n: number }) {
  const ext = safeUrl(c.canonical_url);
  return (
    <li className="as-evidence" id={`cite-${c.evidence_id}`}>
      <span className="as-evidence-n" aria-hidden="true">{fmt(n)}</span>
      <div className="as-evidence-body">
        <Link href={c.internal_url} className="as-evidence-title">{c.title}</Link>
        <div className="as-evidence-meta">
          <Tag tone="neutral">{c.type === 'x' ? 'پست X' : 'خبر'}</Tag>
          {c.source_name && <bdi>{c.source_name}</bdi>}
          {c.published_at && <time dateTime={c.published_at}>{fmtDateTime(c.published_at)}</time>}
          {ext && <a href={ext} target="_blank" rel="noopener noreferrer nofollow" className="sec-link">منبع اصلی<ExternalLink size={12} /></a>}
        </div>
      </div>
    </li>
  );
}

function AssistantMessage({ r }: { r: Result }) {
  const cites = useMemo(() => new Map(r.citations.map((c, i) => [c.evidence_id, i + 1])), [r.citations]);
  const [label, tone] = CONF_FA[r.confidence] ?? CONF_FA.low;
  return (
    <div className={`as-msg as-msg-assistant as-kind-${r.kind}`}>
      <div className="as-msg-head">
        <Tag tone={r.kind === 'answer' ? tone : 'uncertain'}>{r.kind === 'answer' ? label : r.kind === 'no_evidence' ? 'شواهد کافی نیست' : 'پاسخ رد شد'}</Tag>
        <span className="muted">مدل محلی <bdi dir="ltr">{r.model}</bdi> · {fmt(r.context_record_count)} سند · {fmt(Math.round(r.latency_ms / 1000))} ثانیه{r.cache_hit ? ' · از حافظه موقت' : ''}</span>
      </div>
      <AnswerText text={r.answer} cites={cites} />
      {r.limitations.length > 0 && (
        <div className="as-limits"><b>محدودیت‌ها</b>
          <ul>{r.limitations.map((l, i) => <li key={i} className="prose-justify">{l}</li>)}</ul>
        </div>
      )}
      {r.citations.length > 0 && (
        <ol className="as-evidence-list" aria-label="شواهد این پاسخ">
          {r.citations.map((c, i) => <CitationCard key={c.evidence_id} c={c} n={i + 1} />)}
        </ol>
      )}
    </div>
  );
}

export function Assistant() {
  const status = useApi<Status>('assistant/status');
  const usage = useApi<Usage>('assistant/usage');
  const sources = useApi<{ sources: { source_id: string; display_name: string | null; hostname: string }[] }>('sources?page_size=100');
  const topics = useApi<{ categories: { id: string; label: string }[] }>('topics?window=all');
  const [win, setWin] = useState<Window>('7d');
  const [kind, setKind] = useState<Kind>('all');
  const [source, setSource] = useState('');
  const [topic, setTopic] = useState('');
  const [text, setText] = useState('');
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [session, setSession] = useState<string | null>(null);
  const [pending, setPending] = useState<ReqView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  // Restore the last conversation (stored server-side, id kept in this browser).
  useEffect(() => {
    const id = readSession();
    if (!id) return;
    fetch('/api/v1/assistant/sessions/' + encodeURIComponent(id), { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((s: { messages: { id: number; role: 'user' | 'assistant'; content: string; payload: Result }[] }) => {
        setSession(id);
        setMsgs(s.messages.map((m) => ({ id: String(m.id), role: m.role, content: m.content, result: m.role === 'assistant' ? m.payload : undefined })));
      })
      .catch(() => writeSession(null));
  }, []);
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);
  useEffect(() => { endRef.current?.scrollIntoView({ block: 'nearest' }); }, [msgs.length, pending?.status]);

  const poll = useCallback((rid: string) => {
    fetch('/api/v1/assistant/requests/' + rid, { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((v: ReqView) => {
        setPending(v);
        if (TERMINAL.includes(v.status)) {
          if (v.result) setMsgs((m) => [...m, { id: rid, role: 'assistant', content: v.result!.answer, result: v.result }]);
          if (v.status === 'error') setError(ERROR_FA[v.error ?? ''] ?? 'پاسخ ساخته نشد.');
          if (v.status === 'cancelled') setError('تولید پاسخ متوقف شد.');
          setPending(null);
          usage.reload(); status.reload();
          return;
        }
        timer.current = setTimeout(() => poll(rid), 1500);
      })
      .catch(() => { setPending(null); setError('ارتباط با سرور قطع شد.'); });
  }, [usage, status]);

  const ask = async (question: string) => {
    const q = question.trim();
    if (q.length < 2 || pending) return;
    setError(null);
    setMsgs((m) => [...m, { id: 'u' + Date.now(), role: 'user', content: q }]);
    setText('');
    const filters = { window: win, content_type: kind, source_id: source || null, topic: topic || null };
    const r = await post<ReqView>('assistant/query', { question: q, session_id: session, filters });
    if (!r.ok) {
      const d = typeof r.data.detail === 'string' ? r.data.detail : '';
      setError(ERROR_FA[d] ?? 'درخواست پذیرفته نشد.');
      return;
    }
    setSession(r.data.session_id); writeSession(r.data.session_id);
    setPending(r.data);
    timer.current = setTimeout(() => poll(r.data.request_id), 800);
  };

  const stop = async () => {
    if (!pending) return;
    await post<ReqView>(`assistant/requests/${pending.request_id}/cancel`, {});
  };

  const clear = async () => {
    if (pending) return;
    if (session) await post('assistant/sessions/' + encodeURIComponent(session), {}, 'DELETE');
    writeSession(null); setSession(null); setMsgs([]); setError(null);
  };

  const st = status.data;
  const offline = st ? !(st.ollama_reachable && st.model_found) : false;
  const disabled = !st?.enabled || offline;
  const last = [...msgs].reverse().find((m) => m.result && m.result.citations.length > 0)?.result;

  return (
    <Shell>
      <PageHead eyebrow="دستیار هوشمند" title="دستیار هوشمند Defence Monitor"
        lede="پرسش خود را بنویسید؛ پاسخ فقط از خبرها و پست‌های ذخیره‌شده در همین سامانه ساخته می‌شود و هر ادعا به سند داخلی ارجاع دارد. مدل به‌صورت محلی روی همین رایانه اجرا می‌شود و به اینترنت دسترسی ندارد.">
        {st && (
          <Tag tone={offline ? 'warn' : 'ok'} icon={<Cpu size={12} />}>
            {offline ? 'مدل محلی در دسترس نیست' : st.generating || st.model_busy ? 'مدل محلی مشغول' : 'مدل محلی آماده'}
          </Tag>
        )}
      </PageHead>

      <div className="as-layout">
        <section className="as-chat panel" aria-label="گفت‌وگو">
          <div className="as-statusbar" role="status" data-testid="as-status">
            {st ? <>
              <span>مدل: <bdi dir="ltr">{st.model}</bdi></span>
              <span>صف CPU: {fmt(st.queue_length)}</span>
              <span>{st.translation_batch_running ? 'ترجمه دسته‌ای در حال اجرا است (پاسخ‌ها کندتر می‌شوند)' : 'ترجمه دسته‌ای فعال نیست'}</span>
            </> : <span>در حال بررسی وضعیت مدل…</span>}
          </div>
          {offline && <p className="note as-offline" role="alert">مدل محلی (Ollama) در دسترس نیست. خبرها و ترجمه‌های ذخیره‌شده همچنان در بخش‌های دیگر سامانه قابل مشاهده‌اند.</p>}

          <div className="as-thread" aria-live="polite">
            {msgs.length === 0 && !pending && (
              <Empty title="گفت‌وگو را شروع کنید">یکی از پرسش‌های آماده را انتخاب کنید یا پرسش خود را بنویسید.</Empty>
            )}
            {msgs.map((m) => m.role === 'user'
              ? <div key={m.id} className="as-msg as-msg-user"><p className="prose-justify" dir="auto">{m.content}</p></div>
              : m.result ? <AssistantMessage key={m.id} r={m.result} /> : null)}
            {pending && (
              <div className="as-msg as-msg-pending" role="status" data-testid="as-pending">
                <span className="as-dot" aria-hidden="true" />
                {STATUS_FA[pending.status] ?? 'در حال پردازش'}{pending.status === 'queued' && pending.queue_position > 0 ? ` · جایگاه ${fmt(pending.queue_position)}` : ''}
              </div>
            )}
            {error && <p className="note as-error" role="alert">{error}</p>}
            <div ref={endRef} />
          </div>

          <div className="as-suggest" aria-label="پرسش‌های آماده">
            {SUGGESTIONS.map((s) => <button key={s} type="button" className="btn-ghost" disabled={!!pending || disabled} onClick={() => ask(s)}>{s}</button>)}
          </div>

          <form className="as-input" onSubmit={(e) => { e.preventDefault(); ask(text); }}>
            <label htmlFor="as-q" className="sr-only">پرسش</label>
            <textarea id="as-q" value={text} onChange={(e) => setText(e.target.value)} maxLength={1000} rows={3}
              placeholder="مثلاً: کدام منابع درباره رزمایش‌های اخیر نوشته‌اند؟" disabled={disabled}
              onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); ask(text); } }} />
            <div className="as-input-actions">
              {pending
                ? <button type="button" className="btn-ghost" onClick={stop} data-testid="as-stop"><Square size={14} />توقف تولید پاسخ</button>
                : <button type="submit" className="btn-primary" disabled={disabled || text.trim().length < 2}><Send size={14} />ارسال</button>}
              <button type="button" className="btn-ghost" onClick={clear} disabled={!!pending || (msgs.length === 0 && !session)} data-testid="as-clear"><Trash2 size={14} />پاک‌کردن مکالمه</button>
            </div>
          </form>
        </section>

        <aside className="as-side">
          <section className="panel" aria-label="فیلترها">
            <div className="panel-title"><h3>دامنه جست‌وجو</h3></div>
            <Segmented label="بازه زمانی" value={win} onChange={setWin} items={[['24h', '۲۴ ساعت'], ['7d', '۷ روز'], ['30d', '۳۰ روز'], ['all', 'همه']]} />
            <Segmented label="نوع محتوا" value={kind} onChange={setKind} items={[['all', 'همه'], ['news', 'خبر'], ['x', 'X']]} />
            <label className="field">منبع
              <select value={source} onChange={(e) => setSource(e.target.value)}>
                <option value="">همه منابع</option>
                {sources.data?.sources.map((s) => <option key={s.source_id} value={s.source_id}>{s.display_name || s.hostname}</option>)}
              </select>
            </label>
            <label className="field">موضوع
              <select value={topic} onChange={(e) => setTopic(e.target.value)}>
                <option value="">همه موضوعات</option>
                {topics.data?.categories.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
              </select>
            </label>
          </section>

          <section className="panel" aria-label="شواهد آخرین پاسخ">
            <div className="panel-title"><h3><Newspaper size={15} aria-hidden="true" /> شواهد</h3>{last && <Tag>{fmt(last.citations.length)}</Tag>}</div>
            {last
              ? <ol className="as-evidence-list">{last.citations.map((c, i) => <CitationCard key={c.evidence_id} c={c} n={i + 1} />)}</ol>
              : <p className="muted">پس از پاسخ، اسنادی که پاسخ به آن‌ها استناد کرده اینجا نمایش داده می‌شوند.</p>}
          </section>

          <section className="panel" aria-label="مصرف مدل محلی" data-testid="as-usage">
            <div className="panel-title"><h3><Cpu size={15} aria-hidden="true" /> مصرف مدل محلی</h3><Tag tone="ok">هزینه: ۰ دلار</Tag></div>
            {usage.data ? (
              <dl className="kv as-usage">
                <dt>کل استنتاج‌ها</dt><dd>{fmt(usage.data.inferences)}</dd>
                <dt>ترجمه / دستیار</dt><dd>{fmt(usage.data.translation_inferences)} / {fmt(usage.data.assistant_inferences)}</dd>
                <dt>پاسخ از حافظه موقت</dt><dd>{fmt(usage.data.cache_hits)}</dd>
                <dt>توکن ورودی / خروجی</dt><dd>{fmt(usage.data.input_tokens)} / {fmt(usage.data.output_tokens)}</dd>
                <dt>میانگین زمان</dt><dd>{usage.data.average_latency_ms != null ? `${fmt(Math.round(usage.data.average_latency_ms / 1000))} ثانیه` : '—'}</dd>
                <dt>صف</dt><dd>{fmt(usage.data.queue_length)}</dd>
                <dt>ترجمه در انتظار / ناموفق</dt><dd>{fmt(usage.data.translation_pending)} / {fmt(usage.data.translation_failed_jobs)}</dd>
                <dt>خطاهای ثبت‌شده</dt><dd>{fmt(usage.data.failed)}</dd>
                <dt>دسترس‌پذیری مدل</dt><dd>{usage.data.model_available ? 'در دسترس' : 'خارج از دسترس'}</dd>
              </dl>
            ) : <p className="muted">در حال دریافت…</p>}
            {st && <p className="muted as-limits-note">حداکثر {fmt(st.limits.max_records)} سند در هر پاسخ · {fmt(st.limits.history_turns)} نوبت اخیر گفت‌وگو · نگهداری مکالمه {fmt(st.limits.retention_days)} روز</p>}
          </section>
        </aside>
      </div>
    </Shell>
  );
}

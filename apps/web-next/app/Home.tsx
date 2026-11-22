'use client';
import { useState } from 'react';
import Link from 'next/link';
import { Activity, Users, Fuel } from 'lucide-react';
import { Shell } from './design/Shell';
import { useApi, useNow } from './design/useApi';
import { usePrefs } from './design/prefs';
import type { EventRow, FeedResponse, Integration } from './design/types';
import { fmt, fmtDay, fmtRelative, fmtSigned, fmtTime, catVar } from './design/format';
import { CardBones, Empty, Failure, IntegrationNotice, SectionHead, Segmented, Stat } from './design/ui';
import { Columns } from './design/charts';
import { BreakingTicker } from './components/BreakingTicker';
import { StoriesRail } from './components/Stories';
import { BriefingCard } from './components/Briefing';
import { NewsCard } from './components/NewsCard';
import { EventTimeline } from './components/EventTimeline';

interface ActivityResp {
  items: { h1: number; h24: number; prev24: number; d7: number; total: number };
  hourly_48h: { t: string; n: number }[];
  last_run: { started_at: string; status: string; sources_succeeded: number; sources_failed: number; items_inserted: number } | null;
  sources: { total: number; fresh: number; failing: number };
  events: { updated: number; total: number };
  translations: { available: number; error: number; total_items: number };
  categories_24h: { category_id: string; category_label: string; n: number }[];
}

function Lead() {
  const q = useApi<FeedResponse>('feed?window=24h&sort=important&page_size=8');
  const fallback = useApi<FeedResponse>(q.data && q.data.items.length < 3 ? 'feed?sort=newest&page_size=5' : null, [q.data?.items.length]);
  const now = useNow();
  const { t } = usePrefs();
  const data = q.data && q.data.items.length >= 3 ? q.data : fallback.data;
  if (q.error) return <Failure onRetry={q.reload} />;
  if (!data) return <CardBones n={3} />;
  const pool = data.items.filter((x) => x.category_id !== 'other');
  if (!pool.length) return <Empty title={t.leadNoNews} />;
  // The lead slot prefers the most important item that has a real article
  // photo; order is otherwise kept (importance, then recency).
  const lead = pool.find((x) => x.image_url) ?? pool[0];
  const rest = pool.filter((x) => x !== lead).slice(0, 2);
  return (
    <div className="lead-grid">
      <NewsCard item={lead} now={now} variant="lead" />
      <div className="lead-side">{rest.map((i) => <NewsCard key={i.item_id} item={i} now={now} />)}</div>
    </div>
  );
}

function Latest() {
  const [sort, setSort] = useState<'newest' | 'important' | 'coverage'>('newest');
  const q = useApi<FeedResponse>(`feed?sort=${sort}&page_size=12${sort === 'newest' ? '' : '&window=7d'}`, [sort]);
  const now = useNow();
  const { t } = usePrefs();
  return (
    <section className="block" aria-labelledby="latest-h">
      <SectionHead id="latest-h" title={t.latestNewsTitle} kicker={t.latestNewsKicker} action={{ href: `/news?sort=${sort}`, label: t.allNewsAction }} />
      <Segmented label={t.sortLabel} value={sort} onChange={setSort} items={[['newest', t.sortNewest], ['important', t.sortImportant7d], ['coverage', t.sortCoverage7d]]} />
      {q.error && <Failure onRetry={q.reload} />}
      {!q.data && !q.error && <CardBones n={5} />}
      {q.data && (
        <div className="latest-grid">
          <div className="latest-main">{q.data.items.slice(0, 7).map((i) => <NewsCard key={i.item_id} item={i} now={now} variant="row" />)}</div>
          <aside className="latest-aside" aria-label={t.moreNewsAria}>{q.data.items.slice(7).map((i) => <NewsCard key={i.item_id} item={i} now={now} variant="compact" />)}</aside>
        </div>
      )}
    </section>
  );
}

function Timeline() {
  const [sort, setSort] = useState<'latest' | 'important'>('latest');
  const q = useApi<{ events: EventRow[]; total: number }>(`timeline/events?sort=${sort}&page_size=6`, [sort]);
  const now = useNow();
  const { t } = usePrefs();
  return (
    <section className="block" aria-labelledby="tl-h">
      <SectionHead id="tl-h" title={t.timelineTitle} kicker={t.timelineKicker} action={{ href: '/events', label: t.allEventsAction }} />
      <Segmented label={t.timelineSortLabel} value={sort} onChange={setSort} items={[['latest', t.timelineSortLatest], ['important', t.timelineSortImportant]]} />
      {q.error && <Failure onRetry={q.reload} />}
      {!q.data && !q.error && <CardBones n={3} image={false} />}
      {q.data && (q.data.events.length ? <EventTimeline events={q.data.events} now={now} /> : <Empty title={t.timelineEmpty} />)}
    </section>
  );
}

function ActivityBlock() {
  const q = useApi<ActivityResp>('activity');
  const integ = useApi<{ integrations: Integration[] }>('integrations');
  const now = useNow();
  const { t, isEn } = usePrefs();
  const commodity = integ.data?.integrations.find((i) => i.integration_id === 'commodity_prices');
  const a = q.data;
  const delta = a ? a.items.h24 - a.items.prev24 : 0;
  return (
    <section className="block" aria-labelledby="act-h">
      <SectionHead id="act-h" title={t.activityTitle} kicker={t.activityKicker} action={{ href: '/analytics', label: t.analyticsAction }} />
      <div className="activity-grid">
        <div className="panel">
          <div className="panel-title"><Activity size={16} /><h3>{t.activityPast48h}</h3></div>
          {q.error && <Failure onRetry={q.reload} />}
          {a && (
            <>
              <div className="stat-row">
                <Stat label={t.statPastHour} value={a.items.h1} note={t.newsUnit} />
                <Stat label={t.statPast24h} value={a.items.h24} note={isEn ? `${fmtSigned(delta)} vs prior day` : `${fmtSigned(delta)} نسبت به روز قبل`} tone={delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat'} />
                <Stat label={isEn ? "Fresh Sources" : "منابع تازه"} value={`${fmt(a.sources.fresh)} / ${fmt(a.sources.total)}`} note={a.sources.failing ? (isEn ? `${fmt(a.sources.failing)} failing` : `${fmt(a.sources.failing)} منبع با خطا`) : (isEn ? "No consecutive errors" : "بدون خطای پیاپی")} tone={a.sources.failing ? 'down' : 'flat'} />
                <Stat label={isEn ? "Active Events" : "رویدادهای به‌روز"} value={a.events.updated} note={isEn ? `of ${fmt(a.events.total)} total` : `از ${fmt(a.events.total)} رویداد`} />
              </div>
              <Columns unit={t.newsUnit} highlightLast height={120}
                data={a.hourly_48h.map((h) => ({ key: h.t, label: fmtTime(h.t), value: h.n, tip: `${fmtDay(h.t)} ${isEn ? 'hour' : 'ساعت'} ${fmtTime(h.t)}` }))} />
              <p className="fig-note">
                {isEn 
                  ? `Articles by publication hour. Last collection cycle: ${a.last_run ? fmtRelative(a.last_run.started_at, now) : 'None'}.` 
                  : `تعداد خبر بر اساس زمان انتشار در هر ساعت. آخرین چرخه گردآوری: ${a.last_run ? fmtRelative(a.last_run.started_at, now) : 'ثبت نشده'}.`}
              </p>
              <div className="cat-strip">
                {a.categories_24h.map((c) => (
                  <Link key={c.category_id} href={`/news?category=${c.category_id}&window=24h`} className="cat-chip">
                    <i style={{ background: catVar(c.category_id) }} />{c.category_label}<b>{fmt(c.n)}</b>
                  </Link>
                ))}
              </div>
            </>
          )}
          {!a && !q.error && <CardBones n={2} image={false} />}
        </div>
        <div className="panel">
          <div className="panel-title"><Fuel size={16} /><h3>{t.commodityPricesTitle}</h3></div>
          <IntegrationNotice integration={commodity} title={isEn ? "Oil, Gold, FX & Strategic Commodities" : "قیمت نفت، طلا، ارز و کالاهای راهبردی"}>
            <p className="muted">
              {isEn 
                ? "Feed ingestion schema (table commodity_prices) is configured and active. Upon establishing connection with an authorized market provider, price metrics and micro-charts will render here."
                : "ساختار دریافت (جدول commodity_prices با مقدار، واحد، زمان، منبع و شناسه مجوز) آماده است. پس از قرارداد با یک ارائه‌دهنده داده، کارت‌های قیمت در همین‌جا نمایش داده می‌شوند."}
            </p>
          </IntegrationNotice>
        </div>
      </div>
    </section>
  );
}

function Social() {
  const st = useApi<{ integration: Integration }>('social');
  const x = useApi<{ accounts: number; posts: number; posts_today: number; last_registered_at: string | null }>('social/stats');
  const now = useNow();
  return (
    <section className="block" aria-labelledby="soc-h">
      <SectionHead id="soc-h" title="شبکه‌های اجتماعی" kicker="پایش دستی ۳۶ حساب X؛ بدون API پولی و بدون scraping" action={{ href: '/social', label: 'پست‌های ثبت‌شده' }} />
      {(st.error || x.error) && <Failure onRetry={() => { st.reload(); x.reload(); }} />}
      {st.data && x.data && (
        <IntegrationNotice integration={st.data.integration} title="حساب‌های X">
          <p className="muted"><Users size={14} style={{ verticalAlign: 'middle' }} /> {fmt(x.data.accounts)} حساب · {fmt(x.data.posts)} پست ثبت‌شده دستی · امروز {fmt(x.data.posts_today)}{x.data.last_registered_at ? ` · آخرین ثبت ${fmtRelative(x.data.last_registered_at, now)}` : ''}</p>
        </IntegrationNotice>
      )}
    </section>
  );
}

export function Home() {
  return (
    <Shell>
      <h1 className="sr-only">Defence Monitor — اتاق خبر</h1>
      <BreakingTicker />
      <section className="stories-block" aria-label="استوری‌ها"><StoriesRail /></section>
      <div className="home-top">
        <section aria-label="مهم‌ترین خبرهای ۲۴ ساعت گذشته" className="home-lead"><Lead /></section>
        <BriefingCard />
      </div>
      <Latest />
      <div className="home-split">
        <Timeline />
        <div>
          <Social />
        </div>
      </div>
      <ActivityBlock />
    </Shell>
  );
}

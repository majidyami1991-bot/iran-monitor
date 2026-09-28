'use client';
import { useState } from 'react';
import Link from 'next/link';
import { Activity, Users, Fuel } from 'lucide-react';
import { Shell } from './design/Shell';
import { useApi, useNow } from './design/useApi';
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
  const data = q.data && q.data.items.length >= 3 ? q.data : fallback.data;
  if (q.error) return <Failure onRetry={q.reload} />;
  if (!data) return <CardBones n={3} />;
  const pool = data.items.filter((x) => x.category_id !== 'other');
  if (!pool.length) return <Empty title="خبری برای نمایش نیست" />;
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
  return (
    <section className="block" aria-labelledby="latest-h">
      <SectionHead id="latest-h" title="تازه‌ترین خبرها" kicker="از همه منابع فعال، مستقیم از پایگاه داده" action={{ href: `/news?sort=${sort}`, label: 'همه خبرها' }} />
      <Segmented label="مرتب‌سازی" value={sort} onChange={setSort} items={[['newest', 'جدیدترین'], ['important', 'مهم‌ترین (۷ روز)'], ['coverage', 'پربازتاب‌ترین (۷ روز)']]} />
      {q.error && <Failure onRetry={q.reload} />}
      {!q.data && !q.error && <CardBones n={5} />}
      {q.data && (
        <div className="latest-grid">
          <div className="latest-main">{q.data.items.slice(0, 7).map((i) => <NewsCard key={i.item_id} item={i} now={now} variant="row" />)}</div>
          <aside className="latest-aside" aria-label="خبرهای بیشتر">{q.data.items.slice(7).map((i) => <NewsCard key={i.item_id} item={i} now={now} variant="compact" />)}</aside>
        </div>
      )}
    </section>
  );
}

function Timeline() {
  const [sort, setSort] = useState<'latest' | 'important'>('latest');
  const q = useApi<{ events: EventRow[]; total: number }>(`timeline/events?sort=${sort}&page_size=6`, [sort]);
  const now = useNow();
  return (
    <section className="block" aria-labelledby="tl-h">
      <SectionHead id="tl-h" title="خط زمانی رویدادها" kicker="خبرهای هم‌موضوع از منابع مختلف که به یک رویداد پیوند خورده‌اند" action={{ href: '/events', label: 'همه رویدادها' }} />
      <Segmented label="ترتیب رویدادها" value={sort} onChange={setSort} items={[['latest', 'جدیدترین'], ['important', 'مهم‌ترین']]} />
      {q.error && <Failure onRetry={q.reload} />}
      {!q.data && !q.error && <CardBones n={3} image={false} />}
      {q.data && (q.data.events.length ? <EventTimeline events={q.data.events} now={now} /> : <Empty title="هنوز رویدادی شناسایی نشده است" />)}
    </section>
  );
}

function ActivityBlock() {
  const q = useApi<ActivityResp>('activity');
  const integ = useApi<{ integrations: Integration[] }>('integrations');
  const now = useNow();
  const commodity = integ.data?.integrations.find((i) => i.integration_id === 'commodity_prices');
  const a = q.data;
  const delta = a ? a.items.h24 - a.items.prev24 : 0;
  return (
    <section className="block" aria-labelledby="act-h">
      <SectionHead id="act-h" title="فعالیت و قیمت کالاها" kicker="فعالیت واقعی گردآوری و پوشش؛ قیمت کالا فقط از منبع دارای مجوز" action={{ href: '/analytics', label: 'تحلیل آماری' }} />
      <div className="activity-grid">
        <div className="panel">
          <div className="panel-title"><Activity size={16} /><h3>فعالیت ۴۸ ساعت گذشته</h3></div>
          {q.error && <Failure onRetry={q.reload} />}
          {a && (
            <>
              <div className="stat-row">
                <Stat label="یک ساعت اخیر" value={a.items.h1} note="خبر" />
                <Stat label="۲۴ ساعت اخیر" value={a.items.h24} note={`${fmtSigned(delta)} نسبت به روز قبل`} tone={delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat'} />
                <Stat label="منابع تازه" value={`${fmt(a.sources.fresh)} از ${fmt(a.sources.total)}`} note={a.sources.failing ? `${fmt(a.sources.failing)} منبع با خطا` : 'بدون خطای پیاپی'} tone={a.sources.failing ? 'down' : 'flat'} />
                <Stat label="رویدادهای به‌روز" value={a.events.updated} note={`از ${fmt(a.events.total)} رویداد`} />
              </div>
              <Columns unit="خبر" highlightLast height={120}
                data={a.hourly_48h.map((h) => ({ key: h.t, label: fmtTime(h.t), value: h.n, tip: `${fmtDay(h.t)} ساعت ${fmtTime(h.t)}` }))} />
              <p className="fig-note">تعداد خبر بر اساس زمان انتشار در هر ساعت (به وقت تهران). آخرین چرخه گردآوری: {a.last_run ? fmtRelative(a.last_run.started_at, now) : 'ثبت نشده'}.</p>
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
          <div className="panel-title"><Fuel size={16} /><h3>قیمت کالاها و انرژی</h3></div>
          <IntegrationNotice integration={commodity} title="قیمت نفت، طلا، ارز و کالاهای راهبردی">
            <p className="muted">ساختار دریافت (جدول <code>commodity_prices</code> با مقدار، واحد، زمان، منبع و شناسه مجوز) آماده است. پس از قرارداد با یک ارائه‌دهنده داده، کارت‌های قیمت، تغییر، نمودار کوچک و تازگی در همین‌جا نمایش داده می‌شوند.</p>
          </IntegrationNotice>
        </div>
      </div>
    </section>
  );
}

function Social() {
  const q = useApi<{ integration: Integration; registered_accounts: { handle: string }[]; total_posts: number }>('social');
  return (
    <section className="block" aria-labelledby="soc-h">
      <SectionHead id="soc-h" title="شبکه‌های اجتماعی" kicker="پست‌ها فقط از مسیر مجاز گردآوری نمایش داده می‌شوند" action={{ href: '/social', label: 'جزئیات' }} />
      {q.error && <Failure onRetry={q.reload} />}
      {q.data && (
        <IntegrationNotice integration={q.data.integration} title="پست‌های زنده X (توییتر)">
          <p className="muted"><Users size={14} style={{ verticalAlign: 'middle' }} /> {fmt(q.data.registered_accounts.length)} حساب در فهرست منابع مشتری ثبت شده است؛ {fmt(q.data.total_posts)} پست در پایگاه داده وجود دارد.</p>
        </IntegrationNotice>
      )}
    </section>
  );
}

export function Home() {
  return (
    <Shell>
      <h1 className="sr-only">ایران مانیتور — اتاق خبر</h1>
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

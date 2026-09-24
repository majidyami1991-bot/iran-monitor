'use client';
import { useState } from 'react';
import Link from 'next/link';
import { ResponsiveContainer, AreaChart, Area } from 'recharts';
import { Shield, Landmark, Cpu, Coins, Compass, Users, HelpCircle, TrendingUp, TrendingDown } from 'lucide-react';
import { Shell } from '../design/Shell';
import { useApi } from '../design/useApi';
import { EmptyState, ErrorState, Skeleton } from '../design/ui';
import { fmt } from '../design/format';

const ICONS: Record<string, typeof Shield> = {
  security_defense: Shield, politics_geopolitics: Landmark, technology: Cpu,
  economy_infrastructure: Coins, strategic: Compass, social_humanitarian: Users, other: HelpCircle,
};

interface CategoryRow {
  id: string; label: string; count: number; previous_count: number | null; percent: number;
  active_sources: number; latest_item_at: string | null; subtopic_count: number; is_fallback: boolean;
  sparkline: [string, number][];
}
interface Data { window: string; categories: CategoryRow[]; total_items: number }

const WINDOWS: [string, string][] = [['24h', '۲۴ ساعت'], ['7d', '۷ روز'], ['30d', '۳۰ روز'], ['all', 'همه داده‌ها']];

export function Categories() {
  const [window_, setWindow] = useState('30d');
  const { data, error, loading, reload } = useApi<Data>('categories?window=' + window_, [window_]);

  return (
    <Shell title="دسته‌بندی‌ها" breadcrumb="دسته‌بندی‌های اصلی">
      <div className="page-head">
        <div>
          <h1>دسته‌بندی‌های اصلی</h1>
          <p>طبقه‌بندی چندسطحی با کلیدواژه‌های قطعی و امتیاز اطمینان — هر خبر یک دسته اصلی دارد و می‌تواند چند زیرموضوع داشته باشد.</p>
        </div>
      </div>

      <div className="periods">{WINDOWS.map(([v, t]) => <button key={v} className={window_ === v ? 'selected' : ''} onClick={() => setWindow(v)}>{t}</button>)}</div>

      {error && <ErrorState onRetry={reload}>فهرست دسته‌بندی‌ها دریافت نشد.</ErrorState>}
      {loading && <div className="category-grid">{Array.from({ length: 7 }).map((_, i) => <Skeleton key={i} height={150} radius={14} />)}</div>}

      {!loading && !error && data && (
        <div className="category-grid">
          {data.categories.map((cat) => {
            const Icon = ICONS[cat.id] || HelpCircle;
            const delta = cat.previous_count != null ? cat.count - cat.previous_count : null;
            const spark = cat.sparkline.map(([d, n]) => ({ d, n }));
            return (
              <Link href={'/categories/' + encodeURIComponent(cat.id)} key={cat.id}
                className={'category-card' + (cat.is_fallback ? ' category-card-fallback' : '')}>
                <div className="category-card-head">
                  <div className="category-card-icon"><Icon size={17} /></div>
                  {delta != null && delta !== 0 && (
                    <span className={'category-card-delta ' + (delta > 0 ? 'up' : 'down')}>
                      {delta > 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />} {delta > 0 ? '+' : ''}{fmt(delta)}
                    </span>
                  )}
                </div>
                <h3 dir="rtl">{cat.label}</h3>
                <span className="category-card-count">{fmt(cat.count)}</span>
                {spark.length > 1 && (
                  <div className="category-sparkline" dir="ltr">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={spark} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
                        <defs><linearGradient id={'spark-' + cat.id} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="var(--accent-strong)" stopOpacity={0.35} />
                          <stop offset="100%" stopColor="var(--accent-strong)" stopOpacity={0} />
                        </linearGradient></defs>
                        <Area type="monotone" dataKey="n" stroke="var(--accent-strong)" fill={'url(#spark-' + cat.id + ')'} strokeWidth={1.5} isAnimationActive={false} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                )}
                <div className="category-card-meta">
                  <span>{fmt(cat.percent)}٪ از کل</span>
                  <span>{cat.is_fallback ? 'نیازمند بازبینی' : `${fmt(cat.subtopic_count)} زیرموضوع · ${fmt(cat.active_sources)} منبع`}</span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
      {!loading && !error && data && !data.categories.length && <EmptyState title="داده‌ای برای این بازه ثبت نشده" />}
    </Shell>
  );
}

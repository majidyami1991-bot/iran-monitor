'use client';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Bell, ChevronDown, Menu, Search, X, Radio, Languages } from 'lucide-react';
import { useApi, useNow } from './useApi';
import { fmt, fmtClock, fmtDateLong, fmtRelative } from './format';
import { usePrefs } from './prefs';

type NavLeaf = { label: string; href: string; note?: string };
type NavItem = NavLeaf | { label: string; children: NavLeaf[] };

export const NAV: NavItem[] = [
  { label: 'خانه', href: '/' },
  { label: 'اخبار', href: '/news' },
  { label: 'استوری‌ها', href: '/stories' },
  { label: 'گزارش روزانه', href: '/briefing' },
  { label: 'رویدادها', href: '/events' },
  { label: 'موضوعات', href: '/topics' },
  { label: 'منابع', href: '/sources' },
  { label: 'تحلیل', children: [
    { label: 'تحلیل آماری', href: '/analytics', note: 'حجم، زمان انتشار، پوشش موضوعی' },
    { label: 'نقشه', href: '/map', note: 'وضعیت اتصال داده مکانی' },
    { label: 'شبکه‌های اجتماعی', href: '/social', note: 'وضعیت اتصال X' },
  ] },
  { label: 'آینده‌پژوهی', children: [
    { label: 'روندها', href: '/foresight/trends', note: 'تغییر حجم پوشش، توصیفی' },
    { label: 'سیگنال‌های ضعیف', href: '/foresight/weak-signals', note: 'نام‌های تازه کم‌بسامد' },
    { label: 'عدم‌قطعیت‌ها', href: '/foresight/uncertainties', note: 'کیفیت داده و طبقه‌بندی' },
    { label: 'پیشران‌ها و STEEP', href: '/foresight/drivers', note: 'نگاشت موضوعی' },
    { label: 'سناریوها', href: '/foresight/scenarios', note: 'نیازمند تحلیلگر' },
  ] },
  { label: 'پایش سامانه', children: [
    { label: 'وضعیت پایش', href: '/monitoring', note: 'گردآورنده و منابع' },
    { label: 'بازبینی محتوا', href: '/review/content', note: 'صف بازبینی ترجمه' },
    { label: 'هشدارها', href: '/alerts', note: 'قواعد و اعلان‌های سامانه' },
    { label: 'درباره و روش‌ها', href: '/about', note: 'قواعد، نسخه‌ها، محدودیت‌ها' },
  ] },
];

function isActive(pathname: string, href: string) {
  return href === '/' ? pathname === '/' : pathname === href || pathname.startsWith(href + '/');
}

interface Activity { last_run: { started_at: string; status: string } | null; items: { h24: number } }
interface Notification { kind: string; severity: string; title: string; title_lang?: string; at: string | null; href: string }

function Clock() {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => { setNow(new Date()); const t = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(t); }, []);
  if (!now) return <span className="clock" aria-hidden="true" />;
  return (
    <span className="clock" title="به وقت تهران، تقویم خورشیدی">
      <time dateTime={now.toISOString()}>{fmtClock(now)}</time>
      <small>{fmtDateLong(now)}</small>
    </span>
  );
}

function LiveStatus() {
  const q = useApi<Activity>('activity');
  const now = useNow(30000);
  const last = q.data?.last_run?.started_at;
  const ageMin = last ? (now - Date.parse(last)) / 60000 : null;
  const state = q.error ? 'error' : ageMin == null ? 'unknown' : ageMin <= 35 ? 'live' : 'stale';
  const label = state === 'live' ? 'زنده' : state === 'stale' ? 'با تأخیر' : state === 'error' ? 'قطع ارتباط' : '…';
  return (
    <Link href="/monitoring" className={`live live-${state}`} title={last ? `آخرین چرخه گردآوری: ${fmtRelative(last, now)}` : 'وضعیت گردآوری'}>
      <i aria-hidden="true" />
      <span>{label}</span>
      {q.data && <small>{fmt(q.data.items.h24)} خبر در ۲۴ ساعت</small>}
    </Link>
  );
}

function Notifications() {
  const [open, setOpen] = useState(false);
  const q = useApi<{ notifications: Notification[]; total: number }>('notifications');
  const now = useNow();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', close); document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', esc); };
  }, [open]);
  const n = q.data?.total ?? 0;
  return (
    <div className="notif" ref={ref}>
      <button type="button" className="icon-btn" aria-expanded={open} aria-haspopup="true" onClick={() => setOpen(!open)}
        aria-label={`اعلان‌ها${n ? `، ${fmt(n)} مورد` : ''}`}>
        <Bell size={18} />{n > 0 && <span className="notif-count">{fmt(n)}</span>}
      </button>
      {open && (
        <div className="notif-panel" role="dialog" aria-label="اعلان‌ها">
          <div className="notif-head"><strong>اعلان‌ها</strong><small>از وضعیت واقعی منابع، چرخه گردآوری و قاعده خبر فوری</small></div>
          {q.error && <p className="notif-empty">دریافت اعلان‌ها ناموفق بود.</p>}
          {q.data && n === 0 && <p className="notif-empty">اعلان تازه‌ای نیست.</p>}
          <ul>
            {q.data?.notifications.map((x, i) => (
              <li key={i} className={`notif-${x.severity}`}>
                <Link href={x.href} onClick={() => setOpen(false)}>
                  <span dir={x.title_lang === 'en' ? 'ltr' : undefined}>{x.title}</span>
                  <small>{fmtRelative(x.at, now)}</small>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function LangToggle() {
  const { contentLang, setContentLang } = usePrefs();
  return (
    <div className="lang" role="radiogroup" aria-label="زبان اول محتوا">
      <Languages size={15} aria-hidden="true" />
      <button type="button" role="radio" aria-checked={contentLang === 'fa'} onClick={() => setContentLang('fa')} title="نمایش ترجمه فارسی در صورت وجود">فا</button>
      <button type="button" role="radio" aria-checked={contentLang === 'en'} onClick={() => setContentLang('en')} title="نمایش متن اصلی منبع">EN</button>
    </div>
  );
}

function NavMenu({ item, pathname }: { item: Extract<NavItem, { children: NavLeaf[] }>; pathname: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLLIElement>(null);
  const active = item.children.some((c) => isActive(pathname, c.href));
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', close); document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', esc); };
  }, [open]);
  return (
    <li ref={ref} className="nav-menu">
      <button type="button" className="nav-link" aria-expanded={open} data-active={active || undefined} onClick={() => setOpen(!open)}>
        {item.label}<ChevronDown size={14} />
      </button>
      {open && (
        <ul className="nav-drop">
          {item.children.map((c) => (
            <li key={c.href}>
              <Link href={c.href} aria-current={isActive(pathname, c.href) ? 'page' : undefined} onClick={() => setOpen(false)}>
                <strong>{c.label}</strong>{c.note && <small>{c.note}</small>}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

export function Shell({ children, wide = false }: { title?: string; breadcrumb?: string; children: ReactNode; wide?: boolean }) {
  const pathname = usePathname() || '/';
  const router = useRouter();
  const [drawer, setDrawer] = useState(false);
  const [q, setQ] = useState('');
  useEffect(() => { setDrawer(false); }, [pathname]);
  useEffect(() => {
    document.body.style.overflow = drawer ? 'hidden' : '';
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setDrawer(false); };
    window.addEventListener('keydown', esc);
    return () => { window.removeEventListener('keydown', esc); document.body.style.overflow = ''; };
  }, [drawer]);

  const search = (e: React.FormEvent) => {
    e.preventDefault();
    router.push('/news' + (q.trim() ? '?q=' + encodeURIComponent(q.trim()) : ''));
  };

  return (
    <div className="app">
      <a href="#main" className="skip">پرش به محتوای اصلی</a>
      <header className="masthead">
        <div className="masthead-row wrap">
          <button type="button" className="icon-btn only-mobile" aria-label="باز کردن منو" aria-expanded={drawer} onClick={() => setDrawer(true)}><Menu size={20} /></button>
          <Link href="/" className="logo" aria-label="ایران مانیتور، صفحه اصلی">
            <span className="logo-mark" aria-hidden="true"><Radio size={18} /></span>
            <span className="logo-word">ایران مانیتور<small>اتاق خبر رصد منابع باز</small></span>
          </Link>
          <LiveStatus />
          <form className="search" role="search" onSubmit={search}>
            <Search size={16} aria-hidden="true" />
            <input value={q} onChange={(e) => setQ(e.target.value)} aria-label="جست‌وجوی سراسری در اخبار" placeholder="جست‌وجو در عنوان‌ها و خلاصه‌ها…" />
          </form>
          <div className="masthead-tools">
            <Clock />
            <LangToggle />
            <Notifications />
          </div>
        </div>
        <nav className="primary-nav" aria-label="ناوبری اصلی">
          <ul className="wrap">
            {NAV.map((item) => 'href' in item ? (
              <li key={item.href}>
                <Link href={item.href} className="nav-link" aria-current={isActive(pathname, item.href) ? 'page' : undefined}>{item.label}</Link>
              </li>
            ) : <NavMenu key={item.label} item={item} pathname={pathname} />)}
          </ul>
        </nav>
      </header>

      {drawer && (
        <div className="drawer-layer">
          <button type="button" className="drawer-scrim" aria-label="بستن منو" onClick={() => setDrawer(false)} />
          <aside className="drawer" role="dialog" aria-modal="true" aria-label="منوی اصلی">
            <div className="drawer-head">
              <strong>ایران مانیتور</strong>
              <button type="button" className="icon-btn" aria-label="بستن منو" onClick={() => setDrawer(false)} autoFocus><X size={20} /></button>
            </div>
            <form className="search drawer-search" role="search" onSubmit={search}>
              <Search size={16} aria-hidden="true" />
              <input value={q} onChange={(e) => setQ(e.target.value)} aria-label="جست‌وجو در اخبار" placeholder="جست‌وجو…" />
            </form>
            <nav aria-label="ناوبری موبایل">
              {NAV.map((item) => 'href' in item ? (
                <Link key={item.href} href={item.href} className="drawer-link" aria-current={isActive(pathname, item.href) ? 'page' : undefined}>{item.label}</Link>
              ) : (
                <div key={item.label} className="drawer-group">
                  <span>{item.label}</span>
                  {item.children.map((c) => (
                    <Link key={c.href} href={c.href} className="drawer-link" aria-current={isActive(pathname, c.href) ? 'page' : undefined}>{c.label}</Link>
                  ))}
                </div>
              ))}
            </nav>
            <div className="drawer-foot"><Clock /><LangToggle /></div>
          </aside>
        </div>
      )}

      <main id="main" className={wide ? 'main wrap wide' : 'main wrap'}>{children}</main>

      <footer className="footer">
        <div className="wrap footer-row">
          <div>
            <strong>ایران مانیتور</strong>
            <p>همه داده‌ها از پایگاه داده PostgreSQL همین سامانه خوانده می‌شود. آمارها توصیفی‌اند؛ برچسب‌های «قاعده‌محور» و «هوش مصنوعی» منشأ هر خروجی را نشان می‌دهند.</p>
          </div>
          <nav aria-label="پیوندهای پایانی">
            <Link href="/about">روش‌ها و قواعد</Link>
            <Link href="/sources">منابع</Link>
            <Link href="/monitoring">وضعیت سامانه</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}

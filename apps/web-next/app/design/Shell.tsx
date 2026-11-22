'use client';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Bell, ChevronDown, Menu, Search, X, Radio, Languages, LogOut, User as UserIcon } from 'lucide-react';
import { useApi, useNow } from './useApi';
import { fmt, fmtClock, fmtDateLong, fmtRelative } from './format';
import { usePrefs } from './prefs';
import { useAuth } from '../auth/AuthContext';

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
  { label: 'دستیار هوشمند', href: '/assistant' },
  { label: 'تحلیل', children: [
    { label: 'تحلیل آماری', href: '/analytics', note: 'حجم، زمان انتشار، پوشش موضوعی' },
    { label: 'نقشه', href: '/map', note: 'وضعیت اتصال داده مکانی' },
    { label: 'شبکه‌های اجتماعی', href: '/social', note: 'پایش دستی ۳۶ حساب X' },
  ] },
  { label: 'آینده‌پژوهی', children: [
    { label: 'روندها', href: '/foresight/trends', note: 'تغییر حجم پوشش، توصیفی' },
    { label: 'سیگنال‌های ضعیف', href: '/foresight/weak-signals', note: 'نام‌های تازه کم‌بسامد' },
    { label: 'عدم‌قطعیت‌ها', href: '/foresight/uncertainties', note: 'کیفیت داده و طبقه‌بندی' },
    { label: 'پیشران‌ها و STEEP', href: '/foresight/drivers', note: 'نگاشت موضوعی' },
    { label: 'سناریوها', href: '/foresight/scenarios', note: 'نیازمند تحلیلگر' },
  ] },
  { label: 'پایش سامانه', children: [
    { label: 'پنل مدیریت هوش مصنوعی محلی', href: '/admin', note: 'همگام‌سازی، صف ترجمه، دستیار، پشتیبان، هشدارها' },
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
      <button type="button" role="radio" aria-checked={contentLang === 'bi'} onClick={() => setContentLang('bi')} title="ترجمه فارسی و متن اصلی منبع کنار هم">دوزبانه</button>
    </div>
  );
}

function UserProfileMenu() {
  const { user, logout } = useAuth();
  if (!user) {
    return (
      <Link href="/login" style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '5px 12px',
        borderRadius: '6px',
        background: 'rgba(227, 179, 65, 0.12)',
        border: '1px solid rgba(227, 179, 65, 0.3)',
        color: '#f2c75a',
        fontSize: '12px',
        fontWeight: 600,
      }}>
        <UserIcon size={14} />
        <span>ورود</span>
      </Link>
    );
  }

  return (
    <div className="user-profile-widget" style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '8px',
      background: 'rgba(22, 32, 43, 0.85)',
      border: '1px solid #2a3a4a',
      borderRadius: '20px',
      padding: '3px 10px 3px 4px',
      fontSize: '12px',
    }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', lineHeight: 1.15 }}>
        <span style={{ fontWeight: 600, color: '#edf2f7', fontSize: '11.5px' }}>{user.name}</span>
        <span style={{ fontSize: '9.5px', color: user.badgeColor || '#e3b341' }}>{user.role}</span>
      </div>
      <div style={{
        width: '24px',
        height: '24px',
        borderRadius: '50%',
        background: 'rgba(227, 179, 65, 0.15)',
        border: `1px solid ${user.badgeColor || '#e3b341'}`,
        color: user.badgeColor || '#f2c75a',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '10px',
        fontWeight: 700,
      }}>
        {user.avatar}
      </div>
      <button
        type="button"
        onClick={logout}
        title="خروج از حساب کاربری"
        aria-label="خروج از حساب"
        style={{
          background: 'none',
          border: 'none',
          color: '#8497a8',
          cursor: 'pointer',
          padding: '2px 4px',
          display: 'flex',
          alignItems: 'center',
          borderRadius: '4px',
          transition: 'color 0.2s',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.color = '#ef5a4f')}
        onMouseLeave={(e) => (e.currentTarget.style.color = '#8497a8')}
      >
        <LogOut size={13} />
      </button>
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
          <Link href="/" className="logo" aria-label="Defence Monitor، صفحه اصلی">
            <span className="logo-mark" aria-hidden="true"><Radio size={18} /></span>
            <span className="logo-word">Defence Monitor<small>اتاق خبر رصد منابع باز</small></span>
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
            <UserProfileMenu />
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
              <strong>Defence Monitor</strong>
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
            <strong>Defence Monitor</strong>
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

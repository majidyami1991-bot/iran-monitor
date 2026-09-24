'use client';
import { useEffect, useState, type ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  Activity, Newspaper, Globe2, Hash, ChartNoAxesCombined, HeartPulse, Info,
  Search, Menu, ChevronLeft, Radio, Link2,
} from 'lucide-react';

const NAV: [string, typeof Activity, string][] = [
  ['نمای عملیاتی', Activity, '/'],
  ['جریان اخبار', Newspaper, '/news'],
  ['موضوعات', Hash, '/topics'],
  ['رویدادها', Link2, '/events'],
  ['منابع', Globe2, '/sources'],
  ['تحلیل آماری', ChartNoAxesCombined, '/analytics'],
  ['وضعیت پایش', HeartPulse, '/monitoring'],
  ['درباره سامانه', Info, '/about'],
];

/** Shared chrome for every page: collapsible desktop sidebar, mobile drawer,
 * header with breadcrumb + search. One definition, so the product reads as
 * one system rather than a dashboard bolted onto a separate page style. */
export function Shell({ title, breadcrumb, children }: { title: string; breadcrumb?: string; children: ReactNode }) {
  const pathname = usePathname() || '/';
  const [collapsed, setCollapsed] = useState(false);
  const [drawer, setDrawer] = useState(false);

  useEffect(() => {
    try { setCollapsed(localStorage.getItem('im.sidebar.collapsed') === '1'); } catch { /* per-viewer only */ }
  }, []);
  useEffect(() => {
    try { localStorage.setItem('im.sidebar.collapsed', collapsed ? '1' : '0'); } catch { /* per-viewer only */ }
  }, [collapsed]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setDrawer(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className={collapsed ? 'shell collapsed' : 'shell'}>
      <aside className={drawer ? 'shell-sidebar open' : 'shell-sidebar'}>
        <Link href="/" className="brand">
          <span className="brand-mark"><Radio size={22} /></span>
          <span className="brand-word">ایران مانیتور<small>مرکز رصد و دیده‌بانی</small></span>
        </Link>
        <button type="button" className="sidebar-toggle" onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? 'باز کردن نوار کناری' : 'جمع کردن نوار کناری'}>
          <Menu size={18} /><span>{collapsed ? '' : 'نمای فشرده'}</span>
        </button>
        <nav className="side-nav" aria-label="منوی اصلی">
          {NAV.map(([label, Icon, href]) => {
            const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href);
            return (
              <Link key={href} href={href} className="side-nav-link" aria-current={isActive ? 'page' : undefined}
                title={label} onClick={() => setDrawer(false)}>
                <Icon size={19} />
                <span className="side-nav-label">{label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="side-footer">
          <span className="side-footer-text">مرحله ۱ · رصد و دیده‌بانی منابع باز. تحلیل و پیش‌بینی در این نسخه نیست.</span>
        </div>
      </aside>
      {drawer && <button className="scrim" aria-label="بستن منو" onClick={() => setDrawer(false)} />}
      <div className="shell-content">
        <header className="shell-header">
          <button type="button" className="menu-button icon-button" aria-label="باز کردن منو" onClick={() => setDrawer(true)}><Menu size={20} /></button>
          <div className="header-breadcrumb">
            <Link href="/">مرکز پایش</Link><ChevronLeft size={14} /><strong>{breadcrumb ?? title}</strong>
          </div>
          <form action="/news" className="header-search">
            <Search size={17} />
            <input name="q" aria-label="جست‌وجوی سراسری" placeholder="جست‌وجو در اخبار و منابع…" />
          </form>
        </header>
        <main className="shell-main">{children}</main>
      </div>
    </div>
  );
}

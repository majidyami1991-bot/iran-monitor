import './globals.css';
import type { Metadata, Viewport } from 'next';
import { Prefs } from './design/prefs';

export const metadata: Metadata = {
  title: { default: 'Defence Monitor | اتاق خبر رصد منابع باز', template: '%s | Defence Monitor' },
  description: 'رصد زنده، فارسی و مستند منابع باز: چه منتشر شد، کِی، از کدام منبع و درباره چه موضوعی.',
};

export const viewport: Viewport = { themeColor: '#0a0f15', width: 'device-width', initialScale: 1 };

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fa" dir="rtl">
      <body>
        <Prefs>{children}</Prefs>
      </body>
    </html>
  );
}

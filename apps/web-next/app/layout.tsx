import './globals.css';

export const metadata = {
  title: 'ایران مانیتور | مرکز رصد و دیده‌بانی',
  description: 'رصد و دیده‌بانی یکپارچه منابع باز — مرحله ۱',
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fa" dir="rtl">
      <body>{children}</body>
    </html>
  );
}

'use client';

import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from './AuthContext';

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  const isLoginPage = pathname === '/login';

  useEffect(() => {
    if (isLoading) return;

    if (!user && !isLoginPage) {
      router.replace('/login');
    } else if (user && isLoginPage) {
      router.replace('/');
    }
  }, [user, isLoading, isLoginPage, router]);

  // If on login page, render immediately without blocking on session check
  if (isLoginPage) {
    return <>{children}</>;
  }

  // While initializing session for protected pages, display glowing radar loader
  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        backgroundColor: '#060a10',
        color: '#e3b341',
        fontFamily: 'Vazirmatn, Tahoma, sans-serif',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '48px',
            height: '48px',
            margin: '0 auto 16px',
            border: '2px solid rgba(227, 179, 65, 0.2)',
            borderTopColor: '#e3b341',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite'
          }} />
          <div style={{ fontSize: '13px', color: '#8497a8', letterSpacing: '0.5px' }}>
            در حال احراز هویت نشست امن...
          </div>
        </div>
        <style jsx global>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // Prevent rendering protected content before redirect
  if (!user && !isLoginPage) {
    return null;
  }

  return <>{children}</>;
}

'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export interface UserProfile {
  id?: number;
  username: string;
  name: string;
  role: string;
  department: string;
  clearance_level?: string;
  clearanceLevel?: string;
  avatar?: string;
  badge_color?: string;
  badgeColor?: string;
}

const STORAGE_KEY = 'iran_monitor_active_user';
const TOKEN_KEY = 'iran_monitor_auth_token';

interface AuthContextType {
  user: UserProfile | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  login: async () => ({ success: false }),
  logout: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        setUser(parsed);
      }
    } catch {
      // Ignore parsing errors
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = async (username: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          username: username.trim(),
          password,
        }),
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        return {
          success: false,
          error: data.detail || 'نام کاربری یا کلمه عبور وارد شده صحیح نمی‌باشد.',
        };
      }

      const rawUser = data.user;
      const userData: UserProfile = {
        ...rawUser,
        badgeColor: rawUser.badge_color || rawUser.badgeColor,
        clearanceLevel: rawUser.clearance_level || rawUser.clearanceLevel,
      };
      setUser(userData);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(userData));
      if (data.token) {
        localStorage.setItem(TOKEN_KEY, data.token);
      }
      document.cookie = `im_auth=true; path=/; max-age=86400; SameSite=Lax`;
      return { success: true };
    } catch (err) {
      return {
        success: false,
        error: 'خطا در برقراری ارتباط با سرور احراز هویت. لطفاً وضعیت سرویس را بررسی کنید.',
      };
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(TOKEN_KEY);
    document.cookie = `im_auth=; path=/; max-age=0; SameSite=Lax`;
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

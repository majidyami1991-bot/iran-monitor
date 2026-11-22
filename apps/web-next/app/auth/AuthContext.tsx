'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { PRESET_USERS, UserProfile } from '../config/users';

const STORAGE_KEY = 'iran_monitor_active_user';

interface AuthContextType {
  user: UserProfile | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<{ success: boolean; error?: string }>;
  quickLogin: (user: UserProfile) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  login: async () => ({ success: false }),
  quickLogin: () => {},
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
    // Artificial small delay for silky smooth UI feedback
    await new Promise((r) => setTimeout(r, 450));

    const matched = PRESET_USERS.find(
      (u) => u.username.toLowerCase() === username.trim().toLowerCase() && u.password === password
    );

    if (!matched) {
      return { success: false, error: 'نام کاربری یا کلمه عبور وارد شده صحیح نمی‌باشد.' };
    }

    setUser(matched);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(matched));
    document.cookie = `im_auth=true; path=/; max-age=86400; SameSite=Lax`;
    return { success: true };
  };

  const quickLogin = (preset: UserProfile) => {
    setUser(preset);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preset));
    document.cookie = `im_auth=true; path=/; max-age=86400; SameSite=Lax`;
    router.push('/');
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem(STORAGE_KEY);
    document.cookie = `im_auth=; path=/; max-age=0; SameSite=Lax`;
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, quickLogin, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

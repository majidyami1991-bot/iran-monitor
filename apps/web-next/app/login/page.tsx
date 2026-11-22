'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Shield, 
  Lock, 
  User, 
  Eye, 
  EyeOff, 
  Radio, 
  KeyRound, 
  AlertCircle, 
  ChevronDown, 
  ChevronUp, 
  LogIn, 
  CheckCircle2, 
  Fingerprint,
  Zap
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { PRESET_USERS, UserProfile } from '../config/users';
import './login.css';

export default function LoginPage() {
  const { login, quickLogin } = useAuth();
  const router = useRouter();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPresets, setShowPresets] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!username.trim() || !password) {
      setError('لطفاً نام کاربری و رمز عبور را وارد فرمایید.');
      return;
    }

    setIsSubmitting(true);
    const res = await login(username, password);
    setIsSubmitting(false);

    if (res.success) {
      router.push('/');
    } else {
      setError(res.error || 'ورود ناموفق بود. اعتبار سنجی تایید نشد.');
    }
  };

  const handleSelectPreset = (preset: UserProfile) => {
    setUsername(preset.username);
    setPassword(preset.password);
    setError(null);
  };

  const handleDirectQuickLogin = (preset: UserProfile, e: React.MouseEvent) => {
    e.stopPropagation();
    quickLogin(preset);
  };

  return (
    <div className="login-viewport">
      {/* Background Radar & Hologram Effects */}
      <div className="login-bg" aria-hidden="true">
        <div className="login-grid" />
        <div className="login-radial-glow" />
        <div className="login-radar-ring ring-1" />
        <div className="login-radar-ring ring-2" />
        <div className="login-radar-ring ring-3" />
        <div className="radar-sweep" />
      </div>

      <div className="login-card-container">
        <div className="login-card">
          {/* Tactical Corner Brackets */}
          <span className="hud-corner hud-tl" />
          <span className="hud-corner hud-tr" />
          <span className="hud-corner hud-bl" />
          <span className="hud-corner hud-br" />

          {/* Header Branding */}
          <div className="login-header">
            <div className="brand-badge">
              <Shield size={28} />
            </div>
            <h1 className="login-title">سامانه رصد و پایش ایران</h1>
            <div className="login-subtitle">
              <span className="status-dot" />
              <span>اتاق خبر رصد منابع باز • شبکه امن و رمزنگاری‌شده</span>
            </div>
          </div>

          {/* Error Notice */}
          {error && (
            <div className="login-error-alert" role="alert" style={{ marginBottom: '16px' }}>
              <AlertCircle size={17} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          {/* Main Form */}
          <form onSubmit={handleSubmit} className="login-form">
            <div className="input-group">
              <label className="input-label" htmlFor="username">
                <span>شناسه کاربری</span>
                <span className="security-tag">
                  <Fingerprint size={12} />
                  سازمانی
                </span>
              </label>
              <div className="input-wrapper">
                <input
                  id="username"
                  type="text"
                  className="login-input"
                  dir="ltr"
                  placeholder="admin یا نام کاربری..."
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  required
                />
                <User size={18} className="input-icon" />
              </div>
            </div>

            <div className="input-group">
              <label className="input-label" htmlFor="password">
                <span>رمز عبور</span>
                <span className="security-tag">
                  <KeyRound size={12} />
                  محرمانه
                </span>
              </label>
              <div className="input-wrapper">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  className="login-input"
                  dir="ltr"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
                <Lock size={18} className="input-icon" />
                <button
                  type="button"
                  className="toggle-password-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'مخفی کردن رمز' : 'نمایش رمز'}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div className="login-options-row">
              <label className="remember-checkbox-label">
                <input
                  type="checkbox"
                  className="remember-checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                <span>نشست پایدار (ذخیره اطلاعات ورود)</span>
              </label>
            </div>

            <button
              type="submit"
              className="login-submit-btn"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <span className="btn-spinner" />
                  <span>در حال اعتبارسنجی...</span>
                </>
              ) : (
                <>
                  <LogIn size={18} />
                  <span>ورود به اتاق رصد</span>
                </>
              )}
            </button>
          </form>

          {/* Preset User Showcase / Quick Login Drawer */}
          <div className="preset-users-section">
            <button
              type="button"
              className="preset-toggle-btn"
              onClick={() => setShowPresets(!showPresets)}
              aria-expanded={showPresets}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Zap size={15} style={{ color: '#e3b341' }} />
                <span>کاربران نمونه از پیش‌تعریف‌شده در کانفیگ</span>
                <span className="preset-count-badge">۱۰ کاربر</span>
              </div>
              {showPresets ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>

            {showPresets && (
              <div className="preset-users-grid">
                {PRESET_USERS.map((u) => (
                  <div
                    key={u.id}
                    className="preset-user-card"
                    onClick={() => handleSelectPreset(u)}
                    title="کلیک برای درج مشخصات در فرم"
                  >
                    <div className="user-info-cluster">
                      <div
                        className="user-avatar-badge"
                        style={{ color: u.badgeColor, borderColor: `${u.badgeColor}40` }}
                      >
                        {u.avatar}
                      </div>
                      <div>
                        <div className="user-meta-name">{u.name}</div>
                        <div className="user-meta-role">
                          {u.role} • <span style={{ color: '#5d7285' }}>{u.department}</span>
                        </div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div className="user-meta-creds">
                        <div className="user-meta-username">@{u.username}</div>
                        <div className="user-meta-clearance">{u.clearanceLevel}</div>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => handleDirectQuickLogin(u, e)}
                        style={{
                          background: 'rgba(227, 179, 65, 0.15)',
                          border: '1px solid rgba(227, 179, 65, 0.3)',
                          borderRadius: '6px',
                          color: '#f2c75a',
                          padding: '4px 8px',
                          fontSize: '11px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}
                        title="ورود مستقیم و آنی با این پروفایل"
                      >
                        <LogIn size={11} />
                        <span>ورود</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer Security Badges */}
          <div className="login-footer-info">
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              <CheckCircle2 size={12} color="#3fbf7f" />
              تأییدیه امنیتی TLS 1.3
            </span>
            <span>•</span>
            <span>پروتکل احراز هویت محلی SHA-256</span>
            <span>•</span>
            <span>نسخه ۲.۴</span>
          </div>
        </div>
      </div>
    </div>
  );
}

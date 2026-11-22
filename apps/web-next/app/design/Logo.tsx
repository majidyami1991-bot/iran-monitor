import React from 'react';

interface LogoProps {
  size?: number;
  className?: string;
  variant?: 'full' | 'mark';
  showText?: boolean;
  lang?: 'fa' | 'en';
}

/**
 * Iran Monitor / Defence Monitor Official Tactical Insignia.
 * High-precision vector emblem featuring:
 * - Strategic Falcon Wings framing the surveillance shield
 * - Illuminated Globe with latitude / longitude meridian reticle
 * - Orbital Satellite telemetry track & golden targeting crosshairs
 * - Majestic Royal Sapphire & Radiant Amber Gold metallic gradients
 */
export function IranMonitorLogo({
  size = 36,
  className = '',
  variant = 'mark',
  showText = false,
  lang = 'fa'
}: LogoProps) {
  const isEn = lang === 'en';
  const mark = (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
      style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0 }}
    >
      <defs>
        {/* Outer Shield & Wings Metallic Gradient */}
        <linearGradient id="shieldGoldGrad" x1="10%" y1="0%" x2="90%" y2="100%">
          <stop offset="0%" stopColor="#fffbeb" />
          <stop offset="25%" stopColor="#fcd34d" />
          <stop offset="65%" stopColor="#d97706" />
          <stop offset="100%" stopColor="#78350f" />
        </linearGradient>

        {/* Deep Sapphire Radar Base */}
        <radialGradient id="radarNavyGrad" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#1e3a8a" />
          <stop offset="55%" stopColor="#0f1f3d" />
          <stop offset="95%" stopColor="#050c18" />
          <stop offset="100%" stopColor="#02060d" />
        </radialGradient>

        {/* Radiant Inner Core Highlight */}
        <radialGradient id="coreGlowGrad" cx="50%" cy="46%" r="45%">
          <stop offset="0%" stopColor="#fef08a" stopOpacity="0.9" />
          <stop offset="40%" stopColor="#f59e0b" stopOpacity="0.6" />
          <stop offset="85%" stopColor="#3b82f6" stopOpacity="0.15" />
          <stop offset="100%" stopColor="#1d4ed8" stopOpacity="0" />
        </radialGradient>

        {/* Wing Accents Gradient */}
        <linearGradient id="wingAccent" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#fef3c7" />
          <stop offset="50%" stopColor="#f59e0b" />
          <stop offset="100%" stopColor="#b45309" />
        </linearGradient>

        {/* Subtle drop shadow filter for emblem depth */}
        <filter id="logoGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#f59e0b" floodOpacity="0.35" />
        </filter>
      </defs>

      {/* 1. Tactical Hexagonal Outer Rim */}
      <polygon
        points="50,4 88,22 88,68 50,96 12,68 12,22"
        fill="url(#radarNavyGrad)"
        stroke="url(#shieldGoldGrad)"
        strokeWidth="2.5"
        strokeLinejoin="round"
        filter="url(#logoGlow)"
      />

      {/* 2. Inner Telemetry Radar Circle */}
      <circle
        cx="50"
        cy="48"
        r="32"
        fill="#071326"
        stroke="#1d4ed8"
        strokeWidth="1.2"
        strokeDasharray="2 3"
        opacity="0.8"
      />

      {/* Radial Target Reticle Lines */}
      <line x1="50" y1="18" x2="50" y2="78" stroke="#38bdf8" strokeWidth="0.8" opacity="0.35" />
      <line x1="20" y1="48" x2="80" y2="48" stroke="#38bdf8" strokeWidth="0.8" opacity="0.35" />

      {/* 3. Stylized Geopolitical Globe Meridians */}
      <ellipse cx="50" cy="48" rx="24" ry="24" fill="url(#coreGlowGrad)" stroke="#60a5fa" strokeWidth="1" opacity="0.75" />
      <ellipse cx="50" cy="48" rx="14" ry="24" fill="none" stroke="#93c5fd" strokeWidth="0.9" opacity="0.6" />
      <ellipse cx="50" cy="48" rx="6" ry="24" fill="none" stroke="#fcd34d" strokeWidth="0.9" opacity="0.7" />
      <line x1="26" y1="48" x2="74" y2="48" stroke="#fcd34d" strokeWidth="1" opacity="0.7" />
      <line x1="31" y1="36" x2="69" y2="36" stroke="#93c5fd" strokeWidth="0.8" strokeDasharray="3 2" opacity="0.5" />
      <line x1="31" y1="60" x2="69" y2="60" stroke="#93c5fd" strokeWidth="0.8" strokeDasharray="3 2" opacity="0.5" />

      {/* 4. Sovereign Falcon Wings (Strategic Vigilance Crest) */}
      {/* Left Wing Feather Tier 1 */}
      <path
        d="M50 36 C42 26 26 25 14 34 C20 40 32 41 42 43 Z"
        fill="url(#wingAccent)"
        opacity="0.95"
      />
      {/* Left Wing Feather Tier 2 */}
      <path
        d="M48 43 C38 35 22 36 12 46 C20 50 31 50 42 50 Z"
        fill="url(#shieldGoldGrad)"
        opacity="0.85"
      />
      {/* Left Wing Feather Tier 3 */}
      <path
        d="M46 51 C38 46 22 48 14 59 C22 61 32 59 42 57 Z"
        fill="#b45309"
        opacity="0.8"
      />

      {/* Right Wing Feather Tier 1 */}
      <path
        d="M50 36 C58 26 74 25 86 34 C80 40 68 41 58 43 Z"
        fill="url(#wingAccent)"
        opacity="0.95"
      />
      {/* Right Wing Feather Tier 2 */}
      <path
        d="M52 43 C62 35 78 36 88 46 C80 50 69 50 58 50 Z"
        fill="url(#shieldGoldGrad)"
        opacity="0.85"
      />
      {/* Right Wing Feather Tier 3 */}
      <path
        d="M54 51 C62 46 78 48 86 59 C78 61 68 59 58 57 Z"
        fill="#b45309"
        opacity="0.8"
      />

      {/* 5. Orbital Elliptical Telemetry Track with Satellite Node */}
      <ellipse
        cx="50"
        cy="48"
        rx="38"
        ry="13"
        fill="none"
        stroke="url(#shieldGoldGrad)"
        strokeWidth="1.2"
        transform="rotate(-28 50 48)"
        strokeDasharray="7 3 2 3"
        opacity="0.85"
      />
      {/* Satellite Node on Orbit */}
      <circle cx="78" cy="33" r="2.8" fill="#ffffff" stroke="#f59e0b" strokeWidth="1.2" />
      <circle cx="22" cy="63" r="2.0" fill="#38bdf8" />

      {/* 6. Central Strategic Apex Star / Surveillance Diamond */}
      <polygon
        points="50,40 53,47 60,50 53,53 50,60 47,53 40,50 47,47"
        fill="#ffffff"
        stroke="#f59e0b"
        strokeWidth="1"
      />
      <circle cx="50" cy="50" r="1.8" fill="#e11d48" />

      {/* 7. Bottom Chevron Tactical Anchor */}
      <path
        d="M40 76 L50 85 L60 76 L50 79 Z"
        fill="url(#shieldGoldGrad)"
      />
    </svg>
  );

  if (variant === 'mark' && !showText) {
    return mark;
  }

  return (
    <div className={`brand-lockup ${className}`} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.65rem' }}>
      {mark}
      <div className="brand-text" style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.15 }}>
        <span style={{ fontWeight: 800, fontSize: '1.05rem', letterSpacing: isEn ? '-0.02em' : 'normal', color: '#f8fafc' }}>
          {isEn ? 'Iran Monitor' : 'سامانه رصد ایران'}
        </span>
        <small style={{ fontSize: '0.72rem', opacity: 0.72, color: '#e2e8f0' }}>
          {isEn ? 'Defense & Strategic Intelligence' : 'مرکز اطلاعات و پایش دفاعی'}
        </small>
      </div>
    </div>
  );
}

export default IranMonitorLogo;

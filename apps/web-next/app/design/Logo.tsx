import React from 'react';

interface LogoProps {
  size?: number;
  className?: string;
  variant?: 'full' | 'mark';
  showText?: boolean;
  lang?: 'fa' | 'en';
}

/**
 * Iran Monitor Official Tactical Insignia.
 * Loads the vector emblem from /logo.svg.
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
    <img
      src="/logo.svg"
      alt="Defense Monitor"
      width={size}
      height={size}
      className={className}
      style={{
        display: 'inline-block',
        verticalAlign: 'middle',
        flexShrink: 0,
        width: `${size}px`,
        height: `${size}px`,
        objectFit: 'contain'
      }}
    />
  );

  if (variant === 'mark' && !showText) {
    return mark;
  }

  return (
    <div className={`brand-lockup ${className}`} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.65rem' }}>
      {mark}
      <div className="brand-text" style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.15 }}>
        <span style={{ fontWeight: 800, fontSize: '1.05rem', letterSpacing: '-0.02em', color: '#f8fafc' }}>
          Defense Monitor
        </span>
        <small style={{ fontSize: '0.72rem', opacity: 0.72, color: '#e2e8f0' }}>
          {isEn ? 'Defense & Strategic Intelligence' : 'مرکز اطلاعات و پایش دفاعی'}
        </small>
      </div>
    </div>
  );
}

export default IranMonitorLogo;

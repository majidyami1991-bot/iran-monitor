'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Shield, 
  Lock, 
  User, 
  Eye, 
  EyeOff, 
  KeyRound, 
  AlertCircle, 
  LogIn 
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import './login.css';

// Geographic points for Earth landmass silhouette (lat, lon in degrees)
const CONTINENTAL_POINTS: [number, number][] = [
  // Middle East & Iran region
  [35.6892, 51.3890], [32.4279, 53.6880], [38.0800, 46.2919], [29.5918, 52.5837], 
  [36.2605, 59.6168], [31.8974, 54.3569], [27.1832, 56.2666], [37.2808, 49.5832],
  [34.3277, 47.0778], [31.3183, 48.6706], [33.4878, 48.3558], [34.0954, 49.7013],
  [25.2769, 55.2962], [24.4539, 54.3773], [21.4858, 39.1925], [24.7136, 46.6753],
  [33.3152, 44.3661], [33.5138, 36.2765], [31.9522, 35.2332], [39.9334, 32.8597],
  [41.0082, 28.9784], [30.0444, 31.2357], [36.7538, 3.0588], [33.8869, 35.5131],
  // Eurasia / Europe / Asia
  [55.7558, 37.6173], [59.9343, 30.3351], [52.5200, 13.4050], [48.8566, 2.3522],
  [51.5074, -0.1278], [40.4168, -3.7038], [41.9028, 12.4964], [52.3676, 4.9041],
  [50.0755, 14.4378], [52.2297, 21.0122], [59.3293, 18.0686], [60.1699, 24.9384],
  [41.7151, 44.8271], [40.4093, 49.8671], [40.1792, 44.4991], [41.2995, 69.2401],
  [33.6844, 73.0479], [28.6139, 77.2090], [19.0760, 72.8777], [39.9042, 116.4074],
  [31.2304, 121.4737], [35.6762, 139.6503], [37.5665, 126.9780], [60.0, 100.0],
  [56.0, 92.0], [52.0, 104.0], [62.0, 129.0], [53.0, 158.0],
  // Africa
  [9.0820, 8.6753], [6.5244, 3.3792], [-1.2921, 36.8219], [-26.2041, 28.0473],
  [-33.9249, 18.4241], [14.6928, -17.4467], [8.9806, 38.7578], [0.3476, 32.5825],
  // Americas
  [38.9072, -77.0369], [40.7128, -74.0060], [34.0522, -118.2437], [41.8781, -87.6298],
  [29.7604, -95.3698], [45.5017, -73.5673], [19.4326, -99.1332], [-23.5505, -46.6333],
  [-34.6037, -58.3816], [-12.0464, -77.0428],
  // Australia & SE Asia
  [-33.8688, 151.2093], [-37.8136, 144.9631], [1.3521, 103.8198], [13.7563, 100.5018]
];

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Majestic Hazy Earth Canvas (Background only, no text, serene rotation)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let rotation = 0.9;
    const tilt = 0.35; // ~20 degrees axial tilt

    const handleResize = () => {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    };

    handleResize();
    window.addEventListener('resize', handleResize);

    const project = (latDeg: number, lonDeg: number, radius: number, rot: number, cx: number, cy: number) => {
      const lat = (latDeg * Math.PI) / 180;
      const lon = (lonDeg * Math.PI) / 180 + rot;

      let x = radius * Math.cos(lat) * Math.sin(lon);
      let y = -radius * Math.sin(lat);
      let z = radius * Math.cos(lat) * Math.cos(lon);

      const cosT = Math.cos(tilt);
      const sinT = Math.sin(tilt);
      const yTilted = y * cosT - x * sinT * 0.18;
      const xTilted = x * cosT + y * sinT * 0.18;

      return {
        x: cx + xTilted,
        y: cy + yTilted,
        z: z,
        visible: z > 0
      };
    };

    const render = () => {
      rotation += 0.0018; // Slow, majestic continuous rotation

      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      ctx.clearRect(0, 0, width, height);

      // Huge hazy Earth placed majestically in background
      // Centered slightly below or middle, expansive radius
      const cx = width / 2;
      const cy = height * 0.52;
      const radius = Math.min(width, height) * 0.58;

      // 1. Deep Hazy Volumetric Atmospheric Glows (Golden Amber & Deep Midnight Blue)
      const outerGlow = ctx.createRadialGradient(cx, cy, radius * 0.8, cx, cy, radius * 1.55);
      outerGlow.addColorStop(0, 'rgba(227, 179, 65, 0.18)'); // Warm cream/gold haze
      outerGlow.addColorStop(0.35, 'rgba(56, 114, 185, 0.12)'); // Deep warm navy aura
      outerGlow.addColorStop(0.7, 'rgba(15, 30, 55, 0.06)');
      outerGlow.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = outerGlow;
      ctx.beginPath();
      ctx.arc(cx, cy, radius * 1.6, 0, Math.PI * 2);
      ctx.fill();

      // 2. Earth Planet Disc & Subtle Terminator Gradient
      const planetGrad = ctx.createRadialGradient(
        cx - radius * 0.3,
        cy - radius * 0.35,
        radius * 0.1,
        cx,
        cy,
        radius
      );
      planetGrad.addColorStop(0, '#162844');
      planetGrad.addColorStop(0.45, '#0e1c31');
      planetGrad.addColorStop(0.85, '#08111e');
      planetGrad.addColorStop(1, '#040810');
      ctx.fillStyle = planetGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fill();

      // Subtle atmospheric rim
      ctx.strokeStyle = 'rgba(227, 179, 65, 0.35)';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // 3. Delicate Latitude & Longitude Mesh (Golden Ivory, low opacity, hazy)
      ctx.lineWidth = 0.6;
      for (let lat = -60; lat <= 60; lat += 30) {
        ctx.beginPath();
        let first = true;
        for (let lon = 0; lon <= 360; lon += 6) {
          const pt = project(lat, lon, radius, rotation, cx, cy);
          if (pt.visible) {
            const alpha = 0.08 + Math.max(0, pt.z / radius) * 0.15;
            ctx.strokeStyle = `rgba(227, 179, 65, ${alpha})`;
            if (first) {
              ctx.moveTo(pt.x, pt.y);
              first = false;
            } else {
              ctx.lineTo(pt.x, pt.y);
            }
          } else {
            first = true;
          }
        }
        ctx.stroke();
      }

      for (let lon = 0; lon < 360; lon += 30) {
        ctx.beginPath();
        let first = true;
        for (let lat = -80; lat <= 80; lat += 6) {
          const pt = project(lat, lon, radius, rotation, cx, cy);
          if (pt.visible) {
            const alpha = 0.06 + Math.max(0, pt.z / radius) * 0.14;
            ctx.strokeStyle = `rgba(180, 205, 237, ${alpha})`;
            if (first) {
              ctx.moveTo(pt.x, pt.y);
              first = false;
            } else {
              ctx.lineTo(pt.x, pt.y);
            }
          } else {
            first = true;
          }
        }
        ctx.stroke();
      }

      // 4. Soft Continental Point Cloud (Cream / Warm Golden Stars)
      for (const [lat, lon] of CONTINENTAL_POINTS) {
        const pt = project(lat, lon, radius, rotation, cx, cy);
        if (pt.visible) {
          const depthAlpha = Math.max(0.08, pt.z / radius);
          const isIran = lat > 25 && lat < 40 && lon > 44 && lon < 63;
          
          ctx.fillStyle = isIran
            ? `rgba(242, 199, 90, ${0.85 * depthAlpha})`
            : `rgba(215, 228, 245, ${0.4 * depthAlpha})`;

          ctx.beginPath();
          ctx.arc(pt.x, pt.y, isIran ? 2.4 : 1.6, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // 5. Subtle Middle East Luminous Amber Pulse (Quiet beacon, no text)
      const tehran = project(35.6892, 51.3890, radius, rotation, cx, cy);
      if (tehran.visible) {
        const alpha = Math.max(0.1, (tehran.z / radius) * 0.7);
        ctx.beginPath();
        ctx.arc(tehran.x, tehran.y, 4, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(242, 199, 90, ${alpha})`;
        ctx.shadowColor = '#e3b341';
        ctx.shadowBlur = 10;
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      // 6. Two Quiet Orbital Golden Arcs (Pure aesthetics, NO text)
      const drawOrbit = (inclination: number, speed: number, alphaBase: number) => {
        const orbitRadiusX = radius * 1.32;
        const orbitRadiusY = radius * 0.38;
        const satAngle = (Date.now() * 0.0004 * speed) % (Math.PI * 2);

        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(inclination);

        ctx.beginPath();
        ctx.ellipse(0, 0, orbitRadiusX, orbitRadiusY, 0, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(227, 179, 65, ${alphaBase})`;
        ctx.setLineDash([3, 8]);
        ctx.lineWidth = 1;
        ctx.stroke();

        const satX = orbitRadiusX * Math.cos(satAngle);
        const satY = orbitRadiusY * Math.sin(satAngle);

        ctx.beginPath();
        ctx.arc(satX, satY, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = '#f5ebd7';
        ctx.shadowColor = '#e3b341';
        ctx.shadowBlur = 6;
        ctx.fill();
        ctx.shadowBlur = 0;

        ctx.restore();
      };

      drawOrbit(-0.45, 0.9, 0.16);
      drawOrbit(0.62, -0.7, 0.12);

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

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
      setError(res.error || 'ورود ناموفق بود. نام کاربری یا کلمه عبور صحیح نمی‌باشد.');
    }
  };

  return (
    <div className="login-viewport">
      {/* Background Majestic Hazy Earth Canvas (Background Only, No Text) */}
      <div className="login-bg" aria-hidden="true">
        <canvas ref={canvasRef} className="majestic-earth-canvas" />
        <div className="majestic-vignette" />
      </div>

      {/* Centered Elegant Dark Blue & Cream Login Card */}
      <div className="login-card-container">
        <div className="login-card">
          {/* Subtle Warm Gold HUD Corners */}
          <span className="card-corner corner-tl" />
          <span className="card-corner corner-tr" />
          <span className="card-corner corner-bl" />
          <span className="card-corner corner-br" />

          {/* Header Branding */}
          <div className="login-header">
            <div className="brand-badge">
              <Shield size={32} />
            </div>
            <h1 className="login-title">سامانه رصد و پایش ایران</h1>
            <div className="login-subtitle">
              <span className="status-dot" />
              <span>مرکز پردازش اطلاعات و پایش دفاعی</span>
            </div>
          </div>

          {/* Error Notice */}
          {error && (
            <div className="login-alert" role="alert">
              <AlertCircle size={18} className="alert-icon" />
              <span className="alert-text">{error}</span>
            </div>
          )}

          {/* Clean Authentication Form */}
          <form onSubmit={handleSubmit} className="login-form">
            <div className="input-group">
              <label className="input-label" htmlFor="username">
                <User size={15} />
                <span>نام کاربری</span>
              </label>
              <div className="input-wrapper">
                <input
                  id="username"
                  type="text"
                  autoComplete="username"
                  autoFocus
                  placeholder="مانند admin یا intel_officer"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="tactical-input"
                  disabled={isSubmitting}
                />
              </div>
            </div>

            <div className="input-group">
              <label className="input-label" htmlFor="password">
                <KeyRound size={15} />
                <span>رمز عبور</span>
              </label>
              <div className="input-wrapper">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="کلمه عبور..."
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="tactical-input"
                  disabled={isSubmitting}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="toggle-pw-btn"
                  tabIndex={-1}
                  aria-label={showPassword ? 'مخفی کردن رمز عبور' : 'نمایش رمز عبور'}
                >
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </div>

            <div className="form-meta-row">
              <label className="remember-checkbox-label">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="tactical-checkbox"
                />
                <span>مرا به خاطر بسپار</span>
              </label>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className={`login-submit-btn ${isSubmitting ? 'submitting' : ''}`}
            >
              {isSubmitting ? (
                <>
                  <span className="spinner" />
                  <span>در حال احراز هویت...</span>
                </>
              ) : (
                <>
                  <LogIn size={18} />
                  <span>ورود به سامانه</span>
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

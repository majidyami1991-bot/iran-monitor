'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Shield, 
  User, 
  Eye, 
  EyeOff, 
  KeyRound, 
  AlertCircle, 
  LogIn 
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { WORLD_COUNTRIES, CountryData } from './worldCountriesData';
import './login.css';

// 64 Orbiting Artificial Intelligence Satellites across 8 Tactical Orbital Planes
interface OrbitSatellite {
  radiusFactor: number;
  inclination: number; // inclination angle in radians
  speed: number;
  phase: number;
  size: number;
  color: string;
  glowColor: string;
  hasPing: boolean;
  planeId: number;
}

const GENERATE_SATELLITES = (): OrbitSatellite[] => {
  const satellites: OrbitSatellite[] = [];
  const planes = [
    { radiusFactor: 1.14, inclination: 0.15, speed: 0.75, color: '#f2c75a', glowColor: '#e3b341' },
    { radiusFactor: 1.20, inclination: 0.65, speed: -0.85, color: '#e0f2fe', glowColor: '#38bdf8' },
    { radiusFactor: 1.26, inclination: -0.58, speed: 0.68, color: '#fef08a', glowColor: '#ca8a04' },
    { radiusFactor: 1.34, inclination: 1.05, speed: -0.52, color: '#ffffff', glowColor: '#93c5fd' },
    { radiusFactor: 1.42, inclination: -0.32, speed: 0.42, color: '#f2c75a', glowColor: '#d97706' },
    { radiusFactor: 1.18, inclination: 1.42, speed: 0.92, color: '#bfdbfe', glowColor: '#60a5fa' },
    { radiusFactor: 1.28, inclination: -1.35, speed: -0.78, color: '#fed7aa', glowColor: '#ea580c' },
    { radiusFactor: 1.55, inclination: 0.48, speed: 0.32, color: '#fef9c3', glowColor: '#f59e0b' }
  ];

  planes.forEach((plane, pIdx) => {
    const countInPlane = 8;
    for (let i = 0; i < countInPlane; i++) {
      const phase = (i / countInPlane) * Math.PI * 2 + (pIdx * 0.4);
      satellites.push({
        radiusFactor: plane.radiusFactor + (Math.sin(i) * 0.02),
        inclination: plane.inclination,
        speed: plane.speed * (0.95 + (i % 3) * 0.05),
        phase: phase,
        size: 2.2 + (i % 3) * 0.6,
        color: i % 4 === 0 ? '#ffffff' : plane.color,
        glowColor: plane.glowColor,
        hasPing: i % 2 === 0,
        planeId: pIdx
      });
    }
  });

  return satellites;
};

const SATELLITE_FLEET = GENERATE_SATELLITES();

// Point-in-polygon algorithm for GeoJSON country detection
function isPointInRing(lon: number, lat: number, ring: [number, number][]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0], yi = ring[i][1];
    const xj = ring[j][0], yj = ring[j][1];
    const intersect = ((yi > lat) !== (yj > lat)) &&
      (lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

function findCountryAtCoords(lonDeg: number, latDeg: number): CountryData | null {
  let nLon = lonDeg;
  while (nLon > 180) nLon -= 360;
  while (nLon < -180) nLon += 360;

  for (const country of WORLD_COUNTRIES) {
    const [minLon, minLat, maxLon, maxLat] = country.bbox;
    // Bounding box test
    if (nLon < minLon - 0.5 || nLon > maxLon + 0.5 || latDeg < minLat - 0.5 || latDeg > maxLat + 0.5) {
      continue;
    }
    // Ring test
    for (const ring of country.rings) {
      if (isPointInRing(nLon, latDeg, ring)) {
        return country;
      }
    }
  }
  return null;
}

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

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let rotation = 0.95;
    const tilt = 0.38; // ~22 degrees axial tilt
    const cosT = Math.cos(tilt);
    const sinT = Math.sin(tilt);

    // Mouse tracking for country hover & 3D extrusion
    let mouseX = -9999;
    let mouseY = -9999;
    let currentHoveredCountry: CountryData | null = null;
    let activeLift = 0; // 0 to 1 smooth extrusion factor

    const handleMouseMove = (e: MouseEvent) => {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      mouseX = e.clientX - rect.left;
      mouseY = e.clientY - rect.top;
    };

    const handleMouseLeave = () => {
      mouseX = -9999;
      mouseY = -9999;
      currentHoveredCountry = null;
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeave);

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

    // 3D Point Projection onto Tilted Rotating Sphere
    const project3D = (latDeg: number, lonDeg: number, radius: number, rot: number, cx: number, cy: number) => {
      const lat = (latDeg * Math.PI) / 180;
      const lon = (lonDeg * Math.PI) / 180 + rot;

      const x0 = radius * Math.cos(lat) * Math.sin(lon);
      const y0 = -radius * Math.sin(lat);
      const z0 = radius * Math.cos(lat) * Math.cos(lon);

      // Rotate around X-axis by tilt
      const xTilted = x0;
      const yTilted = y0 * cosT - z0 * sinT;
      const zTilted = y0 * sinT + z0 * cosT;

      return {
        x: cx + xTilted,
        y: cy + yTilted,
        z: zTilted,
        visible: zTilted > -radius * 0.05
      };
    };

    // Inverse Raycast: Screen (x, y) -> Sphere Geographic (lat, lon)
    const raycastSphere = (screenX: number, screenY: number, radius: number, rot: number, cx: number, cy: number) => {
      const dx = screenX - cx;
      const dy = screenY - cy;
      const distSq = dx * dx + dy * dy;

      if (distSq > radius * radius) {
        return null;
      }

      const zTilted = Math.sqrt(radius * radius - distSq);
      const yTilted = dy;
      const x0 = dx;

      // Inverse tilt around X
      const y0 = yTilted * cosT + zTilted * sinT;
      const z0 = -yTilted * sinT + zTilted * cosT;

      const sinLat = Math.max(-1, Math.min(1, -y0 / radius));
      const lat = Math.asin(sinLat);
      const cosLat = Math.cos(lat);

      if (Math.abs(cosLat) < 0.0001) return null;

      const sinLonTot = (x0 / radius) / cosLat;
      const cosLonTot = (z0 / radius) / cosLat;
      const lonTot = Math.atan2(sinLonTot, cosLonTot);
      const lon = lonTot - rot;

      let lonDeg = (lon * 180) / Math.PI;
      while (lonDeg > 180) lonDeg -= 360;
      while (lonDeg < -180) lonDeg += 360;

      return {
        latDeg: (lat * 180) / Math.PI,
        lonDeg: lonDeg
      };
    };

    // Deep cosmic background stars
    const backgroundStars: { x: number; y: number; r: number; alpha: number; speed: number }[] = [];
    for (let i = 0; i < 110; i++) {
      backgroundStars.push({
        x: Math.random(),
        y: Math.random(),
        r: Math.random() * 1.6 + 0.4,
        alpha: Math.random() * 0.7 + 0.3,
        speed: Math.random() * 0.002 + 0.001
      });
    }

    const render = () => {
      rotation += 0.0014; // Serene constant planetary rotation

      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      ctx.clearRect(0, 0, width, height);

      const now = Date.now();

      // Render cosmic background stars
      for (const star of backgroundStars) {
        const sx = star.x * width;
        const sy = star.y * height;
        const twinkle = 0.4 + 0.6 * Math.sin(now * star.speed + star.x * 20);
        ctx.fillStyle = `rgba(240, 245, 255, ${star.alpha * twinkle * 0.65})`;
        ctx.beginPath();
        ctx.arc(sx, sy, star.r, 0, Math.PI * 2);
        ctx.fill();
      }

      // Earth positioned on the RIGHT side, significantly BIGGER
      const isMobile = width < 960;
      const cx = isMobile ? width * 0.5 : width * 0.70;
      const cy = isMobile ? height * 0.72 : height * 0.50;
      const radius = Math.min(width, height) * (isMobile ? 0.45 : 0.49);

      // Check mouse raycast for country hover
      const hit = raycastSphere(mouseX, mouseY, radius, rotation, cx, cy);
      if (hit) {
        const found = findCountryAtCoords(hit.lonDeg, hit.latDeg);
        if (found) {
          currentHoveredCountry = found;
          activeLift = Math.min(1, activeLift + 0.15);
        } else {
          activeLift = Math.max(0, activeLift - 0.08);
          if (activeLift <= 0.02) currentHoveredCountry = null;
        }
      } else {
        activeLift = Math.max(0, activeLift - 0.08);
        if (activeLift <= 0.02) currentHoveredCountry = null;
      }

      // 1. Atmospheric Volumetric Glows (Vibrant Golden Cream & Royal Navy)
      const outerGlow = ctx.createRadialGradient(cx, cy, radius * 0.88, cx, cy, radius * 1.68);
      outerGlow.addColorStop(0, 'rgba(242, 199, 90, 0.28)'); // Radiant gold rim
      outerGlow.addColorStop(0.3, 'rgba(56, 114, 210, 0.18)'); // Royal sapphire haze
      outerGlow.addColorStop(0.68, 'rgba(15, 30, 65, 0.08)');
      outerGlow.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = outerGlow;
      ctx.beginPath();
      ctx.arc(cx, cy, radius * 1.68, 0, Math.PI * 2);
      ctx.fill();

      // 2. Planet Base Ocean Disc
      const planetGrad = ctx.createRadialGradient(
        cx - radius * 0.32,
        cy - radius * 0.38,
        radius * 0.12,
        cx,
        cy,
        radius
      );
      planetGrad.addColorStop(0, '#162b4c');
      planetGrad.addColorStop(0.4, '#0f1c32');
      planetGrad.addColorStop(0.78, '#08111e');
      planetGrad.addColorStop(1, '#03070f');
      ctx.fillStyle = planetGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fill();

      // Atmospheric Rim Highlight
      ctx.strokeStyle = 'rgba(242, 199, 90, 0.55)';
      ctx.lineWidth = 1.8;
      ctx.stroke();

      // 3. Delicate Coordinate Graticule (Lat/Lon grid)
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.clip();

      ctx.lineWidth = 0.5;
      for (let lat = -60; lat <= 60; lat += 20) {
        ctx.beginPath();
        let first = true;
        for (let lon = -180; lon <= 180; lon += 5) {
          const pt = project3D(lat, lon, radius, rotation, cx, cy);
          if (pt.visible) {
            const alpha = 0.04 + Math.max(0, pt.z / radius) * 0.12;
            ctx.strokeStyle = `rgba(227, 179, 65, ${alpha})`;
            if (first) { ctx.moveTo(pt.x, pt.y); first = false; }
            else { ctx.lineTo(pt.x, pt.y); }
          } else {
            first = true;
          }
        }
        ctx.stroke();
      }

      for (let lon = -180; lon <= 180; lon += 30) {
        ctx.beginPath();
        let first = true;
        for (let lat = -80; lat <= 80; lat += 5) {
          const pt = project3D(lat, lon, radius, rotation, cx, cy);
          if (pt.visible) {
            const alpha = 0.04 + Math.max(0, pt.z / radius) * 0.12;
            ctx.strokeStyle = `rgba(186, 215, 250, ${alpha})`;
            if (first) { ctx.moveTo(pt.x, pt.y); first = false; }
            else { ctx.lineTo(pt.x, pt.y); }
          } else {
            first = true;
          }
        }
        ctx.stroke();
      }

      // 4. REAL WORLD MAP: Render all 175 Countries on the Sphere Surface
      for (const country of WORLD_COUNTRIES) {
        const isHovered = currentHoveredCountry?.name === country.name;
        if (isHovered) continue; // Draw hovered country separately with 3D lift

        const isIran = country.name === 'Iran';

        ctx.fillStyle = isIran ? 'rgba(242, 199, 90, 0.28)' : 'rgba(18, 38, 64, 0.75)';
        ctx.strokeStyle = isIran ? 'rgba(242, 199, 90, 0.95)' : 'rgba(125, 168, 222, 0.35)';
        ctx.lineWidth = isIran ? 1.6 : 0.8;

        for (const ring of country.rings) {
          ctx.beginPath();
          let drawn = false;
          let first = true;

          for (const [rLon, rLat] of ring) {
            const pt = project3D(rLat, rLon, radius, rotation, cx, cy);
            if (pt.visible) {
              if (first) {
                ctx.moveTo(pt.x, pt.y);
                first = false;
                drawn = true;
              } else {
                ctx.lineTo(pt.x, pt.y);
              }
            } else {
              first = true;
            }
          }

          if (drawn) {
            ctx.closePath();
            ctx.fill();
            ctx.stroke();
          }
        }
      }

      // Tactical Pulse Beacon over Tehran / Iran (Operating Hub)
      const tehran = project3D(35.6892, 51.3890, radius, rotation, cx, cy);
      if (tehran.visible) {
        const alpha = Math.max(0.2, (tehran.z / radius) * 0.9);
        const pulse = (Math.sin(now * 0.005) + 1) * 0.5;

        // Expanding radar pulse ring
        ctx.beginPath();
        ctx.arc(tehran.x, tehran.y, 6 + pulse * 15, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(242, 199, 90, ${alpha * (1 - pulse) * 0.8})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Glowing center dot
        ctx.beginPath();
        ctx.arc(tehran.x, tehran.y, 4, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(242, 199, 90, ${alpha})`;
        ctx.shadowColor = '#e3b341';
        ctx.shadowBlur = 12;
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      ctx.restore(); // End base globe clipping

      // 5. 3D COUNTRY HIGHLIGHT & EXTRUSION / LIFT
      // When a country is hovered, lift its polygon outward in 3D with extruded walls & glowing cap!
      if (currentHoveredCountry && activeLift > 0.01) {
        const liftHeight = 18 * activeLift; // Extrusion height up to 18px outward
        const country = currentHoveredCountry;

        for (const ring of country.rings) {
          // Pre-calculate base and elevated vertices
          const basePts = ring.map(([rLon, rLat]) => project3D(rLat, rLon, radius, rotation, cx, cy));
          const liftedPts = ring.map(([rLon, rLat]) => project3D(rLat, rLon, radius + liftHeight, rotation, cx, cy));

          // Draw 3D Extruded Side Walls connecting ground to elevated polygon
          for (let i = 0; i < ring.length - 1; i++) {
            const b1 = basePts[i];
            const b2 = basePts[i + 1];
            const t1 = liftedPts[i];
            const t2 = liftedPts[i + 1];

            if (b1.visible || b2.visible) {
              ctx.beginPath();
              ctx.moveTo(b1.x, b1.y);
              ctx.lineTo(b2.x, b2.y);
              ctx.lineTo(t2.x, t2.y);
              ctx.lineTo(t1.x, t1.y);
              ctx.closePath();

              ctx.fillStyle = `rgba(200, 135, 25, ${0.75 * activeLift})`;
              ctx.strokeStyle = `rgba(245, 205, 95, ${0.9 * activeLift})`;
              ctx.lineWidth = 1;
              ctx.fill();
              ctx.stroke();
            }
          }

          // Draw Elevated Top Polygon Cap (Luminous Warm Gold Fill & Glowing Edges)
          ctx.beginPath();
          let first = true;
          let capDrawn = false;
          for (const pt of liftedPts) {
            if (pt.visible) {
              if (first) {
                ctx.moveTo(pt.x, pt.y);
                first = false;
                capDrawn = true;
              } else {
                ctx.lineTo(pt.x, pt.y);
              }
            } else {
              first = true;
            }
          }

          if (capDrawn) {
            ctx.closePath();
            ctx.fillStyle = `rgba(245, 215, 115, ${0.85 * activeLift})`;
            ctx.shadowColor = '#f2c75a';
            ctx.shadowBlur = 18 * activeLift;
            ctx.fill();
            ctx.shadowBlur = 0;

            ctx.strokeStyle = `rgba(255, 255, 240, ${activeLift})`;
            ctx.lineWidth = 2.2;
            ctx.stroke();
          }
        }

        // Draw Tactical Sci-Fi HUD Label with Country Name & Coordinates
        const centroidPt = project3D(
          country.centroid[0],
          country.centroid[1],
          radius + liftHeight + 6,
          rotation,
          cx,
          cy
        );

        if (centroidPt.visible) {
          const labelText = `${country.name.toUpperCase()} ${country.code ? `[${country.code}]` : ''}`;
          ctx.font = '600 12px monospace';
          const textWidth = ctx.measureText(labelText).width;

          const tagX = centroidPt.x + 22;
          const tagY = centroidPt.y - 18;

          // Pointer Line
          ctx.beginPath();
          ctx.moveTo(centroidPt.x, centroidPt.y);
          ctx.lineTo(tagX - 6, tagY);
          ctx.lineTo(tagX + textWidth + 14, tagY);
          ctx.strokeStyle = `rgba(242, 199, 90, ${0.85 * activeLift})`;
          ctx.lineWidth = 1.4;
          ctx.stroke();

          // Tag Box Background
          ctx.fillStyle = `rgba(8, 16, 28, ${0.9 * activeLift})`;
          ctx.fillRect(tagX - 4, tagY - 14, textWidth + 16, 20);

          // Tag Border
          ctx.strokeStyle = `rgba(242, 199, 90, ${0.75 * activeLift})`;
          ctx.lineWidth = 1;
          ctx.strokeRect(tagX - 4, tagY - 14, textWidth + 16, 20);

          // Tag Text
          ctx.fillStyle = `rgba(255, 240, 180, ${activeLift})`;
          ctx.fillText(labelText, tagX + 4, tagY);
        }
      }

      // 6. FLEET OF 64 ARTIFICIAL INTELLIGENCE SATELLITES
      // Render orbital guide rings, phosphor tails, satellites and transmission pings
      const drawnPlanes = new Set<number>();

      for (let i = 0; i < SATELLITE_FLEET.length; i++) {
        const sat = SATELLITE_FLEET[i];
        const orbitRadius = radius * sat.radiusFactor;
        const currentAngle = (now * 0.00032 * sat.speed + sat.phase) % (Math.PI * 2);

        // Orbital mechanics on tilted orbital plane
        const satX0 = orbitRadius * Math.cos(currentAngle);
        const satY0 = 0;
        const satZ0 = orbitRadius * Math.sin(currentAngle);

        const cosInc = Math.cos(sat.inclination);
        const sinInc = Math.sin(sat.inclination);

        const xInc = satX0 * cosInc - satY0 * sinInc;
        const yInc = satX0 * sinInc + satY0 * cosInc;
        const zInc = satZ0;

        const xFinal = xInc;
        const yFinal = yInc * cosT - zInc * sinT;
        const zFinal = yInc * sinT + zInc * cosT;

        const screenX = cx + xFinal;
        const screenY = cy + yFinal;

        // Draw orbital guide path once per plane
        if (!drawnPlanes.has(sat.planeId)) {
          drawnPlanes.add(sat.planeId);
          ctx.save();
          ctx.translate(cx, cy);
          ctx.rotate(sat.inclination * 0.4);
          ctx.beginPath();
          ctx.ellipse(0, 0, orbitRadius, orbitRadius * 0.42, sat.inclination, 0, Math.PI * 2);
          ctx.strokeStyle = 'rgba(227, 179, 65, 0.06)';
          ctx.setLineDash([2, 10]);
          ctx.lineWidth = 0.8;
          ctx.stroke();
          ctx.restore();
        }

        // Occlusion check: Is satellite behind the opaque planet body?
        const isBehind = zFinal < 0 && (xFinal * xFinal + yFinal * yFinal < radius * radius);
        if (isBehind) continue;

        // Phosphor comet trail behind satellite
        for (let t = 1; t <= 3; t++) {
          const tailAngle = currentAngle - (sat.speed > 0 ? 0.04 : -0.04) * t;
          const tX0 = orbitRadius * Math.cos(tailAngle);
          const tZ0 = orbitRadius * Math.sin(tailAngle);
          const tXInc = tX0 * cosInc;
          const tYInc = tX0 * sinInc;
          const tailScreenX = cx + tXInc;
          const tailScreenY = cy + (tYInc * cosT - tZ0 * sinT);

          ctx.beginPath();
          ctx.arc(tailScreenX, tailScreenY, sat.size * (1 - t * 0.25), 0, Math.PI * 2);
          ctx.fillStyle = `${sat.glowColor}${Math.floor((0.35 / t) * 255).toString(16).padStart(2, '0')}`;
          ctx.fill();
        }

        // Satellite Body
        ctx.beginPath();
        ctx.arc(screenX, screenY, sat.size, 0, Math.PI * 2);
        ctx.fillStyle = sat.color;
        ctx.shadowColor = sat.glowColor;
        ctx.shadowBlur = 10;
        ctx.fill();
        ctx.shadowBlur = 0;

        // Periodic telemetry radar beacon ping pulse
        if (sat.hasPing) {
          const pingPhase = ((now * 0.002 * Math.abs(sat.speed) + sat.phase * 3) % Math.PI);
          ctx.beginPath();
          ctx.arc(screenX, screenY, sat.size + pingPhase * 9, 0, Math.PI * 2);
          ctx.strokeStyle = `${sat.glowColor}${Math.floor((1 - pingPhase / Math.PI) * 160).toString(16).padStart(2, '0')}`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
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
      {/* Dynamic 3D Earth with Real World Map, Country Lift & 64 Satellites */}
      <div className="login-bg" aria-hidden="true">
        <canvas ref={canvasRef} className="majestic-earth-canvas" />
        <div className="majestic-vignette" />
      </div>

      {/* Main Layout Container: Panel on the LEFT, Earth visible on the RIGHT */}
      <div className="login-layout-container">
        {/* Left Side: Elegant Dark Blue & Warm Cream Login Panel */}
        <div className="login-card-container">
          <div className="login-card">
            {/* Warm Gold Corner Accents */}
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

        {/* Right Side Spacer / Interactive Viewport Area */}
        <div className="login-earth-hero" aria-hidden="true" />
      </div>
    </div>
  );
}

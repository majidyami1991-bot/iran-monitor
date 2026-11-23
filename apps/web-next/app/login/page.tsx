'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { 
  User, 
  Eye, 
  EyeOff, 
  KeyRound, 
  AlertCircle, 
  LogIn 
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { IranMonitorLogo } from '../design/Logo';
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
    // Initial camera rotation centered directly over Asia (Iran 53°E, India 78°E, China 105°E)
    let rotation = -(75 * Math.PI) / 180;
    let currentTilt = -0.28; // Default favorable perspective on Northern Hemisphere
    let targetTilt = -0.28;
    let cosT = Math.cos(currentTilt);
    let sinT = Math.sin(currentTilt);

    // Mouse tracking for country hover & 3D extrusion
    let mouseX = -9999;
    let mouseY = -9999;
    let currentHoveredCountry: CountryData | null = null;
    let activeLift = 0; // 0 to 1 smooth extrusion factor

    // Interactive Drag-to-Spin State (Horizontally constrained per user requirement)
    let isDragging = false;
    let dragStartX = 0;
    let dragRotationStart = 0;
    let dragVelocity = 0;
    let lastDragX = 0;
    let lastDragTime = 0;

    const handleMouseDown = (e: MouseEvent) => {
      if (e.button !== 0) return;
      const target = e.target as HTMLElement | null;
      if (target && target.closest('.login-card')) return;
      isDragging = true;
      dragStartX = e.clientX;
      lastDragX = e.clientX;
      lastDragTime = performance.now();
      dragRotationStart = rotation;
      dragVelocity = 0;
      if (canvas) canvas.style.cursor = 'grabbing';
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      mouseX = e.clientX - rect.left;
      mouseY = e.clientY - rect.top;

      if (isDragging) {
        // Drag spinning ONLY applies to horizontal movement, not vertical
        const deltaX = e.clientX - dragStartX;
        const now = performance.now();
        const dt = Math.max(1, now - lastDragTime);
        const stepDeltaX = e.clientX - lastDragX;
        dragVelocity = (stepDeltaX / dt) * 0.003;
        lastDragX = e.clientX;
        lastDragTime = now;
        rotation = dragRotationStart + (deltaX * 0.005);
      }
    };

    const handleMouseUp = () => {
      if (isDragging) {
        isDragging = false;
        if (canvas) canvas.style.cursor = 'grab';
      }
    };

    const handleTouchStart = (e: TouchEvent) => {
      if (e.touches.length !== 1) return;
      const t = e.touches[0];
      const target = e.target as HTMLElement | null;
      if (target && target.closest('.login-card')) return;
      isDragging = true;
      dragStartX = t.clientX;
      lastDragX = t.clientX;
      lastDragTime = performance.now();
      dragRotationStart = rotation;
      dragVelocity = 0;
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (!isDragging || e.touches.length !== 1) return;
      const t = e.touches[0];
      const deltaX = t.clientX - dragStartX;
      const now = performance.now();
      const dt = Math.max(1, now - lastDragTime);
      const stepDeltaX = t.clientX - lastDragX;
      dragVelocity = (stepDeltaX / dt) * 0.003;
      lastDragX = t.clientX;
      lastDragTime = now;
      rotation = dragRotationStart + (deltaX * 0.005);
    };

    const handleTouchEnd = () => {
      isDragging = false;
    };

    const handleMouseLeave = () => {
      if (isDragging) {
        isDragging = false;
        if (canvas) canvas.style.cursor = 'grab';
      }
      mouseX = -9999;
      mouseY = -9999;
      currentHoveredCountry = null;
    };

    window.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('mouseleave', handleMouseLeave);
    window.addEventListener('touchstart', handleTouchStart, { passive: true });
    window.addEventListener('touchmove', handleTouchMove, { passive: true });
    window.addEventListener('touchend', handleTouchEnd);

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

    // Spherical Hemisphere Polygon Clipper (Sutherland-Hodgman)
    // Clips polygons at the planetary horizon (z >= 0) and closes them along the circular limb.
    // Completely eliminates visual glitches and chords when large countries (like Russia) wrap around the globe.
    const clipRingToHemisphere = (
      ring: [number, number][],
      rad: number,
      rot: number,
      centerX: number,
      centerY: number
    ): { x: number; y: number }[] => {
      const len = ring.length;
      if (len === 0) return [];

      const pts = ring.map(([rLon, rLat]) => {
        const latRad = (rLat * Math.PI) / 180;
        const lonRad = (rLon * Math.PI) / 180 + rot;
        const x0 = rad * Math.cos(latRad) * Math.sin(lonRad);
        const y0 = -rad * Math.sin(latRad);
        const z0 = rad * Math.cos(latRad) * Math.cos(lonRad);
        const xTilted = x0;
        const yTilted = y0 * cosT - z0 * sinT;
        const zTilted = y0 * sinT + z0 * cosT;
        return { x: xTilted, y: yTilted, z: zTilted };
      });

      const clipped: { x: number; y: number }[] = [];
      let lastExitAngle: number | null = null;

      for (let i = 0; i < len; i++) {
        const curr = pts[i];
        const prev = pts[(i - 1 + len) % len];
        const currIn = curr.z >= 0;
        const prevIn = prev.z >= 0;

        if (currIn) {
          if (!prevIn) {
            // Entering visible hemisphere from behind horizon
            const t = -prev.z / (curr.z - prev.z);
            const ix = prev.x + t * (curr.x - prev.x);
            const iy = prev.y + t * (curr.y - prev.y);
            const enterAngle = Math.atan2(iy, ix);

            if (lastExitAngle !== null) {
              const diff = ((enterAngle - lastExitAngle + Math.PI) % (2 * Math.PI)) - Math.PI;
              const steps = Math.max(1, Math.floor(Math.abs(diff) / 0.08));
              for (let s = 1; s < steps; s++) {
                const a = lastExitAngle + diff * (s / steps);
                clipped.push({ x: centerX + rad * Math.cos(a), y: centerY + rad * Math.sin(a) });
              }
              lastExitAngle = null;
            }
            clipped.push({ x: centerX + rad * Math.cos(enterAngle), y: centerY + rad * Math.sin(enterAngle) });
          }
          clipped.push({ x: centerX + curr.x, y: centerY + curr.y });
        } else if (prevIn) {
          // Exiting visible hemisphere to behind horizon
          const t = prev.z / (prev.z - curr.z);
          const ix = prev.x + t * (curr.x - prev.x);
          const iy = prev.y + t * (curr.y - prev.y);
          const exitAngle = Math.atan2(iy, ix);
          clipped.push({ x: centerX + rad * Math.cos(exitAngle), y: centerY + rad * Math.sin(exitAngle) });
          lastExitAngle = exitAngle;
        }
      }

      if (lastExitAngle !== null && clipped.length > 0) {
        const firstPt = clipped[0];
        const firstAngle = Math.atan2(firstPt.y - centerY, firstPt.x - centerX);
        const diff = ((firstAngle - lastExitAngle + Math.PI) % (2 * Math.PI)) - Math.PI;
        const steps = Math.max(1, Math.floor(Math.abs(diff) / 0.08));
        for (let s = 1; s < steps; s++) {
          const a = lastExitAngle + diff * (s / steps);
          clipped.push({ x: centerX + rad * Math.cos(a), y: centerY + rad * Math.sin(a) });
        }
      }

      return clipped;
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
      if (!isDragging) {
        if (Math.abs(dragVelocity) > 0.00005) {
          rotation += dragVelocity;
          dragVelocity *= 0.94; // Smooth inertial spin release
        } else {
          rotation += 0.0014; // Serene constant planetary rotation
        }
      }

      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      ctx.clearRect(0, 0, width, height);

      // Dynamic interactive camera tilt:
      // Moving mouse higher (mouseY -> 0) pitches camera up to reveal the top/Northern Hemisphere (-0.46 rad)
      // Moving mouse lower tilts camera down towards equatorial & southern regions (+0.24 rad)
      if (mouseY > -9000 && height > 0) {
        const normY = Math.max(0, Math.min(1, mouseY / height));
        targetTilt = -0.48 + normY * 0.72;
      } else {
        targetTilt = -0.28; // Default favorable perspective on Northern Hemisphere & Iran
      }
      currentTilt += (targetTilt - currentTilt) * 0.08;
      cosT = Math.cos(currentTilt);
      sinT = Math.sin(currentTilt);

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
      outerGlow.addColorStop(0, 'rgba(252, 211, 77, 0.42)'); // Radiant gold rim
      outerGlow.addColorStop(0.24, 'rgba(96, 165, 250, 0.28)'); // Royal sapphire haze
      outerGlow.addColorStop(0.65, 'rgba(20, 50, 100, 0.08)');
      outerGlow.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = outerGlow;
      ctx.beginPath();
      ctx.arc(cx, cy, radius * 1.68, 0, Math.PI * 2);
      ctx.fill();

      // 2. Planet Base Ocean Disc (Deep, luminous sapphire navy)
      const planetGrad = ctx.createRadialGradient(
        cx - radius * 0.32,
        cy - radius * 0.38,
        radius * 0.12,
        cx,
        cy,
        radius
      );
      planetGrad.addColorStop(0, '#1d3e6d');
      planetGrad.addColorStop(0.42, '#132847');
      planetGrad.addColorStop(0.8, '#0a172a');
      planetGrad.addColorStop(1, '#050c18');
      ctx.fillStyle = planetGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fill();

      // Atmospheric Rim Highlight
      ctx.strokeStyle = 'rgba(252, 211, 77, 0.75)';
      ctx.lineWidth = 2.0;
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

        ctx.fillStyle = isIran ? 'rgba(242, 199, 90, 0.38)' : 'rgba(30, 58, 96, 0.9)';
        ctx.strokeStyle = isIran ? 'rgba(255, 220, 90, 1.0)' : 'rgba(165, 210, 255, 0.85)';
        ctx.lineWidth = isIran ? 2.4 : 1.3;

        for (const ring of country.rings) {
          const pts = clipRingToHemisphere(ring, radius, rotation, cx, cy);
          if (pts.length >= 3) {
            ctx.beginPath();
            ctx.moveTo(pts[0].x, pts[0].y);
            for (let i = 1; i < pts.length; i++) {
              ctx.lineTo(pts[i].x, pts[i].y);
            }
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
          const basePts = clipRingToHemisphere(ring, radius, rotation, cx, cy);
          const liftedPts = clipRingToHemisphere(ring, radius + liftHeight, rotation, cx, cy);

          // Draw 3D Extruded Side Walls connecting ground to elevated polygon
          const minLen = Math.min(basePts.length, liftedPts.length);
          for (let i = 0; i < minLen - 1; i++) {
            const b1 = basePts[i];
            const b2 = basePts[i + 1];
            const t1 = liftedPts[i];
            const t2 = liftedPts[i + 1];

            ctx.beginPath();
            ctx.moveTo(b1.x, b1.y);
            ctx.lineTo(b2.x, b2.y);
            ctx.lineTo(t2.x, t2.y);
            ctx.lineTo(t1.x, t1.y);
            ctx.closePath();

            ctx.fillStyle = `rgba(215, 135, 15, ${0.9 * activeLift})`;
            ctx.strokeStyle = `rgba(255, 235, 140, ${activeLift})`;
            ctx.lineWidth = 1.3;
            ctx.fill();
            ctx.stroke();
          }

          // Draw Elevated Top Polygon Cap (Brilliant Luminous Sunny Gold & White Edges)
          if (liftedPts.length >= 3) {
            ctx.beginPath();
            ctx.moveTo(liftedPts[0].x, liftedPts[0].y);
            for (let i = 1; i < liftedPts.length; i++) {
              ctx.lineTo(liftedPts[i].x, liftedPts[i].y);
            }
            ctx.closePath();
            ctx.fillStyle = `rgba(255, 238, 140, ${0.96 * activeLift})`;
            ctx.shadowColor = '#f59e0b';
            ctx.shadowBlur = 28 * activeLift;
            ctx.fill();
            ctx.shadowBlur = 0;

            ctx.strokeStyle = `rgba(255, 255, 255, ${activeLift})`;
            ctx.lineWidth = 2.6;
            ctx.stroke();
          }
        }

        // Draw Tactical Sci-Fi HUD Label with Country Name (Clean typography, NO black box)
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
          ctx.font = '700 13px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace';
          ctx.textAlign = 'left'; // Enforce left alignment regardless of RTL document context
          ctx.textBaseline = 'bottom'; // Baseline right above horizontal golden line
          const textWidth = ctx.measureText(labelText).width;

          // Glowing Centroid Target Beacon
          ctx.beginPath();
          ctx.arc(centroidPt.x, centroidPt.y, 4, 0, Math.PI * 2);
          ctx.fillStyle = '#ffffff';
          ctx.shadowColor = '#f59e0b';
          ctx.shadowBlur = 10;
          ctx.fill();
          ctx.shadowBlur = 0;

          // Adapt line direction so it never clips off-screen on the right edge
          const goLeft = centroidPt.x > cx + radius * 0.35;
          const elbowX = goLeft ? centroidPt.x - 24 : centroidPt.x + 24;
          const endX = goLeft ? elbowX - textWidth - 12 : elbowX + textWidth + 12;
          const tagY = centroidPt.y - 20;

          // Pointer Line: from centroid to elbow, then horizontal underline
          ctx.beginPath();
          ctx.moveTo(centroidPt.x, centroidPt.y);
          ctx.lineTo(elbowX, tagY + 2);
          ctx.lineTo(endX, tagY + 2);
          ctx.strokeStyle = `rgba(255, 220, 100, ${0.92 * activeLift})`;
          ctx.lineWidth = 1.8;
          ctx.stroke();

          // High-contrast, crystal-clear glowing text sitting strictly on top of the underline
          const textX = goLeft ? endX + 4 : elbowX + 4;
          ctx.shadowColor = '#000000';
          ctx.shadowBlur = 8;
          ctx.fillStyle = '#ffffff';
          ctx.fillText(labelText, textX, tagY);
          ctx.shadowColor = '#f59e0b';
          ctx.shadowBlur = 6;
          ctx.fillStyle = '#fef08a';
          ctx.fillText(labelText, textX, tagY);
          ctx.shadowBlur = 0;
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
      window.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('mouseleave', handleMouseLeave);
      window.removeEventListener('touchstart', handleTouchStart);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', handleTouchEnd);
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
                <IranMonitorLogo size={42} />
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

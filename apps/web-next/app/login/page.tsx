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

// Definition of 16 orbiting artificial intelligence satellites
interface OrbitSatellite {
  radiusFactor: number;
  inclination: number; // radians
  tiltY: number;
  speed: number;
  phase: number;
  size: number;
  color: string;
  glowColor: string;
  hasPing: boolean;
}

const SATELLITE_CONFIGS: OrbitSatellite[] = [
  { radiusFactor: 1.14, inclination: 0.28, tiltY: 0.1, speed: 0.85, phase: 0.2, size: 3.2, color: '#f2c75a', glowColor: '#e3b341', hasPing: true },
  { radiusFactor: 1.22, inclination: -0.42, tiltY: -0.15, speed: -0.72, phase: 1.1, size: 2.8, color: '#e0f2fe', glowColor: '#38bdf8', hasPing: false },
  { radiusFactor: 1.30, inclination: 0.65, tiltY: 0.25, speed: 0.55, phase: 2.3, size: 3.0, color: '#fef08a', glowColor: '#ca8a04', hasPing: true },
  { radiusFactor: 1.18, inclination: -0.78, tiltY: 0.05, speed: -0.92, phase: 3.5, size: 2.5, color: '#ffffff', glowColor: '#93c5fd', hasPing: false },
  { radiusFactor: 1.38, inclination: 0.15, tiltY: -0.3, speed: 0.48, phase: 4.1, size: 3.5, color: '#f2c75a', glowColor: '#d97706', hasPing: true },
  { radiusFactor: 1.26, inclination: -0.32, tiltY: 0.2, speed: 0.68, phase: 5.0, size: 2.6, color: '#bfdbfe', glowColor: '#60a5fa', hasPing: false },
  { radiusFactor: 1.45, inclination: 0.82, tiltY: -0.1, speed: -0.42, phase: 0.7, size: 3.2, color: '#fde047', glowColor: '#eab308', hasPing: true },
  { radiusFactor: 1.12, inclination: -0.18, tiltY: 0.12, speed: 1.05, phase: 1.9, size: 2.4, color: '#ffffff', glowColor: '#cbd5e1', hasPing: false },
  { radiusFactor: 1.34, inclination: 0.48, tiltY: -0.22, speed: -0.62, phase: 2.8, size: 3.1, color: '#fef9c3', glowColor: '#ca8a04', hasPing: false },
  { radiusFactor: 1.50, inclination: -0.60, tiltY: 0.18, speed: 0.38, phase: 3.9, size: 3.6, color: '#f2c75a', glowColor: '#f59e0b', hasPing: true },
  { radiusFactor: 1.20, inclination: 0.95, tiltY: -0.05, speed: 0.78, phase: 4.6, size: 2.7, color: '#e2e8f0', glowColor: '#94a3b8', hasPing: false },
  { radiusFactor: 1.40, inclination: -0.88, tiltY: 0.28, speed: -0.50, phase: 5.5, size: 3.3, color: '#fde68a', glowColor: '#d97706', hasPing: true },
  { radiusFactor: 1.16, inclination: 0.35, tiltY: -0.18, speed: -0.82, phase: 0.4, size: 2.5, color: '#bae6fd', glowColor: '#38bdf8', hasPing: false },
  { radiusFactor: 1.28, inclination: -0.24, tiltY: 0.14, speed: 0.60, phase: 1.6, size: 2.9, color: '#fef08a', glowColor: '#eab308', hasPing: false },
  { radiusFactor: 1.55, inclination: 0.52, tiltY: -0.25, speed: 0.32, phase: 2.7, size: 3.4, color: '#ffffff', glowColor: '#f2c75a', hasPing: true },
  { radiusFactor: 1.42, inclination: -0.45, tiltY: 0.08, speed: -0.54, phase: 4.8, size: 3.0, color: '#fed7aa', glowColor: '#ea580c', hasPing: false }
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

    // Mouse tracking for tangible hover extrusion
    let mouseX = -9999;
    let mouseY = -9999;
    let smoothHoverLat = 0;
    let smoothHoverLon = 0;
    let hoverIntensity = 0; // 0 to 1 smooth fade

    const handleMouseMove = (e: MouseEvent) => {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      mouseX = e.clientX - rect.left;
      mouseY = e.clientY - rect.top;
    };

    const handleMouseLeave = () => {
      mouseX = -9999;
      mouseY = -9999;
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

    // Forward 3D Projection
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
        visible: zTilted > 0
      };
    };

    // Inverse Raycast: Screen (x, y) -> Sphere Geographic (lat, lon)
    const raycastSphere = (screenX: number, screenY: number, radius: number, rot: number, cx: number, cy: number) => {
      const dx = screenX - cx;
      const dy = screenY - cy;
      const distSq = dx * dx + dy * dy;

      if (distSq > radius * radius) {
        return null; // Outside sphere
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

      return {
        latDeg: (lat * 180) / Math.PI,
        lonDeg: (lon * 180) / Math.PI
      };
    };

    // Deep cosmic background stars
    const backgroundStars: { x: number; y: number; r: number; alpha: number; speed: number }[] = [];
    for (let i = 0; i < 90; i++) {
      backgroundStars.push({
        x: Math.random(),
        y: Math.random(),
        r: Math.random() * 1.6 + 0.4,
        alpha: Math.random() * 0.7 + 0.3,
        speed: Math.random() * 0.002 + 0.001
      });
    }

    const render = () => {
      rotation += 0.0015; // Serene constant planetary rotation

      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      ctx.clearRect(0, 0, width, height);

      // Render twinkling background stars
      const now = Date.now();
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
      const cx = isMobile ? width * 0.5 : width * 0.68;
      const cy = isMobile ? height * 0.72 : height * 0.50;
      const radius = Math.min(width, height) * (isMobile ? 0.45 : 0.48);

      // Check mouse raycast for tangible hover extrusion
      const hit = raycastSphere(mouseX, mouseY, radius, rotation, cx, cy);
      if (hit) {
        hoverIntensity = Math.min(1, hoverIntensity + 0.12);
        smoothHoverLat += (hit.latDeg - smoothHoverLat) * 0.25;
        smoothHoverLon += (hit.lonDeg - smoothHoverLon) * 0.25;
      } else {
        hoverIntensity = Math.max(0, hoverIntensity - 0.05);
      }

      // 1. Outer Atmospheric Volumetric Glows (Vibrant Golden Cream & Deep Royal Sapphire)
      const outerGlow = ctx.createRadialGradient(cx, cy, radius * 0.88, cx, cy, radius * 1.65);
      outerGlow.addColorStop(0, 'rgba(242, 199, 90, 0.26)'); // Vibrant warm gold
      outerGlow.addColorStop(0.28, 'rgba(56, 114, 210, 0.18)'); // Royal sapphire haze
      outerGlow.addColorStop(0.65, 'rgba(15, 30, 65, 0.08)');
      outerGlow.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = outerGlow;
      ctx.beginPath();
      ctx.arc(cx, cy, radius * 1.65, 0, Math.PI * 2);
      ctx.fill();

      // 2. Planet Globe Base with Terminator Shading
      const planetGrad = ctx.createRadialGradient(
        cx - radius * 0.32,
        cy - radius * 0.38,
        radius * 0.12,
        cx,
        cy,
        radius
      );
      planetGrad.addColorStop(0, '#1c345a');
      planetGrad.addColorStop(0.35, '#12233c');
      planetGrad.addColorStop(0.75, '#091322');
      planetGrad.addColorStop(1, '#040812');
      ctx.fillStyle = planetGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fill();

      // Sharp golden atmospheric rim highlight
      ctx.strokeStyle = 'rgba(242, 199, 90, 0.55)';
      ctx.lineWidth = 1.8;
      ctx.stroke();

      // 3. Coordinate Graticule Grid (Delicate golden/blue mesh)
      ctx.lineWidth = 0.65;
      for (let lat = -70; lat <= 70; lat += 20) {
        ctx.beginPath();
        let first = true;
        for (let lon = 0; lon <= 360; lon += 5) {
          const pt = project3D(lat, lon, radius, rotation, cx, cy);
          if (pt.visible) {
            const alpha = 0.06 + Math.max(0, pt.z / radius) * 0.16;
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

      for (let lon = 0; lon < 360; lon += 24) {
        ctx.beginPath();
        let first = true;
        for (let lat = -80; lat <= 80; lat += 5) {
          const pt = project3D(lat, lon, radius, rotation, cx, cy);
          if (pt.visible) {
            const alpha = 0.05 + Math.max(0, pt.z / radius) * 0.14;
            ctx.strokeStyle = `rgba(186, 215, 250, ${alpha})`;
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

      // 4. Tangible Visual Effect: Extruding & Glowing 3D Square Region Tiles
      // We generate sectors across latitude and longitude
      const dLat = 8;
      const dLon = 10;
      if (hoverIntensity > 0.02) {
        const hoverCenterLat = Math.round(smoothHoverLat / dLat) * dLat;
        const hoverCenterLon = Math.round(smoothHoverLon / dLon) * dLon;

        // Render a 5x5 localized tile cluster around the cursor
        for (let rLat = -2; rLat <= 2; rLat++) {
          for (let rLon = -2; rLon <= 2; rLon++) {
            const tileLat = hoverCenterLat + rLat * dLat;
            const tileLon = hoverCenterLon + rLon * dLon;

            if (tileLat < -80 || tileLat > 80) continue;

            const distFromHover = Math.sqrt(rLat * rLat + rLon * rLon);
            if (distFromHover > 2.6) continue;

            // Extrusion height based on distance to cursor & hover intensity
            const factor = Math.max(0, 1 - distFromHover / 2.6);
            const extrusionH = (18 * factor + 4) * hoverIntensity; // Up to 22px outward extrusion!

            // 4 Corner coordinates of this spherical tile
            const lat1 = tileLat - dLat * 0.44;
            const lat2 = tileLat + dLat * 0.44;
            const lon1 = tileLon - dLon * 0.44;
            const lon2 = tileLon + dLon * 0.44;

            // Base vertices (on globe surface)
            const b1 = project3D(lat1, lon1, radius, rotation, cx, cy);
            const b2 = project3D(lat2, lon1, radius, rotation, cx, cy);
            const b3 = project3D(lat2, lon2, radius, rotation, cx, cy);
            const b4 = project3D(lat1, lon2, radius, rotation, cx, cy);

            // Extruded top vertices (pushed outwards along sphere normal)
            const t1 = project3D(lat1, lon1, radius + extrusionH, rotation, cx, cy);
            const t2 = project3D(lat2, lon1, radius + extrusionH, rotation, cx, cy);
            const t3 = project3D(lat2, lon2, radius + extrusionH, rotation, cx, cy);
            const t4 = project3D(lat1, lon2, radius + extrusionH, rotation, cx, cy);

            if (b1.visible && b2.visible && b3.visible && b4.visible) {
              // Draw 3D Extrusion Side Walls
              ctx.fillStyle = `rgba(180, 130, 30, ${0.45 * hoverIntensity * factor})`;
              ctx.strokeStyle = `rgba(242, 199, 90, ${0.6 * hoverIntensity * factor})`;
              ctx.lineWidth = 1;

              // Wall 1 (bottom edge)
              ctx.beginPath();
              ctx.moveTo(b1.x, b1.y);
              ctx.lineTo(b4.x, b4.y);
              ctx.lineTo(t4.x, t4.y);
              ctx.lineTo(t1.x, t1.y);
              ctx.closePath();
              ctx.fill();
              ctx.stroke();

              // Wall 2 (right edge)
              ctx.beginPath();
              ctx.moveTo(b4.x, b4.y);
              ctx.lineTo(b3.x, b3.y);
              ctx.lineTo(t3.x, t3.y);
              ctx.lineTo(t4.x, t4.y);
              ctx.closePath();
              ctx.fill();
              ctx.stroke();

              // Draw Extruded Top Cap (Luminous Golden Amber Face)
              ctx.beginPath();
              ctx.moveTo(t1.x, t1.y);
              ctx.lineTo(t2.x, t2.y);
              ctx.lineTo(t3.x, t3.y);
              ctx.lineTo(t4.x, t4.y);
              ctx.closePath();

              const topAlpha = (0.35 + 0.55 * factor) * hoverIntensity;
              ctx.fillStyle = `rgba(245, 210, 110, ${topAlpha})`;
              ctx.shadowColor = '#f2c75a';
              ctx.shadowBlur = 12 * factor * hoverIntensity;
              ctx.fill();
              ctx.shadowBlur = 0;

              ctx.strokeStyle = `rgba(255, 245, 200, ${(0.6 + 0.4 * factor) * hoverIntensity})`;
              ctx.lineWidth = 1.6;
              ctx.stroke();
            }
          }
        }
      }

      // 5. Continental Landmass Silhouettes (Golden / Crisp Ivory Nodes)
      for (const [lat, lon] of CONTINENTAL_POINTS) {
        const pt = project3D(lat, lon, radius, rotation, cx, cy);
        if (pt.visible) {
          const depthAlpha = Math.max(0.12, pt.z / radius);
          const isIran = lat > 25 && lat < 40 && lon > 44 && lon < 63;

          ctx.fillStyle = isIran
            ? `rgba(242, 199, 90, ${0.9 * depthAlpha})`
            : `rgba(215, 230, 250, ${0.45 * depthAlpha})`;

          ctx.beginPath();
          ctx.arc(pt.x, pt.y, isIran ? 2.6 : 1.7, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // 6. Tactical Beacon over Tehran / Iran (Pulsing Amber Radar Core)
      const tehran = project3D(35.6892, 51.3890, radius, rotation, cx, cy);
      if (tehran.visible) {
        const alpha = Math.max(0.2, (tehran.z / radius) * 0.85);
        const pulse = (Math.sin(now * 0.005) + 1) * 0.5;

        // Expanding radio pulse ring
        ctx.beginPath();
        ctx.arc(tehran.x, tehran.y, 6 + pulse * 14, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(242, 199, 90, ${alpha * (1 - pulse) * 0.8})`;
        ctx.lineWidth = 1.4;
        ctx.stroke();

        // Bright beacon dot
        ctx.beginPath();
        ctx.arc(tehran.x, tehran.y, 4, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(242, 199, 90, ${alpha})`;
        ctx.shadowColor = '#e3b341';
        ctx.shadowBlur = 12;
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      // 7. Array of 16 Orbiting Artificial Satellites with Orbits and Trails
      for (let i = 0; i < SATELLITE_CONFIGS.length; i++) {
        const sat = SATELLITE_CONFIGS[i];
        const orbitRadius = radius * sat.radiusFactor;
        const currentAngle = (now * 0.00035 * sat.speed + sat.phase) % (Math.PI * 2);

        // Calculate 3D position on tilted orbital plane
        const satX0 = orbitRadius * Math.cos(currentAngle);
        const satY0 = 0;
        const satZ0 = orbitRadius * Math.sin(currentAngle);

        // Rotate by inclination (around Z) and tilt (around X)
        const cosInc = Math.cos(sat.inclination);
        const sinInc = Math.sin(sat.inclination);

        const xInc = satX0 * cosInc - satY0 * sinInc;
        const yInc = satX0 * sinInc + satY0 * cosInc;
        const zInc = satZ0;

        // Apply Earth tilt & perspective
        const xFinal = xInc;
        const yFinal = yInc * cosT - zInc * sinT;
        const zFinal = yInc * sinT + zInc * cosT;

        const screenX = cx + xFinal;
        const screenY = cy + yFinal;

        // Is satellite in front or behind the planet?
        const isBehind = zFinal < 0 && (xFinal * xFinal + yFinal * yFinal < radius * radius);
        if (isBehind) continue; // Occluded by the planet body

        // Draw faint orbital guide path (subtle arc)
        if (i % 2 === 0) {
          ctx.beginPath();
          ctx.ellipse(cx, cy, orbitRadius, orbitRadius * 0.38, sat.inclination, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(227, 179, 65, 0.05)`;
          ctx.setLineDash([2, 9]);
          ctx.lineWidth = 0.8;
          ctx.stroke();
          ctx.setLineDash([]);
        }

        // Phosphor comet tail behind satellite
        for (let t = 1; t <= 4; t++) {
          const tailAngle = currentAngle - (sat.speed > 0 ? 0.035 : -0.035) * t;
          const tX0 = orbitRadius * Math.cos(tailAngle);
          const tZ0 = orbitRadius * Math.sin(tailAngle);
          const tXInc = tX0 * cosInc;
          const tYInc = tX0 * sinInc;
          const tailScreenX = cx + tXInc;
          const tailScreenY = cy + (tYInc * cosT - tZ0 * sinT);

          ctx.beginPath();
          ctx.arc(tailScreenX, tailScreenY, sat.size * (1 - t * 0.2), 0, Math.PI * 2);
          ctx.fillStyle = `${sat.glowColor}${Math.floor((0.35 / t) * 255).toString(16).padStart(2, '0')}`;
          ctx.fill();
        }

        // Satellite body
        ctx.beginPath();
        ctx.arc(screenX, screenY, sat.size, 0, Math.PI * 2);
        ctx.fillStyle = sat.color;
        ctx.shadowColor = sat.glowColor;
        ctx.shadowBlur = 10;
        ctx.fill();
        ctx.shadowBlur = 0;

        // Periodic telemetry beacon ping pulse
        if (sat.hasPing) {
          const pingPhase = ((now * 0.002 * Math.abs(sat.speed) + sat.phase * 3) % Math.PI);
          ctx.beginPath();
          ctx.arc(screenX, screenY, sat.size + pingPhase * 10, 0, Math.PI * 2);
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
      {/* Dynamic 3D Earth Canvas with Extruding Square Tiles & Satellites */}
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
        <div className="login-earth-hero" aria-hidden="true">
          {/* Transparent interactive region letting the user interact with Earth */}
        </div>
      </div>
    </div>
  );
}

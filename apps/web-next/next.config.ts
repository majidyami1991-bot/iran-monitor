import type { NextConfig } from 'next';
import imageHosts from './media-image-hosts.json';

// API calls go through app/api/v1/[...path]/route.ts, which resolves
// API_ORIGIN at request time (rewrites would freeze it at build time).
//
// Content Security Policy: everything is same-origin except (a) article
// images, allowed only from the publisher/CDN hosts listed in
// media-image-hosts.json (no https: wildcard), and (b) the official X embed,
// which the reader loads by clicking and which runs only from
// platform.twitter.com in its own iframe. 'unsafe-inline' is required by
// Next.js hydration scripts and inline style props; no user or X HTML is
// ever injected into the page.
const IMG_HOSTS = (imageHosts.hosts as string[]).filter((h) => /^[a-z0-9.-]+$/.test(h)).map((h) => `https://${h}`);
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' https://platform.twitter.com",
  "style-src 'self' 'unsafe-inline'",
  `img-src 'self' data: ${IMG_HOSTS.join(' ')}`,
  "font-src 'self'",
  "connect-src 'self'",
  'frame-src https://platform.twitter.com https://syndication.twitter.com',
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join('; ');

const config: NextConfig = {
  output: 'standalone',
  poweredByHeader: false,
  async headers() {
    return [{
      source: '/:path*',
      headers: [
        { key: 'Content-Security-Policy', value: CSP },
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
      ],
    }];
  },
};
export default config;

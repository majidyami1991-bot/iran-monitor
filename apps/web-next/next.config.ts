import type { NextConfig } from 'next';

// API calls go through app/api/v1/[...path]/route.ts, which resolves
// API_ORIGIN at request time (rewrites would freeze it at build time).
const config: NextConfig = { output: 'standalone', poweredByHeader: false };
export default config;

import type { NextConfig } from 'next';
const config:NextConfig={output:'standalone',poweredByHeader:false,
  async rewrites() {
    const origin=process.env.API_ORIGIN || 'http://news-api:3000';
    return ['/news/:path*','/sources/:path*','/analytics','/about','/assets/:path*','/api/v1/:path*']
      .map(source=>({source,destination:`${origin}${source}`}));
  }
};
export default config;

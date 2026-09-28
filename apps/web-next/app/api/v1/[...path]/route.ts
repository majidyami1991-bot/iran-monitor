// Runtime proxy to the news API. Next.js `rewrites()` are frozen into the
// build, which silently pointed a preview image at the production API; this
// handler reads API_ORIGIN per request, so one image serves preview and
// production. Only /api/v1/* is forwarded, only to the configured origin.
import type { NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

const ORIGIN = () => (process.env.API_ORIGIN || 'http://news-api:3000').replace(/\/$/, '');

async function forward(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const target = `${ORIGIN()}/api/v1/${path.map(encodeURIComponent).join('/')}${req.nextUrl.search}`;
  const init: RequestInit = { method: req.method, headers: { accept: 'application/json' }, cache: 'no-store' };
  if (!['GET', 'HEAD'].includes(req.method)) init.body = await req.text();
  try {
    const r = await fetch(target, init);
    return new Response(r.body, {
      status: r.status,
      headers: { 'content-type': r.headers.get('content-type') ?? 'application/json', 'cache-control': 'no-store' },
    });
  } catch {
    return Response.json({ detail: 'api_unreachable' }, { status: 502 });
  }
}

export { forward as GET, forward as POST, forward as PATCH, forward as DELETE };

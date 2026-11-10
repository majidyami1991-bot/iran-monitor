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
  const headers: Record<string, string> = { accept: 'application/json' };
  if (!['GET', 'HEAD'].includes(req.method)) {
    // Writes: JSON only (a cross-site HTML form cannot send it without a
    // CORS preflight, which this app never grants), the CSRF token header,
    // and the browser's own Origin — set here, so a client-supplied
    // x-im-origin is always overwritten.
    if (!(req.headers.get('content-type') || '').toLowerCase().startsWith('application/json')) {
      return Response.json({ detail: 'json_required' }, { status: 415 });
    }
    headers['content-type'] = 'application/json';
    headers['x-im-csrf'] = req.headers.get('x-im-csrf') || '';
    // Operator token for the local-translation admin writes; the API refuses
    // every admin write when it is missing or wrong. Never sent on reads.
    const admin = req.headers.get('x-im-admin');
    if (admin) headers['x-im-admin'] = admin;
    headers['x-im-origin'] = req.headers.get('origin') || 'absent';
  }
  const init: RequestInit = { method: req.method, headers, cache: 'no-store' };
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

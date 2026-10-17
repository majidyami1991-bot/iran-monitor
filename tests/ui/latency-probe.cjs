/**
 * Browser latency probe for 3003: per page, cold load timings, every request (duration, size, status),
 * duplicate requests (same URL fetched more than once in one page view), slow API calls, JS bytes,
 * console errors, requests to :11434, and an idle window to catch polling.
 *   LABEL=before node tests/ui/latency-probe.cjs
 */
const fs = require('fs'), path = require('path');
const { launchEdge } = require('./edge-launcher.cjs');
const BASE = process.env.BASE_URL || 'http://127.0.0.1:3003';
const LABEL = process.env.LABEL || 'run';
const IDLE_MS = +(process.env.IDLE_MS || 20000);
const PAGES = ['/', '/news', '/sources', '/assistant', '/admin'];

(async () => {
  const { browser, close } = await launchEdge();
  const out = { label: LABEL, at: new Date().toISOString(), pages: [] };
  try {
    for (const p of PAGES) {
      const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'fa-IR' });
      const page = await ctx.newPage();
      const reqs = new Map(); const errors = []; const ollama = [];
      page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)); });
      page.on('request', (r) => { reqs.set(r, { url: r.url(), type: r.resourceType(), t0: Date.now() }); if (/:11434|ollama/i.test(r.url())) ollama.push(r.url()); });
      page.on('requestfinished', async (r) => { const e = reqs.get(r); if (!e) return; e.ms = Date.now() - e.t0; try { const s = await r.sizes(); e.bytes = s.responseBodySize; } catch {} try { e.status = (await r.response())?.status(); } catch {} });
      page.on('requestfailed', (r) => { const e = reqs.get(r); if (e) { e.failed = (r.failure() || {}).errorText; e.ms = Date.now() - e.t0; } });
      const t0 = Date.now();
      await page.goto(BASE + p, { waitUntil: 'domcontentloaded' });
      const dcl = Date.now() - t0;
      await page.waitForLoadState('load'); const load = Date.now() - t0;
      await page.waitForLoadState('networkidle', { timeout: 60000 }).catch(() => {}); const idle = Date.now() - t0;
      const settled = reqs.size;
      await page.waitForTimeout(IDLE_MS);
      const all = [...reqs.values()];
      const api = all.filter((e) => e.url.includes('/api/'));
      const byUrl = {}; for (const e of all.slice(0, settled)) if (!e.url.includes('_rsc=')) byUrl[e.url] = (byUrl[e.url] || 0) + 1;
      const dups = Object.entries(byUrl).filter(([, n]) => n > 1).map(([u, n]) => ({ url: u.replace(BASE, ''), n }));
      const js = all.filter((e) => e.type === 'script').reduce((a, e) => a + (e.bytes || 0), 0);
      const row = { page: p, dcl_ms: dcl, load_ms: load, networkidle_ms: idle, requests: settled, requests_during_idle: reqs.size - settled, idle_urls: all.slice(settled).map((e) => e.url.replace(BASE, '').slice(0, 120)),
        api_calls: api.length, slow_api: api.filter((e) => (e.ms || 0) > 500).map((e) => ({ url: e.url.replace(BASE, ''), ms: e.ms })),
        failed: all.filter((e) => e.failed && !e.url.includes('_rsc=')).map((e) => e.url.replace(BASE, '') + ' ' + e.failed),
        http_errors: all.filter((e) => e.status >= 400).map((e) => e.status + ' ' + e.url.replace(BASE, '')),
        duplicates: dups, js_kb: Math.round(js / 1024), console_errors: errors, ollama_requests: ollama,
        api_list: api.map((e) => ({ url: e.url.replace(BASE, ''), ms: e.ms, kb: Math.round((e.bytes || 0) / 1024) })) };
      out.pages.push(row);
      console.log(`${p.padEnd(11)} dcl=${dcl} load=${load} idle=${idle} req=${settled} api=${api.length} dup=${dups.reduce((a, d) => a + d.n - 1, 0)} idle_req=${row.requests_during_idle} js=${row.js_kb}KB slow=${row.slow_api.length} err=${errors.length} fail=${row.failed.length} ollama=${ollama.length}`);
      await ctx.close();
    }
  } finally { await close(); }
  fs.mkdirSync(path.resolve('runtime/latency'), { recursive: true });
  fs.writeFileSync(path.resolve(`runtime/latency/browser-${LABEL}.json`), JSON.stringify(out, null, 1));
})();

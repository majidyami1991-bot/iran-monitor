/**
 * Responsiveness probe of 3003 under real load: API timings (5 runs each, median/max)
 * and browser page timings (navigation timing: TTFB, DOMContentLoaded, load).
 *   LABEL=before node tests/ui/perf-probe.cjs
 */
const fs = require('fs'), path = require('path');
const { launchEdge } = require('./edge-launcher.cjs');
const BASE = process.env.BASE_URL || 'http://127.0.0.1:3003';
const LABEL = process.env.LABEL || 'probe';
const ITEM = process.env.ITEM || 'a93b6ee1caf4d942b31afb98be76aadcacc329f0c9ee22f82f1f22801e6f74ed';
const API = ['feed?page_size=30', `news/${ITEM}`, `feed/${ITEM}/context`, 'events?page_size=20', 'local-ai/ops', 'assistant/status', 'stats/overview'];
const PAGES = ['/', '/news', `/news/${ITEM}`, '/assistant', '/admin'];
const med = (a) => [...a].sort((x, y) => x - y)[Math.floor(a.length / 2)];

(async () => {
  const out = { label: LABEL, at: new Date().toISOString(), api: {}, pages: {} };
  for (const p of API) {
    const t = [];
    for (let i = 0; i < 5; i++) { const s = performance.now(); const r = await fetch(`${BASE}/api/v1/${p}`); await r.arrayBuffer(); t.push(performance.now() - s); }
    out.api[p] = { median_ms: Math.round(med(t)), max_ms: Math.round(Math.max(...t)) };
  }
  const { browser, close } = await launchEdge();
  try {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'fa-IR' });
    const page = await ctx.newPage();
    for (const p of PAGES) {
      const runs = [];
      for (let i = 0; i < 3; i++) {
        await page.goto(BASE + p, { waitUntil: 'load', timeout: 60000 });
        const nav = await page.evaluate(() => { const n = performance.getEntriesByType('navigation')[0]; return { ttfb: n.responseStart, dcl: n.domContentLoadedEventEnd, load: n.loadEventEnd }; });
        await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
        const idle = await page.evaluate(() => performance.now());
        runs.push({ ...nav, networkidle: idle });
      }
      out.pages[p] = Object.fromEntries(['ttfb', 'dcl', 'load', 'networkidle'].map((k) => [k + '_ms', Math.round(med(runs.map((r) => r[k])))]));
    }
  } finally { await close(); }
  fs.mkdirSync(path.resolve('runtime/final-acceptance'), { recursive: true });
  fs.writeFileSync(path.resolve(`runtime/final-acceptance/perf-${LABEL}.json`), JSON.stringify(out, null, 1));
  console.log(JSON.stringify(out, null, 1));
})();

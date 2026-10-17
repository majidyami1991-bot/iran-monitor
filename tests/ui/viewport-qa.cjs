/**
 * 3003 in four viewports: every page must load with zero console errors, zero unexpected requests
 * (failed, HTTP >= 400, anything to :11434 or off-origin) and zero horizontal overflow.
 *   node tests/ui/viewport-qa.cjs
 */
const fs = require('fs'), path = require('path');
const { launchEdge } = require('./edge-launcher.cjs');
const BASE = process.env.BASE_URL || 'http://127.0.0.1:3003';
const VIEWPORTS = [{ name: 'phone', width: 360, height: 740 }, { name: 'tablet', width: 768, height: 1024 },
                   { name: 'laptop', width: 1280, height: 800 }, { name: 'desktop', width: 1920, height: 1080 }];
const results = [];
const check = (name, pass, detail) => { results.push({ name, pass: !!pass, detail: detail ?? null }); if (!pass) console.log('FAIL ' + name + ' — ' + JSON.stringify(detail).slice(0, 300)); };

(async () => {
  const { browser, close } = await launchEdge();
  try {
    const feed = await (await fetch(BASE + '/api/v1/feed?page_size=1')).json();
    const PAGES = ['/', '/news', '/news/' + feed.items[0].item_id, '/sources', '/assistant', '/admin'];
    for (const vp of VIEWPORTS) {
      const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, locale: 'fa-IR', isMobile: vp.width < 500, hasTouch: vp.width < 900 });
      const page = await ctx.newPage();
      for (const p of PAGES) {
        const errors = [], unexpected = [];
        const onConsole = (m) => { if (m.type() === 'error') errors.push(m.text().slice(0, 160)); };
        const onFailed = (r) => { const e = (r.failure() || {}).errorText || ''; if (!(/_rsc=/.test(r.url()) && /ERR_ABORTED/.test(e))) unexpected.push('failed ' + e + ' ' + r.url()); };
        const onResp = (r) => { if (r.status() >= 400) unexpected.push(r.status() + ' ' + r.url()); };
        const onReq = (r) => { const u = r.url(); if (/:11434/.test(u) || !(u.startsWith(BASE) || u.startsWith('data:') || u.startsWith('blob:') || /^https?:\/\/[^/]+\/.*\.(jpe?g|png|webp|gif|avif)(\?|$)/i.test(u))) unexpected.push('request ' + u); };
        page.on('console', onConsole); page.on('requestfailed', onFailed); page.on('response', onResp); page.on('request', onReq);
        const r = await page.goto(BASE + p, { waitUntil: 'load' });
        await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
        await page.waitForTimeout(500);
        const ov = await page.evaluate(() => { const d = document.scrollingElement || document.documentElement; return { sw: d.scrollWidth, cw: d.clientWidth }; });
        const tag = `${vp.name} ${p.startsWith('/news/') ? '/news/:id' : p}`;
        check(`${tag} HTTP 200`, r && r.status() === 200, r && r.status());
        check(`${tag} no console errors`, errors.length === 0, errors);
        check(`${tag} no unexpected requests`, unexpected.length === 0, unexpected.slice(0, 5));
        check(`${tag} no horizontal overflow`, ov.sw <= ov.cw + 1, ov);
        page.off('console', onConsole); page.off('requestfailed', onFailed); page.off('response', onResp); page.off('request', onReq);
      }
      await ctx.close();
    }
  } finally { await close(); }
  const failed = results.filter((r) => !r.pass);
  console.log(`${results.length - failed.length}/${results.length} PASS`);
  fs.mkdirSync(path.resolve('runtime/latency'), { recursive: true });
  fs.writeFileSync(path.resolve('runtime/latency/viewport-qa.json'), JSON.stringify({ at: new Date().toISOString(), results }, null, 1));
  process.exit(failed.length ? 1 : 0);
})();

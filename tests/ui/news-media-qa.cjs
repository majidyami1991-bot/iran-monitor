/**
 * News media v2 browser + API QA against the preview (127.0.0.1:3002).
 * Article images are loaded from publishers exactly as a reader's browser
 * would; every other non-local request is aborted and counted.
 *
 *   node tests/ui/news-media-qa.cjs
 */
const fs = require('fs'), path = require('path');
const { launchEdge } = require('./edge-launcher.cjs');

const BASE = process.env.BASE_URL || 'http://127.0.0.1:3002';
const OUT = path.resolve(process.env.EVIDENCE_DIR || 'runtime/evidence/news-media/after');
const VIEWPORTS = [['1920x1080', 1920, 1080], ['1440x900', 1440, 900], ['1024x768', 1024, 768], ['390x844', 390, 844]];
const results = [], consoleErrors = [], failedLocal = [], overflow = [], shots = [], extFailed = [];
const check = (name, pass, detail) => { results.push({ name, pass: !!pass, detail: detail ?? null }); console.log((pass ? 'PASS ' : 'FAIL ') + name + (pass ? '' : ' — ' + JSON.stringify(detail ?? '').slice(0, 220))); };
const api = async (r) => { const x = await fetch(BASE + '/api/v1/' + r); return { status: x.status, body: await x.json().catch(() => null) }; };
const local = (u) => ['127.0.0.1', 'localhost'].includes(new URL(u).hostname);
const settle = async (p) => { await p.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {}); await p.waitForTimeout(1200); };

(async () => {
  fs.mkdirSync(OUT, { recursive: true });

  // ---------------- API contract
  const feed = (await api('feed?page_size=60')).body;
  const withImg = feed.items.find((i) => i.primary_media && i.primary_media.source_method === 'rss_enclosure')
    || feed.items.find((i) => i.primary_media);
  const noImg = feed.items.find((i) => !i.primary_media);
  check('feed items carry primary_media, media_count, media_status', feed.items.every((i) => 'primary_media' in i && 'media_count' in i && 'media_status' in i));
  check('legacy image_url kept (backward compatible)', feed.items.every((i) => 'image_url' in i && (i.primary_media ? i.image_url === i.primary_media.url : i.image_url === null)));
  check('primary_media shape', withImg && ['id', 'type', 'url', 'thumbnail_url', 'width', 'height', 'alt_text', 'caption', 'credit', 'source_method', 'validation_status'].every((k) => k in withImg.primary_media), withImg?.primary_media);
  check('media_status values are from the contract', feed.items.every((i) => ['available', 'missing', 'rejected', 'blocked', 'unreachable', 'pending'].includes(i.media_status)));
  check('no primary is rejected/blocked/unreachable', feed.items.every((i) => !i.primary_media || !['rejected', 'blocked', 'unreachable'].includes(i.primary_media.validation_status)));
  const st = await api('media/status'); const stats = await api('media/stats');
  check('GET /media/status', st.status === 200 && st.body.policy_version === 'media_policy_v1' && st.body.article_fallback_enabled === false, st.body);
  check('GET /media/stats has coverage, by source, by method, rejection classes', stats.status === 200 && stats.body.totals.coverage_pct != null && stats.body.by_source.length === 12 && stats.body.by_method.length > 0 && 'ad' in stats.body.rejections_by_class, stats.body.totals);
  const im = await api(`news/${withImg.item_id}/media`);
  check('GET /news/{id}/media returns primary with provenance', im.status === 200 && im.body.primary_media && im.body.primary_media.source_method && im.body.primary_media.source_hostname, im.body.primary_media);
  check('GET /news/{id}/media hides rejected by default', im.body.media.every((m) => !['rejected', 'blocked', 'unreachable'].includes(m.validation_status)));
  check('GET /news/{unknown}/media -> 404', (await api('news/does-not-exist/media')).status === 404);
  const rejected = (await api(`news/${withImg.item_id}/media?include_rejected=true`)).body.media.filter((m) => m.validation_status === 'rejected').map((m) => m.url);

  const { browser, close } = await launchEdge();
  try {
    const routes = ['/', '/news', `/news/${withImg.item_id}`, `/news/${noImg.item_id}`];
    for (const [label, width, height] of VIEWPORTS) {
      const ctx = await browser.newContext({ viewport: { width, height }, locale: 'fa-IR', isMobile: width < 500 });
      await ctx.route('**/*', (r) => (local(r.request().url()) || r.request().resourceType() === 'image') ? r.continue() : r.abort());
      const page = await ctx.newPage(); let cur = '';
      page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push({ label, route: cur, text: m.text().slice(0, 160) }); });
      page.on('pageerror', (e) => consoleErrors.push({ label, route: cur, text: 'pageerror ' + e.message }));
      page.on('response', (r) => { if (local(r.url()) && r.status() >= 400 && !r.url().includes('/health/collection')) failedLocal.push({ label, route: cur, url: new URL(r.url()).pathname, status: r.status() }); });
      page.on('requestfailed', (r) => { if (!local(r.url())) extFailed.push({ label, url: r.url().slice(0, 100), err: r.failure()?.errorText }); else if (!(r.failure()?.errorText || '').includes('ERR_ABORTED')) failedLocal.push({ label, route: cur, url: new URL(r.url()).pathname, status: 'failed' }); });
      await page.addInitScript(() => { window.__cls = 0; new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; }).observe({ type: 'layout-shift', buffered: true }); });
      for (const route of routes) {
        cur = route;
        await page.goto(BASE + route, { waitUntil: 'domcontentloaded' }); await settle(page);
        const ov = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        if (ov > 1) overflow.push({ label, route, ov });
        const m = await page.evaluate((rej) => ({
          cls: window.__cls,
          loaded: [...document.querySelectorAll('main img')].filter((i) => i.complete && i.naturalWidth > 0).length,
          placeholders: document.querySelectorAll('main [data-placeholder]').length,
          rejectedShown: [...document.querySelectorAll('main img')].filter((i) => rej.includes(i.getAttribute('src'))).length,
          unsized: [...document.querySelectorAll('main .card-media, main .card-row-media, main .detail-hero')].filter((f) => f.getBoundingClientRect().height < 20).length,
        }), rejected);
        if (label === '1440x900' || label === '390x844') {
          const file = `${label}_${route === '/' ? 'home' : route.slice(1).replace(/\//g, '_').slice(0, 50)}.png`;
          await page.screenshot({ path: path.join(OUT, file), fullPage: route === '/' || route === '/news' }); shots.push(file);
        }
        if (label === '1440x900') {
          check(`CLS small on ${route}`, m.cls < 0.1, m.cls);
          check(`no rejected image rendered on ${route}`, m.rejectedShown === 0, m.rejectedShown);
          check(`image frames sized before load on ${route}`, m.unsized === 0, m.unsized);
          if (route === '/') check('landing shows real images', m.loaded >= 3, m);
          if (route === '/news') check('news stream shows real images', m.loaded >= 5, m);
          if (route.includes(withImg.item_id)) {
            check('detail shows the primary image', m.loaded >= 1, m);
            const cap = await page.locator('.media-caption').innerText();
            check('detail shows image provenance (host + method + validation)', cap.includes('منبع تصویر') && /RSS|فراداده/.test(cap), cap);
          }
          if (route.includes(noImg.item_id)) {
            check('item without valid media shows the neutral placeholder', m.placeholders >= 1, m);
            check('placeholder says the source image is unavailable', (await page.locator('main [data-placeholder]').first().getAttribute('aria-label') || '').includes('تصویر منبع'), null);
          }
        }
      }
      await ctx.close();
    }

    // Image load failure -> placeholder, layout intact
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'fa-IR' });
    await ctx.route('**/*', (r) => local(r.request().url()) ? r.continue() : r.abort());
    const p = await ctx.newPage();
    await p.goto(BASE + '/news/' + withImg.item_id, { waitUntil: 'domcontentloaded' }); await settle(p);
    const heroPh = await p.locator('.detail-hero [data-placeholder]').count();
    check('image load failure falls back to placeholder', heroPh === 1, heroPh);
    check('failure placeholder says it did not load', ((await p.locator('.detail-hero [data-placeholder]').getAttribute('aria-label')) || '').includes('بارگذاری نشد'));
    check('title still readable after image failure', (await p.locator('h1.detail-title').innerText()).length > 5);
    const res = await p.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
    const csp = res.headers()['content-security-policy'] || '';
    const img = (csp.split(';').find((x) => x.trim().startsWith('img-src')) || '').trim();
    check('CSP img-src lists named hosts only (no https: wildcard)', img && !/\shttps:(\s|$)/.test(img + ' ') && img.includes('https://images.jfeed.com'), img.slice(0, 160));
    check('CSP keeps object-src none', csp.includes("object-src 'none'"));
    // keyboard: gallery buttons focusable
    await ctx.close();
  } finally { await close(); }

  const fails = results.filter((r) => !r.pass);
  const report = { checks: results.length, passed: results.length - fails.length, failures: fails, screenshots: shots.length,
    console_errors: consoleErrors, failed_local_requests: failedLocal, horizontal_overflow: overflow, external_image_failures: extFailed };
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
  console.log(`\nNEWS MEDIA QA: ${report.passed}/${report.checks} · SCREENSHOTS ${shots.length} · CONSOLE_ERRORS ${consoleErrors.length} · FAILED_LOCAL ${failedLocal.length} · OVERFLOW ${overflow.length} · EXTERNAL_IMAGE_FAILURES ${extFailed.length}`);
  process.exit(fails.length ? 1 : 0);
})();

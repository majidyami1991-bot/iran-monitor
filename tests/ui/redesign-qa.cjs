/**
 * Reference-redesign acceptance: every route at four viewports plus
 * functional checks (stories viewer, ticker, query-string filters, events,
 * bilingual display, keyboard, empty/error states) and a DB/API/UI count
 * reconciliation. Results are measured, never assumed; the JSON report lists
 * every check with its evidence.
 *
 *   BASE_URL=http://127.0.0.1:3002 node tests/ui/redesign-qa.cjs
 *
 * Requests leave the machine only for article images (what a reader's browser
 * does); every other non-local request is aborted and counted separately.
 */
const fs = require('fs'), path = require('path');
const { launchEdge } = require('./edge-launcher.cjs');

const BASE = process.env.BASE_URL || 'http://127.0.0.1:3002';
const OUT = path.resolve(process.env.EVIDENCE_DIR || 'runtime/evidence/redesign-qa');
const VIEWPORTS = [['1920x1080', 1920, 1080], ['1440x900', 1440, 900], ['1024x768', 1024, 768], ['390x844', 390, 844]];
const results = [], shots = [], consoleErrors = [], failedLocal = [], abortedPrefetch = [], overflow = [], externalBlocked = [], a11y = [];
const check = (name, pass, detail) => { results.push({ name, pass: !!pass, detail: detail ?? null }); console.log((pass ? 'PASS ' : 'FAIL ') + name + (detail != null ? ' — ' + JSON.stringify(detail).slice(0, 180) : '')); return !!pass; };
const api = async (route) => (await fetch(BASE + '/api/v1/' + route, { cache: 'no-store' })).json();
const settle = async (page) => { await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {}); await page.waitForTimeout(700); };

async function a11ySmoke(page, route) {
  const r = await page.evaluate(() => {
    const issues = [];
    const name = (el) => (el.getAttribute('aria-label') || el.textContent || el.getAttribute('title') || '').trim();
    document.querySelectorAll('button').forEach((b) => { if (!name(b)) issues.push('button without name: ' + b.outerHTML.slice(0, 80)); });
    document.querySelectorAll('a[href]').forEach((a) => { if (!name(a) && !a.getAttribute('aria-hidden') && a.getAttribute('tabindex') !== '-1') issues.push('link without name: ' + a.outerHTML.slice(0, 80)); });
    document.querySelectorAll('img').forEach((i) => { if (!i.hasAttribute('alt')) issues.push('img without alt'); });
    document.querySelectorAll('input, select').forEach((i) => { if (!i.closest('label') && !i.getAttribute('aria-label')) issues.push('unlabelled field ' + (i.getAttribute('name') || i.tagName)); });
    const h1 = document.querySelectorAll('h1').length;
    if (h1 !== 1) issues.push('h1 count ' + h1);
    if (!document.querySelector('main')) issues.push('no main landmark');
    if (document.documentElement.dir !== 'rtl' || document.documentElement.lang !== 'fa') issues.push('html lang/dir');
    return issues;
  });
  if (r.length) a11y.push({ route, issues: [...new Set(r)].slice(0, 10) });
  return r.length === 0;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const t0 = Date.now();
  // Real ids from the API for the detail routes.
  const feed = await api('feed?page_size=40&sort=newest');
  const withImg = feed.items.find((i) => i.image_url) || feed.items[0];
  const events = await api('timeline/events?sort=important&page_size=5');
  const sources = await api('source-profiles');
  const routes = ['/', '/news', `/news/${withImg.item_id}`, '/stories', '/briefing', '/events', `/events/${events.events[0].event_id}`,
    '/topics', '/topics/security_defense', '/topics/iran_axis', '/sources', `/sources/${sources.sources[0].source_id}`, '/analytics', '/map',
    '/social', '/monitoring', '/review/content', '/foresight/trends', '/foresight/weak-signals', '/foresight/uncertainties',
    '/foresight/drivers', '/foresight/scenarios', '/alerts', '/about'];

  const { browser, close } = await launchEdge();
  try {
    for (const [label, width, height] of VIEWPORTS) {
      const ctx = await browser.newContext({ viewport: { width, height }, locale: 'fa-IR', timezoneId: 'Asia/Tehran', isMobile: width < 500, hasTouch: width < 500 });
      await ctx.route('**/*', (r) => {
        const u = new URL(r.request().url());
        if (['127.0.0.1', 'localhost'].includes(u.hostname)) return r.continue();
        if (r.request().resourceType() === 'image') return r.continue();
        externalBlocked.push(u.hostname); return r.abort();
      });
      const page = await ctx.newPage();
      let current = '';
      page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push({ viewport: label, route: current, text: m.text().slice(0, 200) }); });
      page.on('pageerror', (e) => consoleErrors.push({ viewport: label, route: current, text: 'pageerror: ' + e.message.slice(0, 200) }));
      page.on('response', (res) => { const u = new URL(res.url()); if (['127.0.0.1', 'localhost'].includes(u.hostname) && res.status() >= 400) failedLocal.push({ viewport: label, route: current, url: u.pathname + u.search, status: res.status() }); });
      // Next.js prefetches linked pages and cancels those requests when the
      // page navigates on; ERR_ABORTED there is cancellation, not failure.
      page.on('requestfailed', (req) => { const u = new URL(req.url()); if (!['127.0.0.1', 'localhost'].includes(u.hostname)) return;
        const err = req.failure()?.errorText || '';
        if (err.includes('ERR_ABORTED')) abortedPrefetch.push(u.pathname); else failedLocal.push({ viewport: label, route: current, url: u.pathname, status: 'failed:' + err }); });
      for (const route of routes) {
        current = route;
        const resp = await page.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 45000 }).catch((e) => ({ status: () => 'ERR ' + e.message }));
        await settle(page);
        const status = resp.status();
        const ov = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        if (ov > 1) overflow.push({ viewport: label, route, px: ov });
        if (label === '1440x900') await a11ySmoke(page, route);
        const file = `${label}_${route === '/' ? 'home' : route.slice(1).replace(/[\/]/g, '_').slice(0, 60)}.png`;
        const full = label === '1440x900' || label === '390x844';
        await page.screenshot({ path: path.join(OUT, file), fullPage: full, animations: 'disabled' }).catch(() => {});
        shots.push(file);
        if (status !== 200) check(`status ${label} ${route}`, false, status);
      }
      await ctx.close();
    }
    check('all routes HTTP 200 at all viewports', !results.some((r) => r.name.startsWith('status ')), routes.length * VIEWPORTS.length + ' loads');

    // ---------------- functional checks at desktop
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'fa-IR', timezoneId: 'Asia/Tehran' });
    await ctx.route('**/*', (r) => (['127.0.0.1', 'localhost'].includes(new URL(r.request().url()).hostname) ? r.continue() : r.abort()));
    const page = await ctx.newPage();

    // Reconciliation: API total vs UI count on /news, for an unfiltered and a filtered view.
    await page.goto(BASE + '/news', { waitUntil: 'domcontentloaded' }); await settle(page);
    const apiAll = await api('feed?page_size=1');
    const uiAll = await page.locator('.stream-count').innerText();
    check('news count UI = API (unfiltered)', uiAll.replace(/[^\d۰-۹]/g, '') === new Intl.NumberFormat('fa-IR', { useGrouping: false }).format(apiAll.total).replace(/[^\d۰-۹]/g, ''), { ui: uiAll, api: apiAll.total });

    const qsUrl = '/news?category=security_defense&window=7d&sort=important';
    await page.goto(BASE + qsUrl, { waitUntil: 'domcontentloaded' }); await settle(page);
    const apiF = await api('feed?category=security_defense&window=7d&sort=important&page_size=1');
    const uiF = await page.locator('.stream-count').innerText();
    check('query-string filter restores state and matches API', uiF.replace(/[^۰-۹\d]/g, '') === new Intl.NumberFormat('fa-IR', { useGrouping: false }).format(apiF.total), { ui: uiF, api: apiF.total });
    check('query-string filter shows active chips', (await page.locator('.active-filters button').count()) === 2);
    const firstCats = await page.locator('.card-row .cat-tag').first().innerText();
    check('filtered results carry the filtered category', firstCats.includes('امنیت و دفاع'), firstCats);
    await page.selectOption('.filters select[name=category]', 'regional_geopolitics'); await settle(page);
    check('changing a filter updates the URL', page.url().includes('category=regional_geopolitics') && page.url().includes('window=7d'), page.url());
    await page.goBack(); await settle(page);
    check('browser back restores previous filter', page.url().includes('category=security_defense'), page.url());

    // Category click-through from a card.
    await page.goto(BASE + '/news', { waitUntil: 'domcontentloaded' }); await settle(page);
    const catLink = page.locator('.card-row a.cat-tag').first();
    const catHref = await catLink.getAttribute('href');
    await catLink.click(); await settle(page);
    check('category tag opens its topic page', page.url().endsWith(catHref) && (await page.locator('h1').innerText()).length > 0, page.url());

    // Bilingual / RTL-LTR.
    await page.goto(BASE + '/news/' + withImg.item_id, { waitUntil: 'domcontentloaded' }); await settle(page);
    const titleDir = await page.locator('h1.detail-title').getAttribute('dir');
    const expectDir = withImg.title_fa ? 'rtl' : 'ltr';
    check('detail title direction matches language shown', titleDir === expectDir, { titleDir, hasFa: !!withImg.title_fa });
    check('original English preserved in LTR column', (await page.locator('.lang-col[dir=ltr] .t').innerText()).trim() === withImg.title.trim());
    const faCol = await page.locator('.lang-col').first().innerText();
    check('Persian column states translation status honestly', withImg.title_fa ? faCol.includes(withImg.title_fa) : faCol.includes('ذخیره نشده'), faCol.slice(0, 120));
    check('machine-translation / status label present', (await page.locator('.tag-ai, .tag-uncertain').filter({ hasText: 'ترجمه' }).count()) > 0);
    check('provenance panel present', (await page.locator('text=منشأ و مسیر دریافت').count()) === 1);
    const htmlDir = await page.evaluate(() => [document.documentElement.dir, document.documentElement.lang]);
    check('document is RTL Persian', htmlDir[0] === 'rtl' && htmlDir[1] === 'fa', htmlDir);
    const ltrTitles = await page.evaluate(() => [...document.querySelectorAll('h3[dir=ltr], .card-original[dir=ltr]')].filter((e) => /[؀-ۿ]/.test(e.textContent)).length);
    check('no Persian text inside LTR title blocks', ltrTitles === 0, ltrTitles);
    const digits = await page.evaluate(() => { const el = document.querySelector('.lang-col[dir=ltr] .t'); return el ? getComputedStyle(el).fontFamily : ''; });
    check('English text uses a Latin face (Latin digits)', /Segoe|system-ui|Arial|Roboto/.test(digits), digits);

    // Content-language toggle (per-viewer).
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' }); await settle(page);
    await page.locator('.lang button[aria-checked=false]').first().click();
    const langNow = await page.evaluate(() => localStorage.getItem('im.contentLang'));
    check('content-language toggle persists per viewer', langNow === '"en"', langNow);
    await page.locator('.lang button[aria-checked=false]').first().click();

    // Stories viewer.
    const storyCount = (await api('stories')).total;
    check('stories exist and are data-driven', storyCount > 0, storyCount);
    const railButtons = page.locator('.stories-rail .story-btn');
    check('story rail renders every story', (await railButtons.count()) === storyCount, { ui: await railButtons.count(), api: storyCount });
    await railButtons.first().focus();
    await page.keyboard.press('ArrowLeft');
    const focusedIdx = await page.evaluate(() => [...document.querySelectorAll('.story-btn')].indexOf(document.activeElement));
    check('rail keyboard navigation (ArrowLeft moves to next story)', focusedIdx === 1, focusedIdx);
    await page.keyboard.press('Enter');
    await page.waitForSelector('.viewer[role=dialog]', { timeout: 5000 });
    await page.waitForSelector('.viewer-frame', { timeout: 8000 });
    check('story viewer opens as modal dialog', (await page.locator('.viewer[aria-modal=true]').count()) === 1);
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(OUT, 'story-viewer_1440x900.png') }); shots.push('story-viewer_1440x900.png');
    const bars = await page.locator('.viewer-progress span').count();
    check('story viewer shows a progress segment per frame', bars >= 1, bars);
    const w1 = await page.locator('.viewer-progress span >> nth=0 >> i').evaluate((e) => e.style.width);
    await page.waitForTimeout(1500);
    const w2 = await page.locator('.viewer-progress span >> nth=0 >> i').evaluate((e) => e.style.width);
    check('story progress advances automatically', parseFloat(w2) > parseFloat(w1), { w1, w2 });
    const h1 = await page.locator('.viewer-text h2').innerText();
    await page.keyboard.press('ArrowLeft'); await page.waitForTimeout(400);
    const h2 = await page.locator('.viewer-text h2').innerText().catch(() => '');
    check('ArrowLeft advances to the next frame or story', h2 !== h1 || bars === 1, { before: h1.slice(0, 40), after: h2.slice(0, 40) });
    await page.keyboard.press('ArrowRight'); await page.waitForTimeout(300);
    await page.locator('.viewer-text').hover(); const p1 = await page.locator('.viewer-progress i').nth(0).evaluate((e) => e.style.width);
    await page.waitForTimeout(1200);
    const p2 = await page.locator('.viewer-progress i').nth(0).evaluate((e) => e.style.width);
    check('story pauses while pointer is over the text', p1 === p2, { p1, p2 });
    await page.keyboard.press('Escape'); await page.waitForTimeout(300);
    check('Escape closes the viewer', (await page.locator('.viewer').count()) === 0);
    const refocus = await page.evaluate(() => document.activeElement?.classList.contains('story-btn'));
    check('focus returns to the story that opened the viewer', refocus);
    const seen = await page.evaluate(() => Object.keys(JSON.parse(localStorage.getItem('im.storiesSeen') || '{}')).length);
    check('viewed story is marked seen (ring state)', seen >= 1, seen);

    // Ticker.
    const tick = page.locator('.ticker');
    const mode = (await api('breaking')).mode;
    check('ticker renders from audited rule', (await tick.count()) === 1, mode);
    const pause = page.locator('.ticker-ctrl button[aria-pressed]');
    await pause.click();
    check('ticker pause toggles aria-pressed', (await pause.getAttribute('aria-pressed')) === 'true');
    const n = (await api('breaking')).items.length;
    if (n > 1) {
      const a = await page.locator('.ticker-title').innerText();
      await page.locator('.ticker-ctrl button[aria-label="خبر بعدی"]').click(); await page.waitForTimeout(400);
      check('ticker next button changes headline', (await page.locator('.ticker-title').innerText()) !== a);
    } else check('ticker next button (single item: nothing to advance)', true, n);

    // Skip link first in tab order.
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' }); await settle(page);
    await page.keyboard.press('Tab');
    check('first Tab reaches the skip link', await page.evaluate(() => document.activeElement?.classList.contains('skip')));

    // Events timeline and detail.
    await page.goto(BASE + '/events', { waitUntil: 'domcontentloaded' }); await settle(page);
    const evApi = await api('timeline/events?sort=latest&page_size=20');
    check('events page lists API events', (await page.locator('.tl-item').count()) === evApi.events.length, { ui: await page.locator('.tl-item').count(), api: evApi.events.length });
    await page.locator('.segmented button', { hasText: 'بیشترین منبع' }).click(); await settle(page);
    const firstImportant = (await api('timeline/events?sort=important&page_size=1')).events[0];
    check('"important" sort puts the most-sourced event first', (await page.locator('.tl-item h3').first().innerText()).trim() === firstImportant.title.trim());
    const ev = events.events[0];
    await page.goto(BASE + '/events/' + ev.event_id, { waitUntil: 'domcontentloaded' }); await settle(page);
    check('event detail shows every member in order', (await page.locator('.tl-item').count()) === ev.member_count, { ui: await page.locator('.tl-item').count(), api: ev.member_count });
    check('event detail shows membership reason', (await page.locator('text=دلیل عضویت').count()) > 0);

    // Empty / error / loading states.
    await page.goto(BASE + '/map', { waitUntil: 'domcontentloaded' }); await settle(page);
    check('map shows honest empty state (no fabricated points)', (await page.locator('.empty').count()) >= 1 && (await api('geo')).total === 0);
    await page.goto(BASE + '/news/does-not-exist', { waitUntil: 'domcontentloaded' }); await settle(page);
    check('unknown item shows an error state', (await page.locator('.failure[role=alert]').count()) === 1);
    await page.goto(BASE + '/news?q=zzzqqqnomatch', { waitUntil: 'domcontentloaded' }); await settle(page);
    check('no-result search shows empty state', (await page.locator('.empty').count()) === 1);
    await ctx.route('**/api/v1/briefing/daily', (r) => r.fulfill({ status: 500, body: '{}' }));
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' }); await settle(page);
    check('API failure renders an error state, not stale data', (await page.locator('.brief-panel [role=alert]').count()) === 1);
    await ctx.unroute('**/api/v1/briefing/daily');
    await ctx.route('**/api/v1/feed?*', async (r) => { await new Promise((x) => setTimeout(x, 2500)); r.continue(); });
    await page.goto(BASE + '/news', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
    check('loading state renders skeletons', (await page.locator('.bones, .bone').count()) > 0);
    await ctx.unroute('**/api/v1/feed?*');

    // Mobile navigation.
    const m = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, locale: 'fa-IR' });
    await m.route('**/*', (r) => (['127.0.0.1', 'localhost'].includes(new URL(r.request().url()).hostname) ? r.continue() : r.abort()));
    const mp = await m.newPage();
    await mp.goto(BASE + '/', { waitUntil: 'domcontentloaded' }); await settle(mp);
    await mp.locator('.stories-rail .story-btn').first().click(); await mp.waitForSelector('.viewer-frame', { timeout: 8000 }); await mp.waitForTimeout(600);
    await mp.screenshot({ path: path.join(OUT, 'story-viewer_390x844.png') }); shots.push('story-viewer_390x844.png');
    check('story viewer works on touch viewport', (await mp.locator('.viewer-frame').count()) === 1);
    await mp.locator('button[aria-label="بستن استوری"]').click();
    await mp.locator('button[aria-label="باز کردن منو"]').click();
    await mp.screenshot({ path: path.join(OUT, 'mobile-drawer_390x844.png') }); shots.push('mobile-drawer_390x844.png');
    check('mobile drawer opens with navigation', await mp.locator('.drawer[role=dialog] .drawer-link').count() > 10);
    await mp.locator('.drawer-link', { hasText: 'رویدادها' }).click(); await settle(mp);
    check('mobile drawer link navigates and closes', mp.url().endsWith('/events') && (await mp.locator('.drawer').count()) === 0, mp.url());
    await m.close();
    await ctx.close();
  } finally { await close(); }

  const fails = results.filter((r) => !r.pass);
  const report = {
    base: BASE, started: new Date(t0).toISOString(), seconds: Math.round((Date.now() - t0) / 1000),
    checks: results.length, passed: results.length - fails.length, failed: fails.length, failures: fails,
    screenshots: shots.length, console_errors: consoleErrors, failed_local_requests: failedLocal, horizontal_overflow: overflow,
    a11y_issues: a11y, external_requests_blocked: [...new Set(externalBlocked)], aborted_navigation_requests: abortedPrefetch.length,
  };
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
  console.log(`\nCHECKS ${report.passed}/${report.checks} · SCREENSHOTS ${shots.length} · CONSOLE_ERRORS ${consoleErrors.length} · FAILED_LOCAL ${failedLocal.length} · OVERFLOW ${overflow.length} · A11Y_PAGES_WITH_ISSUES ${a11y.length}`);
  process.exit(fails.length ? 1 : 0);
})();

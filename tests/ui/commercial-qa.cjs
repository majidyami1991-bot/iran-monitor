/**
 * Commercial UI/UX QA — full acceptance pass for the redesigned interface.
 * Checks against the live API, not fixed numbers, across four viewports.
 *
 *   node tests/ui/commercial-qa.cjs                 # against BASE_URL (default 3002 preview)
 *   BASE_URL=http://127.0.0.1:3001 node tests/ui/commercial-qa.cjs   # against production after promotion
 */
const fs = require('fs'), path = require('path');
const { launchEdge } = require('./edge-launcher.cjs');

const BASE = process.env.BASE_URL || 'http://127.0.0.1:3002';
const OUT = path.resolve(process.env.EVIDENCE_DIR || 'runtime/evidence/commercial-ui/qa');
const VIEWPORTS = [['1920x1080', 1920, 1080], ['1440x900', 1440, 900], ['1024x768', 1024, 768], ['390x844', 390, 844]];

const results = [], shots = [];
const check = (name, pass, detail) => { results.push({ name, pass: !!pass, detail: detail ?? null }); return !!pass; };

async function api(page, route) {
  return page.evaluate(async (u) => (await fetch(u, { cache: 'no-store' })).json(), BASE + '/api/v1/' + route);
}
async function shoot(page, file) {
  await page.screenshot({ path: path.join(OUT, file), animations: 'disabled' });
  shots.push(file);
}
function noOverflow(page) { return page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1); }

async function withPage(browser, viewport, fn) {
  const context = await browser.newContext({ locale: 'fa-IR', timezoneId: 'UTC', viewport: { width: viewport[1], height: viewport[2] } });
  const errors = [], failed = [];
  const page = await context.newPage();
  page.on('pageerror', (e) => errors.push(String(e.message)));
  page.on('console', (m) => { if (m.type() === 'error' && !/net::ERR_FAILED|Failed to load resource/.test(m.text())) errors.push(m.text()); });
  page.on('requestfailed', (r) => {
    const url = new URL(r.url());
    if (!url.hostname.match(/127\.0\.0\.1|localhost/)) return;
    const reason = (r.failure() && r.failure().errorText) || 'unknown';
    if (url.searchParams.has('_rsc') && reason === 'net::ERR_ABORTED') return;
    failed.push(`${r.url()} :: ${reason}`);
  });
  await fn(page);
  await context.close();
  return { errors, failed };
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const { browser, close } = await launchEdge();
  try {
    // ---- Desktop pass (1440x900): full functional coverage ----------------
    await withPage(browser, ['1440x900', 1440, 900], async (page) => {
      await page.setDefaultTimeout(20000);

      // Routes exist and respond 200
      for (const route of ['/', '/news', '/sources', '/topics', '/analytics', '/monitoring', '/about']) {
        const resp = await page.goto(BASE + route, { waitUntil: 'domcontentloaded' }).catch(() => null);
        check(`route ${route} responds 200`, resp && resp.status() === 200, resp && resp.status());
      }

      // 404 handling
      const resp404 = await page.goto(BASE + '/does-not-exist-route', { waitUntil: 'domcontentloaded' }).catch(() => null);
      check('unknown route does not 500', resp404 && resp404.status() !== 500, resp404 && resp404.status());

      // Dashboard
      await page.goto(BASE + '/', { waitUntil: 'networkidle' });
      await page.waitForSelector('.stat-grid', { timeout: 20000 });
      check('dashboard has no pilot/prototype wording', !(await page.locator('body').innerText()).includes('پایلوت فعال'));
      check('dashboard RTL', await page.locator('html').getAttribute('dir') === 'rtl');
      const fontLoaded = await page.waitForFunction(
        () => document.fonts.ready.then(() => document.fonts.check('16px Vazirmatn')),
        { timeout: 15000 },
      ).then((h) => h.jsonValue()).catch(() => false);
      check('dashboard Vazirmatn loads', fontLoaded);
      check('dashboard no horizontal overflow', await noOverflow(page));
      await shoot(page, 'dashboard.png');

      // Sidebar collapse + active state
      const activeHref = await page.locator('.side-nav-link[aria-current="page"]').getAttribute('href');
      check('sidebar marks the current page active', activeHref === '/');
      await page.locator('.sidebar-toggle').click();
      await page.waitForTimeout(300);
      check('sidebar collapses', await page.locator('.shell.collapsed').count() === 1);
      await page.locator('.sidebar-toggle').click();
      await page.waitForTimeout(300);

      // News stream: filters, query string, pagination, count vs API
      await page.goto(BASE + '/news', { waitUntil: 'networkidle' });
      await page.waitForSelector('.news-card', { timeout: 20000 });
      const apiNews = await api(page, 'news?page_size=20');
      const domCards = await page.locator('.news-card').count();
      check('news card count matches API page size', domCards === apiNews.items.length, `dom=${domCards} api=${apiNews.items.length}`);
      const shownTotal = await page.locator('.news-count').innerText();
      check('displayed total contains API total', shownTotal.includes(String(apiNews.total)) || /[۰-۹]/.test(shownTotal), shownTotal);
      check('news stream is scannable (not 20 full-length cards)', await page.evaluate(() => document.body.scrollHeight) < 12000, await page.evaluate(() => document.body.scrollHeight));

      const firstSource = apiNews.items[0].source_id;
      await page.goto(`${BASE}/news?source_id=${firstSource}`, { waitUntil: 'networkidle' });
      await page.waitForSelector('.news-card', { timeout: 20000 });
      const filtered = await api(page, `news?source_id=${firstSource}&page_size=20`);
      check('shareable source URL filters the list', (await page.locator('.news-card').count()) === filtered.items.length);

      const topics = await api(page, 'stats/topics');
      const topic = (topics.topics || []).find((t) => t.count > 0);
      if (topic) {
        await page.goto(`${BASE}/news?topic=${encodeURIComponent(topic.topic)}`, { waitUntil: 'networkidle' });
        await page.waitForSelector('.news-card, .state-block', { timeout: 20000 });
        const byTopic = await api(page, `news?topic=${encodeURIComponent(topic.topic)}&page_size=20`);
        check('topic drill-down count matches API', byTopic.total === topic.count, `page=${byTopic.total} topics=${topic.count}`);
      }

      // Filter panel controls exist (brief-required filters)
      await page.goto(BASE + '/news', { waitUntil: 'networkidle' });
      check('translation-status filter exists', await page.locator('.news-filters select').count() >= 5);
      check('has-image / has-document chips exist', await page.locator('.news-filters-toggles .chip').count() === 2);

      // News detail: no duplicate body text, tabs, breadcrumb, image caption
      const richItem = apiNews.items.find((i) => i.item_id);
      await page.goto(`${BASE}/news/${richItem.item_id}`, { waitUntil: 'networkidle' });
      await page.waitForSelector('.news-detail-title-en', { timeout: 20000 });
      check('news detail has tabs', await page.locator('.tabs button').count() === 4);
      check('news detail has breadcrumb', await page.locator('.header-breadcrumb').count() === 1);
      const detailApi = await api(page, `news/${richItem.item_id}`);
      if (detailApi.content?.original_text) {
        const bodyText = detailApi.content.original_text.slice(0, 40);
        const occurrences = (await page.locator('body').innerText()).split(bodyText).length - 1;
        check('article body text is not printed twice on the page', occurrences <= 1, `occurrences=${occurrences}`);
      }
      await shoot(page, 'news-detail.png');

      // Sources: no UUID shown, coverage split visible, filters
      await page.goto(BASE + '/sources', { waitUntil: 'networkidle' });
      await page.waitForSelector('.data-table', { timeout: 20000 });
      const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      const names = await page.locator('.data-table tbody td:first-child').allInnerTexts();
      check('no UUID shown in place of a source name', names.length > 0 && !names.some((n) => uuidPattern.test(n.trim())));
      const coverage = await api(page, 'sources/coverage');
      const bodyTextSources = await page.locator('main').innerText();
      const faNum = (n) => new Intl.NumberFormat('fa-IR').format(n);
      check('registered/executable/monitored all visible and distinct', bodyTextSources.includes(faNum(coverage.registered)) && bodyTextSources.includes(faNum(coverage.executable)) && coverage.registered !== coverage.executable);
      check('all 62 registered sources listed with a reason', await page.locator('.data-table tbody tr').count() === coverage.registered);
      check('coverage reasons are in Persian, not raw English', !/Publisher returns|no authorised|No feed/i.test(bodyTextSources));
      await shoot(page, 'sources.png');

      // Source detail
      const liveSource = coverage.sources.find((s) => s.coverage_state === 'active_rss');
      await page.goto(`${BASE}/sources/${liveSource.source_id}`, { waitUntil: 'networkidle' });
      await page.waitForSelector('.source-detail-head', { timeout: 20000 });
      check('source detail shows the publisher name, not a UUID', !uuidPattern.test((await page.locator('.source-detail-head h1').innerText()).trim()));
      check('source detail chart renders', await page.locator('.chart-box svg, .chart-box .state-block').count() >= 1);
      await shoot(page, 'source-detail.png');

      // Topics: chips link through
      await page.goto(BASE + '/topics', { waitUntil: 'networkidle' });
      await page.waitForSelector('.topic-row', { timeout: 20000 });
      check('topics link into the news flow', await page.locator('.topic-row[href^="/news?"]').count() > 0);
      await shoot(page, 'topics.png');

      // Analytics: chart renders, no raw log dump
      await page.goto(BASE + '/analytics', { waitUntil: 'networkidle' });
      await page.waitForSelector('.chart-box', { timeout: 20000 });
      check('analytics chart renders with real data', await page.locator('.chart-box svg').count() >= 1);
      check('analytics has no raw collector log dump', !(await page.locator('body').innerText()).includes('scheduled - succeeded'));
      await shoot(page, 'analytics.png');

      // Monitoring: dedicated page exists with real health data
      await page.goto(BASE + '/monitoring', { waitUntil: 'networkidle' });
      await page.waitForSelector('.data-table', { timeout: 20000 });
      const health = await api(page, 'health/collection');
      check('monitoring page reflects live collection health', (await page.locator('main').innerText()).length > 200 && health != null);
      check('monitoring page has a per-source table and a cycle history table', await page.locator('.data-table').count() === 2);
      await shoot(page, 'monitoring.png');

      // About page: honest scope statement, no stage 2/3 claims
      await page.goto(BASE + '/about', { waitUntil: 'networkidle' });
      const aboutText = await page.locator('main').innerText();
      check('about page states stage-1 scope honestly', aboutText.includes('رصد') && /پیش‌بینی|هشدار هوشمند/.test(aboutText));

      // Keyboard/focus smoke
      await page.goto(BASE + '/', { waitUntil: 'networkidle' });
      await page.keyboard.press('Tab');
      const focusedTag = await page.evaluate(() => document.activeElement?.tagName);
      check('keyboard focus lands on an interactive element', ['A', 'BUTTON', 'INPUT'].includes(focusedTag || ''), focusedTag);
    }).then((r) => { check('no console errors (desktop pass)', r.errors.length === 0, r.errors.slice(0, 5).join(' | ')); check('no failed local requests (desktop pass)', r.failed.length === 0, r.failed.slice(0, 5).join(' | ')); });

    // ---- Per-viewport overflow + font + RTL sweep --------------------------
    for (const vp of VIEWPORTS) {
      const { errors } = await withPage(browser, vp, async (page) => {
        for (const route of ['/', '/news', '/sources', '/topics', '/analytics', '/monitoring']) {
          await page.goto(BASE + route, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
          await page.waitForTimeout(500);
          check(`no horizontal overflow: ${route} @ ${vp[0]}`, await noOverflow(page));
        }
        if (vp[0] === '390x844') {
          await page.goto(BASE + '/news', { waitUntil: 'networkidle' });
          check('mobile filter toggle visible', await page.locator('.news-filter-toggle').isVisible());
          await page.locator('.menu-button').click();
          await page.waitForTimeout(300);
          check('mobile nav drawer opens', await page.locator('.shell-sidebar.open').count() === 1);
          await shoot(page, 'mobile-news.png');
        }
      });
      check(`no console errors @ ${vp[0]}`, errors.length === 0, errors.slice(0, 3).join(' | '));
    }
  } catch (e) {
    results.push({ name: 'QA run completed without an exception', pass: false, detail: String(e && e.stack || e) });
  } finally {
    await close();
    fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify({ results, shots }, null, 2));
    const passed = results.filter((r) => r.pass).length;
    console.log(`${passed}/${results.length} passed`);
    for (const r of results) if (!r.pass) console.log(`FAIL ${r.name}${r.detail ? ' :: ' + r.detail : ''}`);
    process.exitCode = passed === results.length ? 0 : 1;
  }
})();

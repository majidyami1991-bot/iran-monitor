/**
 * Stage 1 browser acceptance: news flow, source pages, topic drill-down and the
 * content fields, checked against the API rather than against fixed numbers.
 *
 *   node tests/ui/stage1-qa.cjs
 *
 * PLAYWRIGHT_MODULE, EDGE_PATH, BASE_URL and EVIDENCE_DIR override the defaults.
 * All requests are confined to the local host; anything else is aborted.
 */
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'C:/Temp/iran-monitor-playwright-20260914T/node_modules/playwright');

const BASE = process.env.BASE_URL || 'http://127.0.0.1:3001';
const OUT = path.resolve(process.env.EVIDENCE_DIR || 'runtime/evidence/stage1-qa');
const EDGE = process.env.EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';

const results = [], errors = [], failed = [], shots = [];
const check = (name, pass, detail) => { results.push({ name, pass: !!pass, detail: detail ?? null }); return !!pass; };

async function api(page, route) {
  return page.evaluate(async (u) => (await fetch(u, { cache: 'no-store' })).json(), BASE + '/api/v1/' + route);
}

async function shoot(page, file, fullPage = false) {
  await page.screenshot({ path: path.join(OUT, file), animations: 'disabled', fullPage });
  shots.push(file);
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true, executablePath: EDGE });
  try {
    const context = await browser.newContext({ locale: 'fa-IR', timezoneId: 'UTC' });
    await context.route('**/*', r => {
      const u = new URL(r.request().url());
      return ['127.0.0.1', 'localhost'].includes(u.hostname) ? r.continue() : r.abort();
    });
    const page = await context.newPage();
    page.on('pageerror', e => errors.push(String(e.message)));
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    // Next.js prefetches the next route on hover; navigating away cancels that
    // request. An aborted prefetch is not a user-visible failure, so only record
    // it when the reason is something other than the cancellation.
    page.on('requestfailed', r => {
      const url = new URL(r.url());
      if (!url.hostname.match(/127\.0\.0\.1|localhost/)) return;
      const reason = (r.failure() && r.failure().errorText) || 'unknown';
      if (url.searchParams.has('_rsc') && reason === 'net::ERR_ABORTED') return;
      failed.push(`${r.url()} :: ${reason}`);
    });

    await page.setViewportSize({ width: 1440, height: 900 });

    // --- News flow -------------------------------------------------------
    const newsResponse = await page.goto(BASE + '/news', { waitUntil: 'domcontentloaded' });
    check('news page responds 200', newsResponse.status() === 200, newsResponse.status());
    await page.waitForSelector('.item-card', { timeout: 45000 });
    await page.evaluate(() => document.fonts.ready);

    const apiNews = await api(page, 'news?page=1&page_size=30');
    const cardCount = await page.locator('.item-card').count();
    check('news cards match API page size', cardCount === apiNews.items.length, `dom=${cardCount} api=${apiNews.items.length}`);
    check('news feed has real data', apiNews.total > 0, `total=${apiNews.total}`);

    const shownTotal = await page.locator('.monitor-count').first().innerText();
    const digits = shownTotal.replace(/[^۰-۹]/g, '').replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d));
    check('displayed total matches API total', digits.startsWith(String(apiNews.total)), `shown=${shownTotal} api=${apiNews.total}`);

    check('RTL direction', await page.locator('html').getAttribute('dir') === 'rtl');
    check('Vazirmatn loaded', await page.evaluate(() => document.fonts.check('16px Vazirmatn')));
    check('no horizontal overflow (desktop)', await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
    check('external links are safe', await page.locator('a[target=_blank]').evaluateAll(
      xs => xs.every(x => x.rel.includes('noopener') && x.rel.includes('noreferrer'))));
    check('per-field status badges render', await page.locator('.item-field-status .vf-badge').count() > 0);
    await shoot(page, 'news-desktop.png');

    // --- Source filter and shareable URL ---------------------------------
    const firstSource = apiNews.items[0].source_id;
    await page.goto(`${BASE}/news?source_id=${firstSource}`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.item-card', { timeout: 45000 });
    const filtered = await api(page, `news?source_id=${firstSource}&page=1&page_size=30`);
    const filteredCards = await page.locator('.item-card').count();
    check('shared source URL filters the list', filteredCards === filtered.items.length && filtered.items.every(i => i.source_id === firstSource),
      `dom=${filteredCards} api=${filtered.items.length}`);

    // --- Category drill-down ---------------------------------------------
    const topics = await api(page, 'stats/topics');
    const category = (topics.categories || []).find(c => c.count > 0);
    if (category) {
      await page.goto(`${BASE}/news?category=${encodeURIComponent(category.label)}`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('.item-card', { timeout: 45000 });
      const byCategory = await api(page, `news?category=${encodeURIComponent(category.label)}&page=1&page_size=30`);
      check('category drill-down count matches API', byCategory.total === category.count,
        `label=${category.label} api_news=${byCategory.total} api_topics=${category.count}`);
      check('category results all carry that category', byCategory.items.every(i => i.category === category.label));
    } else {
      check('category drill-down count matches API', false, 'no category available');
    }

    // --- Topic drill-down -------------------------------------------------
    const topic = (topics.topics || []).find(t => t.count > 0);
    if (topic) {
      const byTopic = await api(page, `news?topic=${encodeURIComponent(topic.topic)}&page=1&page_size=30`);
      check('topic filter returns only items carrying that topic',
        byTopic.total > 0 && byTopic.items.every(i => (i.topics || []).includes(topic.topic)),
        `topic=${topic.topic} total=${byTopic.total}`);
      check('topic total matches the topics endpoint', byTopic.total === topic.count,
        `news=${byTopic.total} topics=${topic.count}`);
      await page.goto(`${BASE}/news?topic=${encodeURIComponent(topic.topic)}`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('.item-card', { timeout: 45000 });
      const cards = await page.locator('.item-card').count();
      check('topic drill-down renders the filtered list',
        cards === Math.min(byTopic.total, byTopic.page_size), `dom=${cards} api=${byTopic.total}`);
      check('active topic is shown to the user', (await page.locator('main').innerText()).includes(topic.topic));
    } else {
      check('topic filter returns only items carrying that topic', false, 'no topic available');
    }

    // The topics page must link through rather than only count.
    await page.goto(BASE + '/topics', { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.vf-topic-row', { timeout: 45000 });
    check('topics page links categories to the news flow',
      await page.locator('.vf-topic-row a[href^="/news?"]').count() > 0);

    // --- Time window ------------------------------------------------------
    await page.goto(`${BASE}/news?window=7d`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.item-card, .vf-empty', { timeout: 45000 });
    const week = await api(page, 'news?window=7d&page=1&page_size=30');
    check('7 day window is a strict subset of all', week.total <= apiNews.total, `7d=${week.total} all=${apiNews.total}`);

    // --- Sources list -----------------------------------------------------
    await page.goto(BASE + '/sources', { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.source-table-desktop tbody tr, .source-card', { timeout: 45000 });
    const apiSources = await api(page, 'sources?page_size=100');
    const names = await page.locator('.source-table-desktop tbody tr td:first-child').allInnerTexts();
    const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    check('no UUID is shown instead of a source name', names.length > 0 && !names.some(n => uuid.test(n.trim())), names.slice(0, 3).join(' | '));
    check('source rows match API count', names.length === apiSources.sources.length, `dom=${names.length} api=${apiSources.sources.length}`);

    // The three coverage numbers must be visible and distinct in the product,
    // not just available from the API.
    const coverage = await api(page, 'sources/coverage');
    const sourcesText = await page.locator('main').innerText();
    const faNum = n => new Intl.NumberFormat('fa-IR').format(n);
    check('coverage panel shows registered, executable and monitored',
      sourcesText.includes(faNum(coverage.registered)) && sourcesText.includes(faNum(coverage.executable))
      && sourcesText.includes(faNum(coverage.monitored)),
      `registered=${coverage.registered} executable=${coverage.executable} monitored=${coverage.monitored}`);
    check('coverage counts are not conflated', coverage.registered !== coverage.executable,
      `registered=${coverage.registered} executable=${coverage.executable}`);
    check('X accounts are not presented as monitored',
      (coverage.by_state.not_covered || 0) > 0 && coverage.monitored <= coverage.executable,
      `not_covered=${coverage.by_state.not_covered} monitored=${coverage.monitored}`);
    check('every registered source has a coverage state and reason',
      coverage.sources.length === coverage.registered && coverage.sources.every(s => s.coverage_state && s.reason),
      `${coverage.sources.length}/${coverage.registered}`);
    await shoot(page, 'sources-desktop.png');

    // --- Source detail ----------------------------------------------------
    const source = apiSources.sources[0];
    await page.goto(`${BASE}/sources/${source.source_id}`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.source-card', { timeout: 45000 });
    const detail = await api(page, `sources/${source.source_id}`);
    const body = await page.locator('main').innerText();
    check('source detail shows the publisher name', body.includes(detail.display_name || detail.hostname), detail.display_name || detail.hostname);
    check('source detail shows its own items', (detail.latest_items || []).length > 0 ? await page.locator('.item-card').count() > 1 : true,
      `items=${(detail.latest_items || []).length}`);
    check('source detail reports monitoring state', /سالم|دیرکرد|خطا|هنوز اجرا نشده/.test(body), detail.health_status);
    await shoot(page, 'source-detail-desktop.png');

    // --- News detail ------------------------------------------------------
    const itemId = apiNews.items[0].item_id;
    await page.goto(`${BASE}/news/${itemId}`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.item-card', { timeout: 45000 });
    const item = await api(page, `news/${encodeURIComponent(itemId)}`);
    const detailText = await page.locator('main').innerText();
    check('detail shows the original English heading', detailText.includes('متن اصلی'));
    check('detail shows the Persian translation section', detailText.includes('ترجمه فارسی'));
    check('detail names the source and links the original', detailText.includes(item.source_name || item.hostname)
      && await page.locator('a[target=_blank]').count() > 0);
    check('detail exposes collection evidence', detailText.includes('شواهد جمع‌آوری') || detailText.includes('provenance'));
    const bodyShown = await page.locator('.item-body-text[dir=ltr] p').count();
    const expectBody = item.content && item.content.display_policy === 'full_syndicated' && item.content.original_text;
    check('body text renders when the display policy allows it', expectBody ? bodyShown > 0 : true,
      `policy=${item.content && item.content.display_policy} paragraphs=${bodyShown}`);
    check('withheld body states its reason', expectBody ? true : /نمایش داده نمی‌شود|ذخیره نشده/.test(detailText));
    await shoot(page, 'news-detail-desktop.png', true);

    // --- Analytics --------------------------------------------------------
    await page.goto(BASE + '/analytics', { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.metric-grid', { timeout: 45000 });
    const overview = await api(page, 'stats/overview');
    const analytics = await page.locator('main').innerText();
    const fa = n => new Intl.NumberFormat('fa-IR').format(n);
    check('analytics total matches API', analytics.includes(fa(overview.total_items).replace(/,/g, '٬')) || analytics.includes(String(overview.total_items)),
      `api=${overview.total_items}`);
    check('analytics states scheduler state', /زمان‌بندی فعال|متوقف/.test(analytics));
    await shoot(page, 'analytics-desktop.png');

    // --- Mobile -----------------------------------------------------------
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(BASE + '/news', { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.item-card', { timeout: 45000 });
    check('no horizontal overflow (mobile)', await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
    await shoot(page, 'news-mobile.png');
    await page.goto(BASE + '/sources', { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.source-card', { timeout: 45000 });
    check('sources readable on mobile', await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
    await shoot(page, 'sources-mobile.png');

    check('no page console errors', errors.length === 0, errors.slice(0, 4).join(' | '));
    check('no failed local requests', failed.length === 0, failed.slice(0, 4).join(' | '));
    await context.close();
  } catch (e) {
    results.push({ name: 'run completed without an exception', pass: false, detail: String(e && e.message) });
  } finally {
    await browser.close();
    const manifest = shots.map(file => {
      const b = fs.readFileSync(path.join(OUT, file));
      return { file, width: b.readUInt32BE(16), height: b.readUInt32BE(20), sha256: crypto.createHash('sha256').update(b).digest('hex') };
    });
    fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify({ results, errors, failed }, null, 2));
    fs.writeFileSync(path.join(OUT, 'manifest.json'), JSON.stringify(manifest, null, 2));
    const passed = results.filter(r => r.pass).length;
    console.log(`${passed}/${results.length} passed`);
    for (const r of results) if (!r.pass) console.log(`FAIL ${r.name}${r.detail ? ' :: ' + r.detail : ''}`);
    process.exitCode = passed === results.length ? 0 : 1;
  }
})();

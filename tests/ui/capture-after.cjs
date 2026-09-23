/**
 * Section 1 visual audit: full-page screenshots of every page at four
 * viewports against the live, unmodified system. No code changes accompany
 * this script; it is evidence-gathering only.
 *
 *   node tests/ui/capture-before.cjs
 */
const fs = require('fs'), path = require('path');
const { launchEdge } = require('./edge-launcher.cjs');

const BASE = process.env.BASE_URL || 'http://127.0.0.1:3002';
const OUT = path.resolve(process.env.EVIDENCE_DIR || 'runtime/evidence/commercial-ui/after');

const VIEWPORTS = [
  ['1920x1080', 1920, 1080],
  ['1440x900', 1440, 900],
  ['1024x768', 1024, 768],
  ['390x844', 390, 844],
];

async function api(page, route) {
  return page.evaluate(async (u) => (await fetch(u, { cache: 'no-store' })).json(), BASE + '/api/v1/' + route);
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const { browser, close } = await launchEdge();
  const context = await browser.newContext({ locale: 'fa-IR', timezoneId: 'UTC' });
  const page = await context.newPage();
  page.setDefaultTimeout(20000);
  // fetch() needs a real origin (about:blank's null origin gets CORS-blocked),
  // so land on the site before issuing any API call from inside the page.
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 30000 });

  // Resolve the richest sample records so the "detail" screenshots actually
  // show populated content rather than an arbitrary sparse row.
  const apiNews = await api(page, 'news?page_size=30');
  let richest = apiNews.items[0], richestScore = -1;
  for (const item of apiNews.items) {
    const full = await api(page, `news/${encodeURIComponent(item.item_id)}`);
    const score = (full.content && full.content.text_chars || 0) + ((full.media && full.media.images || []).length * 500);
    if (score > richestScore) { richest = item; richestScore = score; }
  }
  const apiSources = await api(page, 'sources?page_size=100');
  const richestSource = apiSources.sources.reduce((a, b) => (b.item_count > (a.item_count || 0) ? b : a), {});
  console.log('richest item', richest.item_id, 'score', richestScore, '| richest source', richestSource.source_id);

  const pages = [
    ['dashboard', '/'],
    ['news-stream', '/news'],
    ['news-detail', '/news/' + encodeURIComponent(richest.item_id)],
    ['sources', '/sources'],
    ['source-detail', '/sources/' + encodeURIComponent(richestSource.source_id)],
    ['topics', '/topics'],
    ['analytics', '/analytics'],
    ['monitoring', '/monitoring'],
  ];

  const manifest = [];
  for (const [vpName, w, h] of VIEWPORTS) {
    await page.setViewportSize({ width: w, height: h });
    for (const [name, route] of pages) {
      const resp = await page.goto(BASE + route, { waitUntil: 'load', timeout: 30000 }).catch((e) => { console.log('  goto failed', route, e.message); return null; });
      await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
      await page.waitForTimeout(1200);
      const file = `${name}-${vpName}.png`;
      await page.screenshot({ path: path.join(OUT, file), fullPage: true, animations: 'disabled' });
      manifest.push({ file, page: name, route, viewport: vpName, status: resp ? resp.status() : null });
      console.log('captured', file);
    }
  }
  fs.writeFileSync(path.join(OUT, 'manifest.json'), JSON.stringify(manifest, null, 2));
  await close();
  console.log(`done: ${manifest.length} screenshots`);
}
main().catch(e => { console.error(e); process.exitCode = 1; });

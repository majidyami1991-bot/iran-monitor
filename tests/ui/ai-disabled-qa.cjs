/**
 * 3003 with LOCAL_AI_DISABLED_REASON set: pages load, the Persian notice is shown, AI controls are
 * disabled, stored conversations stay readable, no console errors, no failed requests, nothing to :11434.
 *   node tests/ui/ai-disabled-qa.cjs
 */
const fs = require('fs'), path = require('path');
const { launchEdge } = require('./edge-launcher.cjs');
const BASE = process.env.BASE_URL || 'http://127.0.0.1:3003';
const NOTICE = 'قابلیت هوش مصنوعی محلی برای کاهش مصرف منابع و آماده‌سازی انتقال به سرور، موقتاً غیرفعال است.';
const results = [];
const check = (name, pass, detail) => { results.push({ name, pass: !!pass, detail: detail ?? null }); console.log((pass ? 'PASS ' : 'FAIL ') + name + (detail !== undefined ? ' — ' + JSON.stringify(detail).slice(0, 200) : '')); };

(async () => {
  const { browser, close } = await launchEdge();
  const consoleErrors = [], failed = [], aborted = [], ollama = [], requests = [];
  try {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'fa-IR' });
    const page = await ctx.newPage();
    page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(page.url() + ' ' + m.text().slice(0, 160)); });
    // a Next.js route prefetch (?_rsc=) cancelled by the next navigation is expected; anything else counts
    page.on('requestfailed', (r) => { const e = (r.failure() || {}).errorText || ''; (/_rsc=/.test(r.url()) && /ERR_ABORTED/.test(e) ? aborted : failed).push(e + ' ' + r.url()); });
    page.on('response', (r) => { if (r.status() >= 400) failed.push(r.status() + ' ' + r.url()); });
    page.on('request', (r) => { requests.push(r.url()); if (/:11434/.test(r.url())) ollama.push(r.url()); });
    const feed = await (await fetch(BASE + '/api/v1/feed?page_size=1')).json();
    const id = feed.items[0].item_id;
    for (const p of ['/', '/news', '/news/' + id, '/admin']) {
      const r = await page.goto(BASE + p, { waitUntil: 'load' });
      await page.waitForLoadState('networkidle').catch(() => {});
      check(`page ${p} HTTP 200`, r && r.status() === 200, r && r.status());
    }
    check('admin shows AI-off notice', await page.getByTestId('admin-ai-off').isVisible().catch(() => false));
    await page.goto(BASE + '/assistant', { waitUntil: 'load' });
    await page.waitForLoadState('networkidle').catch(() => {});
    const note = page.getByTestId('as-ai-off');
    for (let k = 0; k < 40 && !(await note.isVisible().catch(() => false)); k++) await page.waitForTimeout(250);
    check('assistant shows Persian notice', (await note.innerText().catch(() => '')).includes(NOTICE));
    check('question box disabled', await page.locator('#as-q').isDisabled());
    check('send button disabled', await page.getByRole('button', { name: 'ارسال' }).isDisabled());
    check('no spinner/waiting state', !(await page.getByText(/در صف پردازش محلی|در حال تولید پاسخ|در حال جست‌وجو/).first().isVisible().catch(() => false)));
    const sessions = await (await fetch(BASE + '/api/v1/assistant/sessions?limit=1')).json();
    check('stored conversations readable', sessions.sessions.length > 0, sessions.sessions.length);
    // idle 65 s on a news list: no repeated polling while AI is disabled
    const before = requests.length;
    await page.goto(BASE + '/news', { waitUntil: 'load' });
    await page.waitForLoadState('networkidle').catch(() => {});
    const settled = requests.length;
    await page.waitForTimeout(65000);
    check('no repeated polling on /news while AI off', requests.length === settled, { before, settled, after: requests.length });
  } finally { await close(); }
  check('no console errors', consoleErrors.length === 0, consoleErrors.slice(0, 3));
  check('no failed requests (aborted route prefetches excluded)', failed.length === 0, { failed: failed.slice(0, 5), aborted_prefetches: aborted.length });
  check('no browser request to :11434', ollama.length === 0, ollama);
  fs.mkdirSync(path.resolve('runtime/ai-disable'), { recursive: true });
  fs.writeFileSync(path.resolve('runtime/ai-disable/ui-qa.json'), JSON.stringify({ at: new Date().toISOString(), results }, null, 1));
  process.exit(results.every((r) => r.pass) ? 0 : 1);
})();

/**
 * X-FREE browser QA against the disposable test pair (127.0.0.1:3003).
 * Run after tests/ui/x-free-api.py enabled has created the fixture posts.
 *
 *   node tests/ui/x-free-ui.cjs
 */
const fs = require('fs'), path = require('path');
const { launchEdge } = require('./edge-launcher.cjs');

const BASE = process.env.BASE_URL || 'http://127.0.0.1:3003';
const OUT = path.resolve(process.env.EVIDENCE_DIR || 'runtime/evidence/x-free');
const VIEWPORTS = [['1920x1080', 1920, 1080], ['1440x900', 1440, 900], ['1024x768', 1024, 768], ['390x844', 390, 844]];
const results = [], consoleErrors = [], failedLocal = [], overflow = [], shots = [];
const check = (name, pass, detail) => { results.push({ name, pass: !!pass, detail: detail ?? null }); console.log((pass ? 'PASS ' : 'FAIL ') + name + (pass ? '' : ' — ' + JSON.stringify(detail ?? '').slice(0, 200))); };
const settle = async (p) => { await p.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {}); await p.waitForTimeout(600); };
const api = async (r) => (await fetch(BASE + '/api/v1/' + r)).json();
const local = (u) => ['127.0.0.1', 'localhost'].includes(new URL(u).hostname);

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const accounts = (await api('social/accounts')).accounts;
  const withPost = accounts.find((a) => a.post_count > 0);
  const routes = ['/social', `/social/accounts/${withPost.source_id}`, '/social/posts/900000000000000002', '/social/posts/900000000000000001'];
  const { browser, close } = await launchEdge();
  try {
    for (const [label, width, height] of VIEWPORTS) {
      const ctx = await browser.newContext({ viewport: { width, height }, locale: 'fa-IR', isMobile: width < 500, hasTouch: width < 500 });
      await ctx.route('**/*', (r) => (local(r.request().url()) ? r.continue() : r.abort()));
      const page = await ctx.newPage(); let cur = '';
      page.on('dialog', (d) => { consoleErrors.push({ route: cur, text: 'DIALOG OPENED: ' + d.message() }); d.dismiss(); });
      page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push({ viewport: label, route: cur, text: m.text().slice(0, 160) }); });
      page.on('pageerror', (e) => consoleErrors.push({ viewport: label, route: cur, text: 'pageerror ' + e.message }));
      page.on('response', (r) => { if (local(r.url()) && r.status() >= 400) failedLocal.push({ viewport: label, route: cur, url: new URL(r.url()).pathname, status: r.status() }); });
      for (const route of routes) {
        cur = route;
        const res = await page.goto(BASE + route, { waitUntil: 'domcontentloaded' });
        await settle(page);
        if (res.status() !== 200) check(`status ${label} ${route}`, false, res.status());
        const ov = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        if (ov > 1) overflow.push({ label, route, ov });
        const file = `${label}_${route.slice(1).replace(/\//g, '_')}.png`;
        await page.screenshot({ path: path.join(OUT, file), fullPage: label === '1440x900' || label === '390x844' });
        shots.push(file);
      }
      await ctx.close();
    }
    check('all X routes HTTP 200 at 4 viewports', !results.some((r) => r.name.startsWith('status ')), routes.length * 4);

    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'fa-IR' });
    let widgetMode = 'block';
    await ctx.route('**/*', (r) => {
      const u = r.request().url();
      if (local(u)) return r.continue();
      if (u.startsWith('https://platform.twitter.com/widgets.js') && widgetMode === 'unavailable') {
        // Stub standing in for X saying "this post cannot be shown" — exercises the unavailable state without contacting X.
        return r.fulfill({ contentType: 'application/javascript', body: 'window.twttr={widgets:{createTweet:function(){return Promise.resolve(undefined)}}};' });
      }
      return r.abort();
    });
    const page = await ctx.newPage();
    let dialogs = 0; page.on('dialog', (d) => { dialogs++; d.dismiss(); });

    // RTL + stats + accounts
    await page.goto(BASE + '/social', { waitUntil: 'domcontentloaded' }); await settle(page);
    check('document RTL Persian', await page.evaluate(() => document.documentElement.dir === 'rtl' && document.documentElement.lang === 'fa'));
    check('accounts table lists 36 accounts', (await page.locator('table.data tbody tr').count()) === 36);
    check('manual-monitoring badge shown', (await page.locator('text=پایش دستی').count()) > 0);
    check('handles rendered LTR', (await page.locator('.x-handle[dir=ltr]').count()) > 0);

    // XSS: the fixture text contains <script> and onerror — it must appear as literal text, never execute
    await page.goto(BASE + '/social/posts/900000000000000002', { waitUntil: 'domcontentloaded' }); await settle(page);
    const quote = await page.locator('blockquote.x-original').innerText();
    check('XSS payload rendered as literal text', quote.includes('<script>alert("xss")</script>') && quote.includes('onerror'), quote.slice(0, 80));
    check('no injected elements in the DOM', await page.evaluate(() => !document.querySelector('.x-original script, .x-original img')));
    check('no dialog was opened by page content', dialogs === 0, dialogs);
    check('AI/rule outputs labelled', (await page.locator('.tag-info, .tag-ai').filter({ hasText: /قاعده|هوش/ }).count()) > 0);
    check('history shown', (await page.locator('text=تاریخچه').count()) > 0);

    // Embed: consent first, then blocked (X unreachable)
    check('embed not loaded until clicked', (await page.locator('iframe').count()) === 0 && (await page.locator('text=بارگذاری نمایش رسمی این پست').count()) === 1);
    await page.locator('text=بارگذاری نمایش رسمی این پست').click();
    await page.waitForSelector('.x-embed-msg', { timeout: 20000 });
    check('blocked X shows fallback message, page intact', (await page.locator('.x-embed-msg').innerText()).includes('X در دسترس نیست'));
    check('"view on X" link always present', (await page.locator('.x-embed a.sec-link', { hasText: 'مشاهده در X' }).count()) === 1);
    await page.screenshot({ path: path.join(OUT, 'embed-blocked_1440.png') }); shots.push('embed-blocked_1440.png');

    widgetMode = 'unavailable';
    await page.goto(BASE + '/social/posts/900000000000000002', { waitUntil: 'domcontentloaded' }); await settle(page);
    await page.locator('text=بارگذاری نمایش رسمی این پست').click();
    await page.waitForSelector('.x-embed-msg', { timeout: 20000 });
    check('unavailable post shows its own state', (await page.locator('.x-embed-msg').innerText()).includes('نمایش نداد'));

    // CSP header present
    const resp = await page.goto(BASE + '/social', { waitUntil: 'domcontentloaded' });
    const csp = resp.headers()['content-security-policy'] || '';
    check('CSP header restricts scripts and frames to self + platform.twitter.com', csp.includes("script-src 'self' 'unsafe-inline' https://platform.twitter.com") && csp.includes("object-src 'none'") && csp.includes("frame-ancestors 'none'"), csp.slice(0, 120));
    await settle(page);

    // Filters via query string + empty state
    await page.goto(BASE + '/social?topic=regional_geopolitics', { waitUntil: 'domcontentloaded' }); await settle(page);
    check('topic filter from URL', (await page.locator('.x-post').count()) === 1);
    await page.selectOption('select[name=importance]', 'high'); await settle(page);
    check('filter change updates URL and shows empty state', page.url().includes('importance=high') && (await page.locator('.empty').count()) === 1);

    // Error state
    await page.goto(BASE + '/social/posts/does-not-exist', { waitUntil: 'domcontentloaded' }); await settle(page);
    check('unknown post shows error state', (await page.locator('.failure[role=alert]').count()) === 1);

    // Form: preview then save (third fixture post), and a rejected look-alike domain
    await page.goto(BASE + '/social', { waitUntil: 'domcontentloaded' }); await settle(page);
    await page.locator('button', { hasText: 'ثبت پست X' }).click();
    const handle = accounts[5].handle.slice(1);
    await page.fill('input[name=url]', `https://x.com.evil.io/${handle}/status/900000000000000003`);
    await page.fill('input[name=analyst]', 'qa bot');
    await page.locator('button', { hasText: 'پیش‌نمایش پیش از ثبت' }).click();
    await page.waitForSelector('.x-form .failure', { timeout: 10000 });
    check('form rejects look-alike domain with Persian message', (await page.locator('.x-form .failure').innerText()).includes('x.com'));
    check('save disabled before a successful preview', await page.locator('button', { hasText: 'ثبت نهایی' }).isDisabled());
    await page.fill('input[name=url]', `https://x.com/${handle}/status/900000000000000003`);
    await page.fill('textarea[name=original_text]', '[TEST FIXTURE] UI-registered post text');
    await page.selectOption('select[name=importance]', 'low');
    await page.locator('button', { hasText: 'پیش‌نمایش پیش از ثبت' }).click();
    await page.waitForSelector('.x-preview .x-post', { timeout: 10000 });
    check('preview shows exactly what will be stored', (await page.locator('.x-preview blockquote').innerText()).includes('UI-registered'));
    check('preview wrote nothing', (await (await fetch(BASE + '/api/v1/social/posts/900000000000000003')).status) === 404);
    await page.screenshot({ path: path.join(OUT, 'form-preview_1440.png'), fullPage: false }); shots.push('form-preview_1440.png');
    await page.locator('button', { hasText: 'ثبت نهایی' }).click();
    await page.waitForTimeout(1500); await settle(page);
    const created = await (await fetch(BASE + '/api/v1/social/posts/900000000000000003')).json();
    check('save creates the post with analyst provenance', created.post_id === '900000000000000003' && created.provenance_json.registered_by === 'qa bot');
    check('stream shows the new post', (await page.locator('.x-post').filter({ hasText: 'UI-registered' }).count()) === 1);

    // Mobile
    const m = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, locale: 'fa-IR' });
    await m.route('**/*', (r) => (local(r.request().url()) ? r.continue() : r.abort()));
    const mp = await m.newPage();
    await mp.goto(BASE + '/social', { waitUntil: 'domcontentloaded' }); await settle(mp);
    check('mobile: no horizontal overflow on /social', (await mp.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)) <= 1);
    check('mobile: posts readable', (await mp.locator('.x-post').count()) >= 1);
    await m.close(); await ctx.close();
  } finally { await close(); }
  const fails = results.filter((r) => !r.pass);
  const report = { checks: results.length, passed: results.length - fails.length, failures: fails, screenshots: shots.length,
    console_errors: consoleErrors, failed_local_requests: failedLocal, horizontal_overflow: overflow };
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
  console.log(`\nX-FREE UI: ${report.passed}/${report.checks} · SCREENSHOTS ${shots.length} · CONSOLE_ERRORS ${consoleErrors.length} · FAILED_LOCAL ${failedLocal.length} · OVERFLOW ${overflow.length}`);
  process.exit(fails.length ? 1 : 0);
})();

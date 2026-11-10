/**
 * Local (Ollama) X translation — API + browser QA.
 *
 * Runs against an isolated QA stack whose database holds SYNTHETIC posts in
 * every translation state (see docs/LOCAL OLLAMA X TRANSLATION QA.md), never
 * against production data. Every non-local request is aborted and counted;
 * any request to Ollama (:11434) or a cloud AI host from the page is a failure.
 *
 *   BASE_URL=http://127.0.0.1:3004 node tests/ui/x-translation-qa.cjs
 *   OFFLINE=1 BASE_URL=http://127.0.0.1:3004 node tests/ui/x-translation-qa.cjs   (Ollama unreachable)
 */
const fs = require('fs'), path = require('path');
const { launchEdge } = require('./edge-launcher.cjs');

const BASE = process.env.BASE_URL || 'http://127.0.0.1:3004';
const OFFLINE = process.env.OFFLINE === '1';
const OUT = path.resolve(process.env.EVIDENCE_DIR || 'runtime/evidence/x-translation');
const VIEWPORTS = [['1920x1080', 1920, 1080], ['1440x900', 1440, 900], ['1024x768', 1024, 768], ['390x844', 390, 844]];
const IDS = { available: '8000000000003', pending: '8000000000004', processing: '8000000000005', needs_review: '8000000000006',
  failed: '8000000000007', not_required: '8000000000008', stale: '8000000000009', no_text: '8000000000010' };
const STATE_FA = {
  pending: 'ترجمه فارسی در صف پردازش محلی است.', processing: 'در حال ترجمه با مدل محلی',
  needs_review: 'ترجمه ماشینی نیازمند بازبینی است.', failed: 'ترجمه محلی انجام نشد؛ متن اصلی همچنان در دسترس است.',
  not_required: 'متن اصلی فارسی است.',
};
const SECRET_MARK = 'QA-NEEDS-REVIEW-SHOULD-NOT-RENDER';
const AI_HOSTS = ['openrouter.ai', 'api.openai.com', 'api.anthropic.com', 'generativelanguage.googleapis.com'];

const results = [], consoleErrors = [], failedLocal = [], overflow = [], external = [], aiRequests = [], writes = [], shots = [];
const check = (name, pass, detail) => { results.push({ name, pass: !!pass, detail: detail ?? null }); console.log((pass ? 'PASS ' : 'FAIL ') + name + (pass ? '' : ' — ' + JSON.stringify(detail ?? '').slice(0, 220))); };
const api = async (r) => { const x = await fetch(BASE + '/api/v1/' + r); return { status: x.status, body: await x.json().catch(() => null) }; };
const local = (u) => ['127.0.0.1', 'localhost'].includes(new URL(u).hostname);
const settle = async (p) => { await p.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {}); await p.waitForTimeout(600); };

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const tag = OFFLINE ? 'offline_' : '';

  // ---------------- API contract
  const st = await api('social/translation/status');
  check('GET translation/status shape', st.status === 200 && ['ollama_reachable', 'configured_model', 'worker_running', 'concurrency', 'batch_size', 'enabled'].every((k) => k in st.body), st.body);
  check('status: local only, no scheduler, concurrency 1, model gemma4:e2b',
    st.body.provider === 'ollama/local' && st.body.scheduler === false && st.body.realtime === false && st.body.concurrency === 1
    && st.body.batch_size === 1 && st.body.configured_model === 'gemma4:e2b' && st.body.external_providers === false, st.body);
  check(OFFLINE ? 'status reports Ollama unreachable' : 'status reports Ollama reachable', st.body.ollama_reachable === !OFFLINE, st.body.ollama_reachable);
  const stats0 = (await api('social/translations/stats')).body;
  check('GET translations/stats has every contract key', ['total_x_posts', 'translatable', 'pending', 'processing', 'available', 'needs_review', 'failed', 'not_required', 'average_latency_ms', 'last_success_at', 'ollama_reachable', 'configured_model', 'worker_running'].every((k) => k in stats0), stats0);
  const tAvail = (await api(`social/posts/${IDS.available}/translation`)).body;
  check('available translation carries text, model, prompt version', tAvail.translation.status === 'available' && /[؀-ۿ]/.test(tAvail.translation.translated_text || '') && tAvail.translation.model === 'gemma4:e2b' && tAvail.translation.prompt_version === 'x-post-translation-fa-v1.0.0', tAvail.translation);
  check('history is returned and ends in available', tAvail.history.length >= 3 && tAvail.history[tAvail.history.length - 1].status === 'available', tAvail.history.map((h) => h.status));
  const tRev = (await api(`social/posts/${IDS.needs_review}/translation`)).body;
  check('needs_review translation text is withheld by the API', tRev.translation.status === 'needs_review' && tRev.translation.translated_text === null);
  const list = (await api('social/posts?page_size=50')).body;
  check('post list never carries needs_review text', !JSON.stringify(list).includes(SECRET_MARK));
  check('GET translation for unknown post -> 404', (await api('social/posts/123/translation')).status === 404);
  const histBefore = (await api(`social/posts/${IDS.pending}/translation`)).body.history.length;

  // ---------------- browser
  const { browser, close } = await launchEdge();
  try {
    for (const [label, width, height] of VIEWPORTS) {
      const ctx = await browser.newContext({ viewport: { width, height }, locale: 'fa-IR', isMobile: width < 500 });
      await ctx.route('**/*', (r) => {
        const u = r.request().url();
        if (new URL(u).port === '11434' || AI_HOSTS.some((h) => u.includes(h))) aiRequests.push({ label, url: u.slice(0, 100) });
        if (local(u)) return r.continue();
        external.push({ label, url: u.slice(0, 100) });
        return r.abort();
      });
      const page = await ctx.newPage(); let cur = '';
      page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push({ label, route: cur, text: m.text().slice(0, 160) }); });
      page.on('pageerror', (e) => consoleErrors.push({ label, route: cur, text: 'pageerror ' + e.message }));
      page.on('request', (r) => { if (r.method() !== 'GET' && r.method() !== 'HEAD' && local(r.url())) writes.push({ label, route: cur, method: r.method(), url: new URL(r.url()).pathname }); });
      page.on('response', (r) => { if (local(r.url()) && r.status() >= 400) failedLocal.push({ label, route: cur, url: new URL(r.url()).pathname, status: r.status() }); });
      page.on('requestfailed', (r) => { if (local(r.url()) && !(r.failure()?.errorText || '').includes('ERR_ABORTED')) failedLocal.push({ label, route: cur, url: new URL(r.url()).pathname, status: 'failed' }); });

      const routes = ['/social', '/social/accounts/synthetic-acct', '/social/accounts/synthetic-empty',
        `/social/posts/${IDS.available}`, `/social/posts/${IDS.needs_review}`, `/social/posts/${IDS.not_required}`];
      for (const route of routes) {
        cur = route;
        await page.goto(BASE + route, { waitUntil: 'domcontentloaded' }); await settle(page);
        const ov = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        if (ov > 1) overflow.push({ label, route, ov });
        const body = await page.evaluate(() => document.body.innerText);
        if (body.includes(SECRET_MARK)) check(`needs_review text never rendered (${label} ${route})`, false);
        if (label === '1440x900' || label === '390x844') {
          const file = `${tag}${label}_${route.slice(1).replace(/\//g, '_').slice(0, 60)}.png`;
          await page.screenshot({ path: path.join(OUT, file), fullPage: true }); shots.push(file);
        }
        if (label !== '1440x900' && !(label === '390x844' && route.startsWith('/social/posts/' + IDS.available))) continue;

        if (route === '/social') {
          check('loading resolves: panel and cards render', await page.locator('[data-testid=x-tr-panel]').count() === 1 && await page.locator('article.x-post').count() >= 10);
          check(OFFLINE ? 'panel says local model is off' : 'panel says local model is available',
            (await page.locator('[data-testid=x-tr-panel]').innerText()).includes(OFFLINE ? 'مدل محلی خاموش است' : 'مدل محلی در دسترس'));
          for (const [s, txt] of Object.entries(STATE_FA)) check(`state "${s}" shown on /social`, body.includes(txt), s);
          check('state "stale" shown on /social', body.includes('متن اصلی تغییر کرده است'));
          check('post without text says no local text', body.includes('متن محلی ثبت نشده است'));
          check('available translations shown (3 cards)', await page.locator('[data-testid=x-tr-text]').count() === 3);
          check('label «ترجمه ماشینی محلی» on available cards', (await page.locator('.x-translation[data-state=available] .tag-ai').allInnerTexts()).every((t) => t.includes('ترجمه ماشینی محلی')));
          check('no needs_review/failed card shows a translation', await page.locator('.x-translation:not([data-state=available]) [data-testid=x-tr-text]').count() === 0);
        }
        if (route === '/social/accounts/synthetic-empty') check('empty state rendered', body.includes('هنوز پستی از این حساب ثبت نشده است'));
        if (route === '/social/accounts/synthetic-acct') check('account page lists synthetic posts with states', await page.locator('article.x-post').count() >= 10 && body.includes(STATE_FA.pending));
        if (route === `/social/posts/${IDS.available}`) {
          const tr = page.locator('[data-testid=x-tr-text]');
          check(`[${label}] translation is RTL Persian`, await tr.getAttribute('dir') === 'rtl' && /[؀-ۿ]/.test(await tr.innerText()));
          await page.locator('[data-testid=x-tr-toggle]').click();
          const orig = page.locator('[data-testid=x-original]');
          check(`[${label}] toggle shows original, LTR`, await orig.isVisible() && await orig.getAttribute('dir') === 'ltr' && (await orig.innerText()).startsWith('CENTCOM'));
          check(`[${label}] toggle label switches`, (await page.locator('[data-testid=x-tr-toggle]').innerText()).includes('نمایش ترجمه'));
          await page.locator('[data-testid=x-tr-toggle]').click();
          check(`[${label}] toggle back shows translation`, await page.locator('[data-testid=x-tr-text]').isVisible());
          if (label === '1440x900') {
            await page.locator('.x-tr-prov summary').click();
            const prov = await page.locator('.x-tr-prov').innerText();
            check('provenance shows model, local run, time and review state', prov.includes('gemma4:e2b') && prov.includes('محلی') && prov.includes('بازبینی انسانی نشده') && /زمان ترجمه/.test(prov), prov.slice(0, 200));
            await page.screenshot({ path: path.join(OUT, `${tag}1440x900_post_available_provenance.png`), fullPage: true });
            const ovp = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
            if (ovp > 1) overflow.push({ label, route: route + '#prov', ov: ovp });
          }
        }
        if (route === `/social/posts/${IDS.needs_review}`) check('needs_review detail shows review notice, not text', body.includes(STATE_FA.needs_review) && await page.locator('[data-testid=x-tr-text]').count() === 0);
        if (route === `/social/posts/${IDS.not_required}`) {
          const o = page.locator('[data-testid=x-original]');
          check('Persian original shown RTL with "not required" notice', body.includes(STATE_FA.not_required) && await o.getAttribute('dir') === 'rtl');
        }
      }
      // Reload must not trigger a translation.
      cur = 'reload';
      await page.goto(BASE + `/social/posts/${IDS.pending}`, { waitUntil: 'domcontentloaded' }); await settle(page);
      await page.reload({ waitUntil: 'domcontentloaded' }); await settle(page);
      await ctx.close();
    }
  } finally { await close(); }

  const stats1 = (await api('social/translations/stats')).body;
  const histAfter = (await api(`social/posts/${IDS.pending}/translation`)).body.history.length;
  check('page loads and reloads changed no translation state', JSON.stringify({ ...stats0, worker_running: 0 }) === JSON.stringify({ ...stats1, worker_running: 0 }) && histAfter === histBefore, { stats0, stats1 });
  check('translation request on page load = 0 (no writes from the page)', writes.length === 0, writes.slice(0, 5));
  check('requests to Ollama/cloud AI from the browser = 0', aiRequests.length === 0, aiRequests.slice(0, 5));
  check('console errors = 0', consoleErrors.length === 0, consoleErrors.slice(0, 5));
  check('unexpected failed local requests = 0', failedLocal.length === 0, failedLocal.slice(0, 5));
  check('horizontal overflow = 0', overflow.length === 0, overflow.slice(0, 5));
  check('external requests attempted = 0', external.length === 0, external.slice(0, 5));

  const passed = results.filter((r) => r.pass).length;
  fs.writeFileSync(path.join(OUT, `${tag}report.json`), JSON.stringify({ base: BASE, offline: OFFLINE, results, consoleErrors, failedLocal, overflow, external, aiRequests, writes, shots }, null, 2));
  console.log(`\nX TRANSLATION QA${OFFLINE ? ' (OLLAMA OFFLINE)' : ''}: ${passed}/${results.length} · SCREENSHOTS ${shots.length} · CONSOLE_ERRORS ${consoleErrors.length} · FAILED_LOCAL ${failedLocal.length} · OVERFLOW ${overflow.length} · AI_REQUESTS ${aiRequests.length} · PAGE_WRITES ${writes.length}`);
  process.exit(passed === results.length ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(2); });

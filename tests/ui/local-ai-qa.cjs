/**
 * Local-AI preview (127.0.0.1:3003) browser QA: model/feature states, disabled
 * assistant, saved extractive answer with clickable citations, bilingual news
 * with the local machine-translation label, hidden needs_review translation,
 * justified reading text, four viewports. Non-local requests are aborted and
 * counted separately (publisher images are expected and not failures).
 *
 *   SESSION_ID=<saved session> node tests/ui/local-ai-qa.cjs
 */
const fs = require('fs'), path = require('path');
const { launchEdge } = require('./edge-launcher.cjs');

const BASE = process.env.BASE_URL || 'http://127.0.0.1:3003';
const OUT = path.resolve(process.env.EVIDENCE_DIR || 'runtime/local-ai-evidence/phase5/ui');
const SESSION = process.env.SESSION_ID || '';
const GOOD_ITEM = '338aa434bd1cdd47ce8614537ed77fc1e0bc7d740cccac0f974255e5ceb5d5d8';
const REVIEW_ITEM = 'c1544afcdfa71ea7304820dbcac8f95ebc049ab6bd14bfc60f4993f09197d8b3';
const VIEWPORTS = [['desktop-1920', 1920, 1080], ['laptop-1440', 1440, 900], ['tablet-820', 820, 1180], ['mobile-390', 390, 844]];
const results = [], consoleErrors = [], failedLocal = [], overflow = [], aiRequests = [], shots = [];
const check = (name, pass, detail) => { results.push({ name, pass: !!pass, detail: detail ?? null }); console.log((pass ? 'PASS ' : 'FAIL ') + name + (pass ? '' : ' — ' + JSON.stringify(detail ?? '').slice(0, 200))); };
const local = (u) => ['127.0.0.1', 'localhost'].includes(new URL(u).hostname);
const settle = async (p) => { await p.waitForLoadState('networkidle', { timeout: 40000 }).catch(() => {}); await p.waitForTimeout(800); };

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const models = await (await fetch(BASE + '/api/v1/local-ai/models')).json();
  check('models endpoint: translation and assistant disabled (no approved artifact)', models.features.translation === false && models.features.assistant === false, models.features);
  check('models endpoint lists rejected/revoked/superseded states', ['rejected_quality_gate', 'revoked', 'superseded'].every((s) => models.models.some((m) => m.state === s)));

  const { browser, close } = await launchEdge();
  try {
    for (const [label, width, height] of VIEWPORTS) {
      const ctx = await browser.newContext({ viewport: { width, height }, locale: 'fa-IR', isMobile: width < 500 });
      await ctx.route('**/*', (r) => {
        const u = r.request().url();
        if (new URL(u).port === '11434' || /openrouter|openai|anthropic|googleapis/.test(u)) aiRequests.push(u.slice(0, 100));
        return local(u) || r.request().resourceType() === 'image' ? r.continue() : r.abort();
      });
      const page = await ctx.newPage(); let cur = '';
      page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push({ label, route: cur, text: m.text().slice(0, 160) }); });
      page.on('pageerror', (e) => consoleErrors.push({ label, route: cur, text: 'pageerror ' + e.message }));
      page.on('response', (r) => { if (local(r.url()) && r.status() >= 400) failedLocal.push({ label, route: cur, url: new URL(r.url()).pathname, status: r.status() }); });
      page.on('requestfailed', (r) => { if (local(r.url()) && !(r.failure()?.errorText || '').includes('ERR_ABORTED')) failedLocal.push({ label, route: cur, url: new URL(r.url()).pathname }); });
      if (SESSION) await page.addInitScript((sid) => { try { localStorage.setItem('dm.assistant.session', sid); } catch {} }, SESSION);

      for (const route of ['/assistant', `/news/${GOOD_ITEM}`, `/news/${REVIEW_ITEM}`, '/news', '/']) {
        cur = route;
        await page.goto(BASE + route, { waitUntil: 'domcontentloaded' }); await settle(page);
        const ov = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        if (ov > 1) overflow.push({ label, route, ov });
        const file = `${label}_${route === '/' ? 'home' : route.slice(1).replace(/\//g, '_').slice(0, 40)}.png`;
        if (label === 'laptop-1440' || label === 'mobile-390') { await page.screenshot({ path: path.join(OUT, file), fullPage: true }); shots.push(file); }
        if (label !== 'laptop-1440' && !(label === 'mobile-390' && route === '/assistant')) continue;

        if (route === '/assistant') {
          const body = await page.evaluate(() => document.body.innerText);
          check(`[${label}] assistant disabled notice shown`, await page.locator('[data-testid=as-disabled]').count() === 1);
          check(`[${label}] input disabled while no approved model`, await page.locator('#as-q').isDisabled());
          check(`[${label}] model status panel with Persian states`, await page.locator('[data-testid=as-models]').count() === 1 && body.includes('ردشده در آزمون کیفیت') && body.includes('تأیید لغو شد'));
          check(`[${label}] feature line: translation and assistant disabled`, body.includes('ترجمه: غیرفعال') && body.includes('دستیار: غیرفعال'));
          const chips = await page.evaluate(() => [...document.querySelectorAll('button.btn-ghost')].map((b) => b.innerText.trim()).filter((t) => t.endsWith('؟') || t.startsWith('اخبار مرتبط')));
          check(`[${label}] suggestion chips are v1.3 in-contract questions`, chips.length >= 4 && chips.some((t) => t.includes('F/A-XX')) &&
            !chips.some((t) => /مهم‌ترین|آینده|چرا|۲۴ ساعت/.test(t)), chips);
          if (SESSION) {
            const links = page.locator('.as-msg-assistant .as-evidence-title');
            const n = await links.count();
            check(`[${label}] saved extractive answer restored with citation links`, n >= 1, n);
            const answerText = await page.locator('.as-answer').first().innerText().catch(() => '');
            check(`[${label}] saved answer quotes original text (no machine translation)`, answerText.includes('بدون ترجمه'));
            const ta = await page.evaluate(() => { const e = document.querySelector('.as-answer'); const s = e && getComputedStyle(e); return s ? [s.textAlign, s.textAlignLast] : null; });
            check(`[${label}] assistant answer is justified`, ta && ta[0] === 'justify' && ['start', 'right', 'auto'].includes(ta[1]), ta);
            if (label === 'laptop-1440' && n >= 1) {
              const href = await links.first().getAttribute('href');
              await links.first().click(); await settle(page);
              check('citation link navigates to the internal news record', page.url().includes(href) && href.startsWith('/news/'), href);
              cur = route; await page.goto(BASE + '/assistant', { waitUntil: 'domcontentloaded' }); await settle(page);
            }
          }
          const btn = await page.evaluate(() => getComputedStyle(document.querySelector('.as-input-actions button')).textAlign);
          check(`[${label}] buttons are not justified`, btn !== 'justify', btn);
        }
        if (route === `/news/${GOOD_ITEM}`) {
          const body = await page.evaluate(() => document.body.innerText);
          check('bilingual view: Persian translation and original side by side', await page.locator('.bilingual .lang-col').count() === 2);
          check('label «ترجمه ماشینی محلی» shown with provider', body.includes('ترجمه ماشینی محلی') && body.includes('ollama/local'));
          const sum = await page.evaluate(() => { const e = document.querySelector('.bilingual .lang-col .s'); const s = e && getComputedStyle(e); return s ? [s.textAlign, s.direction] : null; });
          check('Persian summary justified and RTL', sum && sum[0] === 'justify' && sum[1] === 'rtl', sum);
          const orig = await page.evaluate(() => { const e = document.querySelectorAll('.bilingual .lang-col')[1]; return e ? getComputedStyle(e).direction : null; });
          check('original column LTR', orig === 'ltr', orig);
          const h = await page.evaluate(() => getComputedStyle(document.querySelector('h1')).textAlign);
          check('headline not justified', h !== 'justify', h);
        }
        if (route === `/news/${REVIEW_ITEM}`) {
          const body = await page.evaluate(() => document.body.innerText);
          check('needs_review translation hidden (known-bad machine translation not shown)', !body.includes('بنت نامزد') && body.includes('کنترل کیفیت'));
        }
      }
      await ctx.close();
    }
  } finally { await close(); }
  check('console errors = 0', consoleErrors.length === 0, consoleErrors.slice(0, 4));
  check('unexpected failed local requests = 0', failedLocal.length === 0, failedLocal.slice(0, 4));
  check('horizontal overflow = 0', overflow.length === 0, overflow.slice(0, 4));
  check('requests to Ollama/cloud AI from the browser = 0', aiRequests.length === 0, aiRequests.slice(0, 3));
  const passed = results.filter((r) => r.pass).length;
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify({ results, consoleErrors, failedLocal, overflow, aiRequests, shots }, null, 2));
  console.log(`\nLOCAL AI UI QA: ${passed}/${results.length} · SCREENSHOTS ${shots.length} · CONSOLE ${consoleErrors.length} · FAILED_LOCAL ${failedLocal.length} · OVERFLOW ${overflow.length} · AI_REQUESTS ${aiRequests.length}`);
  process.exit(passed === results.length ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(2); });

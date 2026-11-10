/**
 * Final acceptance browser QA of the 3003 Local-AI lab (real Edge, real data).
 * Fixtures (real item ids + the exact rejected Persian texts) are read from
 * runtime/final-acceptance/ui-fixtures.json, extracted read-only from the DB.
 *
 *   node tests/ui/final-acceptance-qa.cjs
 */
const fs = require('fs'), path = require('path');
const { launchEdge } = require('./edge-launcher.cjs');

const BASE = process.env.BASE_URL || 'http://127.0.0.1:3003';
const OUT = path.resolve('runtime/final-acceptance/ui');
const F = JSON.parse(fs.readFileSync(path.resolve('runtime/final-acceptance/ui-fixtures.json'), 'utf8'));
const LABEL = 'ترجمه خودکار ـ تأیید انسانی نشده';
const VIEWPORTS = [['desktop-1440', 1440, 900], ['mobile-390', 390, 844]];
const results = [], consoleErrors = [], failedLocal = [];
const check = (name, pass, detail) => { results.push({ name, pass: !!pass, detail: detail ?? null }); console.log((pass ? 'PASS ' : 'FAIL ') + name + (pass ? '' : ' — ' + JSON.stringify(detail ?? '').slice(0, 220))); };
const local = (u) => ['127.0.0.1', 'localhost'].includes(new URL(u).hostname);
const settle = async (p) => { await p.waitForLoadState('networkidle', { timeout: 40000 }).catch(() => {}); await p.waitForTimeout(700); };

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const { browser, close } = await launchEdge();
  try {
    for (const [label, width, height] of VIEWPORTS) {
      const ctx = await browser.newContext({ viewport: { width, height }, locale: 'fa-IR', isMobile: width < 500 });
      await ctx.route('**/*', (r) => local(r.request().url()) || r.request().resourceType() === 'image' ? r.continue() : r.abort());
      const page = await ctx.newPage(); let cur = '';
      page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push({ label, route: cur, text: m.text().slice(0, 200) }); });
      page.on('response', (r) => { if (local(r.url()) && r.status() >= 500) failedLocal.push({ label, route: cur, url: r.url().slice(0, 120), status: r.status() }); });
      const go = async (route, lang) => {
        cur = route;
        if (lang) await page.addInitScript((l) => { try { localStorage.setItem('im.contentLang', JSON.stringify(l)); } catch {} }, lang);
        await page.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 60000 }); await settle(page);
      };
      const toggle = async (name) => {   // on mobile the language toggle lives in the side drawer
        const radio = page.getByRole('radio', { name }).first();
        if (!(await radio.isVisible().catch(() => false))) await page.getByRole('button', { name: 'باز کردن منو' }).click();
        await page.getByRole('radio', { name }).first().click();
      };
      const shot = async (n) => page.screenshot({ path: path.join(OUT, `${label}-${n}.png`), fullPage: false });
      const overflow = async () => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

      // Home
      await go('/', 'fa');
      check(`${label} home: RTL Persian document`, await page.evaluate(() => document.documentElement.dir === 'rtl' && document.documentElement.lang.startsWith('fa')));
      check(`${label} home: news cards rendered`, (await page.locator('article').count()) >= 5, await page.locator('article').count());
      check(`${label} home: no horizontal overflow`, (await overflow()) <= 1, await overflow()); await shot('home');

      // News list, search, filter
      await go('/news?q=Rheinmetall', 'en');
      const titles = await page.locator('article h3').allInnerTexts();
      // the search matches title OR summary: every card must contain the term in its visible text, and some in the title
      // the search matches title OR full summary (cards truncate the summary, more on mobile): verify every
      // result on the data the page renders, and that some visible titles match
      const api = await (await fetch(BASE + '/api/v1/feed?q=Rheinmetall&page_size=50')).json();
      const rows = api.items || api.results || [];
      const nonMatching = rows.filter((r) => !/rheinmetall/i.test(`${r.title} ${r.summary || ''}`)).map((r) => r.item_id.slice(0, 12));
      check(`${label} search q=Rheinmetall: every result contains the term, cards rendered`, rows.length > 0 && nonMatching.length === 0
        && titles.length > 0 && titles.some((t) => /rheinmetall/i.test(t)), { results: rows.length, nonMatching, cards: titles.length });
      await go('/news?translation=available', 'fa');
      const cards = page.locator('article');
      const n = await cards.count();
      const tags = await page.locator('article').evaluateAll((els, L) => els.map((e) => e.innerText.includes(L)), LABEL);
      check(`${label} filter translation=available: every card carries the "${LABEL}" label`, n > 0 && tags.every(Boolean), { n, tags });
      check(`${label} news list: no horizontal overflow`, (await overflow()) <= 1, await overflow()); await shot('news-filter');

      // Detail: QC-passed item, Persian mode
      await go(`/news/${F.auto}`, 'fa');
      const h1 = page.locator('h1.detail-title');
      check(`${label} detail(translated_auto) fa: Persian title leads (RTL)`, (await h1.getAttribute('dir')) === 'rtl' && (await h1.innerText()).trim() === F.auto_title.trim(), await h1.innerText());
      check(`${label} detail(translated_auto): label "${LABEL}" visible`, await page.getByText(LABEL).first().isVisible());
      check(`${label} detail(translated_auto): English original present`, (await page.locator('.lang-col[lang="en"] .t').innerText()).length > 10); await shot('detail-auto-fa');

      // Detail: QC-failed item (the E2E item) — rejected text must never appear
      await go(`/news/${F.fail}`, 'fa');
      const html = await page.content();
      check(`${label} detail(qc_failed) fa: English title leads`, (await page.locator('h1.detail-title').getAttribute('dir')) === 'ltr' && (await page.locator('h1.detail-title').innerText()).startsWith(F.fail_title_en.slice(0, 20)));
      check(`${label} detail(qc_failed): rejection explained`, html.includes('خطای بحرانی'));
      check(`${label} detail(qc_failed): no rejected Persian text anywhere in the page`, F.fail_texts.every((t) => !html.includes(t.slice(0, 30))), F.fail_texts.map((t) => t.slice(0, 30)));
      await shot('detail-failed-fa');

      // Detail: QC-warning item — hidden in fa, shown with a warning in bilingual mode
      await go(`/news/${F.warn}`, 'fa');
      check(`${label} detail(qc_warning) fa: original title leads`, (await page.locator('h1.detail-title').getAttribute('dir')) === 'ltr');
      check(`${label} detail(qc_warning): warning text shown next to original`, (await page.content()).includes('هشدار کنترل کیفیت'));

      // Bilingual mode via the real toggle
      await go('/news', 'fa');
      await toggle('دوزبانه'); await settle(page);
      check(`${label} toggle "دوزبانه": stored and Persian lines under originals`, (await page.evaluate(() => localStorage.getItem('im.contentLang'))) === '"bi"'
        && (await page.locator('.card-fa').count()) > 0, await page.locator('.card-fa').count());
      await shot('news-bilingual');
      await go('/news'); await toggle('EN'); await settle(page);
      check(`${label} toggle "EN": no Persian lines`, (await page.locator('.card-fa').count()) === 0);

      // Assistant (desktop only: one real model call)
      if (width >= 1000) {
        await go('/assistant', 'fa');
        check(`${label} assistant: experimental label visible`, await page.getByText('آزمایشی ـ پاسخ مبتنی بر منابع خبری موجود').first().isVisible());
        await page.locator('#as-q').fill('درباره موشک AGM-158C و B-52 چه گزارش شده است؟');
        await page.getByRole('button', { name: 'ارسال' }).click();
        await page.locator('.as-evidence-title').first().waitFor({ timeout: 600000 }).catch(() => {});
        const hrefs = await page.locator('.as-evidence-title').evaluateAll((els) => els.map((e) => e.getAttribute('href')));
        check(`${label} assistant: answer cites the real E2E record`, hrefs.includes(`/news/${F.fail}`), hrefs);
        await shot('assistant-answer');
        await page.locator('#as-q').fill('درباره سقوط F-35 در آلاسکا چه گزارش شده است؟');
        await page.getByRole('button', { name: 'ارسال' }).click();
        await page.getByText('در اخبار موجود، شواهد کافی و قابل اتکایی برای پاسخ به این پرسش یافت نشد.').last().waitFor({ timeout: 600000 }).catch(() => {});
        check(`${label} assistant: unsupported question refused with the exact sentence`,
          (await page.getByText('در اخبار موجود، شواهد کافی و قابل اتکایی برای پاسخ به این پرسش یافت نشد.').count()) >= 1);
      }

      // Admin panel
      await go('/admin', 'fa');
      const adminHtml = await page.content();
      const missing = ['دریافت و همگام‌سازی اخبار', 'صف و کیفیت ترجمه', 'دستیار و مدل‌های فعال', 'خوشه‌بندی و موضوع‌ها', 'هشدارهای عملیاتی', 'TranslateGemma 27B']
        .filter((t) => !adminHtml.includes(t));
      check(`${label} admin: real sections rendered`, missing.length === 0, missing);
      check(`${label} admin: no horizontal overflow`, (await overflow()) <= 1, await overflow()); await shot('admin');
      await ctx.close();
    }
  } finally { await close(); }
  check('no console errors', consoleErrors.length === 0, consoleErrors.slice(0, 5));
  check('no failed (5xx) local requests', failedLocal.length === 0, failedLocal.slice(0, 5));
  fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify({ at: new Date().toISOString(), results, consoleErrors, failedLocal }, null, 1));
  const failed = results.filter((r) => !r.pass).length;
  console.log(`\n${results.length - failed}/${results.length} passed`);
  process.exit(failed ? 1 : 0);
})();

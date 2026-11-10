/**
 * Multi-turn Persian conversation with the 3003 assistant in a real browser, while the
 * translator runs: waiting state shown, answers with clickable citations to real records,
 * a follow-up in the SAME session, an honest refusal, and API latency sampled during generation.
 *   LABEL=before node tests/ui/assistant-conversation-qa.cjs
 */
const fs = require('fs'), path = require('path');
const { launchEdge } = require('./edge-launcher.cjs');
const BASE = process.env.BASE_URL || 'http://127.0.0.1:3003';
const LABEL = process.env.LABEL || 'run';
const REFUSAL = 'در اخبار موجود، شواهد کافی و قابل اتکایی برای پاسخ به این پرسش یافت نشد.';
const TURNS = [
  { q: 'درباره موشک AGM-158C و B-52 چه گزارش شده است؟', expect: 'answer' },
  { q: 'کدام منابع درباره قرارداد F/A-XX بوئینگ گزارش داده‌اند؟', expect: 'answer' },
  { q: 'درباره سقوط F-35 در آلاسکا چه گزارش شده است؟', expect: 'refusal' },
];
const results = [];
const check = (name, pass, detail) => { results.push({ name, pass: !!pass, detail: detail ?? null }); console.log((pass ? 'PASS ' : 'FAIL ') + name + (detail !== undefined ? ' — ' + JSON.stringify(detail).slice(0, 240) : '')); };

async function sampleApi(stopRef) {
  const t = [];
  while (!stopRef.stop) {
    const s = performance.now();
    try { const r = await fetch(`${BASE}/api/v1/feed?page_size=30`); await r.arrayBuffer(); t.push(performance.now() - s); } catch { t.push(99999); }
    await new Promise((r) => setTimeout(r, 1000));
  }
  return t;
}

(async () => {
  const { browser, close } = await launchEdge();
  const consoleErrors = [];
  const timings = [];
  try {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'fa-IR' });
    const page = await ctx.newPage();
    page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 200)); });
    await page.goto(BASE + '/assistant', { waitUntil: 'load' });
    await page.waitForLoadState('networkidle').catch(() => {});
    for (const [i, t] of TURNS.entries()) {
      const before = await page.locator('.as-msg-assistant').count();
      await page.locator('#as-q').fill(t.q);
      const stopRef = { stop: false };
      const sampler = sampleApi(stopRef);
      const s = Date.now();
      await page.getByRole('button', { name: 'ارسال' }).click();
      // waiting state visible while the request is processed
      let sawWaiting = false;
      for (let k = 0; k < 20 && !sawWaiting; k++) {
        sawWaiting = await page.getByText(/در صف پردازش محلی|در حال جست‌وجو|مدل محلی مشغول است|در حال تولید پاسخ/).first().isVisible().catch(() => false);
        if (!sawWaiting) await page.waitForTimeout(250);
      }
      for (let k = 0; k < 3600 && (await page.locator('.as-msg-assistant').count()) <= before; k++) await page.waitForTimeout(250);   // CSP forbids eval-based waits
      const secs = Math.round((Date.now() - s) / 1000);
      stopRef.stop = true;
      const api = await sampler;
      const sorted = [...api].sort((a, b) => a - b);
      timings.push({ turn: i + 1, answer_seconds: secs, api_samples: api.length, api_median_ms: Math.round(sorted[Math.floor(sorted.length / 2)] || 0),
                     api_max_ms: Math.round(sorted[sorted.length - 1] || 0) });
      const msg = page.locator('.as-msg-assistant').last();
      const text = await msg.innerText();
      const hrefs = await msg.locator('.as-evidence-title').evaluateAll((els) => els.map((e) => e.getAttribute('href'))).catch(() => []);
      check(`turn ${i + 1}: waiting state shown`, sawWaiting);
      if (t.expect === 'answer') {
        check(`turn ${i + 1}: answer with real citations`, !text.includes(REFUSAL) && hrefs.length > 0 && hrefs.every((h) => /^\/news\/[0-9a-f]{20,}$/.test(h)), { secs, hrefs });
      } else {
        check(`turn ${i + 1}: no-evidence question refused honestly (no citations)`, text.includes(REFUSAL) && hrefs.length === 0, { secs, text: text.slice(0, 120) });
      }
    }
    check('same session: all turns kept in one conversation', (await page.locator('.as-msg-assistant').count()) >= TURNS.length, await page.locator('.as-msg-assistant').count());
    // citation click opens the original record
    const first = page.locator('.as-evidence-title').first();
    const href = await first.getAttribute('href');
    await first.click();
    await page.waitForURL('**' + href, { timeout: 30000 });
    await page.locator('h1.detail-title').waitFor({ timeout: 30000 }).catch(() => {});
    check('citation click opens the cited news page', page.url().endsWith(href) && (await page.locator('h1.detail-title').count()) === 1, page.url());
  } finally { await close(); }
  check('no console errors', consoleErrors.length === 0, consoleErrors.slice(0, 3));
  const out = { label: LABEL, at: new Date().toISOString(), results, timings };
  fs.writeFileSync(path.resolve(`runtime/final-acceptance/assistant-conversation-${LABEL}.json`), JSON.stringify(out, null, 1));
  console.log(JSON.stringify(timings));
  process.exit(results.every((r) => r.pass) ? 0 : 1);
})();

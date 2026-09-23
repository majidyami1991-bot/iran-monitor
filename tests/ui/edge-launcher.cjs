/**
 * Launches Edge headless with a CDP port and connects Playwright over CDP.
 *
 * The installed playwright-core (1.52.0) launches Edge via --remote-debugging-pipe
 * by default, and that named-pipe handshake fails against this machine's Edge
 * build (153.0.4234.48): the process starts but Playwright reports the target
 * closed immediately. A CDP port, launched and verified independently, works.
 */
const { spawn } = require('child_process');
const fs = require('fs'), os = require('os'), path = require('path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'C:/Temp/iran-monitor-playwright-20260914T/node_modules/playwright');

const EDGE = process.env.EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';

async function launchEdge() {
  const port = 9222 + Math.floor(Math.random() * 500);
  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'edge-cdp-'));
  const child = spawn(EDGE, [
    '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars', '--mute-audio',
    `--remote-debugging-port=${port}`, `--user-data-dir=${userDataDir}`,
  ], { stdio: 'ignore', detached: false });

  const endpoint = `http://127.0.0.1:${port}`;
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(endpoint + '/json/version');
      if (r.ok) break;
    } catch { /* not ready yet */ }
    await new Promise(r => setTimeout(r, 200));
  }
  const browser = await chromium.connectOverCDP(endpoint);
  return {
    browser,
    async close() {
      await browser.close().catch(() => {});
      child.kill('SIGKILL');
      // Windows keeps the profile directory locked briefly after the process
      // dies; retry rather than let a cleanup failure fail the whole run.
      for (let attempt = 0; attempt < 5; attempt++) {
        try { fs.rmSync(userDataDir, { recursive: true, force: true }); return; }
        catch { await new Promise(r => setTimeout(r, 400)); }
      }
    },
  };
}

module.exports = { launchEdge };

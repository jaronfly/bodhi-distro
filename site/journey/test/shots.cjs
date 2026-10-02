// Journey layer screenshots and checks.
//   NODE_PATH=$(npm root -g) node site/journey/test/shots.cjs [--quick]
// Serves site/ with python3 -m http.server, opens journey/demo.html in headless
// Chromium (SwiftShader WebGL), scrolls through every scene at two sizes,
// saves screenshots to site/journey/test/shots/, and checks:
//   no console errors · html.journey-on · BodhiJourney.scene matches the scroll
//   reduced motion renders still frames (two frames 1 s apart are identical)
// It also samples frame times with requestAnimationFrame.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const http = require('http');

const JOURNEY = path.resolve(__dirname, '..');
const ROOT = process.env.SITE_ROOT || path.resolve(JOURNEY, '..');
const OUT = path.join(__dirname, 'shots');
const PORT = 8000 + Math.floor(Math.random() * 900);
const QUICK = process.argv.includes('--quick');
const ONLY = (process.argv.find((a) => a.startsWith('--only=')) || '').slice(7);
const SCENES = ['soil', 'roots', 'cell', 'to-be', 'tree', 'sky', 'ancestors', 'questions', 'receipts', 'workbench', 'plant', 'access'];
const POINTS = QUICK ? [0.5] : [0.15, 0.5, 0.85];
const SIZES = [[1440, 900], [390, 844]];
// Optional: ancestry data when the page's assets are not next to this folder.
const ANCESTRY = process.env.ANCESTRY || '';
// PAGE=index.html runs the same checks against the real page when it is served next to journey/.
const PAGE = process.env.PAGE || 'journey/demo.html';
const TAG = process.env.PAGE ? 'page-' : '';

const results = [];
const fail = [];
const log = (s) => { console.log(s); results.push(s); };

function waitForServer(url, tries = 50) {
  return new Promise((res, rej) => {
    const go = (n) => http.get(url, (r) => { r.resume(); res(); }).on('error', () => (n ? setTimeout(() => go(n - 1), 100) : rej(new Error('server did not start'))));
    go(tries);
  });
}

async function openPage(browser, w, h, opts = {}) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1, ignoreHTTPSErrors: true, reducedMotion: opts.reduced ? 'reduce' : 'no-preference' });
  const page = await ctx.newPage();
  const errors = [];
  // On the real page the browser's generic "Failed to load resource" line carries no URL, so those are
  // judged by response instead: Google Fonts (can flake behind a proxy) and the empty jf.svg slot are expected.
  const expected = /fonts\.(googleapis|gstatic)\.com|assets\/marks\/jf\.svg/;
  page.on('console', (m) => { if (m.type() === 'error' && !(process.env.PAGE && /Failed to load resource/.test(m.text()))) errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));
  if (process.env.PAGE) {
    page.on('response', (r) => { if (r.status() >= 400 && !expected.test(r.url())) errors.push(`${r.status()} ${r.url()}`); });
    page.on('requestfailed', (r) => { if (!expected.test(r.url())) errors.push(`failed ${r.url()}`); });
  }
  await page.route('**/assets/data/ancestry.js', async (route) => {
    const local = path.join(ROOT, 'assets/data/ancestry.js');
    const file = fs.existsSync(local) ? local : ANCESTRY && fs.existsSync(ANCESTRY) ? ANCESTRY : null;
    await route.fulfill({ status: 200, contentType: 'text/javascript', body: file ? fs.readFileSync(file, 'utf8') : '/* no ancestry data */' });
  });
  if (opts.reduced) await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(`http://127.0.0.1:${PORT}/${PAGE}?journey=force&jdpr=1`, { waitUntil: 'load' });
  await page.waitForFunction(() => document.documentElement.classList.contains('journey-on'), null, { timeout: 120000 });
  return { ctx, page, errors };
}

async function scrollTo(page, id, p) {
  return page.evaluate(([id, p]) => {
    const el = document.getElementById(id);
    const top = el.getBoundingClientRect().top + scrollY;
    const y = Math.max(0, top + el.offsetHeight * p - innerHeight * 0.5);
    window.scrollTo({ top: y, behavior: 'instant' }); // the real page sets scroll-behavior: smooth
    return y;
  }, [id, p]);
}
// wait until the layer has rendered n more frames (or the still frame is in place)
const settle = (page, n = 2) => page.evaluate((n) => new Promise((res) => {
  const j = window.BodhiJourney;
  if (j.snap) j.snap();
  if (j.still) { setTimeout(res, 300); return; }
  const f0 = j.frames; const t0 = performance.now();
  (function wait() { if ((j.frames - f0 >= n && Math.abs(j.renderedC - j.c) < 0.01) || performance.now() - t0 > 90000) res(); else requestAnimationFrame(wait); })();
}), n);

async function frameTimes(page, ms = 2500) {
  return page.evaluate((ms) => new Promise((res) => {
    const d = []; let last = 0; const t0 = performance.now();
    (function tick(t) { if (last) d.push(t - last); last = t; if (t - t0 < ms) requestAnimationFrame(tick); else res(d); })(performance.now());
  }), ms);
}
const stats = (d) => { const s = d.slice().sort((a, b) => a - b); const q = (x) => s[Math.min(s.length - 1, Math.floor(x * s.length))]; return { n: s.length, median: q(0.5), p90: q(0.9) }; };

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1', '--directory', ROOT], { stdio: 'ignore' });
  let browser;
  try {
    await waitForServer(`http://127.0.0.1:${PORT}/${PAGE}`);
    browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
    for (const [w, h] of SIZES) {
      const { ctx, page, errors } = await openPage(browser, w, h);
      log(`[${w}x${h}] journey-on set`);
      let i = 0;
      for (const id of SCENES) {
        if (ONLY && !ONLY.split(',').includes(id)) continue;
        for (const p of POINTS) {
          await scrollTo(page, id, p);
          await settle(page);
          const got = await page.evaluate(() => window.BodhiJourney.scene);
          const name = `${TAG}${w}x${h}-${String(i).padStart(2, '0')}-${id}-${Math.round(p * 100)}.png`;
          await page.screenshot({ path: path.join(OUT, name), timeout: 180000 });
          i++;
          if (got !== id) { fail.push(`[${w}x${h}] scene at ${id}@${p} was ${got}`); log(`FAIL ${name}: BodhiJourney.scene = ${got}`); }
          else log(`ok   ${name}: BodhiJourney.scene = ${got}`);
        }
      }
      for (const id of ['soil', 'tree', 'sky']) {
        await scrollTo(page, id, 0.5); await settle(page);
        const s = stats(await frameTimes(page));
        const q = await page.evaluate(() => ({ dpr: window.BodhiJourney.dpr }));
        log(`[${w}x${h}] frame time at ${id}: median ${s.median.toFixed(1)} ms, p90 ${s.p90.toFixed(1)} ms over ${s.n} frames (dpr ${q.dpr})`);
      }
      if (errors.length) { fail.push(`[${w}x${h}] console errors: ${errors.join(' | ')}`); log(`FAIL console errors: ${errors.length}\n  ${errors.join('\n  ')}`); }
      else log(`[${w}x${h}] no console errors`);
      await ctx.close();
    }
    // Reduced motion: still frames only.
    {
      const { ctx, page, errors } = await openPage(browser, 1440, 900, { reduced: true });
      for (const id of ['tree', 'sky', 'cell']) {
        await scrollTo(page, id, 0.5);
        await page.waitForTimeout(1500);
        const a = await page.screenshot({ timeout: 180000 });
        const f0 = await page.evaluate(() => window.BodhiJourney.frames);
        await page.waitForTimeout(1000);
        const b = await page.screenshot({ timeout: 180000 });
        const f1 = await page.evaluate(() => window.BodhiJourney.frames);
        const j = await page.evaluate(() => ({ still: window.BodhiJourney.still, scene: window.BodhiJourney.scene }));
        fs.writeFileSync(path.join(OUT, `${TAG}reduced-${id}.png`), a);
        const same = a.equals(b) && f0 === f1;
        if (!same || !j.still || j.scene !== id) fail.push(`reduced motion at ${id}: identical=${a.equals(b)} frames ${f0}->${f1} still=${j.still} scene=${j.scene}`);
        log(`${same && j.still ? 'ok  ' : 'FAIL'} reduced motion at ${id}: frames 1 s apart identical=${a.equals(b)}, render count ${f0} -> ${f1}, still=${j.still}, scene=${j.scene}`);
      }
      // the Motion switch (data-motion="off") behaves the same with motion allowed by the OS
      await page.emulateMedia({ reducedMotion: 'no-preference' });
      await page.waitForTimeout(500);
      const moving = await page.evaluate(() => new Promise((r) => { const f = window.BodhiJourney.frames; setTimeout(() => r(window.BodhiJourney.frames - f), 1500); }));
      await page.click('[data-motion-toggle]');
      await page.waitForTimeout(800);
      const f0 = await page.evaluate(() => window.BodhiJourney.frames);
      await page.waitForTimeout(1000);
      const f1 = await page.evaluate(() => window.BodhiJourney.frames);
      const ok = moving > 0 && f0 === f1;
      if (!ok) fail.push(`motion switch: frames while on ${moving}, while off ${f0}->${f1}`);
      log(`${ok ? 'ok  ' : 'FAIL'} motion switch: ${moving} frames in 1.5 s with motion on; ${f0} -> ${f1} with data-motion="off"`);
      if (errors.length) { fail.push(`reduced: console errors: ${errors.join(' | ')}`); log(`FAIL console errors (reduced): ${errors.join(' | ')}`); }
      else log('[reduced] no console errors');
      await ctx.close();
    }
  } catch (e) {
    fail.push(String(e && e.stack || e));
    console.error(e);
  } finally {
    if (browser) await browser.close();
    server.kill();
  }
  log(fail.length ? `\n${fail.length} FAILED:\n- ${fail.join('\n- ')}` : '\nALL CHECKS PASSED');
  fs.writeFileSync(path.join(OUT, `${TAG}results.txt`), results.join('\n') + '\n');
  process.exit(fail.length ? 1 : 0);
})();

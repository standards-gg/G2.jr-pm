// Demo 1 · G2 × ExpressVPN (projects/expressvpn/): layout, accessibility, navigation, the ways in from the main deck,
// back links, CSP and the no-JavaScript fallback.
const assert = require('assert');
const fs = require('fs');
const launch = require('./browser');
const { start } = require('./server');

const SLIDES = 10;
const VIEWPORTS = [[320, 568], [375, 667], [414, 896], [768, 1024], [1024, 768], [1280, 720], [1366, 768], [1440, 900], [1536, 864], [1920, 1080], [2560, 1080]];
const mustFit = (w, h) => w >= 1440 && h >= 860;
let pass = 0, fail = 0;
async function t(name, fn) { try { await fn(); pass++; console.log('  ✓ ' + name); } catch (e) { fail++; console.log('  ✗ ' + name + ' — ' + e.message.split('\n')[0]); } }

module.exports = async function run() {
  const server = await start();
  const ROOT = `http://127.0.0.1:${server.address().port}/`;
  const BASE = ROOT + 'projects/expressvpn/';
  const b = await launch();

  await t(`layout: ${SLIDES} slides × ${VIEWPORTS.length} viewports × DE + EN, nothing clipped or too wide`, async () => {
    const problems = [];
    for (const lang of ['de', 'en']) for (const [w, h] of VIEWPORTS) {
      const p = await b.newPage({ viewport: { width: w, height: h }, reducedMotion: 'reduce' });
      for (let n = 1; n <= SLIDES; n++) {
        await p.goto(`${BASE}?lang=${lang}#${n}`);
        await p.waitForTimeout(350);
        const r = await p.evaluate(() => {
          const s = document.querySelector('.slide.active');
          const sr = s.getBoundingClientRect(), ir = s.querySelector('.inner').getBoundingClientRect();
          return { clipped: ir.top < sr.top - 1, wide: Math.max(s.scrollWidth - s.clientWidth, document.documentElement.scrollWidth - innerWidth), tall: s.scrollHeight - s.clientHeight };
        });
        if (r.clipped) problems.push(`[${lang}] ${w}×${h} slide ${n}: top unreachable`);
        if (r.wide > 0) problems.push(`[${lang}] ${w}×${h} slide ${n}: ${r.wide}px too wide`);
        if (r.tall > 1 && mustFit(w, h)) problems.push(`[${lang}] ${w}×${h} slide ${n}: ${r.tall}px too tall`);
      }
      await p.close();
    }
    if (problems.length) throw new Error(problems.slice(0, 8).join(' | ') + (problems.length > 8 ? ` … +${problems.length - 8}` : ''));
  });

  await t('axe: no accessibility violations on any slide (DE + EN)', async () => {
    const axeSource = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
    const p = await b.newPage({ viewport: { width: 1440, height: 900 }, bypassCSP: true, reducedMotion: 'reduce' });
    const problems = [];
    for (const lang of ['de', 'en']) for (let n = 1; n <= SLIDES; n++) {
      await p.goto(`${BASE}?lang=${lang}#${n}`); await p.waitForTimeout(600);
      await p.addScriptTag({ content: axeSource });
      const v = await p.evaluate(async () => (await axe.run(document, { resultTypes: ['violations'] })).violations
        .map(x => `${x.id} (${x.impact}): ${x.nodes[0].target.join(' ')}`));
      v.forEach(x => problems.push(`[${lang}] slide ${n}: ${x}`));
    }
    await p.close();
    if (problems.length) throw new Error(problems.slice(0, 6).join(' | '));
  });

  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, timezoneId: 'America/New_York' });
  const p = await ctx.newPage(); const errors = [];
  p.on('pageerror', e => errors.push('pageerror: ' + e.message));
  p.on('console', m => { if (m.type() === 'error' || /Content Security Policy/.test(m.text())) errors.push(m.text()); });
  const counter = () => p.$eval('#counter', e => e.textContent);
  const settle = () => p.waitForTimeout(250);

  await t('"Demo 1" in the first-slide Demos menu, on the last CV slide and the first slide-11 card open ExpressVPN', async () => {
    await p.goto(ROOT + 'index.html?lang=en#1'); await p.waitForTimeout(400);
    await p.click('.slide.active .demo-menu .menu-btn');
    assert.match(await p.locator('.slide.active .demo-menu a[href="projects/expressvpn/"]').innerText(), /ExpressVPN$/);
    await p.keyboard.press('Escape');
    for (const n of [10]) {
      await p.goto(ROOT + 'index.html?lang=en#' + n); await p.waitForTimeout(400);
      assert.match(await p.locator('.slide.active a[href="projects/expressvpn/"]').innerText(), /^Demo 1\s*→?$/);
    }
    await p.goto(ROOT + 'index.html?lang=en#11'); await p.waitForTimeout(500);
    const cards = await p.$$eval('.slide.active a.project-card', as => as.map(a => a.getAttribute('href')));
    assert.deepEqual(cards, ['projects/expressvpn/', 'projects/akg/', 'projects/beyerdynamic/']);
    await Promise.all([p.waitForURL(/projects\/expressvpn\/$/), p.click('.slide.active a.project-card[href="projects/expressvpn/"]')]);
    await p.waitForTimeout(400);
    assert.equal(await counter(), `1 / ${SLIDES}`);
  });
  await t('keys, Start button and hash navigate; ends clamp', async () => {
    await p.click('.start-btn'); await settle(); assert.equal(await counter(), `2 / ${SLIDES}`);
    await p.keyboard.press('End'); await settle(); assert.equal(await counter(), `${SLIDES} / ${SLIDES}`);
    await p.keyboard.press('ArrowRight'); await settle(); assert.equal(await counter(), `${SLIDES} / ${SLIDES}`);
    await p.keyboard.press('Home'); await settle(); assert.equal(await counter(), `1 / ${SLIDES}`);
    await p.goto(BASE + '#6'); await p.waitForTimeout(400); assert.equal(await counter(), `6 / ${SLIDES}`);
  });
  await t('back links lead to the bonus slide and the CV', async () => {
    const hrefs = await p.$$eval('.crumb', as => as.map(a => new URL(a.href).pathname + new URL(a.href).hash));
    assert.deepEqual(hrefs, ['/#11', '/#1']);
  });
  await t('no console errors or CSP violations on any slide', async () => {
    for (let n = 1; n <= SLIDES; n++) { await p.goto(BASE + '#' + n); await p.waitForTimeout(200); }
    assert.deepEqual(errors, []);
  });
  await ctx.close();

  const nj = await b.newContext({ viewport: { width: 1280, height: 800 }, javaScriptEnabled: false });
  const np = await nj.newPage(); await np.goto(BASE); await np.waitForTimeout(400);
  await t('without JavaScript every slide is visible', async () => {
    const vis = await np.$$eval('.slide', s => s.filter(x => getComputedStyle(x).visibility === 'visible' && getComputedStyle(x).opacity === '1').length);
    assert.equal(vis, SLIDES);
  });
  await nj.close();

  await b.close(); server.close();
  return { pass, fail };
};

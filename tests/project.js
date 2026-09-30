// Bonus project (projects/beyerdynamic/): layout, accessibility and behaviour of the web presentation,
// plus the way in from the main deck's Bonus: Example Project slide.
const assert = require('assert');
const fs = require('fs');
const launch = require('./browser');
const { start } = require('./server');

const SLIDES = 5;
const VIEWPORTS = [[320, 568], [375, 667], [414, 896], [768, 1024], [1024, 768], [1280, 720], [1366, 768], [1440, 900], [1536, 864], [1920, 1080], [2560, 1080]];
const mustFit = (w, h) => w >= 1440 && h >= 860;
let pass = 0, fail = 0;
async function t(name, fn) { try { await fn(); pass++; console.log('  ✓ ' + name); } catch (e) { fail++; console.log('  ✗ ' + name + ' — ' + e.message.split('\n')[0]); } }

module.exports = async function run() {
  const server = await start();
  const ROOT = `http://127.0.0.1:${server.address().port}/`;
  const BASE = ROOT + 'projects/beyerdynamic/';
  const b = await launch();

  await t(`layout: ${SLIDES} slides × ${VIEWPORTS.length} viewports × DE + EN, nothing clipped or too wide`, async () => {
    const problems = [];
    for (const lang of ['de', 'en']) for (const [w, h] of VIEWPORTS) {
      const p = await b.newPage({ viewport: { width: w, height: h } });
      for (let n = 1; n <= SLIDES; n++) {
        await p.goto(`${BASE}?lang=${lang}#${n}`);
        await p.waitForTimeout(450);
        const r = await p.evaluate(() => {
          const s = document.querySelector('.slide.active');
          const sr = s.getBoundingClientRect(), ir = s.querySelector('.inner').getBoundingClientRect();
          const crumbs = [...document.querySelectorAll('.crumb')].map(c => c.getBoundingClientRect().right);
          return {
            clipped: ir.top < sr.top - 1, wide: Math.max(s.scrollWidth - s.clientWidth, document.documentElement.scrollWidth - innerWidth), tall: s.scrollHeight - s.clientHeight,
            hud: Math.max(...crumbs) > document.querySelector('.hud .nav').getBoundingClientRect().left,
          };
        });
        if (r.hud && n === 1) problems.push(`[${lang}] ${w}×${h}: bottom bar links overlap the slide controls`);
        if (r.clipped) problems.push(`[${lang}] ${w}×${h} slide ${n}: top unreachable`);
        if (r.wide > 0) problems.push(`[${lang}] ${w}×${h} slide ${n}: ${r.wide}px too wide`);
        if (r.tall > 1 && mustFit(w, h)) problems.push(`[${lang}] ${w}×${h} slide ${n}: ${r.tall}px too tall`);
      }
      await p.close();
    }
    if (problems.length) throw new Error(problems.join(' | '));
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
    if (problems.length) throw new Error(problems.join(' | '));
  });

  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, timezoneId: 'America/New_York' });
  const p = await ctx.newPage(); const errors = [];
  p.on('pageerror', e => errors.push('pageerror: ' + e.message));
  p.on('console', m => { if (m.type() === 'error' || /Content Security Policy/.test(m.text())) errors.push(m.text()); });
  const counter = () => p.$eval('#counter', e => e.textContent);
  const settle = () => p.waitForTimeout(250);

  await t('the first-slide Demos menu and the last CV slide link to Demo 3 (beyerdynamic)', async () => {
    await p.goto(ROOT + 'index.html?lang=en#1'); await p.waitForTimeout(400);
    await p.click('.slide.active .demo-menu .menu-btn');
    assert.match(await p.locator('.slide.active .demo-menu a[href="projects/beyerdynamic/"]').innerText(), /beyerdynamic$/);
    await p.keyboard.press('Escape');
    for (const n of [10]) {
      await p.goto(ROOT + 'index.html?lang=en#' + n); await p.waitForTimeout(500);
      const link = p.locator('.slide.active a.chip[href="projects/beyerdynamic/"]');
      assert.match(await link.innerText(), /^Demo 3\s*→?$/);
      assert.equal(await link.getAttribute('href'), 'projects/beyerdynamic/');
    }
    await p.evaluate(() => localStorage.clear());
  });
  await t('Bonus: Example Project slide: card opens the project', async () => {
    await p.goto(ROOT + 'index.html#11'); await p.waitForTimeout(600);
    assert.ok(await p.isVisible('.slide.active a.project-card'));
    await Promise.all([p.waitForURL(/projects\/beyerdynamic\/$/), p.click('.slide.active a.project-card[href="projects/beyerdynamic/"]')]);
    await p.waitForTimeout(400);
    assert.equal(await counter(), `1 / ${SLIDES}`);
  });
  await t('keys, Start button, dots and hash navigate; ends clamp', async () => {
    await p.click('.start-btn'); await settle(); assert.equal(await counter(), `2 / ${SLIDES}`);
    await p.keyboard.press('ArrowRight'); await settle(); assert.equal(await counter(), `3 / ${SLIDES}`);
    await p.keyboard.press('ArrowLeft'); await settle(); assert.equal(await counter(), `2 / ${SLIDES}`);
    await p.keyboard.press('End'); await settle(); assert.equal(await counter(), `${SLIDES} / ${SLIDES}`);
    await p.keyboard.press('ArrowRight'); await settle(); assert.equal(await counter(), `${SLIDES} / ${SLIDES}`, 'clamps at end');
    assert.ok(await p.$eval('#next', b => b.disabled));
    await p.keyboard.press('Home'); await settle(); assert.equal(await counter(), `1 / ${SLIDES}`);
    await p.click('#dots button:nth-child(5)'); await settle(); assert.equal(await counter(), `5 / ${SLIDES}`);
    assert.equal(new URL(p.url()).hash, '#5');
    await p.goto(BASE + '#999'); await p.waitForTimeout(400); assert.equal(await counter(), `${SLIDES} / ${SLIDES}`);
  });
  await t('Venn diagram: each area shows its own detail', async () => {
    await p.goto(BASE + '#4'); await p.waitForTimeout(600);
    const visible = () => p.$$eval('.venn-detail', ds => ds.filter(d => getComputedStyle(d).display !== 'none').map(d => d.dataset.for));
    assert.deepEqual(await visible(), ['overlap']);
    await p.click('.k-beyer'); await settle();
    assert.deepEqual(await visible(), ['beyer']);
    assert.equal(await p.$eval('.k-beyer', b => b.getAttribute('aria-pressed')), 'true');
    await p.click('.slide.active .tab-btn[data-tab="map"]'); await settle();
    assert.ok(!(await p.isVisible('.venn-detail[data-for="beyer"]')), 'venn details hide with their tab');
    assert.equal(await p.$$eval('.slide.active .map tbody tr', r => r.length), 5);
    await p.keyboard.press('ArrowRight'); await settle(); assert.equal(await counter(), `5 / ${SLIDES}`, 'arrows still change slides');
  });
  await t('architecture flow: selecting a step shows its detail', async () => {
    await p.goto(BASE + '#5'); await p.waitForTimeout(600);
    await p.click('.slide.active .tab-btn[data-tab="met"]'); await settle();
    await p.focus('.flow-step[data-step="7"]'); await p.keyboard.press('Enter'); await settle();
    const shown = await p.$$eval('.flow-detail', ds => ds.filter(d => getComputedStyle(d).display !== 'none').map(d => d.dataset.for));
    assert.deepEqual(shown, ['7']);
    assert.equal(await counter(), `5 / ${SLIDES}`, 'Enter on a step does not change the slide');
  });
  await t('back links lead to the Bonus: Example Project slide and the CV', async () => {
    const hrefs = await p.$$eval('.crumb', as => as.map(a => a.href));
    assert.deepEqual(hrefs.map(h => new URL(h).pathname + new URL(h).hash), ['/#11', '/#1']);
    await p.click('.crumb >> nth=0'); await p.waitForTimeout(600);
    assert.equal(await counter(), '11 / 11');
  });
  await t('language: English outside DACH, switch to German is shared with the main deck', async () => {
    await p.goto(BASE); await p.waitForTimeout(400);
    assert.equal(await p.evaluate(() => document.documentElement.lang), 'en');
    await p.click('[data-set-lang="de"]'); await settle();
    assert.ok(await p.isVisible('.slide.active h1 + .role span[lang="de"]'));
    assert.equal(await p.title(), 'G2 × beyerdynamic · Partnerschaftsarchitektur');
    assert.equal(await p.$eval('#next', b => b.getAttribute('aria-label')), 'Nächste Folie');
    await p.goto(ROOT + 'index.html'); await p.waitForTimeout(400);
    assert.equal(await p.evaluate(() => document.documentElement.lang), 'de', 'choice carries over');
    await p.evaluate(() => localStorage.clear());
  });
  await t('no console errors or CSP violations', async () => { assert.deepEqual(errors, []); });
  await ctx.close();

  const m = await b.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  const mp = await m.newPage(); await mp.goto(BASE); await mp.waitForTimeout(500);
  await t('swipe changes slides on touch devices', async () => {
    const swipe = (x0, x1) => mp.evaluate(([x0, x1]) => {
      const mk = (type, x) => { const tt = new Touch({ identifier: 1, target: document.body, clientX: x, clientY: 400 });
        document.dispatchEvent(new TouchEvent(type, { touches: type === 'touchend' ? [] : [tt], changedTouches: [tt], bubbles: true })); };
      mk('touchstart', x0); mk('touchend', x1); }, [x0, x1]);
    await swipe(300, 100); await mp.waitForTimeout(200); assert.equal(await mp.$eval('#counter', e => e.textContent), `2 / ${SLIDES}`);
    await swipe(100, 300); await mp.waitForTimeout(200); assert.equal(await mp.$eval('#counter', e => e.textContent), `1 / ${SLIDES}`);
  });
  await m.close();

  const nj = await b.newContext({ viewport: { width: 1280, height: 800 }, javaScriptEnabled: false });
  const np = await nj.newPage(); await np.goto(BASE); await np.waitForTimeout(400);
  await t('without JavaScript every slide and every diagram detail is visible', async () => {
    const vis = await np.$$eval('.slide', s => s.filter(x => getComputedStyle(x).visibility === 'visible' && getComputedStyle(x).opacity === '1').length);
    assert.equal(vis, SLIDES);
    const hidden = await np.$$eval('.venn-detail, .flow-detail', ds => ds.filter(d => getComputedStyle(d).display === 'none').length);
    assert.equal(hidden, 0);
  });
  await nj.close();

  await b.close(); server.close();
  return { pass, fail };
};

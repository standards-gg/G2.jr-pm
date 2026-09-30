// AKG × G2 dashboard (projects/akg/): layout of every slide and tab, accessibility, tabs, charts, datasets,
// the numbers against the brief, and the ways in from the main deck ("Demo 2", slide 11 card).
const assert = require('assert');
const fs = require('fs');
const path = require('path');
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
  const BASE = ROOT + 'projects/akg/';
  const b = await launch();

  // every slide, every tab: nothing clipped or wider than the screen; from 1440×900 nothing taller than the screen
  await t(`layout: ${SLIDES} slides × all tabs × ${VIEWPORTS.length} viewports × DE + EN`, async () => {
    const problems = [];
    for (const lang of ['de', 'en']) for (const [w, h] of VIEWPORTS) {
      const p = await b.newPage({ viewport: { width: w, height: h }, reducedMotion: 'reduce' });
      for (let n = 1; n <= SLIDES; n++) {
        await p.goto(`${BASE}?lang=${lang}#${n}`);
        await p.waitForTimeout(350);
        const tabs = await p.$$eval('.slide.active .tab-btn', bs => bs.map(x => x.dataset.tab));
        for (const tab of tabs) {
          await p.click(`.slide.active .tab-btn[data-tab="${tab}"]`);
          await p.waitForTimeout(60);
          const r = await p.evaluate(() => {
            const s = document.querySelector('.slide.active');
            s.scrollTop = 0; // clicking a tab may have scrolled the slide
            const sr = s.getBoundingClientRect(), ir = s.querySelector('.inner').getBoundingClientRect();
            const crumbs = Math.max(...[...document.querySelectorAll('.crumb')].map(c => c.getBoundingClientRect().right));
            return { clipped: ir.top < sr.top - 1, wide: Math.max(s.scrollWidth - s.clientWidth, document.documentElement.scrollWidth - innerWidth),
              tall: s.scrollHeight - s.clientHeight, hud: crumbs > document.querySelector('.hud .nav').getBoundingClientRect().left };
          });
          const where = `[${lang}] ${w}×${h} slide ${n}/${tab}`;
          if (r.clipped) problems.push(`${where}: top unreachable`);
          if (r.wide > 0) problems.push(`${where}: ${r.wide}px too wide`);
          if (r.tall > 1 && mustFit(w, h)) problems.push(`${where}: ${r.tall}px too tall`);
          if (r.hud) problems.push(`${where}: bottom bar overlaps`);
        }
      }
      await p.close();
    }
    if (problems.length) throw new Error(problems.slice(0, 8).join(' | ') + (problems.length > 8 ? ` … +${problems.length - 8}` : ''));
  });

  await t('axe: no accessibility violations on any slide or tab (DE + EN)', async () => {
    const axeSource = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
    const p = await b.newPage({ viewport: { width: 1440, height: 900 }, bypassCSP: true, reducedMotion: 'reduce' });
    const problems = [];
    for (const lang of ['de', 'en']) for (let n = 1; n <= SLIDES; n++) {
      await p.goto(`${BASE}?lang=${lang}#${n}`); await p.waitForTimeout(500);
      await p.addScriptTag({ content: axeSource });
      const tabs = await p.$$eval('.slide.active .tab-btn', bs => bs.map(x => x.dataset.tab));
      for (const tab of tabs) {
        await p.click(`.slide.active .tab-btn[data-tab="${tab}"]`); await p.waitForTimeout(120);
        const v = await p.evaluate(async () => (await axe.run(document, { resultTypes: ['violations'] })).violations
          .map(x => `${x.id} (${x.impact}): ${x.nodes[0].target.join(' ')}`));
        v.forEach(x => problems.push(`[${lang}] ${n}/${tab}: ${x}`));
      }
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

  await t('"Demo 2" in the first-slide Demos menu, on the last CV slide and the slide-11 card open the dashboard', async () => {
    await p.goto(ROOT + 'index.html?lang=en#1'); await p.waitForTimeout(400);
    await p.click('.slide.active .demo-menu .menu-btn');
    assert.match(await p.locator('.slide.active .demo-menu a[href="projects/akg/"]').innerText(), /AKG$/);
    await p.keyboard.press('Escape');
    for (const n of [10]) {
      await p.goto(ROOT + 'index.html?lang=en#' + n); await p.waitForTimeout(400);
      const link = p.locator('.slide.active a[href="projects/akg/"]');
      assert.match(await link.innerText(), /^Demo 2\s*→?$/);
    }
        await p.goto(ROOT + 'index.html?lang=en#11'); await p.waitForTimeout(500);
    assert.equal(await p.locator('.slide.active a.project-card').count(), 3);
    await Promise.all([p.waitForURL(/projects\/akg\/$/), p.click('.slide.active a.project-card[href="projects/akg/"]')]);
    await p.waitForTimeout(400);
    assert.equal(await counter(), `1 / ${SLIDES}`);
    await p.evaluate(() => localStorage.clear());
  });
  await t('tabs: one panel at a time, pressed state follows, arrow keys still change slides', async () => {
    await p.goto(BASE + '?lang=en#4'); await p.waitForTimeout(500);
    const shown = () => p.$$eval('.slide.active .tab-panel', ps => ps.filter(x => getComputedStyle(x).display !== 'none').map(x => x.dataset.for));
    assert.deepEqual(await shown(), ['trk']);
    await p.click('.slide.active .tab-btn[data-tab="rsk"]'); await settle();
    assert.deepEqual(await shown(), ['rsk']);
    assert.equal(await p.$eval('.slide.active .tab-btn[data-tab="rsk"]', x => x.getAttribute('aria-pressed')), 'true');
    await p.keyboard.press('ArrowRight'); await settle();
    assert.equal(await counter(), `5 / ${SLIDES}`);
  });
  await t('tracker lists all 31 deliverables; weekly table has 8 weeks; risk table 6 risks', async () => {
    await p.goto(BASE + '?lang=en#4'); await p.waitForTimeout(400);
    assert.equal(await p.$$eval('.tracker tbody tr', r => r.length), 31);
    assert.equal(await p.$$eval('.risks tbody tr', r => r.length), 6);
    await p.goto(BASE + '?lang=en#3'); await p.waitForTimeout(400);
    assert.equal(await p.$$eval('.weekly tbody tr', r => r.length), 8);
  });
  await t('every chart loads in both languages', async () => {
    for (const lang of ['en', 'de']) {
      await p.goto(`${BASE}?lang=${lang}#1`); await p.waitForTimeout(300);
      const srcs = await p.$$eval(`.chart img[lang="${lang}"]`, is => is.map(i => i.getAttribute('src')));
      assert.ok(srcs.length >= 9, 'charts: ' + srcs.length);
      for (const s of srcs) {
        const res = await p.request.get(BASE + s);
        assert.equal(res.status(), 200, s);
        assert.match(res.headers()['content-type'], /svg/, s);
      }
    }
  });
  await t('datasets download and kpis.json matches the brief', async () => {
    await p.goto(BASE + '#5'); await p.waitForTimeout(300);
    const files = await p.$$eval('.files a', as => as.map(a => a.getAttribute('href')));
    assert.equal(files.length, 12);
    for (const f of files) assert.equal((await p.request.get(BASE + f)).status(), 200, f);
    const k = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'projects', 'akg', 'data', 'kpis.json'), 'utf8'));
    const eq = (a, b, name) => assert.equal(a, b, name);
    eq(k.assets, 31, 'assets'); eq(Math.round(k.impressions), 8400000, 'impressions'); eq(Math.round(k.views), 3100000, 'views');
    eq(Math.round(k.reach), 1700000, 'reach'); eq(Math.round(k.engagements), 412000, 'engagements'); eq(Math.round(k.clicks), 86000, 'clicks');
    eq(k.giveaway_entries, 18400, 'entries'); eq(Math.round(k.completion * 100), 62, 'completion'); eq(Math.round(k.watch_minutes), 1900000, 'watch');
    eq(k.meetings, 46, 'meetings'); eq(k.internal_tasks, 73, 'tasks'); eq(k.client_comms, 38, 'comms'); eq(k.revisions, 19, 'revisions');
    eq(k.approval_requests, 31, 'approvals'); eq(k.escalated, 2, 'escalated'); eq(k.dependencies, 14, 'deps'); eq(k.risks, 6, 'risks');
    eq(Math.round(k.on_time_rate * 100), 94, 'on time'); eq(Math.round(k.sla_rate * 100), 97, 'sla'); eq(Math.round(k.fr_rate * 100), 89, 'first round');
    eq(Math.round(k.action_rate * 100), 96, 'actions'); eq(Math.round(k.lift_eng * 100), 38, 'lift eng'); eq(Math.round(k.lift_clicks * 100), 41, 'lift clicks');
    eq(Math.round(k.lift_reach * 100), 22, 'lift reach'); eq(Math.round(k.lift_comp * 100), 27, 'lift completion');
    assert.match(k.note, /hypothetical/);
  });
  await t('back links lead to the bonus slide and the CV', async () => {
    await p.goto(BASE + '#5'); await p.waitForTimeout(300);
    const hrefs = await p.$$eval('.crumb', as => as.map(a => new URL(a.href).pathname + new URL(a.href).hash));
    assert.deepEqual(hrefs, ['/#11', '/#1']);
  });
  await t('language switch: German labels, title and charts', async () => {
    await p.goto(BASE + '?lang=en#1'); await p.waitForTimeout(300);
    await p.click('[data-set-lang="de"]'); await settle();
    assert.equal(await p.title(), 'AKG × G2 · Partnerschafts-Dashboard');
    assert.ok(await p.isVisible('.slide.active .dash-sub span[lang="de"]'));
    await p.goto(BASE + '#5'); await p.waitForTimeout(400);
    assert.ok(await p.isVisible('.slide.active .tab-btn[data-tab="evi"] span[lang="de"]'));
    assert.ok(await p.isVisible('.slide.active img[src="charts/format-rates-de.svg"]'));
    assert.ok(!(await p.isVisible('.slide.active img[src="charts/format-rates-en.svg"]')));
    await p.evaluate(() => localStorage.clear());
  });
  await t('no console errors or CSP violations', async () => { assert.deepEqual(errors, []); });
  await ctx.close();

  const m = await b.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  const mp = await m.newPage(); await mp.goto(BASE); await mp.waitForTimeout(500);
  await t('swipe changes slides; swiping inside a wide table does not', async () => {
    const swipe = (x0, x1, sel) => mp.evaluate(([x0, x1, sel]) => {
      const target = sel ? document.querySelector(sel) : document.body;
      const mk = (type, x) => { const tt = new Touch({ identifier: 1, target, clientX: x, clientY: 400 });
        target.dispatchEvent(new TouchEvent(type, { touches: type === 'touchend' ? [] : [tt], changedTouches: [tt], bubbles: true })); };
      mk('touchstart', x0); mk('touchend', x1); }, [x0, x1, sel]);
    await swipe(300, 100); await mp.waitForTimeout(200); assert.equal(await mp.$eval('#counter', e => e.textContent), `2 / ${SLIDES}`);
    await swipe(300, 100); await mp.waitForTimeout(200); assert.equal(await mp.$eval('#counter', e => e.textContent), `3 / ${SLIDES}`);
    await mp.click('.slide.active .tab-btn[data-tab="ops"]'); await mp.waitForTimeout(200);
    await swipe(300, 100, '.slide.active .weekly'); await mp.waitForTimeout(200);
    assert.equal(await mp.$eval('#counter', e => e.textContent), `3 / ${SLIDES}`, 'table swipe kept the slide');
  });
  await m.close();

  const nj = await b.newContext({ viewport: { width: 1280, height: 800 }, javaScriptEnabled: false });
  const np = await nj.newPage(); await np.goto(BASE); await np.waitForTimeout(400);
  await t('without JavaScript every slide and every tab panel is visible', async () => {
    const vis = await np.$$eval('.slide', s => s.filter(x => getComputedStyle(x).visibility === 'visible' && getComputedStyle(x).opacity === '1').length);
    assert.equal(vis, SLIDES);
    assert.equal(await np.$$eval('.tab-panel', ps => ps.filter(x => getComputedStyle(x).display === 'none').length), 0);
  });
  await nj.close();

  await b.close(); server.close();
  return { pass, fail };
};

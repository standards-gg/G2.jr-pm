// Behaviour tests: navigation, keyboard, overlays, touch, no-JS fallback and print.
const assert = require('assert');
const launch = require('./browser');
const { start } = require('./server');
let pass = 0, fail = 0;
async function t(name, fn) { try { await fn(); pass++; console.log('  ✓ ' + name); } catch (e) { fail++; console.log('  ✗ ' + name + ' — ' + e.message.split('\n')[0]); } }
module.exports = async function run() {
  const server = await start();
  const BASE = `http://127.0.0.1:${server.address().port}/index.html`;
  const b = await launch();
  // a visitor in Germany: time zone Europe/Berlin → German by default
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, timezoneId: 'Europe/Berlin' });
  const p = await ctx.newPage(); const problems = [];
  p.on('pageerror', e => problems.push('pageerror: ' + e.message));
  p.on('console', m => { if (m.type() === 'error' || /Content Security Policy/.test(m.text())) problems.push(m.text()); });
  const counter = () => p.$eval('#counter', e => e.textContent);
  const settle = () => p.waitForTimeout(250);

  await p.goto(BASE); await p.waitForTimeout(600);
  await t('starts on slide 1 without adding a hash', async () => { assert.equal(await counter(), '1 / 11'); assert.equal(new URL(p.url()).hash, ''); });
  await t('ArrowRight / ArrowLeft / End / Home navigate', async () => {
    await p.keyboard.press('ArrowRight'); await settle(); assert.equal(await counter(), '2 / 11');
    await p.keyboard.press('End'); await settle(); assert.equal(await counter(), '11 / 11');
    await p.keyboard.press('ArrowRight'); await settle(); assert.equal(await counter(), '11 / 11', 'clamps at end');
    await p.keyboard.press('Home'); await settle(); assert.equal(await counter(), '1 / 11');
    await p.keyboard.press('ArrowLeft'); await settle(); assert.equal(await counter(), '1 / 11', 'clamps at start');
  });
  await t('green dot jumps to the first slide, gold dot to the conclusion', async () => {
    await p.click('#last'); await settle(); assert.equal(await counter(), '10 / 11');
    await p.click('#first'); await settle(); assert.equal(await counter(), '1 / 11');
    assert.equal(await p.$eval('#first', b => b.getAttribute('aria-label')), 'Erste Folie');
    await p.evaluate(() => document.activeElement.blur());
  });
  await t('Space on the page advances, Shift+Space goes back', async () => {
    await p.keyboard.press('Space'); await settle(); assert.equal(await counter(), '2 / 11');
    await p.keyboard.press('Shift+Space'); await settle(); assert.equal(await counter(), '1 / 11');
  });
  await t('hash updates, back button and direct links work', async () => {
    await p.click('#next'); await settle(); assert.equal(new URL(p.url()).hash, '#2');
    await p.goto(BASE + '#7'); await p.waitForTimeout(500); assert.equal(await counter(), '7 / 11');
    await p.evaluate(() => { location.hash = '#9'; }); await settle(); assert.equal(await counter(), '9 / 11', 'hashchange');
    await p.goto(BASE + '#999'); await p.waitForTimeout(500); assert.equal(await counter(), '11 / 11', 'out of range clamps');
    await p.goto(BASE + '#abc'); await p.waitForTimeout(500); assert.equal(await counter(), '1 / 11', 'garbage hash');
  });
  await t('Enter on a focused link activates the link, not the deck', async () => {
    await p.goto(BASE + '#10'); await p.waitForTimeout(500);
    await p.evaluate(() => { const a = document.querySelector('.slide.active a[href^="mailto"]'); a.addEventListener('click', e => { e.preventDefault(); window.__hit = 1; }); a.focus(); });
    await p.keyboard.press('Enter'); await settle();
    assert.ok(await p.evaluate(() => window.__hit), 'link not activated'); assert.equal(await counter(), '10 / 11');
  });
  await t('Space on a focused dot activates that dot', async () => {
    await p.focus('#dots button:nth-child(3)'); await p.keyboard.press('Space'); await settle();
    assert.equal(await counter(), '3 / 11');
    assert.equal(await p.$eval('#dots button:nth-child(3)', d => d.getAttribute('aria-current')), 'step');
  });
  await t('focus follows to the new slide when the old one hides', async () => {
    await p.goto(BASE + '#10'); await p.waitForTimeout(500);
    await p.focus('.slide.active a[href^="mailto"]'); await p.keyboard.press('ArrowLeft'); await settle();
    assert.ok(await p.evaluate(() => document.activeElement.classList.contains('active')));
  });
  await t('screen-reader announcement and buttons state', async () => {
    await p.goto(BASE + '#3'); await p.waitForTimeout(500);
    assert.match(await p.$eval('#announcer', e => e.textContent), /Folie 3 von 11: Standards\.gg/);
    await p.goto(BASE + '#1'); await p.waitForTimeout(400); assert.ok(await p.$eval('#prev', b => b.disabled));
  });
  await t('HADALON preview on hover, lightbox on click, Esc closes, keys blocked while open', async () => {
    await p.goto(BASE + '#3'); await p.waitForTimeout(600);
    await p.hover('button[data-preview]'); await p.waitForTimeout(500);
    assert.ok(await p.$eval('#sitePreview', e => e.classList.contains('show') && e.classList.contains('tall')));
    const box = await p.$eval('#sitePreview', e => { const r = e.getBoundingClientRect(); return [r.top, r.bottom]; });
    assert.ok(box[0] >= 0 && box[1] <= 900, 'preview inside viewport ' + box);
    await p.click('button[data-preview]'); await settle();
    assert.ok(await p.$eval('#lightbox', d => d.open)); assert.ok(!(await p.$eval('#sitePreview', e => e.classList.contains('show'))));
    assert.ok(await p.$eval('#lightbox img', i => i.complete && i.naturalWidth > 0), 'lightbox image loaded');
    await p.keyboard.press('ArrowRight'); await settle(); assert.equal(await counter(), '3 / 11');
    await p.keyboard.press('Escape'); await settle(); assert.ok(!(await p.$eval('#lightbox', d => d.open)));
  });
  await t('link previews: keyboard focus shows, Escape and slide change hide', async () => {
    await p.focus('a[data-preview*="talents"]'); await p.waitForTimeout(400);
    assert.ok(await p.$eval('#sitePreview', e => e.classList.contains('show')));
    assert.ok(await p.$eval('#sitePreview img', i => i.naturalWidth > 0), 'screenshot loaded');
    await p.keyboard.press('Escape'); assert.ok(!(await p.$eval('#sitePreview', e => e.classList.contains('show'))));
    await p.focus('a[data-preview*="codex"]'); await p.waitForTimeout(200); await p.keyboard.press('ArrowRight'); await settle();
    assert.ok(!(await p.$eval('#sitePreview', e => e.classList.contains('show'))));
  });
  await t('Forever Atlas: hover plays a 3-image slideshow, click opens the frame on screen', async () => {
    await p.goto(BASE + '#3'); await p.waitForTimeout(600);
    const atlas = 'button[data-shot*="atlas-1"]';
    await p.hover(atlas); await p.waitForTimeout(400);
    assert.equal(await p.$eval('#sitePreview .bar b', e => e.textContent), '1 / 3');
    assert.match(await p.$eval('#sitePreview img', i => i.src), /atlas-1\.webp$/);
    await p.waitForTimeout(2700);
    assert.equal(await p.$eval('#sitePreview .bar b', e => e.textContent), '2 / 3');
    assert.match(await p.$eval('#sitePreview img', i => i.src), /atlas-2\.webp$/);
    assert.ok(await p.$eval('#sitePreview img', i => i.naturalWidth > 0 && !i.classList.contains('fading')), 'frame visible');
    await p.click(atlas); await settle();
    assert.match(await p.$eval('#lightbox img', i => i.src), /atlas-2\.webp$/);
    await p.keyboard.press('Escape'); await settle();
    await p.mouse.move(5, 5); await p.waitForTimeout(2600);
    assert.ok(!(await p.$eval('#sitePreview', e => e.classList.contains('show'))), 'slideshow stops when hidden');
  });
  await t('Smashion thumbnail opens lightbox, backdrop click closes', async () => {
    await p.goto(BASE + '#7'); await p.waitForTimeout(500);
    await p.click('.thumb'); await settle(); assert.ok(await p.$eval('#lightbox', d => d.open));
    await p.mouse.click(5, 5); await settle(); assert.ok(!(await p.$eval('#lightbox', d => d.open)));
  });
  await t('all images load (incl. avatars) and external links are safe', async () => {
    for (let n = 1; n <= 11; n++) { await p.goto(BASE + '#' + n); await p.waitForTimeout(150); }
    await p.waitForTimeout(500);
    const broken = await p.$$eval('.deck img', ims => ims.filter(i => !(i.complete && i.naturalWidth > 0)).map(i => i.src));
    assert.deepEqual(broken, []);
    const unsafe = await p.$$eval('a[target=_blank]', as => as.filter(a => !/noopener/.test(a.rel)).map(a => a.href));
    assert.deepEqual(unsafe, []);
  });
  await t('language: German for a DACH visitor, switch to English and back, remembered and shareable', async () => {
    await p.evaluate(() => localStorage.clear());
    await p.goto(BASE + '#2'); await p.waitForTimeout(500);
    assert.equal(await p.evaluate(() => document.documentElement.lang), 'de');
    assert.equal(await p.title(), 'Christian Balan · Bewerbung G2 Esports');
    assert.ok(await p.isVisible('.slide.active h2 span[lang="de"]'));
    assert.ok(!(await p.isVisible('.slide.active h2 span[lang="en"]')));
    assert.equal(await p.$eval('#next', b => b.getAttribute('aria-label')), 'Nächste Folie');
    await p.click('[data-set-lang="en"]'); await settle();
    assert.equal(await p.evaluate(() => document.documentElement.lang), 'en');
    assert.ok(await p.isVisible('.slide.active h2 span[lang="en"]'));
    assert.ok(!(await p.isVisible('.slide.active h2 span[lang="de"]')));
    assert.equal(await p.$eval('#next', b => b.getAttribute('aria-label')), 'Next slide');
    assert.equal(await p.$eval('#slideTitle', e => e.textContent), 'Profile');
    assert.match(await p.$eval('#announcer', e => e.textContent), /^Slide 2 of 11/);
    assert.equal(await p.$eval('[data-set-lang="en"]', b => b.getAttribute('aria-pressed')), 'true');
    assert.equal(new URL(p.url()).search, '?lang=en'); assert.equal(new URL(p.url()).hash, '#2');
    await p.click('#next'); await settle();
    assert.equal(new URL(p.url()).search + new URL(p.url()).hash, '?lang=en#3', 'slide change keeps ?lang');
    await p.goto(BASE); await p.waitForTimeout(400);
    assert.equal(await p.evaluate(() => document.documentElement.lang), 'en', 'choice remembered');
    await p.click('[data-set-lang="de"]'); await settle();
    assert.equal(await p.evaluate(() => document.documentElement.lang), 'de');
    assert.equal(new URL(p.url()).search, '?lang=de', 'explicit choice is shareable');
    await p.goto(BASE + '?lang=en'); await p.waitForTimeout(400);
    assert.equal(await p.evaluate(() => document.documentElement.lang), 'en', '?lang=en wins');
    await p.goto(BASE + '?lang=xx'); await p.waitForTimeout(400);
    assert.equal(await p.evaluate(() => document.documentElement.lang), 'de', 'unknown language falls back');
  });
  await t('language switch: joke tooltips on hover, keyboard operable', async () => {
    await p.goto(BASE + '#1'); await p.waitForTimeout(400);
    await p.hover('[data-set-lang="en"]'); await p.waitForTimeout(300);
    assert.equal(await p.$eval('[data-set-lang="en"] .tip', e => getComputedStyle(e).opacity), '1');
    assert.equal(await p.$eval('[data-set-lang="en"] .tip', e => e.textContent), 'Translate for QWERTY users');
    assert.equal(await p.$eval('[data-set-lang="de"] .tip', e => e.textContent), 'Übersetzen für QWERTZ-Nutzer');
    await p.focus('[data-set-lang="en"]'); await p.keyboard.press('Enter'); await settle();
    assert.equal(await p.evaluate(() => document.documentElement.lang), 'en');
    assert.equal(await p.$eval('#counter', e => e.textContent), '1 / 11', 'Enter switched language, not slide');
    await p.evaluate(() => localStorage.clear());
  });
  await t('CV: served as PDF, downloadable, viewer opens (or PDF opens directly) and closes', async () => {
    const res = await p.request.get(BASE.replace('index.html', 'assets/christian-balan-cv.pdf'));
    assert.equal(res.status(), 200); assert.equal(res.headers()['content-type'], 'application/pdf');
    await p.goto(BASE + '#1'); await p.waitForTimeout(500);
    const dl = await p.$$eval('a[download]', as => as.map(a => [a.getAttribute('href'), a.getAttribute('download')]));
    assert.ok(dl.length >= 1 && dl.every(([h, d]) => h === 'assets/christian-balan-cv.pdf' && d === 'Christian-Balan-CV.pdf'), JSON.stringify(dl));
    const inline = await p.evaluate(() => navigator.pdfViewerEnabled !== false && matchMedia('(min-width: 861px) and (hover: hover)').matches);
    if (inline) {
      await p.click('[data-cv-open]'); await settle();
      assert.ok(await p.$eval('#cvViewer', d => d.open), 'viewer open');
      assert.match(await p.$eval('#cvViewer iframe', f => f.src), /christian-balan-cv\.pdf$/);
      await p.keyboard.press('ArrowRight'); await settle(); assert.equal(await counter(), '1 / 11', 'keys blocked while open');
      await p.click('#cvViewer .cv-close'); await settle(); assert.ok(!(await p.$eval('#cvViewer', d => d.open)));
      await p.click('[data-cv-open]'); await settle(); await p.keyboard.press('Escape'); await settle();
      assert.ok(!(await p.$eval('#cvViewer', d => d.open)), 'Esc closes');
    } else {
      const [popup] = await Promise.all([p.context().waitForEvent('page'), p.click('[data-cv-open]')]);
      assert.match(popup.url(), /christian-balan-cv\.pdf$/); await popup.close();
      assert.ok(!(await p.$eval('#cvViewer', d => d.open)), 'no empty viewer without PDF support');
    }
  });
  await t('references: a menu of three PDFs, each opens in the viewer with its own name and download', async () => {
    await p.goto(BASE + '?lang=en#1'); await p.waitForTimeout(500);
    await p.click('.slide.active .ref-menu .menu-btn');
    assert.equal(await p.getAttribute('.slide.active .ref-menu .menu-btn', 'aria-expanded'), 'true');
    const refs = await p.$$eval('.slide.active a.ref-chip', as => as.map(a => [a.getAttribute('href'), a.innerText.trim()]));
    assert.deepEqual(refs.map(r => r[1]), ['Event', 'Partner', 'Ownership']);
    await p.keyboard.press('Escape');
    assert.equal(await p.getAttribute('.slide.active .ref-menu .menu-btn', 'aria-expanded'), 'false');
    for (const [href] of refs) {
      const res = await p.request.get(BASE.replace('index.html', href));
      assert.equal(res.status(), 200, href); assert.equal(res.headers()['content-type'], 'application/pdf');
    }
    const inline = await p.evaluate(() => navigator.pdfViewerEnabled !== false && matchMedia('(min-width: 861px) and (hover: hover)').matches);
    if (!inline) return;
    await p.click('.slide.active .ref-menu .menu-btn');
    await p.click('.slide.active a.ref-chip[href$="reference-po.pdf"]'); await settle();
    assert.match(await p.$eval('#cvViewer iframe', f => f.src), /reference-po\.pdf$/);
    assert.equal(await p.$eval('#cvViewer .cv-name', e => e.innerText.trim().toLowerCase()), 'reference · ownership');
    assert.equal(await p.$eval('#cvViewer .cv-download', a => a.getAttribute('download')), 'Christian-Balan-Reference-Ownership.pdf');
    await p.keyboard.press('Escape'); await settle();
    await p.click('.slide.active [data-cv-open]:not(.ref-chip)'); await settle();
    assert.match(await p.$eval('#cvViewer iframe', f => f.src), /christian-balan-cv\.pdf$/, 'CV again after a reference');
    assert.equal(await p.$eval('#cvViewer .cv-name', e => e.innerText.trim().toLowerCase()), 'cv');
    await p.keyboard.press('Escape'); await settle();
    await p.evaluate(() => localStorage.clear());
  });
  await t('no console errors or CSP violations during use', async () => { assert.deepEqual(problems, []); });

  // touch swipe
  const m = await b.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  const mp = await m.newPage(); await mp.goto(BASE); await mp.waitForTimeout(500);
  await t('swipe left/right changes slides on touch devices', async () => {
    const swipe = (x0, x1) => mp.evaluate(([x0, x1]) => {
      const mk = (type, x) => { const tt = new Touch({ identifier: 1, target: document.body, clientX: x, clientY: 400 });
        document.dispatchEvent(new TouchEvent(type, { touches: type === 'touchend' ? [] : [tt], changedTouches: [tt], bubbles: true })); };
      mk('touchstart', x0); mk('touchend', x1); }, [x0, x1]);
    await swipe(300, 100); await mp.waitForTimeout(200); assert.equal(await mp.$eval('#counter', e => e.textContent), '2 / 11');
    await swipe(100, 300); await mp.waitForTimeout(200); assert.equal(await mp.$eval('#counter', e => e.textContent), '1 / 11');
  });

  await t('language by location: English outside DACH, German in Germany, Austria and Switzerland', async () => {
    for (const [zone, want] of [['America/New_York', 'en'], ['Europe/London', 'en'], ['Europe/Paris', 'en'], ['Asia/Tokyo', 'en'],
      ['Europe/Berlin', 'de'], ['Europe/Vienna', 'de'], ['Europe/Zurich', 'de']]) {
      const c = await b.newContext({ viewport: { width: 1280, height: 800 }, timezoneId: zone });
      const gp = await c.newPage(); await gp.goto(BASE); await gp.waitForTimeout(300);
      assert.equal(await gp.evaluate(() => document.documentElement.lang), want, zone);
      assert.equal(await gp.$eval('#next', b => b.getAttribute('aria-label')), want === 'de' ? 'Nächste Folie' : 'Next slide', zone + ' attributes');
      if (zone === 'America/New_York') {
        await gp.goto(BASE + '?lang=de'); await gp.waitForTimeout(300);
        assert.equal(await gp.evaluate(() => document.documentElement.lang), 'de', 'a German link opens German anywhere');
      }
      await c.close();
    }
  });

  // no JavaScript
  const nj = await b.newContext({ viewport: { width: 1280, height: 800 }, javaScriptEnabled: false });
  const np = await nj.newPage(); await np.goto(BASE); await np.waitForTimeout(500);
  await t('without JavaScript every slide is visible and stacked', async () => {
    const vis = await np.$$eval('.slide', s => s.filter(x => getComputedStyle(x).visibility === 'visible' && getComputedStyle(x).opacity === '1').length);
    assert.equal(vis, 11);
    assert.ok(await np.isVisible('h1'), 'title visible');
    assert.ok(await np.isVisible('.slide h2 span[lang="en"]'), 'English without JavaScript');
    assert.ok(!(await np.isVisible('span[lang="de"]')), 'only English without JavaScript');
  });

  // print
  const pp = await ctx.newPage(); await pp.goto(BASE); await pp.waitForTimeout(800);
  await t('print / Save as PDF: 11 pages, nothing cut off', async () => {
    await pp.emulateMedia({ media: 'print' });
    const cut = await pp.$$eval('.slide', s => s.map((x, i) => [i + 1, x.scrollHeight - x.clientHeight]).filter(([, d]) => d > 1));
    assert.deepEqual(cut, [], 'slides overflowing a page');
    const pdf = await pp.pdf({ preferCSSPageSize: true, printBackground: true });
    const pages = (pdf.toString('latin1').match(/\/Type\s*\/Page[^s]/g) || []).length;
    assert.equal(pages, 11, 'pages=' + pages);
  });

  await b.close(); server.close();
  return { pass, fail };
};

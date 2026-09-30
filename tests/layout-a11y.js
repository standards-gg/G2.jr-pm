// Layout + accessibility checks for every slide at common screen sizes.
const fs = require('fs');
const launch = require('./browser');
const { start } = require('./server');

const VIEWPORTS = [[320, 568], [375, 667], [414, 896], [768, 1024], [1024, 768], [1280, 720], [1366, 768], [1440, 900], [1536, 864], [1920, 1080], [2560, 1080]];
// From 1440×900 / 1536×864 upwards every slide must fit without scrolling; smaller screens (incl. 1280×720, 1366×768)
// may scroll inside the dense merged slides, but content is never clipped or wider than the screen.
const mustFit = (w, h) => w >= 1440 && h >= 860;

module.exports = async function run() {
  const server = await start();
  const BASE = `http://127.0.0.1:${server.address().port}/index.html`;
  const b = await launch();
  const problems = [];

  for (const lang of ['de', 'en']) for (const [w, h] of VIEWPORTS) {
    const p = await b.newPage({ viewport: { width: w, height: h } });
    for (let n = 1; n <= 11; n++) {
      await p.goto(`${BASE}?lang=${lang}#${n}`);
      await p.waitForTimeout(500);
      const r = await p.evaluate(() => {
        const s = document.querySelector('.slide.active');
        const sr = s.getBoundingClientRect(), ir = s.querySelector('.inner').getBoundingClientRect();
        return {
          clipped: ir.top < sr.top - 1,
          wide: Math.max(s.scrollWidth - s.clientWidth, document.documentElement.scrollWidth - innerWidth),
          tall: s.scrollHeight - s.clientHeight,
        };
      });
      if (r.clipped) problems.push(`[${lang}] ${w}×${h} slide ${n}: top of content is unreachable`);
      if (r.wide > 0) problems.push(`[${lang}] ${w}×${h} slide ${n}: ${r.wide}px wider than the screen`);
      if (r.tall > 1 && mustFit(w, h)) problems.push(`[${lang}] ${w}×${h} slide ${n}: ${r.tall}px taller than the screen`);
    }
    await p.close();
  }

  // axe-core on each slide (bypassCSP only so the test can inject axe)
  const axeSource = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
  // reduced motion: the staggered reveal (up to ~0.9s) must not be half-faded while axe measures contrast
  const p = await b.newPage({ viewport: { width: 1440, height: 900 }, bypassCSP: true, reducedMotion: 'reduce' });
  for (const lang of ['de', 'en']) for (let n = 1; n <= 11; n++) {
    await p.goto(`${BASE}?lang=${lang}#${n}`);
    await p.waitForTimeout(700);
    await p.addScriptTag({ content: axeSource });
    const violations = await p.evaluate(async () => (await axe.run(document, { resultTypes: ['violations'] })).violations
      .map(v => `${v.id} (${v.impact}): ${v.nodes[0].target.join(' ')}`));
    violations.forEach(v => problems.push(`[${lang}] axe slide ${n}: ${v}`));
  }

  await b.close();
  server.close();
  problems.forEach(x => console.log('  ✗ ' + x));
  console.log(`  ${problems.length ? '✗' : '✓'} DE + EN: layout at ${VIEWPORTS.length} viewports × 11 slides, axe on 11 slides: ${problems.length} problem(s)`);
  return { pass: problems.length ? 0 : 1, fail: problems.length ? 1 : 0 };
};

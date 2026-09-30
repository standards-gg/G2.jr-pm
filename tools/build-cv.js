// `npm run build:cv`: renders cv/index.html to assets/christian-balan-cv.pdf (A4) with Chromium.
const path = require('path');
const { chromium } = require('playwright');
const { start } = require('../tests/server');

(async () => {
  const server = await start();
  const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
  try {
    const page = await browser.newPage();
    await page.goto(`http://127.0.0.1:${server.address().port}/cv/index.html`, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts.ready);
    const out = path.join(__dirname, '..', 'assets', 'christian-balan-cv.pdf');
    await page.pdf({ path: out, format: 'A4', printBackground: true, preferCSSPageSize: true });
    console.log(`wrote ${path.relative(process.cwd(), out)}`);
  } finally {
    await browser.close();
    server.close();
  }
})();

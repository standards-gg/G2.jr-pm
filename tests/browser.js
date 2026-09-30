// Launch Chromium via Playwright. Set CHROMIUM_PATH to use a system browser instead of `npx playwright install chromium`.
const { chromium } = require('playwright');
module.exports = () => chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});

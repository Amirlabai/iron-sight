import { chromium } from 'playwright';

const url = process.argv[2] || 'http://localhost:5175/';
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
const logs = [];
page.on('console', (msg) => logs.push(`[${msg.type()}] ${msg.text()}`));
page.on('pageerror', (err) => logs.push(`[pageerror] ${err.message}\n${err.stack}`));
await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
await page.waitForTimeout(2000);
const root = await page.evaluate(() => ({
  childCount: document.getElementById('root')?.childElementCount ?? -1,
  html: document.getElementById('root')?.innerHTML?.slice(0, 300) ?? '',
}));
console.log('URL:', url);
console.log('root:', JSON.stringify(root, null, 2));
console.log('--- console ---');
logs.forEach((l) => console.log(l));
await browser.close();

// Render the painted backgrounds to PNG with Playwright, then convert to WebP:
//   python3 scripts/paint_backgrounds.py /tmp/art
//   node scripts/render_backgrounds.cjs /tmp/art
//   python3 -c "from PIL import Image; [Image.open(f'/tmp/art/{k}.png').convert('RGB').save(f'services/web/app/static/art/{k}.webp', quality=80) for k in ('sunrise','coast','highlands','evening')]"
const { chromium } = require("playwright");
const dir = process.argv[2];
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1800, height: 1200 } });
  for (const key of ["sunrise", "coast", "highlands", "evening"]) {
    await page.goto(`file://${dir}/${key}.svg`);
    await page.screenshot({ path: `${dir}/${key}.png` });
  }
  await browser.close();
})();

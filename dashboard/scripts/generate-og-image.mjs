import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.resolve(__dirname, '../public');
const source = path.join(publicDir, 'icon-512.png');
const dest = path.join(publicDir, 'og-image.png');
const faviconDest = path.join(publicDir, 'favicon.png');

async function main() {
  let sharp;
  try {
    sharp = (await import('sharp')).default;
  } catch {
    console.warn('sharp not installed; copying icon-512.png as og-image.png and favicon.png');
    fs.copyFileSync(source, dest);
    if (!fs.existsSync(faviconDest)) {
      fs.copyFileSync(source, faviconDest);
    }
    return;
  }

  await sharp(source)
    .resize(1200, 630, { fit: 'cover', position: 'centre' })
    .png({ compressionLevel: 9, palette: true, effort: 10, quality: 80 })
    .toFile(dest);

  const { size } = fs.statSync(dest);
  console.log('og-image.png size:', Math.round(size / 1024), 'KB');

  if (!fs.existsSync(faviconDest)) {
    await sharp(source).resize(32, 32).png().toFile(faviconDest);
  }

  console.log('Generated', dest);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

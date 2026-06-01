import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const spritesDir = path.resolve(__dirname, '../public/sprites');
const sourceDir = path.join(spritesDir, 'sprite files');

const EXPORTS = [
  { newt: 'rocket.newt', png: 'rocket.png' },
  { newt: 'drone.newt', png: 'drone.png' },
];

function hexToRgba(hex) {
  let h = String(hex).replace('#', '');
  if (h.length === 3) h = [...h].map((c) => c + c).join('');
  const n = Number.parseInt(h, 16);
  if (!Number.isFinite(n)) return [0, 0, 0, 0];
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255, 255];
}

function flattenNewt(doc) {
  const size = doc.size;
  const tokens = Object.fromEntries(doc.tokens.map((t) => [t.name, t.value]));
  const rgba = Buffer.alloc(size * size * 4, 0);
  const frame = doc.frames[0];
  for (const layer of frame.layers) {
    layer.cells.forEach((cell, i) => {
      if (!cell) return;
      const x = i % size;
      const y = Math.floor(i / size);
      const [r, g, b, a] = hexToRgba(tokens[cell] ?? '#000000');
      const o = (y * size + x) * 4;
      rgba[o] = r;
      rgba[o + 1] = g;
      rgba[o + 2] = b;
      rgba[o + 3] = a;
    });
  }
  return { size, rgba };
}

async function main() {
  let sharp;
  try {
    sharp = (await import('sharp')).default;
  } catch {
    console.warn('newt-to-png: sharp not installed; skipping sprite export');
    return;
  }

  for (const { newt, png } of EXPORTS) {
    const src = path.join(sourceDir, newt);
    const dest = path.join(spritesDir, png);
    if (!fs.existsSync(src)) {
      console.warn('newt-to-png: missing', src);
      continue;
    }
    const doc = JSON.parse(fs.readFileSync(src, 'utf8'));
    const { size, rgba } = flattenNewt(doc);
    await sharp(rgba, { raw: { width: size, height: size, channels: 4 } })
      .png({ compressionLevel: 9 })
      .toFile(dest);
    console.log('newt-to-png: wrote', dest);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

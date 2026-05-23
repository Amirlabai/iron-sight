import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.resolve(__dirname, '../public');
const dest = path.join(publicDir, 'sitemap.xml');

const DEFAULT_SITE_URL = 'https://iron-sight-drab.vercel.app';
const siteUrl = (process.env.VITE_SITE_URL || DEFAULT_SITE_URL).replace(/\/+$/, '');
const lastmod = new Date().toISOString().slice(0, 10);

const routes = [
  { loc: '/', changefreq: 'daily', priority: '1.0' },
  { loc: '/about', changefreq: 'monthly', priority: '0.8' },
  { loc: '/accessibility', changefreq: 'monthly', priority: '0.5' },
  { loc: '/privacy', changefreq: 'monthly', priority: '0.5' },
  { loc: '/terms', changefreq: 'monthly', priority: '0.5' },
];

const urls = routes
  .map(
    (route) => `  <url>
    <loc>${siteUrl}${route.loc === '/' ? '/' : route.loc}</loc>
    <lastmod>${lastmod}</lastmod>
    <changefreq>${route.changefreq}</changefreq>
    <priority>${route.priority}</priority>
  </url>`,
  )
  .join('\n');

const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;

fs.writeFileSync(dest, xml, 'utf8');
console.log('Generated', dest, 'for', siteUrl);

# Iron Sight → Tournament / SPA handoff

Full summary of SEO, legal pages, accessibility UI, and dashboard fixes on **iron-sight**, with steps you can reuse on a similar Vite + React project (e.g. ramadan-tournament or another marketing + app shell).

**Production URL:** `https://iron-sight-drab.vercel.app/`  
**Canonical env:** `VITE_SITE_URL` in Vercel / `dashboard/.env`

---

## 1. Executive summary

| Area | What we did |
|------|-------------|
| SEO | Per-route meta (English title/description), Hebrew **only** in `<meta name="keywords">`, JSON-LD, `sitemap.xml`, `og-image.png`, `llms.txt` |
| Routing | `react-router-dom`: `/`, `/about`, `/accessibility`, `/privacy`, `/terms`, 404 |
| Legal / compliance | English legal pages, cookie banner (analytics gated), IS 5568 accessibility statement + mailto report form |
| Build | Prerender **legal routes only** (not `/` map). Optional `PRERENDER=0` for fast CI builds |
| Black screen | Fixed react-helmet-async crash, prerender mismatch, Framer/reduced-motion traps |
| Legal UX | Single scrollbar, viewport-fixed high-contrast overlay, no splash when returning from legal pages in same session |
| Legal nav on map | Desktop: in-flow `SiteFooter` (compact). Mobile (≤1024px): footer hidden; legal links in header **Settings** cog menu (`HeaderSettingsControl`) |
| Map dev | Vite proxy for `/api` and `/ws`; do not point `VITE_WS_URL` at `:8080` in dev (CORS) |

**Language policy (iron-sight):**

- UI, legal copy, footer, cookies, FAQ body: **English only**
- Hebrew: **`keywords` meta only** (plus JSON-LD can stay `inLanguage: en`)

---

## 2. Repository map (dashboard)

```
dashboard/
  index.html              # Minimal shell; #a11y-viewport-overlay + #root
  vite.config.js          # Prerender on build; PWA; dev proxy
  scripts/
    generate-og-image.mjs
    generate-sitemap.mjs
  public/
    sitemap.xml           # Regenerated at build (also from script)
    robots.txt
    og-image.png
    llms.txt
  src/
    main.jsx              # HelmetProvider; imports a11y toolbar CSS globally
    App.jsx               # Routes; TacticalDashboard + splash; header Settings cog
    config/seoConfig.js   # Routes, keywords, JSON-LD helpers
    components/
      SEO.jsx             # Helmet — NO function components inside <Helmet>
      LegalPageLayout.jsx
      SiteFooter.jsx      # Full footer on legal pages; compact on desktop map only
      HeaderSettingsControl.jsx  # Cog: desktop → prefs wizard; mobile → menu + legal links
      HeaderSettingsControl.css
      CookieNotice.jsx
      AccessibilityToolbar.jsx  # Map vs legal (portal to #a11y-viewport-overlay)
    pages/                  # About, Accessibility, Privacy, Terms, NotFound
    prerender.jsx           # Legal stubs only (no `/` dashboard)
    utils/sessionBoot.js    # Skip splash on same-tab return to map
    styles/
      layout.css            # body overflow:hidden for map
    pages/LegalPage.css     # body scroll on legal routes
```

---

## 3. Step-by-step: replicate on another project

### Phase A — Dependencies and config

1. Install:

   ```bash
   npm install react-router-dom react-helmet-async
   npm install -D vite-prerender-plugin sharp
   ```

2. Add `VITE_SITE_URL` to `.env.example` (production canonical base, no trailing slash).

3. **`vite.config.js`**

   - Load `vite-prerender-plugin` **only** when `process.argv.includes('build')` (keeps `npm run dev` fast).
   - Prerender routes: **static pages only**, e.g. `['/about', '/accessibility', '/privacy', '/terms']`.
   - **Do not prerender `/`** if the live app is a different DOM (map, game, dashboard).

   ```js
   additionalPrerenderRoutes: ['/about', '/accessibility', '/privacy', '/terms'],
   // Skip prerender in CI when needed:
   // if (isBuild && process.env.PRERENDER !== '0') { ... }
   ```

4. **`package.json`**

   ```json
   "prebuild": "node scripts/generate-og-image.mjs && node scripts/generate-sitemap.mjs",
   "build": "vite build"
   ```

### Phase B — SEO core

5. Create `seoConfig.js`:

   - `getSiteUrl()` from `import.meta.env.VITE_SITE_URL`
   - Per-path title, description, `keywords` (EN + HE merged for keywords only)
   - Helpers: Organization, WebSite, WebApplication, FAQPage, BreadcrumbList JSON-LD

6. Create `SEO.jsx`:

   - One `<Helmet>` per page with title, description, keywords, canonical, OG, Twitter.
   - JSON-LD: **only native elements inside Helmet**:

   ```jsx
   {blocks.map((block, i) => (
     <script key={i} type="application/ld+json">
       {JSON.stringify(block)}
     </script>
   ))}
   ```

   **Never** wrap JSON-LD in a custom React component inside `<Helmet>` (react-helmet-async v3 throws; React never mounts → empty `#root` / black screen).

7. Trim `index.html`: charset, viewport, theme-color, fonts, favicon. Let Helmet own title/description on each route.

8. Generate `og-image.png` (1200×630) and `favicon.png`; link in Helmet + `index.html` apple-touch-icon.

9. `scripts/generate-sitemap.mjs`: emit URLs for all public routes; run in `prebuild`.

### Phase C — Routing and legal pages

10. Wrap app in `BrowserRouter` + `HelmetProvider` in `main.jsx`.

11. Add routes:

    - `/` → main app (wrapped in your data provider)
    - `/about`, `/accessibility`, `/privacy`, `/terms` → `LegalPageLayout` + page content
    - `*` → `NotFound` (noindex)

12. `LegalPageLayout.jsx`:

    - `<SEO pathname={...} breadcrumbs={...} />`
    - Skip link → `#legal-main`
    - Header link back to home
    - `<main id="legal-main">` {children} `</main>`
    - `<SiteFooter />`
    - `<AccessibilityToolbar legalPage />` (see Phase E)

13. Copy/adapt legal copy (English). Contact: name + email only if that is your policy.

### Phase D — Cookie banner and analytics

14. `useCookieConsent`: store `accepted` | `essential` | null in `localStorage`.

15. Show banner until choice. Gate `<Analytics />` (or any tracker) on `accepted === true`.

16. Focus trap + Escape on cookie dialog (shared `useFocusTrap` hook recommended).

### Phase E — Accessibility (IS 5568 baseline)

17. **Skip link** on map and legal pages (`#main-content` / `#legal-main`).

18. **High contrast**

    - `useHighContrast` → `data-high-contrast` on `<html>`
    - Map: fixed toolbar (existing `dashboard-a11y-toolbar` in `layout.css`)
    - Legal pages: **viewport overlay** (critical pattern below)

19. **`index.html`** — add before `#root`:

    ```html
    <div id="a11y-viewport-overlay" hidden></div>
    ```

20. **`AccessibilityToolbar.jsx`**

    - `import './AccessibilityToolbar.css'` (required — missing import caused toolbar at document footer)
    - Also import CSS from `main.jsx` so direct loads to `/accessibility` get styles
    - Legal: portal into `#a11y-viewport-overlay`; on mount remove `hidden` and set overlay `position:fixed; inset:0; z-index:10050; pointer-events:none`
    - Toolbar inside overlay: `position:absolute; bottom/left` + `pointer-events:auto`

21. **`LegalPage.css`** — one scroll container:

    ```css
    html:has(.legal-page-shell) { overflow: hidden; height: 100%; }
    body:has(.legal-page-shell) { overflow-y: auto; height: 100%; }
  #root:has(.legal-page-shell) { height: auto; min-height: 100dvh; overflow: visible; }
    ```

    Do **not** also set `overflow-y: auto` on `.legal-page-shell` (double scrollbars).

22. Accessibility statement at `/accessibility` with known limits (e.g. map not fully AT-accessible) and mailto report form.

### Phase F — Map / app shell (iron-sight specific)

23. `layout.css`: `body { overflow: hidden }` for full-viewport map.

24. Splash: show only until `history_sync` or 6s timeout; use `sessionBoot.js` to skip splash when user already booted once in the tab.

25. Mount header + map under splash (do not hide entire app behind `{isReady && ...}` only).

26. `animations.css`: do **not** use global `* { transition-duration: 0.01ms }` under `prefers-reduced-motion` (breaks Framer Motion opacity).

27. Dev networking (`constants.js`):

    ```js
    const RAW_HOST = IS_PROD
      ? (import.meta.env.VITE_WS_URL || window.location.host)
      : window.location.host;
    ```

    Vite proxy `/api` and `/ws` → backend `localhost:8080`.

28. **Header settings (map route)** — `HeaderSettingsControl` in `App.jsx` (`useMobileLayout`, breakpoint ≤1024px):

    | Viewport | Cog behavior |
    |----------|----------------|
    | Desktop (≥1025px) | Single click opens **Alert preferences** wizard (`openWizard` from `useAlertPreferences`). Same as former bell button. `aria-label`: “Alert notification preferences”. |
    | Mobile (≤1024px) | Click toggles dropdown `role="menu"`: **Alert preferences** + links to `/about`, `/accessibility`, `/privacy`, `/terms`. Escape or outside click closes. `aria-expanded` / `aria-haspopup="menu"`. |

    **Why:** `layout.css` hides `.dashboard-container .site-footer--compact` on mobile so the bottom sheet is unobstructed. Legal pages still use full `SiteFooter` via `LegalPageLayout`.

    **Active state:** `icon-btn-active` when alert scope ≠ `all` (scoped prefs), desktop and mobile.

    **Cookie banner:** Still links to `/privacy#cookies` on first visit; not a substitute for ongoing legal nav on mobile.

### Phase G — Build and deploy

29. Local:

    ```powershell
    cd dashboard
    npm run lint
    $env:PRERENDER='0'; npm run build   # fast, no headless prerender
    npm run build                      # full prerender for legal URLs
    npm run dev
    ```

30. Vercel: set `VITE_SITE_URL`, framework preset Vite, `vercel.json` API rewrites if needed.

31. After deploy — Search Console:

    - Add property, verify, submit `sitemap.xml`
    - Rich Results Test on `/` and `/about`
    - Social debuggers for `og-image.png`

---

## 4. Pitfall checklist (black screen and UI)

Use this when something looks “broken” or pitch black.

| Symptom | Likely cause | Fix |
|--------|----------------|-----|
| Empty `#root`, one script tag | JS error on load | DevTools Console first line |
| “nest Helmet” / Invariant | Function component inside `<Helmet>` | Inline `<script>` for JSON-LD only |
| Black after production build, OK in dev | Prerendered `/` HTML ≠ SPA | Remove `/` from prerender routes |
| Black + splash forever | `isReady` never true, WS down | Backend up; 6s fallback; check WS URL |
| Black but header visible, no map tiles | Carto CDN blocked | Network tab `basemaps.cartocdn.com` |
| Wizard/fullscreen dark overlay | Alert prefs wizard open | Header **Settings** cog → Alert preferences, or dismiss wizard |
| Mobile: no legal links on map | Footer hidden ≤1024px | Header cog menu → About / Accessibility / Privacy / Terms |
| Two scrollbars on legal pages | `body` + `.legal-page-shell` both scroll | Single scroll on `body` only |
| High contrast at footer, scrolls away | Overlay CSS not loaded | `import './AccessibilityToolbar.css'` + `main.jsx` import |
| High contrast not fixed on legal | Same as above | `#a11y-viewport-overlay` + portal + inline fixed styles |
| CORS in dev | `VITE_WS_URL=localhost:8080` on port 5173 | Dev uses `window.location.host` + proxy |
| `npm run build` hangs | `vite-prerender-plugin` headless Chrome | `PRERENDER=0` or prerender fewer routes |

### DevTools quick checks (browser console)

```javascript
document.getElementById('a11y-viewport-overlay')?.querySelector('.legal-a11y-toolbar')
document.querySelector('.splash-screen')
document.querySelector('.leaflet-tile')
getComputedStyle(document.getElementById('a11y-viewport-overlay')).position  // should be "fixed"
```

---

## 5. Verification checklist (before handoff to tournament team)

### Functional

- [ ] `/` loads map (or main app), not empty root
- [ ] Legal routes scroll with **one** scrollbar
- [ ] High contrast visible bottom-left on legal pages **while scrolling top/middle/bottom**
- [ ] High contrast on map still works
- [ ] Legal → map: no splash (same tab, after first boot)
- [ ] Cookie accept enables analytics only after accept
- [ ] Desktop map: compact footer links resolve (About, Accessibility, Privacy, Terms)
- [ ] Desktop map: header Settings cog opens alert preferences wizard only
- [ ] Mobile map: header Settings cog menu lists preferences + all four legal routes

### SEO

- [ ] View source / Elements: unique `<title>` per route
- [ ] `keywords` contains Hebrew on home; page copy English
- [ ] `/sitemap.xml` lists all public URLs
- [ ] `og-image.png` returns 200, 1200×630

### Build

- [ ] `npm run lint` (known legacy warnings OK if documented)
- [ ] `npm run build` completes
- [ ] `npm run preview` — spot-check `/`, `/accessibility`, `/privacy`

### Mobile

- [ ] Legal pages scroll on phone; full footer on legal routes
- [ ] Map (≤1024px): compact footer not shown; cog menu reaches legal pages
- [ ] Cog menu closes on outside tap and Escape
- [ ] Overlay button not hidden behind home indicator (safe-area)
- [ ] Map tested on LAN via `vite --host` if needed

---

## 6. Pointers specifically for tournament-style sites

If the tournament repo is **mostly static** (brackets, info, registration) without a full-screen map:

1. You **can** prerender `/` if the prerender component matches what React renders (or use static HTML only).
2. Skip `sessionBoot`, WebSocket, Leaflet, and `body overflow: hidden` unless you have a similar full-viewport app route.
3. Keep: `seoConfig`, `SEO.jsx`, legal routes, sitemap, og-image, cookie gate, accessibility statement, footer.
4. High contrast: legal overlay pattern is enough; map toolbar optional.
5. Reuse **language policy** from iron-sight if the audience is Israel: EN UI, HE keywords only, unless law requires more Hebrew.

If tournament shares the **same Vercel + React stack**, copy file-by-file:

| Iron Sight file | Tournament action |
|-----------------|-------------------|
| `seoConfig.js` | Replace titles, keywords, FAQ_ITEMS |
| `SEO.jsx` | Keep structure |
| `LegalPageLayout.jsx` | Adjust branding links |
| `LegalPage.css` | Reuse scroll + overlay rules |
| `AccessibilityToolbar.jsx` + `.css` | Reuse portal pattern |
| `HeaderSettingsControl.jsx` + `.css` | Copy if map hides footer on mobile; adjust `LEGAL_LINKS` |
| `vite.config.js` prerender list | Match your static routes |
| `generate-sitemap.mjs` | Update route list |

---

## 7. Key contacts and constants (iron-sight)

| Item | Value |
|------|--------|
| Site name | Iron Sight |
| Canonical | `https://iron-sight-drab.vercel.app/` |
| Support / privacy | `amirlabay+support@gmail.com` |
| Operator | Amir Labay |
| GitHub | `https://github.com/amirlabay/iron-sight` |

---

## 8. Related repo docs

- `context.md` — architecture and SEO note
- `status.md` — completed milestones
- `review/is-5568-iron-sight.md` — accessibility review notes
- `.cursor/rules/israeli-accessibility-is5568.mdc` — agent rule for IS 5568

---

*Last updated: 2026-05-23 — iron-sight dashboard SEO v1.2 + legal UI fixes + mobile header Settings menu (legal nav).*

# IRON SIGHT — Mobile Shell & Boot UX Contract

**Status:** Active (2026-05-17)  
**Authority:** Read this before changing mobile layout, bottom sheet, header, or boot/splash behavior.  
**Audit checklist:** [`REVIEW-STATUS.md`](../REVIEW-STATUS.md)

---

## Purpose

Documents **intentional** mobile/dashboard UX decisions so bug fixes do not reintroduce regressions (e.g. tabs in peek, clock inside header row, `animate={{ y }}` fighting drag, viewport-based collapse math).

---

## Breakpoints & constants

| Constant | Value | File |
|----------|-------|------|
| `MOBILE_LAYOUT_BREAKPOINT` | `1024` | `dashboard/src/utils/constants.js` |
| `MOBILE_SIDEBAR_HEIGHT_RATIO` | `0.78` | same |
| `MOBILE_SIDEBAR_PEEK_PX` | `44` (fallback only) | same |
| CSS `--mobile-sheet-peek` | Set at runtime from measured peek | `layout.css`, `Sidebar.jsx` |

**Do not** use a separate `768px` breakpoint for shell behavior without unifying JS + CSS (see `REVIEW-STATUS.md` → `breakpoint-1024-768`).

---

## Mobile bottom sheet (≤1024px)

### Collapsed peek — handle only

- **Visible when collapsed:** drag strip + pill only. **No** LIVE | HISTORY | SANDBOX tabs.
- **Rationale:** Space-saving; user drags up to reveal tabs + content.
- **Do not** include `.sidebar-tabs` in peek height measurement or show tabs in collapsed state.

### DOM order (sidebar)

1. `.sidebar-drag-zone` (`ref={peekChromeRef}`) — peek measurement target  
2. `.sidebar-tabs`  
3. `.tab-content`

### Position & collapse math

- Sheet: `position: fixed; bottom: 0; left: 0; right: 0` (viewport-bottom flush, not only `main-content`).
- **Collapsed offset:** `collapsedY = sidebar.offsetHeight - peekChrome.offsetHeight` via `ResizeObserver` on both nodes.  
  **Do not** use `window.innerHeight * MOBILE_SIDEBAR_HEIGHT_RATIO - PEEK` alone (header steals height → wrong peek slice).
- **Runtime CSS var:** `document.documentElement.style.setProperty('--mobile-sheet-peek', …)` for return-live bar positioning.

### Drag (Framer Motion)

- `drag={isMobile ? 'y' : false}` — no drag on desktop.
- `dragListener={false}` — drag starts from `.sidebar-drag-zone` via `useDragControls().start(e)`.
- **Position:** `useMotionValue` + `style={{ y: sheetY }}`. Animate with `animate(sheetY, target)` on state change.
- **Do not** use `animate={{ y: … }}` on the same axis as drag — it fights the gesture and prevents pulling down.
- Snap on `onDragEnd`: offset/velocity thresholds; else snap by `sheetY.get() < collapsedY * 0.5`.
- **Tab change does not expand sheet** — `handleTabChange` only sets `activeTab` (no `setIsSidebarExpanded(true)`).

### Drag strip styling

- Pill via `.sidebar-drag-zone::after` (~40×5px), not a full-width gradient bar.
- Safe area: `padding-bottom: calc(8px + env(safe-area-inset-bottom))` on drag zone only; sidebar `padding-bottom: 0`.
- Sheet `border-top` separates map from panel; avoid extra bottom padding on `.sidebar`.

### Desktop sidebar

- Full height, no Y drag, `sheetY` stays `0`.

---

## Mobile header (≤1024px)

### Single-row chrome

- `.header-bar`: **45px** fixed height, `flex-wrap: nowrap`. Logo + status sizes unchanged (do not shrink/grow to “fill” extra space).
- **Do not** put clock in header flex flow (no second row, no `flex: 1 1 100%` on clock).

### Tactical clock

- `position: absolute; top: 100%; left: …; margin-top: 6px` relative to `.premium-header`.
- Sits **below** the 45px bar, overlaying the map — **not** inside the bar.
- Typography: 10px date/time (`layout.css` mobile block). Desktop remains 16px (`App.css` `@media (min-width: 1025px)`).

### Desktop header (≥1025px)

- Clock in `.header-bar` between logo and status; `flex: 1` centered. See `App.css` desktop block.

---

## Boot & splash

- Shell (header, map, sidebar) mounts only when `isReady` (`App.jsx`).
- WebSocket mount effect deps: **`[connect]` only** — not `isReady` (avoids reconnect flash).
- `history_sync`: `setIsReady(true)` immediately — no artificial 1500ms delay.
- Splash exit: opacity only, ~0.45s — no `scale` zoom.

---

## Map motion

- `fitBounds` duration `0.8`, `flyTo` `0.6` (`MapViewer.jsx` `MapController`).
- Skip refit when bounds key unchanged; `resize`/`orientationchange` → `invalidateSize` + refit.

---

## PWA

- Manifest `background_color` / `theme_color`: `#0a0a0c` (`vite.config.js`).
- `orientation: "any"`.
- `index.html` `theme-color` matches.

---

## Fonts

- **No** `@import` in `layout.css`.
- Preconnect + preload + stylesheet in `index.html` (Outfit + JetBrains Mono).

---

## Return to live (mobile archive/timeframe)

- Header button hidden ≤1024px; fixed `.sidebar-return-live` bar above peek.
- `bottom: calc(var(--mobile-sheet-peek) + env(safe-area-inset-bottom) + 8px)`.

---

## Files to touch together

| Concern | Primary files |
|---------|----------------|
| Sheet peek / drag | `Sidebar.jsx`, `layout.css` (mobile block), `constants.js` |
| Header / clock | `layout.css`, `App.css`, `App.jsx` |
| Boot / WS | `TacticalProvider.jsx`, `App.jsx` |
| PWA colors | `vite.config.js`, `index.html` |
| Map timing | `MapViewer.jsx` |

---

## Anti-patterns (regression list)

1. Showing tabs in collapsed peek  
2. Measuring peek with `window.innerHeight * 0.78`  
3. `animate={{ y }}` + drag on same element  
4. Clock as second row in mobile header  
5. `padding-bottom` on whole sidebar pushing peek off bottom  
6. Full-width “handle bar” gradient (user expects pill only)  
7. Auto-expand sidebar on tab switch  
8. Re-adding `isReady` to WebSocket effect deps  

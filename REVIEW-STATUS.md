# IRON SIGHT — Smooth UX Review Status

**Goal:** Load cleanly on desktop & mobile — no lag, flicker, or surprise overlays.

**Last reviewed:** 2026-05-17 (follow-up bug pass)

**Legend:** `[ ]` todo · `[~]` in progress · `[x]` done · `[-]` wontfix / deferred

---

## Priority order

| # | ID | Severity | Status |
|---|-----|----------|--------|
| 1 | `ws-ready-effect` | 🔴 bug | `[x]` |
| 2 | `sidebar-tab-expand` | 🔴 bug | `[x]` |
| 3 | `defer-shell-until-ready` | 🟡 risk | `[x]` |
| 4 | `splash-exit-scale` | 🟡 risk | `[x]` |
| 5 | `memo-timeframe-merge` | 🟡 risk | `[x]` |
| 6 | `map-fly-duration` | 🟡 risk | `[x]` |
| 7 | `fonts-preload` | 🟡 risk | `[x]` |
| 8 | `mobile-backdrop-blur` | 🟡 risk | `[x]` |
| 9 | `mobile-drag-handle-hidden` | 🔴 bug | `[x]` |
| 10 | `mobile-sidebar-not-draggable` | 🔴 bug | `[x]` |
| 11 | `pwa-manifest-colors` | 🟡 risk | `[x]` |

---

## Boot & first paint

| ID | Status | Location | Problem | Fix |
|----|--------|----------|---------|-----|
| `ws-ready-effect` | `[x]` | `TacticalProvider.jsx` | 🔴 `useEffect(..., [connect, isReady])` closes WS when `isReady` flips → reconnect flash | Remove `isReady` from deps; mount `connect` once |
| `history-sync-delay` | `[x]` | `TacticalProvider.jsx` | 🟡 Forced `setTimeout(1500)` after `history_sync` on fast networks | Set `isReady` on sync; optional short exit anim only |
| `defer-shell-until-ready` | `[x]` | `App.jsx` | 🟡 Map/header/sidebar mount under splash; Leaflet works hidden | Gate shell on `isReady` or hide `.main-content` until ready |
| `splash-exit-scale` | `[x]` | `App.jsx` | 🟡 `exit={{ scale: 1.1 }}` + 1s zoom flashes content below | Opacity-only exit |
| `fonts-import-block` | `[x]` | `layout.css` | 🟡 `@import` Google Fonts blocks first paint | Preload in `index.html` or self-host |
| `fonts-preload` | `[x]` | `index.html` | 🔵 No font preload | Add `<link rel="preload">` for Outfit + JetBrains Mono |

---

## Mobile shell & layout shift

| ID | Status | Location | Problem | Fix |
|----|--------|----------|---------|-----|
| `sidebar-tab-expand` | `[x]` | `TacticalProvider.jsx` `handleTabChange` | 🔴 Tab change auto-expands 78% sheet on ≤1024px | Expand on drag only, not tab switch |
| `sidebar-drag-desktop` | `[x]` | `Sidebar.jsx` | 🟡 `drag="y"` + spring on desktop (no UX gain) | `drag={isMobile}` or plain `<aside>` desktop |
| `sidebar-height-duel` | `[x]` | `layout.css` + `Sidebar.jsx` | 🟡 `height: 78% !important` vs Framer `sidebarHeight` | Single owner for height |
| `leaflet-margin-magic` | `[ ]` | `layout.css` | 🟡 Hard-coded `margin-bottom` per mode/sidebar state → control jitter | CSS var tied to sheet `translateY` |
| `return-live-bar-pop` | `[x]` | `App.jsx`, `App.css` | 🟡 Fixed red bar appears + `bottom` jumps collapsed/expanded | Fade in or integrate into sheet chrome |
| `mobile-clock-reflow` | `[x]` | `layout.css` | 🟡 Clock `top:100%` grows header → map reflow | Reserve header min-height or overlay clock |
| `mobile-drag-handle-hidden` | `[x]` | `layout.css`, `Sidebar.jsx` | 🔴 Drag pill at `order: 3` (bottom of sheet); collapsed peek ~80px shows `tab-content` top — handle off-screen | Move `.sidebar-drag-zone` to `order: 0` (top of sheet); widen/contrast handle |
| `mobile-sidebar-not-draggable` | `[x]` | `Sidebar.jsx` | 🔴 `dragListener={false}` — only `.sidebar-drag-zone` starts drag; zone not in peek → sheet feels locked | Top drag zone + optional `dragListener={isMobile}` on header strip; verify `touchAction` / no scroll steal |

---

## PWA (installed app vs browser tab)

| ID | Status | Location | Problem | Fix |
|----|--------|----------|---------|-----|
| `pwa-manifest-colors` | `[x]` | `vite.config.js` | 🟡 `background_color: "#ffffff"`, `theme_color: "#000000"` vs app `#0a0a0c` → white/status-bar flash on launch | Align manifest + `index.html` theme to `#0a0a0c` |
| `pwa-standalone-viewport` | `[ ]` | `vite.config.js` | 🟡 `display: "standalone"` changes usable height (no URL bar); sheet/`100dvh` math differs from in-tab Safari | Compare tab vs Add to Home Screen; tune `collapsedY` / safe-area for standalone |
| `pwa-portrait-lock` | `[x]` | `vite.config.js` | 🟡 `orientation: "portrait"` — landscape/tablet layout untested | `"any"` or landscape breakpoints |
| `pwa-stale-precache` | `[ ]` | `vite.config.js`, `sw.js` | 🟡 `autoUpdate` + precache can serve old CSS → “stuck” mobile layout after deploy | Hard-refresh test; confirm SW updates post-deploy |
| `pwa-start-url` | `[ ]` | `vite.config.js` | 🔵 `start_url: "/?utm_source=pwa"` ≠ `/` | OK unless routing depends on exact `/` |

**Isolate:** broken in installed app only → PWA/manifest; same in mobile tab → layout/JS (rows above).

---

## Map motion & overlays

| ID | Status | Location | Problem | Fix |
|----|--------|----------|---------|-----|
| `map-fly-duration` | `[x]` | `MapViewer.jsx` | 🟡 1.5s `fitBounds`/`flyTo` on every config change feels sluggish | Shorter on filters; skip if bounds unchanged |
| `fit-padding-resize` | `[x]` | `MapViewer.jsx` | 🟡 `getFitPadding()` static until config changes | `resize`/`orientationchange` → `invalidateSize` + refit |
| `watermark-pop` | `[x]` | `MapViewer.jsx`, `App.css` | 🟡 Watermarks mount/unmount instantly with `viewMode` | Opacity transition or persistent strip |
| `archive-auto-live` | `[x]` | `TacticalProvider.jsx` | 🟡 `multi_alert` in archive forces `viewMode='live'` | Toast + explicit user action |
| `drone-raf-react` | `[ ]` | `ThreatOverlay.jsx` | 🟡 Per-drone rAF + `setProgress` re-renders React; N threats = jank | Canvas / Leaflet-only motion |
| `timeframe-double-polygon` | `[ ]` | `MapViewer.jsx` | 🔵 Double polygon per origin (heavy paint) | Merge pathOptions where possible |

---

## Re-renders & animation noise

| ID | Status | Location | Problem | Fix |
|----|--------|----------|---------|-----|
| `memo-timeframe-merge` | `[x]` | `TacticalProvider.jsx` | 🟡 `getRenderableEvents()` merge every render | `useMemo` on deps |
| `clock-raf-loop` | `[x]` | `TacticalClock.jsx` | 🟡 Eternal rAF for 1Hz clock | `setInterval(1000)` |
| `clock-framer-mount` | `[x]` | `TacticalClock.jsx` | 🔵 Framer fade on remount flickers header | `initial={false}` or static div |
| `tab-animate-wait` | `[x]` | `Sidebar.jsx` | 🟡 `AnimatePresence mode="wait"` slides full panel | Lighter / no exit on mobile |
| `live-alert-re-stagger` | `[x]` | `Sidebar.jsx` | 🟡 Every alert `initial` anim on WS updates | Animate new ids only |
| `history-height-auto` | `[ ]` | `Sidebar.jsx` | 🔵 `height:'auto'` expand thrashes long lists | `max-height` + overflow |

---

## GPU / CSS cost

| ID | Status | Location | Problem | Fix |
|----|--------|----------|---------|-----|
| `mobile-backdrop-blur` | `[x]` | `layout.css` | 🟡 Stacked `backdrop-filter` on header + sidebar | Solid bg + lighter blur on mobile |
| `will-change-always` | `[ ]` | `App.css`, `animations.css` | 🟡 Permanent `will-change` promotes layers forever | Only during active anim |
| `svg-filter-dom` | `[ ]` | `App.jsx` | 🔵 Unused blur filter still in DOM | Mount when map/threat needs it |

---

## Duplication & breakpoints

| ID | Status | Location | Problem | Fix |
|----|--------|----------|---------|-----|
| `return-live-dual` | `[ ]` | `App.jsx` | 🔵 Two RETURN TO LIVE paths (OK if never both visible) | Verify CSS; document intent |
| `breakpoint-1024-768` | `[ ]` | `constants.js`, `layout.css` | 🔵 1024 vs 768 split | Single shared mobile token JS + CSS |

---

## Notes

- **Authoritative mobile/shell contract:** [`.context/MOBILE_SHELL_SPEC.md`](.context/MOBILE_SHELL_SPEC.md) — read before bug fixes so peek/drag/header decisions are not reverted.
- Priority **1–11** shipped 2026-05-17 (see table above).
- **Follow-up pass:** mobile drag handle top-of-sheet, PWA `#0a0a0c` colors, clock interval, archive no auto-live, map resize refit, return-live fade, live-alert animate-on-new-id only.
- **Concrete UX (do not regress):** collapsed peek = **drag pill only** (no tabs); mobile clock **below** 45px bar (not in bar); sheet `useMotionValue` Y; measured peek height.
- Remaining: leaflet margin CSS var, drone canvas, PWA standalone viewport tuning, `will-change` cleanup.
- Smoke: cold load, collapsed **pill flush to bottom**, tab switch (no auto-expand), Add to Home Screen vs Safari tab.

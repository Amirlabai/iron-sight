# Iron Sight — Status

**Updated:** 2026-05-17

## Deploy

| Target | State | Notes |
|--------|--------|--------|
| Vercel (`main` @ `8e821d8`) | **Failed** | `Sidebar.jsx` duplicate declarations after PR #11 merge |
| Fix branch `fix/vercel-sidebar-duplicate` | **Build OK** | Local `npm run build` passes; push + merge to `main` to redeploy |

## Cause

Vite/Rolldown error: `Identifier 'viewport' has already been declared` (and `setViewport`, `isMobile`, `collapsedY`, `sidebarHeight`). Duplicate mobile hook block pasted below `startSheetDrag`.

## Next

1. Merge `fix/vercel-sidebar-duplicate` → `main` (or cherry-pick the 21-line deletion).
2. Redeploy on Vercel.

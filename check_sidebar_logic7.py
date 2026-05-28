# Wait, look at this:
# In Sidebar.jsx:
# ```javascript
#   React.useLayoutEffect(() => {
#     if (!isMobile) {
#       sheetY.set(0);
#       return;
#     }
#     if (isSidebarExpanded || collapsedY <= 0) return;
#     sheetY.set(collapsedY);
#   }, [collapsedY, isMobile, isSidebarExpanded, sheetY]);
# ```
# If `collapsedY <= 0`, it returns. What if `collapsedY` IS 0 initially?
# `const nextY = Math.max(0, sidebarH - peekH);`
# `peekH` is 0. So `nextY` is `sidebarH`.
# So `collapsedY` is `sidebarH`. It is NOT 0.
# Is it possible that `isSidebarExpanded` IS true, but the sidebar is not visible because `height` is 0?
# No, `sidebarHeight = '60%'`.

# Let's think about the user's issue.
# Could the `isSidebarExpanded` state simply not be updating because `useTactical()` isn't propagating the state?
# No, `isSidebarExpanded` is a standard state.
# What if the map click event IS STILL firing?
# In App.jsx, the button is:
# `<button onClick={(e) => { e.stopPropagation(); setIsSidebarExpanded(true); }} onPointerDown={(e) => e.stopPropagation()} ... >`
# If this button is clicked on a mobile device (touch event), does it fire a touchstart/touchend that Leaflet intercepts?
# Leaflet listens to `touchstart`, `touchend`, `mousedown`, `mouseup`.
# If we only stop `onClick` and `onPointerDown`, maybe Leaflet still catches `touchstart` and `touchend`, triggering a map click?
# Yes! `MapClickHandler` listens to `click` on the map. Leaflet converts touch events to click events!
# To prevent Leaflet from catching the click, we should also stop propagation on `onTouchStart` and `onTouchEnd`!
# Let's add `onTouchStart` and `onTouchEnd` and `onMouseDown` and `onMouseUp` `e.stopPropagation()`.

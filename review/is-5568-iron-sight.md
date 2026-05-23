# IS 5568 / WCAG 2.1 AA — Iron Sight dashboard checklist

**Coordinator:** Amir Labay — amirlabay+support@gmail.com  
**Statement:** [/accessibility](https://iron-sight-drab.vercel.app/accessibility)

## Shipped (engineering)

- [x] English accessibility statement page
- [x] Skip link to `#main-content`
- [x] High-contrast mode (toolbar + `localStorage`)
- [x] Scroll-to-top control on legal pages and map shell
- [x] `prefers-reduced-motion` CSS
- [x] Cookie notice; analytics gated until consent
- [x] Footer links: About, Accessibility, Privacy, Terms
- [x] Header icon `aria-label`s (existing + toolbar)

## Open / manual verification

- [ ] Keyboard-only pass on map header, sidebar tabs, wizard, legal pages
- [ ] NVDA or VoiceOver on `/`, `/about`, wizard steps
- [ ] Contrast audit (normal + high-contrast) on map chrome and legal prose
- [ ] 200% and 400% zoom on legal pages and mobile shell
- [ ] Map: verify alert state is not conveyed by color alone in sidebar list (icons/labels)
- [ ] Lighthouse Accessibility ≥90 on `/about` and `/accessibility` after deploy
- [ ] Document any remaining map SR gaps on accessibility page if found in testing

## Known limitations (documented)

- Leaflet map canvas and dynamic overlays are not fully available to assistive tech
- Third-party map tiles and Google Fonts require network
- Splash/boot animation reduced under `prefers-reduced-motion` but still present briefly

## Sign-off

| Role | Name | Date |
|------|------|------|
| Accessibility coordinator | Amir Labay | |
| Engineering verification | | |

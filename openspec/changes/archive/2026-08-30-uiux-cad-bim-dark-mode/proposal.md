# Proposal: CAD/BIM Dark Mode Studio UI Redesign

## Intent

Redesign the SketchOS validator frontend from a generic light-themed single-section UI into a professional CAD/BIM dark studio aesthetic. The current flat sidebar with light panels (`#f5f5f5`, `#202124` text) reads as a dev tool—not a presentation-ready architectural application. This aligns with industry CAD/BIM conventions: dark viewport, tab-based sidebar, technical HUD, and professional typography (Inter + JetBrains Mono).

**Prior attempt**: A full SDD pipeline completed but verification FAILED with 3 critical bugs (SceneStatsContext never updates React context, clipping planes are scalar not a set, HUD shows "0" instead of "—"). This proposal inherits those as verified pitfalls.

## Scope

### In Scope
- **Dark theme**: CSS custom properties (#0b0f19/#1e293b palette, #0ea5e9 accent), Inter + JetBrains Mono fonts via Google Fonts `<link>` in Layout.astro
- **ValidatorDashboard 3-tab layout**: Ingesta Multimodal, Normativa & Umbrales, Diagnóstico — replacing 5 sequential `<section>` blocks with a tab component; SVG icons per tab
- **GeometryScene viewport controls**: 4 camera presets (Planta/Fachada Frontal/Fachada Lateral/Isométrica) with lerp animation; Z+Y section clipping planes (combinable via array, not scalar); bottom HUD status bar (triangle count, object count, AABB ms, "—" on empty)
- **BYOK API key modal**: password input, localStorage persistence, `X-Gemini-Api-Key` header injection in api.js
- **Component tests**: TDD-first unit tests for all new/modified components (currently zero)

### Out of Scope
- Backend API changes (header injection is frontend-only; proxy rewrite `/api` → '' preserved intact)
- New npm packages; new icon library (inline SVG only)
- Mobile/responsive layout; post-processing effects; shadow maps

## Capabilities

### New Capabilities
- `cad-dark-theme`: Global dark palette, typography tokens, and Layout.astro font loading
- `viewport-controls`: Camera view presets, section clipping planes (Z+Y), HUD metrics bar
- `byok-api-key-modal`: API key modal with localStorage + fetch header injection

### Modified Capabilities
- `frontend-validator-dashboard`: Tab navigation replaces sequential sections; SVG icons replace text headers; dark-themed component styles

## Approach

Three stacked PRs (auto-chain, ≤400 lines each):

1. **PR #1 — Theme foundation**: Rewrite `:root` CSS tokens, add Google Fonts to Layout.astro. No JSX changes. Validate old components render with new palette.
2. **PR #2 — Sidebar refactor**: 3-tab layout + SVG icon components + BYOK modal + api.js header injection. Component tests before refactor.
3. **PR #3 — Viewport enhancement**: Camera presets, clipping planes (array-based for Z+Y), HUD bar with SceneStatsContext (design mandates `setStats` call on geometry load), HUD fallback "—".

TDD-first: zero component tests exist today — every PR gates on tests written before implementation (`strict_tdd: true`).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/styles/global.css` | Modified | Dark palette tokens, tab/HUD/BYOK styles |
| `frontend/src/layouts/Layout.astro` | Modified | Google Fonts `<link>` |
| `frontend/src/components/ValidatorDashboard.jsx` | Modified | Tab layout, SVG icons, BYOK trigger |
| `frontend/src/components/GeometryScene.jsx` | Modified | View presets, clipping planes, HUD, `#0b0f19` bg |
| `frontend/src/components/BYOKModal.jsx` | New | API key modal + localStorage |
| `frontend/src/components/icons/` | New | 7 inline SVG components |
| `frontend/src/contexts/SceneStatsContext.jsx` | New | HUD metrics context |
| `frontend/src/lib/api.js` | Modified | `X-Gemini-Api-Key` injection |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| SceneStatsContext never updates React context (statsRef→context gap — prior FAIL) | High | Design mandates explicit `setStats` on geometry load; test context value propagation in isolation |
| Clipping `clipAxis` is scalar, can't enable Z+Y simultaneously (prior FAIL) | High | Design uses `clippingPlanes` array concatenation: `(clipZ ? [zPlane] : []).concat(clipY ? [yPlane] : [])`; test both planes active |
| HUD shows "0" instead of "—" on empty/no-geometry state (prior FAIL) | High | Test null/empty state rendering with exact string assertion (`"—"`) |
| CSS cascade: dark tokens make old selectors invisible text | Med | Audit every selector against `:root` vars; visual regression check |
| BYOK localStorage anti-pattern for production | Low | Clear UI notice: dev-tool scope; key stored unhashed |
| Zero component tests — refactoring blind | High | Write ALL component tests before any JSX/3D changes |
| OrbitControls capture HUD button clicks | Med | `pointerEvents: 'none'` on Html wrapper; `auto` on interactive children |
| EdgesGeometry performance on 100+ object models | Med | `useMemo` overlay array; warn if >100 objects |

## Rollback Plan

Revert PR #3 → PR #2 → PR #1 in reverse order. Each PR is autonomous — reverting one leaves prior PRs functional. No backend changes, no data migration.

## Dependencies

- React 19, Three.js 0.170, @react-three/fiber 9, @react-three/drei 10 (existing)
- No new npm packages

## Success Criteria

- [ ] Dark palette renders: `#0b0f19` viewport, `#1e293b` panel borders, `#0ea5e9` accent
- [ ] ValidatorDashboard renders 3 tabs with correct SVG icons; tab switch preserves panel state
- [ ] 4 camera presets animate to correct positions (Planta/Fachada Frontal/Fachada Lateral/Isométrica)
- [ ] Z and Y clipping planes can be enabled simultaneously; both slice geometry
- [ ] HUD shows real triangle/object/AABB-ms values after geometry load; `"—"` when empty
- [ ] BYOK modal persists key (`gemini_api_key`) and injects `X-Gemini-Api-Key` on all requests
- [ ] ≥50 component tests pass (vitest); existing 15 api+obj tests unchanged
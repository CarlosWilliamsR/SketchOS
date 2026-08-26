# Tasks: CAD/BIM Dark Mode Studio UI Redesign

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~900–1050 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |
| Suggested split | PR #1 → PR #2 → PR #3 (stacked to main) |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Dark theme foundation | PR 1 | `vitest run src/components/icons/` | `npm run dev` — viewport renders `#0b0f19` | Revert global.css + Layout.astro + icons/ |
| 2 | Tab sidebar + BYOK | PR 2 | `vitest run src/components/ValidatorDashboard.test.jsx src/components/BYOKModal.test.jsx` | `npm run dev` — 3 tabs, BYOK modal stores key | Revert ValidatorDashboard.jsx + BYOKModal.jsx + api.js |
| 3 | Viewport + clip + HUD | PR 3 | `vitest run src/components/GeometryScene.test.jsx src/contexts/` | `npm run dev` — camera presets animate, Z+Y clip, HUD shows "—" | Revert GeometryScene.jsx + SceneStatsContext.jsx + HUD CSS |

## Phase 1: Theme Foundation + SVG Icons (PR #1)

### RED tests
- [x] 1.1 Write `icons.test.jsx`: 7 icons render with `currentColor`, correct viewBox, no emoji
- [x] 1.2 Write dark-theme CSS token test: verify `:root` vars exist via computed styles in jsdom

### GREEN
- [x] 1.3 Rewrite `:root` in `frontend/src/styles/global.css`: add `--bg-primary`, `--bg-secondary`, `--bg-tertiary`, `--accent`, `--accent-hover`, `--text-primary`, `--text-secondary`, `--text-muted`, `--border`, `--pass`, `--violation`, `--viewport-bg`, `--panel-bg` dark tokens
- [x] 1.4 Replace 8 hardcoded colors in global.css: `#f5f5f5`→`var(--bg-secondary)`, `#3a3d41`→`var(--viewport-bg)`, `#202124`→`var(--text-primary)`, `#5f6368`→`var(--text-muted)`, `#c9ccd0`→`var(--border)`, `#fff`(upload bg)→`var(--bg-tertiary)`, `#e6f4ea`→`var(--bg-secondary)`, `#fce8e6`→`var(--bg-secondary)`; add dark panel/button/HUD selectors
- [x] 1.5 Add font-family/spacing tokens to `:root`: `--font-sans`, `--font-mono`, `--space-xs/sm/md/lg/xl`
- [x] 1.6 Add Google Fonts preconnect + `<link>` (Inter 400/500/600, JetBrains Mono 400) to `frontend/src/layouts/Layout.astro`
- [x] 1.7 Create `frontend/src/components/icons/UploadIcon.jsx`, `SketchIcon.jsx`, `RulesIcon.jsx`, `DiagnosticsIcon.jsx`, `WarningIcon.jsx`, `PassIcon.jsx`, `ApiKeyIcon.jsx` — each 16×16 viewBox, `currentColor`, `1.5px` stroke
- [x] 1.8 Change `vitest.config.js`: `environment: 'node'` → `'jsdom'`
- [x] 1.9 Set GeometryScene bg to `#0b0f19`, viewport overlay dark; verify old selectors survive

### REFACTOR
- [x] 1.10 Audit all CSS selectors for light-theme remnants; confirm `var(--pass)`/`var(--violation)` resolve correctly

## Phase 2: Dashboard Tabs + BYOK Modal (PR #2)

### RED tests
- [ ] 2.1 Write `ValidatorDashboard.test.jsx`: tab switch changes visible panel, keyboard ArrowRight/ArrowLeft navigates, Home/End jumps to first/last, tab survives data load
- [ ] 2.2 Write `BYOKModal.test.jsx`: open/close/Escape, save to localStorage, masked display `••••`+last4, empty key blocked, clear removes key, missing-key renders warning
- [ ] 2.3 Write `api.test.js` extension: `X-Gemini-Api-Key` header present when key in localStorage, absent when no key, proxy rewrite `/api`→`''` intact

### GREEN
- [ ] 2.4 Add `activeTab` useState to `ValidatorDashboard.jsx` (coexists with `phase` machine): 0=Ingest, 1=Regulations, 2=Diagnostics
- [ ] 2.5 Refactor `<section>` blocks into 3 tab panels with `role="tabpanel"`, `aria-labelledby`, `hidden`/`display:none` toggle; tab buttons use `role="tab"`, `aria-selected`
- [ ] 2.6 Wire SVG icons: UploadIcon+I SketchIcon on Tab 1, RulesIcon on Tab 2, DiagnosticsIcon+WarningIcon+PassIcon on Tab 3 alongside Violations/Status
- [ ] 2.7 Apply dark-theme CSS classes: `--bg-secondary` panel, `--border` separators, `--accent` active tab, `--text-secondary` body; remove all `#f5f5f5`/`#202124` references
- [ ] 2.8 Write tab keyboard handler: ArrowLeft/Right, Home/End with `e.preventDefault()` + `stopPropagation` in useEffect
- [ ] 2.9 Create `frontend/src/components/BYOKModal.jsx`: portal (`createPortal`), `useState` for `isOpen`+`keyValue`, useEffect read localStorage, password input, masked display, Save/Clear/Rotate, inline error for <10 chars, Escape+backdrop close, warning style when no key
- [ ] 2.10 Add BYOK trigger button (ApiKeyIcon + "API Key") in sidebar header, near title
- [ ] 2.11 Inject `X-Gemini-Api-Key` in `frontend/src/lib/api.js` `request()`: read `localStorage.getItem('gemini_api_key')`, set header if non-empty; preserve `/api`→`''` proxy

### REFACTOR
- [ ] 2.12 Verify existing `obj.test.js` + `api.test.js` still pass (15 tests); confirm phase state machine not broken by `activeTab`

## Phase 3: Viewport + Clip Planes + HUD (PR #3)

### RED tests
- [ ] 3.1 Write `SceneStatsContext.test.jsx`: default `{triangles:0,objects:0,aabbMs:0}`, setStats updates, consumer sees "—" when stats unchanged
- [ ] 3.2 Write `GeometryScene.test.jsx` (Canvas mocked): camera preset positions correct, clippingPlanes array contains both planes when Z+Y active, HUD renders "—" on empty, `pointerEvents` isolation present
- [ ] 3.3 Write pure-function tests for clippingPlanes array logic (Z+Y combo) and camera target positions

### GREEN
- [ ] 3.4 Create `frontend/src/contexts/SceneStatsContext.jsx`: context with `{triangles,objects,aabbMs}`, `SceneStatsProvider`, `useSceneStats` hook, `setStats` export; default state `{triangles:0,objects:0,aabbMs:0}`; HUD renders "—" when no `setStats` called
- [ ] 3.5 Integrate `SceneStatsProvider` into `GeometryScene.jsx` Canvas; call `setStats` via useEffect after `parseObj`+AABB compute, using `useMemo` for stats derivation
- [ ] 3.6 Replace `MESH_COLOR='#cfd3d7'` with PBR matte `#94a3b8`, roughness 0.85, metalness 0.0; add `EdgesGeometry` wireframe overlay (`#60a5fa`, `renderOrder:1`) per mesh via `useMemo`
- [ ] 3.7 Add camera preset system: 4 buttons (TopDown→`[0,maxY,0]`, Front→`[0,0,maxZ]`, Side→`[maxX,0,0]`, Iso→`[maxX,maxY,maxZ]`), `useFrame` lerp factor 0.08, active preset highlight
- [ ] 3.8 Add clipping plane system: `useState(clipZ)`+`useState(clipY)`, independent boolean toggles, `renderer.clippingPlanes = (clipZ?[zPlane]:[]).concat(clipY?[yPlane]:[])`, `localClippingEnabled=true` on renderer, slider inputs for plane constant
- [ ] 3.9 Add HUD overlay: Drei `<Html>` wrapper with `pointerEvents:'none'`, 3 metrics (Triangles/Objects/AABB ms) in `<code>` with `--font-mono`+`tabular-nums`, `aria-live="polite"`, "—" fallback
- [ ] 3.10 Add status bar (bottom 28px): `--bg-secondary` strip, fixed position, displays HUD metrics
- [ ] 3.11 Set HUD interactive children `pointerEvents:'auto'` (preset buttons, clip toggles, sliders)

### REFACTOR
- [ ] 3.12 Verify 1.10 + 2.12 tests still pass; verify clipping planes Z+Y simultaneously; verify camera preset lerp smooth at 60fps
- [ ] 3.13 Final CSS visual audit: all selectors reference dark tokens only; remove `#3a3d41`/`#cfd3d7`/`#d7dade` remnants; confirm `--viewport-bg: #0b0f19` across all states
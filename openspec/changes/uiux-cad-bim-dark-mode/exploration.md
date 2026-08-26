# Exploration: CAD/BIM Dark Mode Studio UI Redesign

**Change**: `uiux-cad-bim-dark-mode`
**Date**: 2026-08-26
**Agent**: sdd-explore
**Codebase snapshot**: commit `6266507` (main) — **current code is UNMODIFIED** for this change

---

## Current State

### Architecture Overview

The SketchOS validator frontend is an Astro 5 + React 19 single-page application with an embedded Three.js 3D viewport. It communicates with a FastAPI backend through a Vite dev proxy (`/api` → `127.0.0.1:8000`). The entire UI is a single island component (`ValidatorDashboard`) with a client-only React render.

```
index.astro (page)
  └─ Layout.astro (HTML shell + global.css)
       └─ ValidatorDashboard.jsx (client:only)
            ├─ side-panel (upload, thresholds, violations, autocorrect)
            └─ main.viewport
                 └─ GeometryScene.jsx (@react-three/fiber Canvas)
                      └─ Model component
                           ├─ OBJ parsed mesh (MeshStandardMaterial)
                           ├─ AABB overlays (Edges, green/red)
                           ├─ CameraFit (auto-fit)
                           └─ Grid (infinite reference grid)
```

### Component: ValidatorDashboard.jsx (198 lines)

**State machine**: `idle → loading → loaded(pass|violations) → empty → error`

**State variables**:
| Variable | Type | Initial | Purpose |
|----------|------|---------|---------|
| `phase` | `PHASES` enum | idle | UI state machine |
| `rules` | object|null | null | Thresholds from `/api/extract-rules` |
| `rulesError` | string|null | null | Error fetching thresholds |
| `result` | object|null | null | `{status, report, fixes}` from backend |
| `objText` | string|null | null | Raw OBJ text for GeometryScene |
| `fileName` | string|null | null | Uploaded filename |
| `error` | string|null | null | User-facing error message |
| `dsl` | string | '' | ArchitecturalDSL JSON textarea value |

**Data flow**:
1. **On mount**: `fetchRules()` → `GET /api/extract-rules` → sets `rules`
2. **On file upload**: reads file text locally → `POST /api/validate-geometry` (FormData) → sets `result`, `objText`
3. **On autocorrect**: parses DSL JSON → `POST /api/autocorrect` → sets `result`

**Current sidebar structure** (SEQUENTIAL, NO TABS):
1. `<h1>Validator Dashboard</h1>` — page title
2. Upload section: `<input type="file" accept=".obj">`
3. Thresholds section (conditional on `rules`): `<dl>` grid with 4 rule values
4. Status banner + Violations list + Applied fixes (conditional on `phase === loaded`)
5. Autocorrect section: `<textarea>` DSL editor + `<button>`

**Current styling approach for sidebar elements**:
- `.side-panel` — 320px fixed, `#f5f5f5` background, `1px solid #c9ccd0` right border, overflow-y auto
- `.panel-section` — `margin-top: 16px`, sections are stacked vertically with no tab navigation
- `.upload-control` — inline-flex button-like container with white background
- `.status-banner` — colored pill (green `#e6f4ea` / red `#fce8e6`)
- `.violation` — grid layout with mono-spaced rule type and muted measurements
- `.dsl-editor` — monospace textarea with `resize: vertical`
- `.button` — blue accent `#1a73e8` background

**Emojis/icons used**: NONE. The current code has zero emojis. Only text labels.

### Component: GeometryScene.jsx (130 lines)

**Three.js setup**:
| Element | Config | Current Value |
|---------|--------|---------------|
| Canvas background | `<color>` attach | `#3a3d41` |
| Camera | Position, FOV, near/far | `[10, 8, 10]`, 45°, 0.1/10000 |
| Ambient light | intensity | 0.7 |
| Directional light | position, intensity | `[10, 20, 5]`, 1.2 |
| Antialias | gl prop | true |
| Controls | OrbitControls | damping 0.1, makeDefault |
| Grid | infiniteGrid | cellSize 1, sectionSize 5, fade 80 |

**OBJ Rendering**:
- Client-side parsing via `OBJLoader.parse(text)`
- Single `MeshStandardMaterial` applied to all meshes:
  - `color: #cfd3d7` (light gray)
  - `roughness: 0.6`
  - `metalness: 0.0`
- No edge highlighting (no `EdgesGeometry` on the model itself)
- No wireframe overlay
- No architectural clay material

**AABB Overlays**:
- `computePerObjectAABBs()` groups vertices by `o`/`g` name, builds `Box3` per object
- `Edges` component renders box edges with `lineWidth: 2`
- Green (`#2e7d32`) for passing, Red (`#c62828`) for violations
- Color mapping via `colorForBox(name, violatingObjectsSet)`

**Camera auto-fit**:
- `CameraFit` component reads camera/controls from `useThree`
- Calculates `fitDistance` from FOV and max dimension, offsets camera at 45° angle
- Sets near/far planes proportionally

**MISSING — No current implementation of**:
- Viewport HUD (floating quick-view buttons)
- Section cut plane (`clippingPlane`)
- Bottom status bar (triangles, objects, time)
- Post-processing effects
- Shadow maps (no shadowMap enabled on renderer)
- Material edge highlighting on geometry

### Styling: global.css (244 lines)

**Current CSS architecture**:
- Single `global.css` file — no modules, no Tailwind, no CSS-in-JS
- CSS custom properties on `:root` for theme tokens
- BEM-like class naming: `.validator-dashboard`, `.side-panel`, `.panel-section`
- Grid layout: `grid-template-columns: 320px 1fr`
- Viewport uses `position: relative` to layer the `viewport-message` overlay

**Current color palette (LIGHT theme)**:
| Token | Value | Usage |
|-------|-------|-------|
| `--viewport-bg` | `#3a3d41` | Canvas background |
| `--viewport-grid` | `#4a4d52` | Grid cell color (passed as prop) |
| `--panel-bg` | `#f5f5f5` | Sidebar background |
| `--panel-border` | `#c9ccd0` | Separator borders |
| `--accent` | `#1a73e8` | Buttons, hover states |
| `--text` | `#202124` | Primary text |
| `--muted` | `#5f6368` | Secondary text |
| `--pass` | `#2e7d32` | Validation success |
| `--violation` | `#c62828` | Validation failure |

**Fonts**: `system-ui` stack, `ui-monospace` for code elements, `tabular-nums` for measurements

### API Proxy Layer: api.js (71 lines)

**Proxy mechanism** (astro.config.mjs):
```js
'/api': { target: 'http://127.0.0.1:8000', changeOrigin: true, rewrite: path => path.replace(/^\/api/, '') }
```
CRITICAL: The rewrite strips `/api` — backend routes are prefix-less (`/extract-rules`, NOT `/api/extract-rules`).

**Endpoints consumed**:
| Function | Method | Endpoint | Body | Response |
|----------|--------|----------|------|----------|
| `fetchRules()` | GET | `/extract-rules` | — | `{min_height, max_height, min_thickness, max_thickness}` |
| `validateGeometry(file)` | POST | `/validate-geometry` | FormData (`file` field) | `{status, report}` |
| `autocorrect(dsl)` | POST | `/autocorrect` | JSON (`Content-Type: application/json`) | `{status, report, fixes}` |

**Error handling**: `ApiError` class with status code + FastAPI `detail` string. Network failures → status 0 with "Backend unreachable" message.

### Dependencies (package.json)

| Package | Version | Role |
|---------|---------|------|
| `astro` | ^5.0.0 | Build framework + routing + proxy |
| `@astrojs/react` | ^4.0.0 | React island integration |
| `react` / `react-dom` | ~19.0.0 | UI rendering |
| `three` | ^0.170.0 | 3D engine |
| `@react-three/fiber` | ^9.0.0 | React renderer for Three.js |
| `@react-three/drei` | ^10.0.0 | Helper components (OrbitControls, Grid, Edges) |
| `vitest` | ^4.1.11 | Test runner |
| `@types/three` | ^0.170.0 | Three.js type definitions |

**Notable absences**:
- No Tailwind CSS
- No `@react-three/postprocessing` (for effects)
- No UI component library (Radix, Headless UI, etc.)
- No CSS framework

### Test Infrastructure

| File | Tests | Coverage |
|------|-------|----------|
| `src/lib/api.test.js` | 5 suites, 7 cases | API client (URL, method, body shape, errors) |
| `src/lib/obj.test.js` | 3 suites, 10 cases | OBJ parsing, AABB computation, color mapping |
| Component tests | **0** | ValidatorDashboard and GeometryScene have NO tests |

**Test runner**: Vitest 4.1.11, Node environment, `vitest run` via npm script

### Backend API Contract (unchanged by this UI-only change)

The backend is preserved intact. Key facts:
- FastAPI on `127.0.0.1:8000`
- `GET /extract-rules` → `{min_height, max_height, min_thickness, max_thickness}` (dict of floats)
- `POST /validate-geometry` → multipart `file` → `{status: "pass"|"violations"|"parse_error", report: {objects, violations, aabb}}`
- `POST /autocorrect` → JSON DSL body → `{status, report, fixes: [{wall_id, rule, dimension, from, to}]}`
- Error status codes: 422 (parse), 503 (spawn), 504 (timeout)

---

## Affected Areas

| File | Lines | Why affected | Risk |
|------|-------|-------------|------|
| `frontend/src/styles/global.css` | 244 | Complete theme rewrite: new CSS custom properties, tab styles, BYOK modal styles, HUD styles, status bar styles | Medium — cascading changes touch all selectors |
| `frontend/src/components/ValidatorDashboard.jsx` | 198 | Major restructure: 3-tab sidebar, BYOK modal, new section content, SVG icons, monospaced metrics | High — state management may need restructuring for tabs |
| `frontend/src/components/GeometryScene.jsx` | 130 | Significant additions: clay material, EdgeGeometry, clippingPlane, HUD, status bar | High — Three.js changes are fragile |
| `frontend/src/lib/api.js` | 71 | **PRESERVE INTACT** — no API changes | None |
| `frontend/src/lib/obj.js` | 111 | **PRESERVE INTACT** — OBJ parsing unchanged | None |
| `frontend/src/layouts/Layout.astro` | 22 | May need `<meta>` or `<title>` update for CAD branding | Low |
| `frontend/src/pages/index.astro` | 8 | **UNCHANGED** | None |
| `frontend/astro.config.mjs` | 23 | **PRESERVE INTACT** — proxy MUST remain | None |
| `frontend/package.json` | 27 | May need `@react-three/postprocessing` if effects are added | Low |

---

## Approaches

### 1. Incremental CSS + Component Refactor (Recommended)

Refactor in stacked PRs, each autonomous:

**PR #1 — Theme system**: Rewrite `global.css` CSS custom properties to dark palette, add tab styles, add BYOK modal styles. No JSX changes. Validate visually that old components still render correctly.

**PR #2 — Sidebar refactor**: Restructure `ValidatorDashboard.jsx` into 3-tab layout. Add tab state management. Replace text with SVG icons and monospaced metrics. Add BYOK Config Modal component with `localStorage` integration. Add component tests.

**PR #3 — Viewport enhancement**: Add architectural clay material, `EdgesGeometry` highlighting, section cut plane (`clippingPlane`), viewport HUD buttons, bottom status bar. Add rendering tests.

- **Pros**: Review-friendly (each PR ≤400 lines), testable in isolation, easy rollback per PR
- **Cons**: More PR overhead, need careful branch management for chained PRs
- **Effort**: Medium

### 2. Single-PR Refactor

Rewrite all files in one PR.

- **Pros**: Single atomic change, simpler branch management
- **Cons**: Exceeds 400-line review budget (~1,200 estimated), hard to review, risky rollback
- **Effort**: Low for developer, High for reviewer

### 3. Component Extraction + New Architecture

Extract tabs into separate components (`IngestionTab`, `RegulationsTab`, `DiagnosticsTab`), extract `BYOKModal`, extract `ViewportHUD`, extract `StatusBar`. Refactor `GeometryScene` into composable sub-components.

- **Pros**: Clean architecture, better testability, aligns with container-presentational pattern
- **Cons**: More files, more boilerplate, over-engineering for current scope
- **Effort**: High

---

## Recommendation

**Approach 1 — Incremental CSS + Component Refactor with stacked-to-main chained PRs.**

The 400-line budget demands splitting. Three stacked PRs provide clean separation:
1. CSS theme → low risk, purely visual
2. Sidebar UX → medium risk, state changes but no 3D
3. Viewport → medium risk, Three.js fragile but isolated

Each PR can be independently verified and reviewed. This matches the existing chain strategy (`stacked-to-main`) and review budget (400 lines).

---

## Risks

1. **Three.js clippingPlane fragility**: `clippingPlanes` is an array on the renderer/material, not the scene. If a user enables clipping and toggles between views, the plane must be updated before render or artifacts appear. Must test with both Z and Y axis slices.
2. **CSS cascade conflicts**: Rewriting `:root` custom properties affects ALL components simultaneously. If the old selectors assume light backgrounds, they may produce invisible text. Every selector must be audited.
3. **BYOK localStorage security**: User concern — storing API keys in localStorage is a known anti-pattern for production. Must clearly document that this is a developer/demo tool, not a production authentication mechanism.
4. **Tab state + file upload reset**: Tabbing away during a file upload should preserve state. The current state machine doesn't track tab selection — adding tabs requires careful state co-location.
5. **No component tests exist**: Both target components have ZERO tests. The refactor will be done blind without safety nets unless tests are written first (strict TDD policy in SDD config).
6. **OrbitControls conflict with HUD buttons**: Floating HUD buttons overlay the Canvas. Pointer events on the HUD buttons must NOT propagate to OrbitControls, or clicking "Front Elevation" will also rotate the camera. Requires `pointer-events` CSS or event stop-propagation.
7. **EdgesGeometry performance**: `EdgesGeometry` recalculates on every geometry change. On large models (100+ objects), this could cause frame drops. Should be memoized.
8. **verify-report from prior attempt**: Engram contains a FAIL verdict from a previous apply/verify cycle — `SceneStatsContext` was broken (HUD always showed 0). This indicates the status bar feature has a known implementation pitfall with React state references across the R3F imperative boundary.

---

## Ready for Proposal

**Yes**. The codebase is fully explored, all files mapped, all dependencies identified, all risks documented. The prior SDD pipeline artifacts (proposal, spec, design, tasks) exist in Engram and can inform a fresh proposal pass. Recommend launching `sdd-propose` next to formalize scope and approach with the learnings from this exploration.

---

## Key Learnings

1. The current ValidatorDashboard uses a flat sequential sidebar with no tabs; adding a 3-tab structure requires introducing a new `activeTab` state variable that must coexist with the existing phase state machine.
2. GeometryScene has no edge highlighting on the model geometry itself — EdgesGeometry is only used for AABB overlays; adding architectural clay style requires a separate EdgesGeometry pass on each mesh.
3. The Astro Vite proxy rewrite (`/api` → '') is load-bearing and must be preserved exactly; any misconfiguration breaks all backend communication.
4. Three.js `clippingPlanes` is applied per-material, not per-scene, which means the section cut implementation must traverse all mesh materials and toggle the clippingPlanes array on each.
5. There are zero component-level tests for ValidatorDashboard or GeometryScene, meaning the refactor will need TDD-first test creation before any implementation changes under the project's strict TDD policy.
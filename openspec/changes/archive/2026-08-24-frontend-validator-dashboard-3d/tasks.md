# Tasks: Frontend Validator Dashboard (3D)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~700–900 (10 source + 2 test files + vitest config) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (scaffold) → PR 2 (libs) → PR 3 (viewer UI) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Scaffold + proxy builds | PR 1 | `npm run build` | `npm run dev` + `curl http://localhost:4321/api/extract-rules` (backend up) | delete `frontend/` |
| 2 | Pure libs `obj.js` + `api.js` + tests | PR 2 | `npx vitest run` | N/A — pure functions, no WebGL/DOM | delete `frontend/src/lib/` + tests |
| 3 | Viewer UI (`GeometryScene` + `ValidatorDashboard`) | PR 3 | `npm run build` | `npm run dev` + browser upload `.obj` against backend | delete `frontend/src/components/` |

## Phase 1: Foundation / Infrastructure

- [x] 1.1 Install Node.js + npm (prerequisite; resolves Spec R1 "Node.js prerequisite missing").
- [x] 1.2 Create `frontend/package.json`: pinned deps (astro ^5, @astrojs/react ^4, react ~19.0.0, react-dom ~19.0.0, three ^0.170.0, @react-three/fiber ^9, @react-three/drei ^10; dev @types/react, @types/react-dom, @types/three); `scripts.build="astro build"`, `scripts.test="vitest run"`.
- [x] 1.3 Create `frontend/astro.config.mjs`: `integrations:[react()]` + `vite.server.proxy['/api']` target `http://127.0.0.1:8000`, `rewrite: p => p.replace(/^\/api/,'')` (Spec R1).
- [x] 1.4 Create `frontend/tsconfig.json`: Astro strict TS, `jsx: react-jsx`.
- [x] 1.5 Create `frontend/src/layouts/Layout.astro`: html shell + global CSS link.
- [x] 1.6 Create `frontend/src/styles/global.css`: SketchUp-style viewport + panel.
- [x] 1.7 Create `frontend/src/pages/index.astro`: renders `<ValidatorDashboard client:only="react" />`.
- [x] 1.8 `npm install` then `npm run build` — empty scaffold builds (Spec R1 "Build succeeds").

## Phase 2: Core Implementation

- [x] 2.1 Create `frontend/src/lib/obj.js`: `groupVerticesByObject(text)` splits on `o `/`g `; `computePerObjectAABBs` via `THREE.Box3.setFromPoints`; fallback to global `report.aabb` when no names (Spec R3).
- [x] 2.2 Create `frontend/src/lib/api.js`: `fetchRules()` GET `/api/extract-rules`; `validateGeometry(file)` POST FormData field `file` to `/api/validate-geometry`; `autocorrect(dsl)` POST JSON to `/api/autocorrect` (Spec R4).
- [x] 2.3 Create `frontend/src/components/GeometryScene.jsx`: `<Canvas>` camera/lights/OrbitControls/drei `<Grid>`; meshes via `OBJLoader.parse`; auto-fit camera; AABB `LineSegments` green/red (Spec R2, R3).
- [x] 2.4 Create `frontend/src/components/ValidatorDashboard.jsx`: state machine `idle→loading→loaded(pass|violations)→empty→error`; upload control; violations panel; autocorrect re-validate (Spec R4, R5).

## Phase 3: Testing / Verification

- [x] 3.1 Add Vitest config to `frontend/` + confirm `scripts.test` resolves.
- [x] 3.2 Unit tests for `obj.js`: `groupVerticesByObject`, fallback path, violation→color mapping (Spec R3 "Passing object", "Violating object").
- [x] 3.3 Integration tests for `api.js`: URL shape, FormData `file` field, DSL body shape (Spec R4).
- [x] 3.4 `npm run build` final gate; verify Spec R2 (Geometry renders, Auto-fit camera) + R5 (Loading, Backend unreachable, Upload error, Empty report) manually against backend.

## Phase 4: Cleanup

- [x] 4.1 Confirm exact `three` minor vs `drei@10` peer; record resolved version in `package.json` (design Open Question).

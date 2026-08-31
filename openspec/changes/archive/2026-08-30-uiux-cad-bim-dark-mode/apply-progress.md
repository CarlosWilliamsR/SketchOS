# Apply Progress: CAD/BIM Dark Mode Studio UI Redesign

## Work Unit: PR #1 — CSS Theme System + SVG Icons + Dark Mode Migration

**Status**: ✅ Complete (committed as `9aae9e1`)

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.8 | N/A | N/A | ✅ 18/18 | N/A | ✅ Passed | ➖ Structural | ✅ Clean |
| 1.2 | `global.css.test.js` | Unit | ✅ 18/18 | ✅ Written | ✅ Passed | ✅ 29 cases | ✅ Clean |
| 1.3–1.5 | `global.css.test.js` | Unit | ✅ 47/47 | N/A | ✅ Passed | ➖ Covered | ✅ Clean |
| 1.1 | `icons.test.jsx` | Component | ✅ 47/47 | ✅ Written | ✅ Passed | ✅ 42 cases | ✅ Clean |
| 1.7 | `icons.test.jsx` | Component | ✅ 47/47 | N/A | ✅ Passed | ➖ Covered | ✅ Clean |
| 1.6 | N/A | N/A | ✅ 89/89 | N/A | ✅ Done | ➖ Structural | ✅ Clean |
| 1.9 | N/A | N/A | ✅ 89/89 | N/A | ✅ Done | ➖ Structural | ✅ Clean |
| 1.10 | `global.css.test.js` | Unit | ✅ 89/89 | N/A | ✅ Audited | ➖ Covered | ✅ Clean |

## Work Unit: PR #2 — 3-Tab Sidebar + BYOK Modal + Header Injection

**Status**: ✅ Complete (committed as `1fee15b`, pushed to `main`)

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.1 | `ValidatorDashboard.test.jsx` | Component | ✅ 114 baseline (16 RED) | ✅ Written | ✅ Passed | ✅ 18 cases | ✅ Clean |
| 2.2 | `BYOKModal.test.jsx` | Component | N/A (new) | ✅ Written | ✅ Passed | ✅ 18 cases | ✅ Clean |
| 2.3 | `api.test.js` | Unit | ✅ | ✅ Written | ✅ Passed | ✅ 5 BYOK cases | ✅ Clean |
| 2.4–2.8 | `ValidatorDashboard.test.jsx` | Component | ✅ 130/130 | ✅ Written | ✅ Passed | ✅ nav+ARIA covered | ✅ Clean |
| 2.9–2.10 | `BYOKModal.test.jsx` | Component | ✅ | ✅ Written | ✅ Passed | ✅ CRUD covered | ✅ Clean |
| 2.11 | `api.test.js` | Unit | ✅ | ✅ Written | ✅ Passed | ✅ 5 cases | ✅ Clean |
| 2.12 | (full suite) | All | ✅ 130/130 | N/A (verify) | ✅ Passed | ➖ Verify step | ✅ Clean |

## Work Unit: PR #3 — Viewport Clay Render + Clip Planes + Camera Presets + HUD

**Status**: ✅ Complete (this batch)

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 3.3 | `viewport.test.js` | Unit | ✅ 130/130 | ✅ Written | ✅ Passed | ✅ 17 cases | ✅ Clean |
| 3.1 | `SceneStatsContext.test.jsx` | Component | ✅ 130/130 | ✅ Written | ✅ Passed | ✅ 7 cases | ✅ Clean |
| 3.2 | `GeometryScene.test.jsx` | Component | ✅ 130/130 | ✅ Written | ✅ Passed | ✅ 7 cases | ✅ Clean |
| 3.4 | `SceneStatsContext.jsx` | N/A | ✅ | N/A | ✅ Passed | ➖ Covered by 3.1 | ✅ Clean |
| 3.5 | `GeometryScene.jsx` | N/A | ✅ | N/A | ✅ Passed | ➖ Covered by 3.1/3.2 | ✅ Clean |
| 3.6 | `GeometryScene.jsx` | N/A | ✅ | N/A | ✅ Passed | ➖ Covered by 3.3 constants | ✅ Clean |
| 3.7 | `GeometryScene.jsx` | N/A | ✅ | N/A | ✅ Passed | ➖ Covered by 3.3 positions | ✅ Clean |
| 3.8 | `GeometryScene.jsx` | N/A | ✅ | N/A | ✅ Passed | ➖ Covered by 3.3 concat + 3.2 toggles | ✅ Clean |
| 3.9 | `SceneStatsBar` (context) | N/A | ✅ | N/A | ✅ Passed | ➖ Covered by 3.1 | ✅ Clean |
| 3.10 | `global.css` + `SceneStatsBar` | N/A | ✅ | N/A | ✅ Passed | ➖ Structural | ✅ Clean |
| 3.11 | `GeometryScene.jsx` | N/A | ✅ | N/A | ✅ Passed | ➖ Covered by 3.2 pointerEvents | ✅ Clean |
| 3.12 | (full suite) | All | ✅ 130→161 | N/A (verify) | ✅ Passed | ➖ Verify step | ✅ Clean |
| 3.13 | `global.css` audit | Unit | ✅ | N/A | ✅ Audit passed | ➖ Covered | ✅ Clean |

### Test Summary (PR #3)
- **Total tests passing**: 161 across 9 files (was 130 after PR #2)
- **New tests in PR #3**: 31 (17 viewport + 7 SceneStatsContext + 7 GeometryScene)
- **Layers used**: Unit (17), Component (14)

### Focused Test Command Result
```
npx vitest run   →   Test Files 9 passed (9) | Tests 161 passed (161)
npm run build    →   Complete! (1 page built; 606 modules transformed)
```

### Work Unit Evidence (PR #3)

| Evidence | Value |
|---|---|
| Focused test command + result | `npx vitest run` → 9 files / 161 tests passed, exit 0 |
| Runtime harness + result | `npm run build` (astro build, static) → Complete, 1 page; `npm run dev` scenario: clay render + 4 camera presets + Z/Y clip + HUD "—" (manual, not automated) |
| Rollback boundary | Revert `GeometryScene.jsx` (viewport controls), `SceneStatsContext.jsx`, `viewport.js` + their tests, `global.css` HUD block — restores pre-PR#3 viewport without touching PR #1/#2 theme + sidebar |

### Files Created (PR #3)
| File | Description |
|------|-------------|
| `frontend/src/lib/viewport.js` | Pure helpers: clay constants, cameraPresetPosition, buildClippingPlanes, formatMetrics, countMeshStats |
| `frontend/src/lib/viewport.test.js` | 17 pure-function tests |
| `frontend/src/contexts/SceneStatsContext.jsx` | SceneStatsProvider + useSceneStats + SceneStatsBar (explicit setStats, "—" empty state) |
| `frontend/src/contexts/SceneStatsContext.test.jsx` | 7 context tests |
| `frontend/src/components/GeometryScene.test.jsx` | 7 component tests (Canvas/drei mocked) |

### Files Modified (PR #3)
| File | What Changed |
|------|-------------|
| `frontend/src/components/GeometryScene.jsx` | PBR matte `#94a3b8` (roughness 0.85) + EdgesGeometry `#60a5fa` renderOrder 1; 4 camera presets (lerp 0.08); Z+Y clip planes (per-material, localClippingEnabled); HUD Html overlay (pointerEvents none/auto); stats via useEffect setStats |
| `frontend/src/styles/global.css` | HUD overlay styles: preset buttons (semi-transparent), clip controls, 28px status bar (--font-mono + tabular-nums) |

### Deviations from Design
1. **Per-material clipping (not renderer-global).** The spec wrote "renderer.clippingPlanes SHALL be set via array concatenation", but Three.js applies clipping per-material: with `renderer.localClippingEnabled = true`, each material's own `clippingPlanes` is used and the renderer-global array is ignored. Per the orchestrator's explicit technical constraint, the concat array is computed by the pure `buildClippingPlanes()` and assigned to every mesh material (`material.clipping`, `material.clippingPlanes`, `material.clipShadows`) with `localClippingEnabled = true`. The array logic itself is exactly the spec's `(clipZ ? [zPlane] : []).concat(clipY ? [yPlane] : [])`.
2. **Lerp factor 0.08 (not 0.1).** The spec scenario says factor 0.1; the design decision table and task 3.7 both specify 0.08 (`CAMERA_LERP_FACTOR`). Followed tasks/design.
3. **Soft shadows (PCFSoftShadowMap) not implemented.** Listed in the scope note but marked "Deferred" in the design decision table and absent from the proposal in-scope list and the tasks (3.1–3.13). No shadow task exists; deferred.
4. **Stats context default is `null` (not a zero object) internally**, while `DEFAULT_SCENE_STATS = {triangles:0,objects:0,aabbMs:0}` is exported for the zero shape. `null` is the "no geometry loaded" sentinel that lets the HUD distinguish "—" (empty) from an explicit zero. This is the fix for verify bug #3.

### Issues Found
None blocking. The `#4a4d52` / `#2f3134` grid cell/section colors remain hardcoded in GeometryScene JSX — pre-existing from PR #1, outside the PR #3 removal list (`#3a3d41`/`#cfd3d7`/`#d7dade`, all now removed).

## Rollback Boundary (cumulative)
Revert PR #3 → PR #2 → PR #1 in reverse order; each PR is autonomous.

## Remaining Tasks
- [x] All tasks 1.1–3.13 complete.

## Workload / PR Boundary
- Mode: auto-chain (stacked-to-main)
- PR #1 → `9aae9e1`, PR #2 → `1fee15b`, PR #3 → next commit on `main`
- PR #3 authored size: ~314 insertions / 32 deletions (GeometryScene.jsx + global.css) plus 3 new lib/context modules + 3 new test files.

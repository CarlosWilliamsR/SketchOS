# Apply Progress: frontend-validator-dashboard-3d

- **Change**: frontend-validator-dashboard-3d
- **Mode**: Standard (no `openspec/config.yaml`, no `strict_tdd`)
- **Delivery**: ask-on-risk → resolved chained PRs; chain strategy `stacked-to-main`
- **PR slices**: PR 1 (foundation/infrastructure) DONE · PR 2 (libs + components) DONE · PR 3 (tests + pin) DONE
- **Date**: 2026-08-24

## Task Progress

### Phase 1: Foundation / Infrastructure — COMPLETE (PR 1)

- [x] 1.1 Install Node.js + npm
- [x] 1.2 Create `frontend/package.json`
- [x] 1.3 Create `frontend/astro.config.mjs`
- [x] 1.4 Create `frontend/tsconfig.json`
- [x] 1.5 Create `frontend/src/layouts/Layout.astro`
- [x] 1.6 Create `frontend/src/styles/global.css`
- [x] 1.7 Create `frontend/src/pages/index.astro`
- [x] 1.8 `npm install` + `npm run build`

### Phase 2: Core Implementation — COMPLETE (PR 2)

- [x] 2.1 `frontend/src/lib/obj.js`
- [x] 2.2 `frontend/src/lib/api.js`
- [x] 2.3 `frontend/src/components/GeometryScene.jsx`
- [x] 2.4 `frontend/src/components/ValidatorDashboard.jsx` (full)

### Phase 3: Testing / Verification — COMPLETE (PR 3)

- [x] 3.1 Vitest config
- [x] 3.2 `obj.js` unit tests
- [x] 3.3 `api.js` integration tests
- [x] 3.4 Final build gate + `npm test` gate (manual R2/R5 browser verify deferred)

### Phase 4: Cleanup — COMPLETE

- [x] 4.1 Confirm `three` minor vs `drei@10` peer (resolved in PR 1; re-confirmed here — no `package.json` change)

## Work Unit Evidence

### PR 1 (foundation)

| Evidence | Result |
|---|---|
| Focused test command | `npm run build` → exit 0, "1 page(s) built in 997ms", "Complete!", zero errors |
| Runtime harness | `npm run dev` (Astro on :4321) + `curl http://localhost:4321/api/extract-rules` → HTTP 200 `{"min_height":2.0}`; echo backend on :8000 logged `GET /extract-rules` (rewrite stripped `/api`) |
| Rollback boundary | `rm -rf frontend/` (backend, `validator_go/`, `blender-mcp/` untouched) |

### PR 2 (libs + components)

| Evidence | Result |
|---|---|
| Focused test command | `npm run build` → exit 0, "1 page(s) built in 3.50s", "Complete!", zero errors; 595 modules transformed |
| Runtime harness | Live FastAPI backend on :8000 (`VALIDATOR_GO_BIN=/home/david/go/bin/validator-go`) + `npm run dev` on :4321; `curl http://localhost:4321/api/extract-rules` → HTTP 200 `{"min_height":2.0,"max_height":0.0,"min_thickness":0.1,"max_thickness":0.0}` (proxy rewrite verified end-to-end); `/` → HTTP 200 with `ValidatorDashboard` island present |
| Rollback boundary | `git checkout -- frontend/src/lib frontend/src/components frontend/src/styles/global.css` (slice 2 files only; PR 1 scaffold untouched) |

### PR 3 (tests + pin)

| Evidence | Result |
|---|---|
| Focused test command | `npm test` (vitest run v4.1.11) → **exit 0**; "Test Files 2 passed (2), Tests 18 passed (18)", ~154 ms |
| Runtime harness | `npm run build` → **exit 0**, "1 page(s) built in 3.38s", "Complete!", 595 modules transformed (real Astro/Vite production bundle emitted to `dist/`). Interactive R2 (geometry renders / auto-fit camera) + R5 (loading / backend-unreachable / upload-error / empty-report) browser verification is a **manual** step, deferred per design "E2E deferred" — backend was not running in this slice and the binding scopes R2/R5 to manual note only. |
| Rollback boundary | delete `frontend/vitest.config.js`, `frontend/src/lib/obj.test.js`, `frontend/src/lib/api.test.js`; revert the `colorForBox` extraction in `frontend/src/lib/obj.js` + `frontend/src/components/GeometryScene.jsx`; `npm uninstall vitest` (and remove the devDep from `package.json`). No production-code behavior is otherwise touched. |

Note: the repo has no git commits yet (everything untracked on `master`), so rollback is expressed at the file level rather than `git checkout`.

## Files Changed

| File | Action | Notes |
|------|--------|-------|
| `frontend/src/lib/obj.js` | Created | `groupVerticesByObject` (split on `o `/`g `) + `computePerObjectAABBs` (`Box3.setFromPoints`, global-`aabb` fallback) |
| `frontend/src/lib/api.js` | Created | `fetchRules`/`validateGeometry`/`autocorrect` + `ApiError`; all via `/api/*` |
| `frontend/src/components/GeometryScene.jsx` | Created | R3F `<Canvas>` + lights + `OrbitControls` + drei `<Grid>`; meshes via `OBJLoader.parse`; auto-fit camera; per-object `<Edges>` AABB green/red |
| `frontend/src/components/ValidatorDashboard.jsx` | Replaced stub | Full state machine `idle→loading→loaded(pass|violations)→empty→error`; upload control; rules on mount; violations panel; DSL textarea + autocorrect re-validate |
| `frontend/src/styles/global.css` | Extended | Panel sections, upload control, rules table, status banner, violation/fix lists, DSL editor, viewport overlay states, spinner |
| `frontend/vitest.config.js` | Created | `environment: node`, `include: ['src/**/*.test.js']` |
| `frontend/src/lib/obj.test.js` | Created | 11 unit tests: grouping (o/g split, malformed skip, non-vertex skip), per-object AABB, global-aabb fallback, empty fallback, `colorForBox` green/red + constants |
| `frontend/src/lib/api.test.js` | Created | 7 integration tests: URL shape (`/api/*`), FormData `file` field + filename, DSL JSON body shape, ApiError status/detail/network/unreachable, non-JSON fallback, Error subclass |
| `frontend/src/lib/obj.js` | Modified | Added `PASS_COLOR`/`VIOLATION_COLOR` + pure `colorForBox(name, violatingObjects)` (testability extraction — see Deviations) |
| `frontend/src/components/GeometryScene.jsx` | Modified | Now imports `colorForBox` from `obj.js`; removed inline `PASS_COLOR`/`VIOLATION_COLOR` duplication |
| `frontend/package.json` | Modified | Added devDependency `vitest ^4.1.11` (`scripts.test="vitest run"` already present) |

## Environment (Prerequisite 1.1)

- Node.js **v24.19.0 (Krypton LTS)** + npm **11.17.0** via official `linux-x64` tarball → `~/.local/node`, binaries symlinked into `~/.local/bin` (already on PATH).
- `npm install`: 389 packages added (24s). PR 3 adds `vitest` (+23 packages, 413 total).

## Dependency Resolution (design Open Question 4.1)

`npm ls` confirms a clean tree, no peer/invalid issues (resolved in PR 1, re-confirmed in PR 3):

| Package | Resolved |
|---|---|
| `astro` | 5.18.2 |
| `@astrojs/react` | 4.4.2 |
| `react` / `react-dom` | 19.0.8 (satisfies `~19.0.0` and fiber@9 peer `>=19 <19.3`) |
| `three` | 0.170.0 (exact; `^0.170.0` did not drift — caret on 0.x pins the minor) |
| `@react-three/fiber` | 9.7.0 |
| `@react-three/drei` | 10.7.8 (peer accepts `three@0.170.0`) |
| `@types/react` / `@types/react-dom` / `@types/three` | 19.2.18 / 19.2.5 / 0.170.0 |
| `vitest` (new, dev) | 4.1.11 |

`three` minor is already recorded as `^0.170.0` in `package.json`; no change required (task 4.1 done).

## Deviations from Design

- **PR 1**: added `dev`/`preview` scripts and `frontend/.gitignore` (Astro scaffold hygiene). `changeOrigin: true` added to the proxy entry (conventional).
- **PR 2 (DSL source)**: the design's data flow shows `autocorrect` consuming a "JSON DSL" but does not specify where the dashboard obtains that DSL — `/validate-geometry` returns only `{status, report}` and the upload is `.obj`-bytes-only, so the DSL cannot be reconstructed client-side. Resolution: a DSL `<textarea>` in the side panel holds the full ArchitecturalDSL JSON; the "Autocorrect & re-validate" button POSTs it to `/api/autocorrect`. After autocorrect the returned `{status, report, fixes}` re-renders the panel/status/overlays; the 3D viewport keeps the last uploaded `.obj` (the backend does not return corrected `.obj` bytes, only a corrected report).
- **AABB overlay primitive**: design allows "`LineSegments`/`Edges`"; used drei `<Edges>` (Line2 fat lines) over a `THREE.BoxGeometry` per object for a SketchUp-like look, rather than raw `LineSegments`. Still maps min/max → `Box3` with no axis swap.
- **Global-fallback box color**: when the OBJ has no `o`/`g` names, the single global box is colored red if any violations exist, green otherwise (name-based matching is impossible with no names).
- **PR 3 (testability extraction)**: task 3.2 requires unit tests for "violation→color mapping", but PR 2 left that decision inline inside the `GeometryScene.jsx` `overlays` useMemo (only reachable through an R3F render path). Extracted it into a pure `colorForBox(name, violatingObjects)` + `PASS_COLOR`/`VIOLATION_COLOR` constants in `obj.js` so the tests target real production logic rather than a dead duplicate; `GeometryScene.jsx` now imports `colorForBox` (single source of truth). No runtime behavior change.

## Issues / Risks

- **PR 1**: `npm audit` reports 3 vulnerabilities (astro@5.18.2, esbuild, sharp) — out of scope (design pins `astro ^5`); flagged for a future maintenance pass.
- **PR 2**: `vite` warns the dashboard chunk is ~908 kB (246 kB gzip) — three + R3F + drei are heavy; expected for a client-side 3D island and not a build error. Code-splitting/dynamic-import is a possible future optimization, out of scope for this slice.
- **PR 3**: `npm audit` still reports 3 vulnerabilities (unchanged; `vitest` adds none). The 907.65 kB dashboard chunk warning persists (same as PR 2).
- **Manual verification still outstanding**: interactive R2 (3D render + auto-fit camera) and R5 (loading / backend-unreachable / upload-error / empty-report states) require a live backend + browser session; they are manual per design "E2E deferred" and were not automated in this slice. Recommended for the `sdd-verify` phase or a human browser pass with the FastAPI backend on :8000.

## PR Boundary

- Mode: chained PR slice (stacked-to-main)
- Current unit: PR 3 — Vitest + tests + three-minor pin (5 tasks: 3.1–3.4 + 4.1)
- Boundary: starts from the PR 2 libs/components, ends at `npm test` exit 0 (18 tests) + `npm run build` exit 0, with the three minor re-confirmed
- Review budget: 4 new files + 3 small edits (~300 authored lines incl. 2 test files + vitest config); well under the 400-line budget and self-contained to `frontend/`

# Design: Frontend Validator Dashboard (3D)

## Technical Approach

Greenfield `frontend/` Astro 5 app. One React island `ValidatorDashboard.jsx` (`client:only="react"`) hosts an R3F `<Canvas>`. The browser fetches same-origin `/api/*`, forwarded by Astro's Vite dev proxy to FastAPI on `127.0.0.1:8000` (zero backend change, no CORS). The backend router is **prefix-less** (`/extract-rules`, `/validate-geometry`, `/autocorrect`), so the proxy rewrites `/api` off the path. Per-object AABBs are computed client-side because the Go report exposes only a global `aabb` and two measurements per object.

## Architecture Decisions

### Decision 1: Vite proxy with `/api` rewrite

| option | tradeoff | decision |
|---|---|---|
| Astro Vite proxy `/api` → `:8000` + rewrite | zero backend change; same-origin; rewrite strips `/api` because backend routes are prefix-less | **chosen** |
| CORSMiddleware on FastAPI | ~5-line backend change; still needs absolute base URL | rejected |

### Decision 2: client-side per-object AABB

| option | tradeoff | decision |
|---|---|---|
| group vertices by `o`/`g` name → `Box3.setFromPoints` | needs a manual OBJ-text pass; bytes already in-browser from upload | **chosen** |
| global box only + mesh tint | simpler but cannot color per-wall | rejected (spec requires per-object green/red) |

### Decision 3: dependency pinning

| option | tradeoff | decision |
|---|---|---|
| `@react-three/fiber@9` + react `~19.0.0` | fiber@9 peers `react >=19 <19.3`, `three >=0.156` | **chosen** |
| react `^19` unbounded | caret drifts to 19.3+ → peer conflict breaks scaffold | rejected |

Pinned set: `astro ^5`, `@astrojs/react ^4`, `react ~19.0.0`, `react-dom ~19.0.0`, `three ^0.170.0`, `@react-three/fiber ^9`, `@react-three/drei ^10`; dev `@types/react`, `@types/react-dom`, `@types/three`.

## Data Flow

```
mount ──GET /api/extract-rules────────────▶ thresholds{min_height,…}
upload .obj ──FormData(file=...)──▶ POST /api/validate-geometry ──▶ {status, report}
report ──▶ FileReader.readAsText ──▶ OBJLoader.parse ──▶ meshes
        └─▶ group vertices by o/g ──▶ per-object Box3 ──▶ overlay green/red
autocorrect ──JSON DSL──▶ POST /api/autocorrect ──▶ {status, report, fixes} ──▶ re-render
```

Component state machine: `idle → loading → loaded(pass|violations) → error`; `empty` branch for reports with no objects.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/package.json` | Create | pinned deps above; `scripts.build = "astro build"` |
| `frontend/astro.config.mjs` | Create | `integrations:[react()]` + `vite.server.proxy['/api']` target `http://127.0.0.1:8000`, `rewrite: p => p.replace(/^\/api/, '')` |
| `frontend/tsconfig.json` | Create | Astro strict TS, `jsx: react-jsx` |
| `frontend/src/pages/index.astro` | Create | renders `<ValidatorDashboard client:only="react" />` |
| `frontend/src/layouts/Layout.astro` | Create | html shell + global CSS link |
| `frontend/src/components/ValidatorDashboard.jsx` | Create | island: state machine, upload control, violations panel |
| `frontend/src/components/GeometryScene.jsx` | Create | `<Canvas>` camera/lights/OrbitControls/Grid/meshes/overlays |
| `frontend/src/lib/obj.js` | Create | `groupVerticesByObject(text)` + `computePerObjectAABBs` |
| `frontend/src/lib/api.js` | Create | `fetchRules`, `validateGeometry(file)`, `autocorrect(dsl)` |
| `frontend/src/styles/global.css` | Create | SketchUp-style viewport + panel styling |

## Interfaces / Contracts

Report JSON (from `validator_go/internal/report`; field order fixed, nil slices → `[]`):

```json
{
  "aabb": {"min":{"x":0,"y":0,"z":0}, "max":{"x":10.25,"y":3,"z":5},
           "dimensions":{"dx":10.25,"dy":3,"dz":5}},
  "objects": [{"name":"wall_1","height":3,"thickness":0.25}],
  "violations": [{"type":"wall_height_min","object":"wall_1",
                  "measured":1.5,"threshold":2,"message":"..."}]
}
```

| endpoint | method | body | returns |
|---|---|---|---|
| `/api/extract-rules` | GET | — | `{min_height, max_height, min_thickness, max_thickness}` (0 = unenforced) |
| `/api/validate-geometry` | POST | multipart field `file` (.obj bytes) | `{status: "pass"|"violations", report}` |
| `/api/autocorrect` | POST | JSON = full ArchitecturalDSL payload | `{status, report, fixes[]}` |

Status mapping: 422 parse error (`detail=stderr`), 503 spawn failure, 504 timeout.

**Per-object AABB**: split OBJ text on `o ` / `g ` lines into named vertex groups; build `THREE.Box3().setFromPoints(vertices)` per group. Match each object to `report.violations[].object` by name → red; no match → green. Fallback when no `o`/`g` names exist: single global box from `report.aabb`. Y-up maps directly (`min/max` → `THREE.Vector3`), no axis swap.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Build gate | scaffold + types + SSR-avoidance | `npm run build` (primary gate) |
| Unit | `groupVerticesByObject`, fallback path, violation→color mapping | Vitest, no WebGL needed |
| Integration | API helper URL/FormData/DSL body shape | Vitest + fetch mock |

E2E deferred: requires Node + running backend + browser; not gate.

## Threat Matrix

N/A — no shell, subprocess, VCS/PR automation, executable classification, or runtime process-integration boundary. The `/api` proxy is static dev config; it accepts no dynamic input.

## Migration / Rollout

No migration. Rollback: delete `frontend/` (backend untouched).

## Open Questions

- [x] Exact `three` minor — resolved on first `npm install`: `three@0.170.0` (exact; caret `^0.170.0` pins the minor for 0.x), `@react-three/drei@10.7.8` peer accepts `three@0.170.0`, `@react-three/fiber@9.7.0`. No `package.json` change required.

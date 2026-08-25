## Exploration: frontend-validator-dashboard-3d

### Current State

The repo (no commits, no remote — everything uncommitted in the working tree) has three
completed backend components plus three archived SDD changes under `openspec/changes/archive/`:

- `backend/` — FastAPI + FastMCP, src-layout, Python 3.14 (`pyproject.toml` requires-python `>=3.10`).
- `blender-mcp/` — Blender MCP addon/server driving geometry generation.
- `validator_go/` — Go 1.26 CLI validator: read-only, single-pass streaming, deterministic JSON report, exit codes `0` pass / `1` violations / `2` parse error.
- `openspec/specs/` — main specs for `arch-dsl`, `arch-macros`, `backend-service`, `blender-mcp-client`, `geometry-validator`. (No `openspec/config.yaml` exists yet.)

The frontend is **greenfield**: no `frontend/` directory, no `package.json` anywhere in the
tree. **Critical environment finding: Node.js/npm is NOT installed** (`node`/`npm` → "command
not found"); Go 1.26.5 and Python 3.14.6 are present. The apply phase will need to install Node
first.

#### Backend HTTP contract (the exact shape the frontend consumes)

Backend is served by `uvicorn` on `127.0.0.1:8000` (`main.py`). The three validator endpoints
live on an `APIRouter` with **no path prefix** and no CORS middleware:

1. `GET /extract-rules` — no body. Returns 200:
   `{"min_height": 2.0, "max_height": 0, "min_thickness": 0.1, "max_thickness": 0}`.
   A value of `0` signals an unenforced bound. Errors: 503 (validator binary spawn failure), 504 (timeout).

2. `POST /validate-geometry` — **multipart/form-data**, one `UploadFile` field named `file`
   carrying raw `.obj` bytes (`file: UploadFile = File(...)`). Returns 200:
   `{"status": "pass"|"violations", "report": <report>}`. On Go exit 2 (parse error) returns
   422 with `detail = stderr`. Errors: 422 / 503 / 504.

3. `POST /autocorrect` — **JSON body** = a full ArchitecturalDSL payload
   (`ArchitectureModel.model_validate(payload)`), NOT a file. Returns 200:
   `{"status": ..., "report": <report>, "fixes": [...]}` where `fixes` is a list of
   `{wall_id, rule, dimension, from, to}`. Errors: 422 invalid DSL, 422 parse error, 502 Blender error, 503, 504.

Status mapping is centralized in `validator_routes.py`: spawn → 503, timeout → 504, parse (exit 2) → 422, pass/violations → 200.

#### Go validator report JSON schema

`validator_go/internal/report/report.go` (field order fixed: `aabb`, `objects`, `violations`;
nil slices serialize as `[]`) + `validate/rules.go`:

```json
{
  "aabb": {
    "min": {"x": 0, "y": 0, "z": 0},
    "max": {"x": 10.25, "y": 3, "z": 5},
    "dimensions": {"dx": 10.25, "dy": 3, "dz": 5}
  },
  "objects": [
    {"name": "wall_1", "height": 3, "thickness": 0.25}
  ],
  "violations": [
    {"type": "wall_height_min", "object": "wall_1", "measured": 1.5, "threshold": 2, "message": "wall_height_min: object \"wall_1\" measured 1.500 m, limit 2.000 m"}
  ]
}
```

- **AABB** (global only): `min{x,y,z}`, `max{x,y,z}`, `dimensions{dx,dy,dz}`.
- **ObjectMeasurement**: `name`, `height`, `thickness`. Names follow Blender `_add_cube`
  convention (`wall_<id>`, `floor_<id>`, `volume_<id>`). **No per-object bounding box is
  returned** — only the two measurements.
- **Violation**: `type` ∈ `wall_height_min | wall_height_max | wall_thickness_min | wall_thickness_max`,
  `object` (the Blender/OBJ name), `measured`, `threshold`, `message`.

**Axis convention (critical for 3D mapping)**: the OBJ export is **Y-up** (Blender). Wall
height = Y extent (`maxY - minY`), thickness = `min(dx, dz)`. Three.js is also Y-up by default,
so the AABB `min`/`max` map **directly** to
`new THREE.Box3(new Vector3(min.x, min.y, min.z), new Vector3(max.x, max.y, max.z))`
with **no axis swap**.

### Affected Areas

- `frontend/` — **NEW**. Entire Astro app (scaffold, `astro.config.mjs`, `src/components/ValidatorDashboard.jsx`).
- `frontend/package.json` — **NEW**. `astro`, `@astrojs/react`, `react`, `react-dom`, `three`, `@react-three/fiber`, `@react-three/drei`.
- `backend/src/sketchos_backend/main.py` — add `CORSMiddleware` only if browser-origin fetch is chosen over the Astro proxy (no backend change otherwise).
- `openspec/specs/` — **NEW** `frontend` domain delta spec.
- No changes to `validator_go/`, `blender-mcp/`, `arch_dsl.py`, `arch_macros.py`.

### Approaches

1. **Astro + single React island (`client:only="react"`) hosting an R3F `<Canvas>`** (recommended)
   - Astro shell (static/hybrid) with one `ValidatorDashboard.jsx` island mounted `client:only="react"`; WebGL runs purely client-side.
   - Pros: matches the change intent exactly; Astro handles routing/static delivery; zero-JS-by-default for the shell.
   - Cons: island boundary adds a build concept; the canvas must never be SSR'd.
   - Effort: Medium

2. **Pure React SPA (Vite), no Astro**
   - Pros: simpler mental model; R3F docs assume Vite.
   - Cons: contradicts the explicit "using Astro" intent.
   - Effort: Low (off-intent)

3. **Client-side `.obj` parse vs server-side parse**
   - (a) Client: `FileReader.readAsText` on the uploaded file → `OBJLoader.parse(text)` → mesh; per-object AABBs computed in the browser by grouping vertices by `o`/`g` name.
   - (b) Server: Astro endpoint proxies to FastAPI and returns pre-parsed geometry.
   - Pros of client: the bytes are already in the browser (the user uploaded them), no extra hop, `.obj` is trivial to parse. Cons: large models jank the main thread; needs a manual grouping pass for per-object boxes.
   - Recommend (a).
   - Effort: Low

4. **AABB overlay strategy — global box vs per-object boxes**
   - The report's `aabb` is **global only**; per-object boxes are absent. To draw green/red
     per-wall boxes the frontend must compute per-object AABBs itself from the parsed geometry.
   - Effort: Low (but see Risks — this is the key semantic fork)

### Recommendation

Astro 5 + React 19 + `@react-three/fiber@9` + `@react-three/drei@10` + `three@^0.1xx`
(pin the exact coherent set at proposal time — R3F v8↔React 18, v9↔React 19, v10 requires
react ≥19 <19.3). One React island `ValidatorDashboard.jsx` mounted `client:only="react"`
hosting an R3F `<Canvas>` with drei `OrbitControls`, a `Grid` helper (SketchUp-style ground
plane), directional + ambient lighting, and an auto-fit camera centered on the global AABB.

Flow: on mount `fetch('/api/extract-rules')`; on file select/drop, POST the `.obj` as
`FormData` to `/api/validate-geometry`; parse the report; render the `.obj` via `OBJLoader.parse`;
overlay the global AABB as an `EdgesGeometry`/`LineSegments` box; compute per-object AABBs
client-side and color the violated wall's box **red**, passing walls **green**; surface the
`violations` list in a side panel (object, rule, measured vs threshold).

Dev integration: use Astro's Vite dev proxy (`vite.server.proxy` in `astro.config.mjs`,
`/api` → `http://127.0.0.1:8000`) so the browser fetches same-origin and **no CORS is needed**;
expose `PUBLIC_API_BASE_URL` env var for production. (Alternative: add `CORSMiddleware` to
`main.py` allowing `http://localhost:4321` — a ~5-line backend change.)

### Risks

- **Node runtime missing** — apply phase must install Node/npm before the scaffold can run (environment blocker, not a code issue).
- **Version pairing** — R3F v8↔React 18, v9↔React 19, v10 requires react ≥19<19.3; an incoherent set breaks the scaffold immediately.
- **Global-only AABB** — the report returns one AABB; per-wall green/red boxes require client-side per-object AABB computation from parsed geometry (vertex grouping by `o`/`g` name).
- **Red/green semantics ambiguity** — is the violated *wall mesh* tinted, its *AABB overlay* red, or both? Violations reference `wall_<id>` which matches the OBJ object names, so they join cleanly; the proposal must fix overlay-vs-mesh-tint.
- **`.obj` rendering** — `OBJLoader.parse()` needs the text form (async `FileReader`); large models can block the main thread (the Go validator streams, the browser parse does not).
- **SketchUp-style look** — needs explicit grid + camera auto-fit to the global AABB; default R3F camera faces -Z and won't frame the model.
- **CORS** — direct browser fetch to `:8000` is blocked without `CORSMiddleware`; proxy or middleware required.
- **Autocorrect is DSL-only** — `/autocorrect` corrects an `ArchitectureModel` DSL payload, not an arbitrary uploaded `.obj`; a "fix" button on the .obj-upload view cannot call it directly and is out of scope for the validator view.

### Ready for Proposal

Yes. Before proposal, the orchestrator should confirm three forks with the user:
(a) per-object AABB overlays computed client-side vs global-AABB-only + mesh tinting;
(b) Astro Vite proxy (zero backend change) vs adding `CORSMiddleware` to FastAPI;
(c) whether `/autocorrect` is in scope for this dashboard (it is DSL-based, not `.obj`-based).
Also flag the missing Node.js runtime as an apply-phase prerequisite.

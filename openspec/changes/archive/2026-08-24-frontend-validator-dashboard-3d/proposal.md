# Proposal: Frontend Validator Dashboard (3D)

## Intent

Provide a browser UI for the geometry validator: upload a `.obj`, view it in an interactive SketchUp-style 3D viewport with green/red per-wall AABB overlays, and review violations. Frontend is greenfield.

## Scope

### In Scope
- `frontend/` Astro 5 scaffold: `package.json`, `astro.config.mjs` (React + `/api` Vite proxy → `127.0.0.1:8000`), `tsconfig.json`, `src/pages`, layout.
- `ValidatorDashboard.jsx` island (`client:only="react"`): fetch `/extract-rules` on mount; upload → `POST /validate-geometry` (FormData); render `.obj`; Grid + OrbitControls + auto-fit; AABB overlays (green/red); violations panel.
- Client-side per-object AABB computation (vertex grouping — Go report is global-only).
- `/autocorrect` re-validate button (see Open Decisions).
- `npm run build` + component/unit tests.

### Out of Scope
- Backend changes (no CORS with proxy), auth, deployment, SSR of the canvas, materials/textures, server-side `.obj` parsing.

## Capabilities

### New Capabilities
- `frontend-validator-dashboard`: Astro + React + R3F UI for upload, 3D visualization, AABB overlays, violations panel.

### Modified Capabilities
- None.

## Approach

Astro 5 + React 19 + `@react-three/fiber@9` + `@react-three/drei@10` + `three` (pinned set). One island hosts R3F `<Canvas>`. Mount → fetch `/api/extract-rules`; upload → POST FormData to `/api/validate-geometry`; render `.obj`; overlay global AABB as `LineSegments`; compute per-object AABBs client-side (red/green). Dev: Vite proxy `/api` → `:8000`; `PUBLIC_API_BASE_URL` for prod.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/` | New | Astro scaffold + config + src |
| `frontend/src/components/ValidatorDashboard.jsx` | New | R3F island, upload, overlays, panel |
| `frontend/package.json` | New | astro, @astrojs/react, react, react-dom, three, R3F, drei |
| `openspec/specs/frontend-validator-dashboard/` | New | New spec |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Node/npm not installed | High | Install as apply prerequisite |
| R3F/React version mismatch (v9↔R19) | Med | Pin coherent set in `package.json` |
| Global-only AABB forces client-side boxes | Med | Compute from parsed geometry |
| Large `.obj` janks main thread | Low | Async FileReader; accept slice limit |

## Rollback Plan

Delete `frontend/` and the new spec file. `backend/`, `validator_go/`, `blender-mcp/` untouched.

## Dependencies

- Node.js/npm runtime (install prerequisite). Backend on `127.0.0.1:8000` with resolvable `validator-go` binary.

## Success Criteria

- [ ] `npm run build` succeeds; scaffold renders.
- [ ] Uploading a `.obj` renders geometry with grid, orbit, auto-fit.
- [ ] Violated walls red, passing green; violations listed in panel.
- [ ] Thresholds from `/extract-rules`; report from `/validate-geometry`.

## Open Decisions (recommended defaults)

1. AABB overlays — **client-side per-object boxes** vs global-only box + mesh tint.
2. Dev integration — **Astro Vite proxy** `/api` → `:8000` vs backend CORSMiddleware.
3. `/autocorrect` — **IN scope** (DSL re-validate button) vs OUT (validate-only).

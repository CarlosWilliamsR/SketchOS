# Design: CAD/BIM Dark Mode Studio UI Redesign

## Technical Approach

Incremental CSS migration via `:root` var replacement + 3 stacked PRs, each autonomous and review-safe at ≤400 lines. Component refactors are TDD-gated: zero existing component tests → all tests written before JSX/3D changes. The prior verify failure (SceneStatsContext never propagated) is preempted via explicit `useEffect`-driven stats collection inside the Canvas boundary.

## Architecture Decisions

| Area | Option | Tradeoff | Decision |
|------|--------|----------|----------|
| CSS migration | Rewrite :root vars + audit hardcoded colors | Risk: missed hardcoded values. Mitigation: full selector audit (8 hardcoded values found) | Single-pass :root rewrite |
| Tab state | Orthogonal `activeTab` useState | Coexists with phase state machine; no persistence needed | Independent `activeTab` |
| SVG icons | Inline React components with `currentColor` | No extra deps; props: `{size?, className?}` | 7 inline SVG `.jsx` files |
| Stats propagation | `useMemo` compute + `useEffect` setStats | Prevents render-phase setState; explicit, not implicit ref→context | Explicit setStats on geometry load |
| Clipping planes | Array concatenation of per-axis planes | `localClippingEnabled`; tested both Z+Y active simultaneously | Array-based, not scalar |
| Vitest env | `jsdom` globally | obj.test.js pure math works in jsdom; no dual-env config needed | Single jsdom environment |
| Shadows | PCFSoftShadowMap | Proposal excludes shadow maps; flagged for future | Deferred |
| Camera animation | useFrame lerp (factor 0.08) | No extra deps; smooth enough for CAD presets | THREE.MathUtils.lerp |

## Data Flow

```
ValidatorDashboard
  ├─ activeTab: 'ingesta'|'normativa'|'diagnostico'
  ├─ phase: idle→loading→loaded→empty→error
  ├─ shared: rules, result, objText, fileName, error
  ├─ Tab 1: upload + file status (reads phase, fileName)
  ├─ Tab 2: rules grid (reads rules)
  ├─ Tab 3: violations + fixes + autocorrect (reads result)
  │
  └─ GeometryScene (Canvas)
       ├─ SceneStatsProvider
       │   ├─ Model: parseObj → stats via useEffect(setStats)
       │   └─ Html HUD: useContext(stats), "—" fallback
       ├─ ClipPlaneManager: useState(clipZ) + useState(clipY) → array
       └─ CameraPresets: useFrame lerp → target refs
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/styles/global.css` | Modify | Dark palette tokens, dark-theme all selectors (8 hardcoded colors → vars) |
| `frontend/src/layouts/Layout.astro` | Modify | Google Fonts `<link>` for Inter + JetBrains Mono |
| `frontend/src/components/icons/*.jsx` | Create | 7 SVG icon components (ingest, normativa, diagnostico, camera-top, camera-front, camera-side, camera-iso) |
| `frontend/src/components/ValidatorDashboard.jsx` | Modify | 3-tab layout, SVG icons, BYOK trigger |
| `frontend/src/components/BYOKModal.jsx` | Create | Portal-based modal, localStorage hook, key validation |
| `frontend/src/components/GeometryScene.jsx` | Modify | PBR matte, EdgesGeometry, clipping planes, camera presets, HUD, #0b0f19 background |
| `frontend/src/contexts/SceneStatsContext.jsx` | Create | Context + provider + useSceneStats hook |
| `frontend/src/lib/api.js` | Modify | `X-Gemini-Api-Key` header from localStorage |
| `frontend/vitest.config.js` | Modify | `environment: 'node'` → `'jsdom'` |

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Component | ValidatorDashboard render states, tab transitions | `@testing-library/react`; mock GeometryScene + api.js |
| Component | BYOKModal CRUD, localStorage, validation | `@testing-library/react`; test open/close/save/clear |
| Component | SVG icon render + currentColor | `@testing-library/react`; snapshot size prop, color inheritance |
| Unit | Camera preset positions (4 × expected Vector3) | Pure function; no Canvas needed |
| Unit | Clipping plane array logic (Z+Y combo) | Pure function; `renderer.localClippingEnabled = true` assertion |
| Unit | Stats collection (triangle/object count, "—" empty) | Pure function; no Canvas |
| Logic | api.js header injection | Extend api.test.js: assert localStorage key read + header presence |

**Canvas mocking**: GeometryScene tests mock `@react-three/fiber` Canvas to render children in jsdom without WebGL. Integration with actual Three.js rendering is verified manually.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. The change is purely a frontend refactor within the existing Vite proxy architecture (astro.config.mjs unchanged).

## PR Split

1. **PR #1 — Theme foundation**: global.css `:root` rewrite + Layout.astro fonts + SVG icons. No JSX changes. Validate old components render with dark palette.
2. **PR #2 — Sidebar refactor**: 3-tab ValidatorDashboard + BYOKModal + api.js header injection. Component tests gate every change.
3. **PR #3 — Viewport enhancement**: PBR matte, EdgesGeometry, clipping planes, camera presets, HUD status bar. SceneStatsContext with explicit setStats.

Each PR autonomous, targets main via stacked-to-main, ≤400 lines.

## Open Questions

- [ ] Shadow maps: proposal excludes them but orchestrator requested PCFSoftShadowMap. Deferred per proposal scope.
- [ ] BYOK key rotation/expiry UX: proposal treats localStorage as dev-tool scope. No refresh-token flow planned.
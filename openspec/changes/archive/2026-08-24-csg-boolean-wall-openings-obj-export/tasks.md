# Tasks: CSG boolean wall openings and OBJ export

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~350–450 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (arch_macros + tests) → PR 2 (client rewire) → PR 3 (server param + spec) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Pure `arch_macros.py` emitters + unit tests | PR 1 | `pytest backend/tests/test_arch_macros.py -q` | N/A — no Blender in CI; deterministic string assertions | delete `arch_macros.py` + `test_arch_macros.py` |
| 2 | `blender_client` cutout/rotation rewire + test relaxation | PR 2 | `pytest backend/tests/test_blender_client.py -q` | N/A — substring/golden string assertions | revert `blender_client.py` + `test_blender_client.py` |
| 3 | `server.py` `export_path` + server tests + `backend-service` delta | PR 3 | `pytest backend/tests/test_server.py -q` | N/A — SpyClient assertions | revert `server.py` + `test_server.py` + spec delta |

## Phase 1: Foundation — `arch_macros` pure module

- [x] 1.1 Create `backend/src/sketchos_backend/arch_macros.py`: `OPENING_OVEREXTEND = 0.2`, `wall_rotation(wall)` → `atan2(dy, dx)`, `cutter_params(wall, opening)` (z-center = `pos.z + h/2`, depth = `thickness + 0.2`), `emit_boolean_header()` (`_boolean_difference` def), `emit_opening_cutout(wall, opening)`, `emit_export_obj(filepath)` (Blender 4.x `bpy.ops.wm.obj_export`, filepath via `json.dumps`). No `import bpy`. → arch-macros R1–R4.
- [x] 1.2 Create `backend/tests/test_arch_macros.py`: determinism (byte-identical re-emission), overextend (depth > thickness), rotation (== `atan2`), export string contains `wm.obj_export`, importable with no Blender. → arch-macros scenarios S1–S6.

## Phase 2: Core — `blender_client` rewire

- [x] 2.1 Extend `_HEADER`: `_add_cube` returns the created object; add `_boolean_difference(target, cutter, mod_name)` helper (active-object set → BOOLEAN DIFFERENCE → `modifier_apply` → delete cutter). → blender-mcp-client MODIFIED "Code generation".
- [x] 2.2 Rewire `generate_blender_code(model, export_path: str | None = None)`: emit `emit_opening_cutout` (rotated cutter + DIFFERENCE) per opening instead of marker `_cube_line("opening_…")`; keep dangling-`wall_id` plain-marker fallback. → ADDED "Opening cutout geometry" + "Deterministic modifier lifecycle".
- [x] 2.3 Append `emit_export_obj(export_path)` after all cutouts when `export_path` is set. → MODIFIED "Optional OBJ export".
- [x] 2.4 Relax `backend/tests/test_blender_client.py`: replace exact `_add_cube("opening_o1", …)` marker asserts with substring/golden (`_boolean_difference("wall_w1", "cutter_o1", …)`; assert NO `_add_cube("opening_…")`); add angled-wall (atan2(4,3)) rotation + export-after-boolean cases. → all 5 blender-mcp-client scenarios.

## Phase 3: Server `export_path` + pending `backend-service` delta

- [x] 3.1 `backend/src/sketchos_backend/server.py`: add `export_path: str = ""` to `build_architecture` (empty → `None`) and to `build_architecture_tool`; pass through to `generate_blender_code`. → backend-service tool signature (delta PENDING).
- [x] 3.2 `backend/tests/test_server.py`: SpyClient asserts export pass-through (emitted code contains `wm.obj_export`) and no-export default (absent).
- [x] 3.3 FLAGGED — `backend-service` delta not yet in specs: add MODIFIED requirement (tool registration gains `export_path`) + ADDED "optional OBJ export" to `openspec/specs/backend-service/spec.md`. verify MUST map this task to the pending delta.

## Phase 4: Verification

- [x] 4.1 Run `pytest backend/tests -q`; confirm full pass and deterministic output across regenerations.
- [ ] 4.2 Manual/deferred E2E: confirm real boolean DIFFERENCE cutout + OBJ file in Blender (no Blender in CI).

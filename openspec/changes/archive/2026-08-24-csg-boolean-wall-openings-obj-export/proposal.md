# Proposal: CSG boolean wall openings and OBJ export

## Intent

Openings (doors/windows) are currently emitted as unrotated box markers (`rotation_z=0.0`) that ignore the wall's `atan2(dy, dx)` angle — they are not real holes. This change makes openings actual CSG boolean `DIFFERENCE` cutouts rotated to match their wall, and adds OBJ export preparation.

## Scope

### In Scope (first slice)
- New `backend/src/sketchos_backend/arch_macros.py`: pure code-emitting bpy helpers (boolean DIFFERENCE cutters, mesh extrusion, wall rotation, OBJ export).
- Emit opening cutters rotated to their wall's angle, apply a `BOOLEAN` (`operation='DIFFERENCE'`) modifier on the wall, then delete the cutter.
- OBJ export preparation: apply modifiers, join meshes, set units, export via `bpy.ops.wm.obj_export` (Blender 4.x).
- `blender_client.py` consumes `arch_macros.py` and corrects wall rotation.
- Relax `test_blender_client.py` exact-string assertions (substring/golden).

### Out of Scope (non-goals)
- Frontend (Astro + React + Three.js), Go validator, bidirectional sync, auth/persistence.
- Boolean union/intersection beyond DIFFERENCE (unless trivial).
- Exact floor polygons (floors stay bounding-box slabs).

## Capabilities

### New Capabilities
- `arch-macros`: reusable pure bpy-code-emitting macros (boolean cutters, extrusion, rotation, OBJ export).

### Modified Capabilities
- `blender-mcp-client`: openings become rotated boolean DIFFERENCE cutouts; optional OBJ export codegen.
- `arch-dsl`: None (conditional on Open Decision 1 — no change under default assumption).

## Approach

`arch_macros.py` returns deterministic bpy code strings (no Blender import), composed by `generate_blender_code` into one self-contained script — respecting the fresh-`exec(code, {"bpy": bpy})` namespace per call. Per opening: emit a cutter box overextending past wall thickness, rotated to the wall angle, add a `BOOLEAN` modifier on the wall, apply it, delete the cutter. Export uses Blender 4.x `bpy.ops.wm.obj_export`.

## Proposed Artifacts

- `proposal.md` (this) → `specs/` → `design.md` → `tasks.md` → `verify-report.md`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/src/sketchos_backend/arch_macros.py` | New | bpy code-emitting macro helpers |
| `backend/src/sketchos_backend/blender_client.py` | Modified | consume macros; CSG + export codegen; wall rotation |
| `backend/src/sketchos_backend/server.py` | Modified | optional export flag/param (or new tool — Open Decision 2) |
| `backend/src/sketchos_backend/arch_dsl.py` | Maybe | Opening sill/type (conditional) |
| `backend/tests/test_blender_client.py` | Modified | relax exact-string assertions |
| `openspec/specs/blender-mcp-client/spec.md` | Delta | boolean cutouts + OBJ export |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Cutter/wall rotation misalignment | High | cutter shares wall rotation; golden tests for angled walls |
| Coplanar/degenerate boolean faces | Med | overextend cutter past wall thickness |
| bpy active-object/context ordering errors | Med | deterministic emit order; apply-then-delete in one script |
| OBJ `filepath` on remote Blender host | Med | explicit path convention (Open Decision 3) |
| Test brittleness | Med | substring/golden assertions |

## Rollback Plan

Revert `blender_client.py`/`server.py` to marker codegen, delete `arch_macros.py`, restore exact test assertions. Working tree is uncommitted — rollback is a `git checkout` of touched files plus module removal.

## Dependencies

- Existing backend (uncommitted) and `blender-mcp` (`execute_blender_code`, Blender 4.x).

## Success Criteria

- [ ] Non-axis-aligned wall with an opening emits a rotated cutter and an applied DIFFERENCE modifier.
- [ ] `bpy.ops.wm.obj_export` is emitted after modifier application/join.
- [ ] Codegen stays deterministic; tests pass with substring/golden assertions.

## Open Decisions (proposal question round)

1. Opening vertical anchor: `position.z` = hole base (default) vs. add `sill_height`/type to `Opening`.
2. Export surface: flag/param on `build_architecture` (default) vs. new `export_architecture_obj` tool.
3. Export path: caller-supplied vs. fixed dir under a configurable root (remote host filesystem).

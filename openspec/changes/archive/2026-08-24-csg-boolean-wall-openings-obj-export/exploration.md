## Exploration: csg-boolean-wall-openings-obj-export

### Current State

The SketchOS backend (uncommitted in the working tree) is a src-layout Python service under `backend/src/sketchos_backend/`:

- `arch_dsl.py` — pure Pydantic v2 models (`extra="forbid"`): `Vec3`, `Wall` (id, start, end, height, thickness), `Floor` (id, outline, thickness, elevation), `Opening` (id, wall_id, position:Vec3, width, height), `Volume`, `Relationship`, `ArchitectureModel`. Openings have NO depth/sill/type fields — the cut depth is derived from `wall.thickness` at codegen time, and `position.z` is used as-is as the opening's vertical anchor.
- `blender_client.py` — `generate_blender_code(model) -> str` emits a header defining a single `_add_cube` helper, then one `_add_cube(name, location, size, rotation_z)` line per wall/floor/opening/volume. Walls are rotated boxes (`rotation_z = atan2(dy, dx)`); openings are emitted as **geometry markers** sized `(width, wall_thickness, height)` at `opening.position` with `rotation_z=0.0` — i.e. NOT boolean cutouts and NOT rotated with their wall. `BlenderMCPClient.execute(code, user_prompt="")` calls blender-mcp's `execute_blender_code` over MCP stdio.
- `server.py` — FastMCP `build_architecture` tool; validation-before-execution is the hard boundary.
- `main.py` — FastAPI mounts the streamable-HTTP surface.

blender-mcp side: `execute_blender_code(ctx, code, user_prompt="")` → `BlenderConnection.send_command("execute_code", {code})` → addon `execute_code(code)` runs `exec(code, {"bpy": bpy})`. **The namespace is a fresh dict per call** — Python variables/functions do NOT persist between `execute_blender_code` calls; only `bpy.data`/`bpy.context` scene state persists. The addon already branches on `bpy.app.version >= (4, 0)`, so the target Blender is 4.x.

### Affected Areas

- `backend/src/sketchos_backend/blender_client.py` — `generate_blender_code`, `_HEADER`, `_wall_box`/`_floor_box`/`_volume_box`, `_cube_line`. Must emit boolean cutters + applied modifiers + optional export instead of plain `_add_cube` markers.
- `backend/src/sketchos_backend/arch_macros.py` — **NEW**. Helper module that generates bpy code strings for CSG booleans, extrusion, and OBJ export. Consumed by `blender_client`.
- `backend/src/sketchos_backend/arch_dsl.py` — possibly extend `Opening` (sill/type/base-vs-center position) only if the hole's vertical placement needs more than `position.z + height`.
- `backend/tests/test_blender_client.py` — asserts exact `_add_cube("opening_o1", (2.5, 0, 1), (1, 0.25, 2.1), 0)` marker strings (and the dangling-wall fallback); these break under CSG cutouts.
- `openspec/specs/blender-mcp-client/spec.md` — delta spec for boolean cutouts + OBJ export.
- `backend/src/sketchos_backend/server.py` — if OBJ export becomes a user-facing action, a new tool (`export_architecture_obj`) or a flag on `build_architecture` is needed here.

### Approaches

1. **`arch_macros.py` as a bpy-code generator module (Recommended)**
   - Pure-Python module with no Blender import; each function returns a deterministic bpy code string (e.g. `emit_boolean_difference(target, cutter)`, `emit_export_obj(filepath, apply_modifiers=True)`). `blender_client.generate_blender_code` composes them into one self-contained script, mirroring the existing `_HEADER` + `_add_cube` pattern (which already works around the fresh-namespace constraint by defining helpers inline in the same script).
   - Pros: keeps codegen deterministic and string-testable; matches existing architecture and the change's stated module name; no runtime Blender import; reusable macros.
   - Cons: generated script grows; requires careful bpy active-object/context management; string assertions get more complex.
   - Effort: Medium

2. **Inline boolean + export logic directly in `blender_client.generate_blender_code`**
   - No new module; the cut/export logic is written straight into the generator.
   - Pros: fewer files, simplest diff.
   - Cons: ignores the change intent (explicitly names `arch_macros.py`); bloats `blender_client.py`; less reusable for future extrusion/geometry macros.
   - Effort: Low

3. **Ship a runtime `arch_macros` module into Blender and import it**
   - `exec` the module source into Blender so its functions are importable at runtime.
   - Pros: cleaner generated scripts (functions callable, not re-emitted).
   - Cons: the fresh-namespace `exec(code, {"bpy": bpy})` model means the module would have to be re-exec'd on every call anyway — reduces to Approach 1 with extra steps and no persistence benefit.
   - Effort: High (no benefit)

### Recommendation

**Approach 1.** Create `backend/src/sketchos_backend/arch_macros.py` as a pure code-emitting module. `generate_blender_code` should: (1) emit wall/floor/volume boxes as today, (2) for each opening emit a cutter box rotated to match its wall (`rotation_z` from the wall's `atan2(dy,dx)` — this is the key correctness fix, since current markers ignore wall rotation), (3) add a `BOOLEAN` modifier on the wall with `operation='DIFFERENCE'` targeting the cutter, apply it, and delete the cutter, (4) optionally emit OBJ export via `bpy.ops.wm.obj_export` (Blender 4.x; `bpy.ops.export_scene.obj` is the legacy name).

### Risks

- **Wall rotation vs cutter alignment**: current opening markers are unrotated (`rotation_z=0`). A correct boolean DIFFERENCE requires the cutter to share the wall's rotation, otherwise non-axis-aligned walls get holes cut at the wrong angle. Must be fixed for CSG to be correct.
- **bpy active-object / context management**: boolean modifiers need the target wall as `bpy.context.view_layer.objects.active`; the cutter must stay in the scene until the modifier is applied, then be removed. Ordering errors produce silent no-ops or crashes.
- **Coplanar/degenerate boolean faces**: a cutter exactly flush with the wall face yields non-manifold results; the cutter should slightly overextend beyond the wall thickness. Standard Blender boolean pitfall.
- **OBJ export filepath**: the backend talks to a *remote* Blender over the MCP socket; the `filepath` is on the Blender host's filesystem, not the backend's. Needs an explicit, well-defined export path convention.
- **Test brittleness**: `test_blender_client.py` asserts exact marker strings; boolean + export codegen requires relaxing to substring/semantic assertions or golden files.
- **Namespace non-persistence**: any helper must live in the same emitted script string; no cross-call Python state (already respected by the `_HEADER` pattern, but a trap if macros are split across calls).

### Ready for Proposal

Yes. Before the proposal, the orchestrator should confirm three open forks with the user: (a) whether `Opening` needs a `sill_height`/type field or `position.z` remains the hole's base; (b) whether OBJ export is a new MCP tool (`export_architecture_obj`) vs. a flag/parameter on `build_architecture`; (c) the export filepath convention (fixed relative dir under a configurable root vs. caller-supplied path).

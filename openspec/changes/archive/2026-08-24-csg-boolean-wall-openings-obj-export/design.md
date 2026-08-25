# Design: CSG boolean wall openings and OBJ export

## Technical Approach

Replace opening box markers with real CSG `BOOLEAN` `DIFFERENCE` cutouts and add optional OBJ export. A new pure module `arch_macros.py` emits deterministic bpy strings (no `import bpy`); `blender_client.generate_blender_code` composes them into one self-contained script, respecting blender-mcp's fresh `exec(code, {"bpy": bpy})` namespace. `build_architecture` gains an optional `export_path` param that flows through to codegen.

## Architecture Decisions

| Decision | Options | Tradeoff | Choice |
|---|---|---|---|
| Codegen module | (1) pure `arch_macros.py` (2) inline in client (3) exec module into Blender | (1) matches proposal, string-testable, no Blender import; (2) bloats client; (3) reduces to (1) + re-exec every call | (1) |
| Hole anchor | `position.z` base vs `sill`/type field | base needs no DSL change | `position.z` = hole base; `arch_dsl.py` unchanged |
| Export surface | flag on `build_architecture` vs new tool | flag keeps one tool, smaller surface | optional `export_path` param on `build_architecture` |
| Export filepath | caller-supplied vs fixed root | caller-supplied avoids remote-host fs assumptions | caller-supplied, forwarded verbatim |
| Cutter overextend | fixed epsilon vs thickness factor | fixed is deterministic and simple | depth = `thickness + 0.2` (0.1 per face) |
| Mesh extrusion | in-scope vs deferred | no concrete behavior; floors stay slabs | deferred — future macro, module leaves room |
| Export join/units | join meshes vs export-all | join adds state and risk; export-all sufficient | export all scene objects; join deferred |

## Data Flow

```
DSL payload ──► server.build_architecture ── validate (ArchitectureModel)
     │                                              │ invalid → "Invalid DSL:"
     │                                              ▼ valid
     │                        generate_blender_code(model, export_path)
     │                                              │
     │              ┌───────────────────────────────┼──────────────────────────┐
     │              ▼                               ▼                          ▼
     │        arch_macros.wall_rotation   arch_macros.emit_opening_cutout   emit_export_obj
     │              │                               │ (cutter + boolean)        │
     │              └──────────► single script string ◄─────────────────────────┘
     ▼
 BlenderMCPClient.execute ──► blender-mcp execute_blender_code ──► exec(code, {"bpy": bpy})
```

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/src/sketchos_backend/arch_macros.py` | Create | Pure bpy-string emitters: wall rotation, cutter params, boolean helper, OBJ export |
| `backend/src/sketchos_backend/blender_client.py` | Modify | Extend `_HEADER` (`_add_cube` returns obj; add `_boolean_difference`), consume macros, `export_path` param |
| `backend/src/sketchos_backend/server.py` | Modify | `build_architecture` + tool gain optional `export_path`; pass to codegen |
| `backend/tests/test_blender_client.py` | Modify | Relax exact strings → substring/golden; angled-wall + export cases |
| `backend/tests/test_server.py` | Modify | export_path pass-through + no-export cases |
| `backend/tests/test_arch_macros.py` | Create | Determinism, overextend, rotation, export emission |
| `openspec/specs/backend-service/spec.md` | Delta | MODIFIED tool registration + ADDED optional export (see Open Questions) |

## Interfaces / Contracts

`arch_macros.py` (pure; no Blender runtime, no `import bpy`):

```python
OPENING_OVEREXTEND: float = 0.2  # cutter depth = wall.thickness + this

def wall_rotation(wall) -> float                    # atan2(dy, dx)
def cutter_params(wall, opening) -> tuple[loc, size, rot_z]  # size z-center = pos.z + h/2
def emit_boolean_header() -> str                    # _boolean_difference helper def
def emit_opening_cutout(wall, opening) -> str       # _add_cube(cutter) + _boolean_difference(...)
def emit_export_obj(filepath: str) -> str           # bpy.ops.wm.obj_export(filepath=...)
```

`blender_client.generate_blender_code(model, export_path: str | None = None) -> str` composes header + wall/floor/volume boxes + per-opening cutout + trailing export. `server.build_architecture(payload, client, user_prompt="", export_path="")` maps empty string → `None`.

## bpy boolean cut sequence (per opening, wall W)

```python
cutter = _add_cube("cutter_<id>", (pos.x, pos.y, pos.z + h/2),
                   (width, thickness + OPENING_OVEREXTEND, height), wall_rotation(W))
_boolean_difference("wall_<W>", "cutter_<id>", "opening_<id>")
# _boolean_difference:
#   target = bpy.data.objects[target_name]; cutter = bpy.data.objects[cutter_name]
#   bpy.context.view_layer.objects.active = target
#   mod = target.modifiers.new(name=mod_name, type='BOOLEAN')
#   mod.operation = 'DIFFERENCE'; mod.object = cutter
#   bpy.ops.object.modifier_apply(modifier=mod_name)
#   bpy.data.objects.remove(cutter, do_unlink=True)
```

Deterministic order: modifier apply precedes cutter delete, per opening, before any export.

## OBJ export sequence

```python
bpy.ops.wm.obj_export(filepath=<json.dumps(export_path)>)   # emitted last
```

Modifiers are already applied inline (apply-then-delete), so no pending modifiers remain; all surviving objects export directly.

## Error Handling

- Validation-before-execution unchanged: invalid DSL → `"Invalid DSL:"`, no code sent.
- `export_path` embedded via `json.dumps` (safe quoting, matches `_cube_line`).
- Transport/exec failure → `BlenderClientError` → `"Blender error:"` (unchanged).
- `arch_macros.py` cannot fail at import (no bpy) and has no runtime I/O.

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit (arch_macros) | determinism, overextend, rotation, export string | byte-identical re-emission; depth > thickness; rotation == `atan2`; substring `wm.obj_export` |
| Unit (client codegen) | cutout vs marker, angled walls, export order, dangling fallback | substring/golden: `_boolean_difference("wall_w1","cutter_o1",…)`; NO `_add_cube("opening_…")`; angled wall (atan2(4,3)) rotation value; export after boolean |
| Unit (server) | export_path pass-through, no-export default | SpyClient asserts emitted code contains/omits export |
| E2E | real boolean result in Blender | manual/deferred (no Blender in CI) |

Dangling `wall_id`: keep defensive fallback — emit a plain marker box (no boolean), preserving current behavior.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary is introduced. `export_path` is a data string forwarded as an operator argument (escaped via `json.dumps`), not executed.

## Migration / Rollout

No migration. Working tree is uncommitted; rollback = `git checkout` touched files + delete `arch_macros.py`.

## Open Questions

- [ ] `backend-service` delta: `build_architecture` signature changes (new `export_path`), which is a server-layer change beyond the client delta. Recommended: add a `backend-service` MODIFIED delta (tool registration) + ADDED "optional OBJ export" requirement; needs sdd-spec follow-up or task-level capture.
- [ ] "meshes joined" wording in arch-macros OBJ requirement: satisfied vacuously here (cutters deleted, modifiers applied inline); explicit mesh join is deferred. Confirm acceptable.

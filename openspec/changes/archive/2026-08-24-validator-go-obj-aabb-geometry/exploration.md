# Exploration: validator-go-obj-aabb-geometry

Go CLI microservice (`validator_go/main.go`) to parse `.obj` files exported by Blender, compute the Axis-Aligned Bounding Box (AABB), and validate geometric rules ("normativas geométricas") for walls and heights in milliseconds.

## Current State

The repo is GREENFIELD for Go: `find . -name '*.go'` and `go.mod` return nothing. The stack today is three Python/Blender components plus a kernel sidecar:

- `backend/src/sketchos_backend/arch_dsl.py` — pure Pydantic v2 models, `extra="forbid"` everywhere:
  - `Vec3{x,y,z: float}`
  - `Wall{id: str, start: Vec3, end: Vec3, height: float (gt=0), thickness: float (gt=0)}`
  - `Floor{id, outline: list[Vec3], thickness (gt=0), elevation (=0)}`
  - `Opening{id, wall_id, position: Vec3, width (gt=0), height (gt=0)}`
  - `Volume{id, origin: Vec3, size: Vec3}`
  - `Relationship{source_id, target_id, kind: Literal["contains","adjacent","opening_in"]}`
  - `ArchitectureModel{walls, floors, openings, volumes, relationships}`
- `backend/src/sketchos_backend/blender_client.py` — `generate_blender_code(model, export_path)` emits one `_add_cube(name, location, size, rotation_z)` per wall/floor/volume; walls are rotated boxes (`rotation_z = atan2(dy,dx)`); openings become CSG boolean `DIFFERENCE` cutters that are applied then deleted. `export_path` appends `bpy.ops.wm.obj_export(filepath=...)`.
- `backend/src/sketchos_backend/arch_macros.py` — `emit_export_obj(filepath)` → `bpy.ops.wm.obj_export(filepath=<json-quoted>)`.
- `backend/src/sketchos_backend/server.py` — FastMCP `build_architecture(payload, user_prompt, export_path)` with validation-before-execution.
- `backend/src/sketchos_backend/main.py` — FastAPI mounts `/mcp`.

### Units

No unit is declared anywhere. The DSL uses bare floats (`height=3`, `thickness=0.25` in tests) in Blender's default dimensionless unit system (unit scale 1.0). By convention these read as meters, but **the codebase never states it**. The only geometric constraints that exist today are positivity (`Field(gt=0)`). There are NO min/max height/thickness ranges — those would be exactly the "normativas" the Go validator introduces, but a unit convention must be pinned first.

### What "normativas geométricas de muros y alturas" can validate

From the DSL (pre-Blender, already enforced): positivity of `height`, `thickness`, `width`. From the exported OBJ (post-Blender, the Go validator's domain): per-object AABB of `wall_<id>`, `floor_<id>`, `volume_<id>`, whole-model AABB, wall height extent, wall thickness extent, overall building height, plus any numeric thresholds (min/max wall height, min wall thickness, max building height). Classification is by object-name prefix (`wall_`, `floor_`, `volume_`) because the DSL carries no semantic tags into the OBJ beyond those names.

### OBJ export behavior (what the parser will receive)

- `generate_blender_code` emits walls/floors/volumes as **separate objects** named `wall_<id>`, `floor_<id>`, `volume_<id>`. Each becomes its own `o <name>` group in the OBJ.
- Openings (cutters) are **deleted after the boolean apply** (verified by `test_script_orders_apply_then_delete_then_export`), so they never appear in the OBJ; the hole is embedded in the wall mesh, which will have more than 8 vertices per wall after the boolean cut.
- No materials are assigned by `_add_cube`, so the export is unlikely to emit `mtllib`/`usemtl`, but the parser must tolerate them anyway.
- The export call passes **only** `filepath` — no `forward_axis`/`up_axis`. Blender's `wm.obj_export` defaults are `forward_axis=NEGATIVE_Z`, `up_axis=Y`, which converts Blender's Z-up to OBJ's Y-up. **Consequence: a wall's "height" (Blender Z) lands on the OBJ Y axis.** The Go validator must compute height from the Y extent of the exported geometry, not Z, unless the export call is changed to pin the axis mapping. This is the single most important correctness gotcha and must be verified against a real exported file.

## Affected Areas

- `validator_go/` (NEW) — the entire Go CLI: module, parser, AABB, validation rules, tests.
- `backend/src/sketchos_backend/arch_macros.py` — `emit_export_obj` may need explicit `forward_axis`/`up_axis` args to pin the coordinate mapping so the validator's axis assumptions are stable.
- `backend/src/sketchos_backend/server.py` / a new module — the point that invokes the Go binary (subprocess) and the .obj file-location convention (see Risks).
- `Makefile` (root) — currently a NASM/i686-elf kernel build, unrelated to Go; do NOT overload it. A new `validator_go/Makefile` is the clean home for `build`/`test`/`install`.
- `openspec/specs/` — new `validator-go` (or `geometry-validator`) domain spec.

## Approaches

1. **Standalone Go CLI + subprocess from Python (Recommended)**
   - `validator_go/` compiles to a single static binary; invoked via `subprocess.run`, reads the .obj path from a flag, writes JSON to stdout, exits non-zero on validation failure.
   - Pros: zero runtime deps, ms-scale cold start (~2–5 ms), trivially testable with `go test`, no import of Python/Blender; matches "microservicio CLI" intent.
   - Cons: process spawn per call; the .obj must be reachable from the machine running the binary (see Risks); JSON contract between Go and Python must be pinned.
   - Effort: Medium

2. **Persistent Go sidecar (HTTP/gRPC)**
   - Same parser/validator, but resident server accepting `POST /validate`.
   - Pros: eliminates per-call process startup; hot-loop friendly.
   - Cons: operational overhead (port, lifecycle, health); overkill at this scale — process startup is already in the low ms and the parse itself is sub-ms.
   - Effort: High (not justified yet)

3. **`go run` ad-hoc from Python**
   - No prebuilt binary; `subprocess.run(["go", "run", "./main.go", ...])`.
   - Pros: no build step.
   - Cons: requires the Go toolchain at runtime and adds ~100–300 ms (compile) — destroys the "milliseconds" goal.
   - Effort: Low (rejected for perf)

### Module name fork

No git remote exists (empty repo, zero commits). Two viable paths: (a) `github.com/sketchos/validator-go` (forward-looking, survives a future remote) or (b) local `sketchos/validator-go` (works today, but `go get` can't fetch a dotless first segment). Recommend (a) as the module path regardless; it costs nothing and avoids a rename later. Confirm with the user if a different org/namespace is intended.

## Recommendation

**Approach 1** — a self-contained `validator_go/` module:

```
validator_go/
├── go.mod                      # module github.com/sketchos/validator-go
├── main.go                     # package main: flag parsing, wiring, JSON output
├── obj/                        # streaming Wavefront OBJ parser
│   ├── parser.go               #   bufio.Scanner, handles v/f/o/g/s/usemtl/mtllib/#
│   └── parser_test.go
├── aabb/
│   ├── aabb.go                 #   AABB{MinX,MinY,MinZ,MaxX,MaxY,MaxZ} + Dimensions()
│   └── aabb_test.go
├── validate/
│   ├── rules.go                #   wall/height/thickness thresholds, per-object + global
│   └── rules_test.go
└── Makefile                    #   build / test / install (go build, go test, go vet)
```

- **Parser** must handle: `v x y z` (1-based, signed/scientific floats), `f` with `v`, `v/vt/vn`, `v//vn` forms, **negative relative indices** (`f -1 -2 -3`), arbitrary polygon fan size, `o`/`g` object/group lines, `#` comments, `s`/`usemtl`/`mtllib`/`vt`/`vn` lines (skip, don't error), backslash line continuation, and CRLF/whitespace tolerance. Use `bufio.Scanner` + `strings.Fields` + `strconv.ParseFloat` — **no regexp**.
- **AABB** is a single-pass min/max over every parsed `v` line; report 6 scalars plus `dx/dy/dz`. Optionally track per-object AABB keyed by the current `o`/`g` name for wall/height rules.
- **CLI flags**: `-input <file.obj>` (or stdin), `-format json|text` (JSON is the Python contract), `-min-wall-height`, `-max-wall-height`, `-min-wall-thickness`, `-max-building-height`, etc. Exit 0 = pass, 1 = violations, 2 = parse error. Emit violations as structured JSON.
- **Python integration**: precompile with `go build -o validator`; `subprocess.run([validator, "-input", export_path, "-format", "json"], capture_output=True)`; parse stdout JSON. Decode the returned AABB/height values, remembering the Y-up axis mapping.

### Performance ("milliseconds")

Trivially achievable. The DSL produces one box per wall/floor/volume; even a 200-wall building with boolean-cut meshes is a few thousand to ~10k `v` lines. Go's `bufio.Scanner` parses ~1M lines/sec or better; 10k vertices parse in ~1 ms. The dominant cost is process startup (~2–5 ms for a static binary), so total wall-clock is ~5–10 ms per invocation — comfortably "milliseconds". The existing test models are tiny (1 wall/floor/opening/volume). The only thing that would break the budget is `go run` (Approach 3), which is rejected.

## Risks

- **Y-up vs Z-up axis swap**: default `wm.obj_export` (forward=-Z, up=Y) puts wall height on the OBJ Y axis. If the validator reads height from Z (or the caller reads the wrong axis back), all height validations are silently wrong. Must pin export axis args and/or normalize in the validator, and verify against a real exported file.
- **.obj file location**: the backend talks to Blender over MCP stdio on a (possibly remote) host; `export_path` is on the Blender host's filesystem, not the backend's. The Go validator must run where the .obj is reachable, or the file must be transferred. This is the key unresolved fork for `sdd-propose`.
- **No unit convention**: bare floats with no declared unit make "height ≤ 3" thresholds ambiguous. Pin a unit (meters) explicitly or the normativa is untestable.
- **Object-name coupling**: per-object rules depend on the `wall_`/`floor_`/`volume_` naming convention from `generate_blender_code`; a rename breaks classification. Consider making the prefix configurable.
- **Boolean-cut vertex inflation**: cut walls are non-cuboid meshes; per-object height/thickness extent still holds (AABB), but "thickness = AABB depth" is only exact for axis-aligned walls — rotated walls have a thicker AABB than their true `thickness`. Flag this semantic in the rules, not a silent mismatch.
- **Greenfield build wiring**: no existing Go build convention; root `Makefile` is a kernel build and must not be overloaded.

## Ready for Proposal

**Yes.** Before `sdd-propose`, the orchestrator should confirm three forks with the user:
1. Module path: `github.com/sketchos/validator-go` vs. a local `sketchos/validator-go` (no remote exists yet).
2. Where the Go binary runs relative to the .obj — co-located on the Blender host, invoked from the backend after transferring the file, or a shared filesystem.
3. Unit + axis conventions: confirm meters as the unit and whether the validator should normalize the Y-up OBJ or the exporter should pin `forward_axis`/`up_axis`.

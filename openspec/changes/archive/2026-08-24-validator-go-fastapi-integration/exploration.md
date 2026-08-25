# Exploration: validator-go-fastapi-integration

Connect the Go validator (`validator_go`) to the FastAPI backend (`backend/src/sketchos_backend`) via CLI subprocess execution, exposing `/extract-rules`, `/validate-geometry`, and `/autocorrect`.

## Current State

### Python backend (`backend/src/sketchos_backend/`)

- `main.py` — a single `FastAPI` app (`title="SketchOS Backend"`). It mounts the FastMCP streamable-HTTP surface with `app.mount("/mcp", mcp.streamable_http_app())` and that is the **only** route. There are no other HTTP endpoints today, so the three new endpoints are net-new. They would be added either directly on `app` in `main.py` or (cleaner) in a new `validator_routes.py` module registered via `app.include_router(...)`.
- `server.py` — owns the `FastMCP("SketchOS", streamable_http_path="/")` instance and the single `build_architecture` tool. `build_architecture(payload, client, user_prompt, export_path)` enforces **validation-before-execution**: `ArchitectureModel.model_validate(payload)` first, then `generate_blender_code(model, export_path=export_path or None)`, then `await client.execute(code, user_prompt=...)`. `export_path` is forwarded verbatim to codegen and only ever embedded as an operator argument (`json.dumps`), never executed.
- `blender_client.py` — `generate_blender_code(model, export_path)` emits one `_add_cube(...)` per wall/floor/volume (names `wall_<id>`/`floor_<id>`/`volume_<id>`) and, when `export_path` is set, appends `arch_macros.emit_export_obj(export_path)` → `bpy.ops.wm.obj_export(filepath="...")`. Export uses Blender defaults (`forward_axis=NEGATIVE_Z`, `up_axis=Y`), so wall height lands on the OBJ **Y** axis. `BlenderMCPClient` executes via the `blender-mcp` stdio subprocess on `execute_blender_code`; the `.obj` is therefore written to the **blender-mcp host** filesystem, which is not necessarily the backend host.
- The backend has **no subprocess usage** anywhere today — `BlenderMCPClient` uses the MCP stdio transport, not `subprocess`.

### Go validator (`validator_go/`)

- `main.go` — single static CLI. Flags: `-input` (required `.obj` path), `-output` (default stdout), `-min-height` 2.0, `-max-height` 0 (unenforced), `-min-thickness` 0.1, `-max-thickness` 0 (unenforced). Exit codes: **0** pass, **1** violations, **2** parse/input error. JSON → stdout (or `-output`); diagnostics → stderr. `run(args, stdout, stderr) int` is the testable core (not exposed to Python).
- `internal/report/report.go` — deterministic JSON (fixed field order, empty slices encode as `[]`):

```json
{
  "aabb":       {"min":{"x":0,"y":0,"z":0}, "max":{"x":10.25,"y":3,"z":5},
                 "dimensions":{"dx":10.25,"dy":3,"dz":5}},
  "objects":    [{"name":"wall_1","height":3,"thickness":0.25}],
  "violations": [{"type":"wall_height_min","object":"wall_1","measured":1.5,
                  "threshold":2,"message":"wall \"wall_1\" height below minimum"}]
}
```

- `internal/validate/rules.go` — four rule identifiers (`wall_height_min`, `wall_height_max`, `wall_thickness_min`, `wall_thickness_max`). `Thresholds{MinHeight, MaxHeight, MinThickness, MaxThickness}` with `DefaultThresholds()` = min-height 2.0, min-thickness 0.1, max unenforced. Classification by name prefix (`wall_`/`floor_`/`volume_`). `Measure` = height from Y extent, thickness = `min(dx, dz)` (exact only for axis-aligned walls).
- **No autocorrect. No extract-rules.** The validator is report-only (parse → AABB → validate → JSON). `go.mod` = `github.com/sketchos/validator-go`, go 1.26, zero external deps. `Makefile` has `build`/`test`/`vet`/`bench` but no install/binary-output target, and **no compiled binary is currently present** in the repo.

### Repo facts

- No git remote, no commits (greenfield VCS state). Root `Makefile` is a NASM/i686-elf **kernel** build — unrelated; never overload it.

## Affected Areas

- `backend/src/sketchos_backend/main.py` — register the new HTTP endpoints (directly or via an APIRouter).
- `backend/src/sketchos_backend/validator_client.py` (NEW) — subprocess wrapper around the Go binary, mirroring the transport-isolation pattern of `blender_client.py`.
- `backend/src/sketchos_backend/validator_routes.py` (NEW) — FastAPI routes for the three endpoints (request/response models).
- `backend/tests/` — new `test_validator_client.py` / `test_validator_routes.py` (mock the subprocess boundary; optionally a fixture binary).
- `validator_go/main.go` — only if `extract-rules` (and possibly `autocorrect`) is implemented as Go capability rather than mirrored config.
- `validator_go/Makefile` — add an `install`/`build` target that emits a named binary the backend can locate.
- `openspec/specs/backend-service` and `openspec/specs/geometry-validator` — new requirements for the endpoints and any new Go capability.

## Approaches

### A. Subprocess invocation strategy

1. **`asyncio.create_subprocess_exec` (Recommended)** — non-blocking, idiomatic in an async FastAPI handler; `asyncio.wait_for(..., timeout=N)` for timeouts; list-form argv (no `shell=True`) for injection safety.
   - Pros: no event-loop blocking; native async; easy timeout + kill.
   - Cons: slightly more code than `subprocess.run`.
   - Effort: Low

2. **`subprocess.run` in a threadpool** (`asyncio.to_thread` / `run_in_threadpool`) — reuse the familiar sync API.
   - Pros: simple; well-understood semantics.
   - Cons: needs explicit threadpool discipline or it blocks the loop.
   - Effort: Low

3. **`go run` ad-hoc** — rejected: requires the Go toolchain at runtime and adds ~100–300 ms compile, destroying the "milliseconds" goal.

### B. Binary location

1. **Env-var / settings path with PATH fallback (Recommended)** — resolve order: `SKETCHOS_VALIDATOR_BIN` env var → `validator-go` on PATH → a repo-relative prebuilt path (`validator_go/bin/validator-go`). Fail with a clear "binary not found; run `make install` in validator_go/`" error.
   - Pros: works in dev and deploy; explicit.
   - Cons: must document/build the binary.
   - Effort: Low

2. **Prebuilt binary committed/required** — `go build -o validator_go/validator .` output expected at a fixed path.
   - Pros: zero config.
   - Cons: platform-specific binary in a greenfield repo with no commits; brittle.
   - Effort: Low

### C. Endpoint input shape (`.obj` transport)

1. **Uploaded bytes (multipart or raw body) (Recommended)** — backend writes to a `tempfile` and runs the validator against it, then deletes it.
   - Pros: sidesteps the "`.obj` is on the Blender host, not the backend" mismatch; no arbitrary filesystem path exposure; works over HTTP.
   - Cons: upload cost for large meshes (negligible at this scale).
   - Effort: Low

2. **Filesystem path passthrough** — client passes an `export_path`; backend runs the validator against that path.
   - Pros: matches the existing `export_path` flow; no upload.
   - Cons: the path is on the Blender host, not necessarily reachable by the backend; arbitrary-path read risk.
   - Effort: Low (but carries the reachability/security risk)

### D. `/extract-rules` source of truth

1. **New Go capability: `-print-defaults` / `rules` subcommand emitting thresholds as JSON (Recommended)** — single source of truth stays in `validate.DefaultThresholds()`.
   - Pros: no drift between Go and Python; trivially implemented + tested.
   - Cons: one small Go change + a new flag.
   - Effort: Low

2. **Mirror defaults in Python config** — expose the four thresholds from a Python constant.
   - Pros: no Go change.
   - Cons: drift risk; duplicates the "normativa" in two places.
   - Effort: Low

3. **Shared rules config file** consumed by both — heavier; unnecessary at this scale.

### E. `/autocorrect` capability

1. **Backend/Blender re-codegen (Recommended)** — the validator reports violations; the backend recomputes corrected dimensions against the DSL `ArchitectureModel` and re-emits Blender code + OBJ export via the existing `generate_blender_code`/`blender_client` path. The Go validator only re-validates the corrected result.
   - Pros: reuses existing, tested codegen; no mesh-editing in Go (which today has no mesh/write capability).
   - Cons: requires the DSL payload (not just the `.obj`) as input; correctness lives in Python.
   - Effort: Medium

2. **New Go mesh-editing capability** — read `.obj`, scale/repair wall height and thickness, write a corrected `.obj`.
   - Pros: corrects geometry without Blender.
   - Cons: large new scope (Go currently parses vertices only, discards faces, never writes meshes); normativa semantics (e.g. "extrude to min height") underspecified.
   - Effort: High

## Recommendation

Add a new `validator_client.py` (subprocess wrapper using `asyncio.create_subprocess_exec`, env-var-configurable binary path, `asyncio.wait_for` timeout, list-form argv) and a new `validator_routes.py` APIRouter registered in `main.py`.

- `/validate-geometry` — accept uploaded `.obj` bytes, write to a temp file, run the validator with optional threshold overrides, and return the Go JSON report plus a derived `status` (pass/violations/parse_error) mapped from the exit code. Use `-output` to a temp file OR parse stdout; on exit 2, surface stderr.
- `/extract-rules` — add a minimal Go `-print-defaults` flag (JSON of the four thresholds + units + axis convention + rule identifiers) and have the endpoint invoke it, so Go remains the single source of truth.
- `/autocorrect` — **flag as a scope question** (see Risks). Recommended shape: accept the DSL payload, compute corrected heights/thicknesses from violations, re-emit via Blender codegen, and re-validate. No new Go capability required.

Keep the Go validator a pure, report-first CLI; do not add a sidecar server (overkill — cold start is low-ms).

## Risks

- **Binary not built / not on PATH** — no binary exists today; must add a build/install step and a clear runtime error path.
- **`.obj` reachability mismatch** — `export_path` is on the Blender host filesystem; the backend may not see it. Uploaded-bytes input (Approach C1) avoids this entirely.
- **stdout vs stderr + exit-code mapping** — JSON on stdout only for exit 0/1; exit 2 means no JSON and stderr carries the diagnostic. Must not treat violations (exit 1) as an error.
- **Event-loop blocking** — a sync `subprocess.run` inside an async handler blocks the loop; use `create_subprocess_exec` or a threadpool.
- **Command injection / arbitrary path** — always list-form argv (never `shell=True`), never interpolate paths into a shell string; restrict to uploaded temp files or a vetted root.
- **Threshold drift** — if `/extract-rules` mirrors defaults in Python, the two copies can diverge; prefer Go as source of truth.
- **Axis convention** — Y-up export already handled by the Go validator, but any backend-side correction logic must respect the same mapping.
- **Autocorrect scope is open** — the validator is report-only; "autocorrect" requires either new Go mesh editing or backend re-codegen. This is the single biggest unresolved fork and should be confirmed before `sdd-spec`.

## Ready for Proposal

**Yes.** Before `sdd-propose`, the orchestrator should confirm with the user:
1. `.obj` transport: uploaded bytes vs filesystem path (recommend bytes).
2. Binary location/build: env-var-configurable path vs committed prebuilt binary (recommend env-var + `make install`).
3. `/extract-rules` source of truth: new Go `-print-defaults` flag vs mirrored Python config (recommend Go flag).
4. `/autocorrect` scope: backend/Blender re-codegen vs new Go mesh-editing capability (recommend backend re-codegen).

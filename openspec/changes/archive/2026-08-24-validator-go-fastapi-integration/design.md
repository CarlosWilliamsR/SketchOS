# Design: Conectar el validador en Go (validator_go) con el backend en FastAPI (main.py) mediante ejecuciones de subproceso CLI

## Technical Approach

Expose the existing report-only Go validator over HTTP by wrapping it as an asyncio subprocess, never a sidecar server. `validator_client.py` owns binary resolution, argv composition, temp-file staging, timeout, and exit-code mapping. `validator_routes.py` exposes three endpoints on an `APIRouter` registered by `main.py` (the `/mcp` mount stays untouched). Go gains one flag, `-print-defaults`, which is the single source of truth for thresholds. Autocorrect is a backend/Blender re-codegen loop, re-validated by Go; the Go binary never edits meshes.

## Architecture Decisions

| # | Decision | Options considered | Choice |
|---|----------|--------------------|--------|
| 1 | Subprocess transport | shell=True / in-process cgo / FastMCP sidecar / `asyncio.create_subprocess_exec` | `create_subprocess_exec` with list-form argv. No shell (injection-safe), async (non-blocking), no extra server to run. |
| 2 | .obj transport | path reference / streamed multipart / uploaded bytes → temp file | Uploaded bytes written to a temp file. Deterministic `-input` path; no cross-host FS assumption. |
| 3 | Binary resolution | hardcoded repo path / bundle binary / env-var + PATH | `VALIDATOR_GO_BIN` env-var, else `validator-go` on PATH. Clear `make install` guidance on failure. |
| 4 | `/extract-rules` source of truth | hardcoded Python copy / parse `--help` / `-print-defaults` | New Go `-print-defaults` flag emitting `validate.DefaultThresholds()`. Removes threshold drift. |
| 5 | `/autocorrect` scope | Go mesh-editing / backend re-codegen | Backend/Blender re-codegen via `build_architecture`; Go stays read-only. |
| 6 | Parse-error status | 400 / 422 | 422 Unprocessable Entity: HTTP envelope is valid, the `.obj` payload is semantically unparseable. |
| 7 | Correction algorithm | iterate-to-fixpoint / margin padding | Exact `threshold`, single pass, single re-validate. Deterministic; no unbounded loop. |

## Data Flow

```
POST /validate-geometry (.obj bytes)
   UploadFile ──read──▶ temp file ──▶ create_subprocess_exec(binary, -input tmp, thresholds)
                                        stdout=JSON, stderr=diag, returncode
   exit 0 ─▶ 200 {status:"pass", report}
   exit 1 ─▶ 200 {status:"violations", report}
   exit 2 ─▶ 422 {detail: stderr}
   timeout/spawn ─▶ 504 / 503

POST /autocorrect (DSL payload)
   payload ──validate──▶ ArchitectureModel
   ──▶ build_architecture(export=tmp.obj) ──▶ Blender ──▶ tmp.obj
   ──▶ Go validate ──▶ violations? ──▶ correct_model(wall heights/thicknesses) ──▶ re-codegen ──▶ re-validate
   ──▶ 200 {status, report, fixes[]}
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/src/sketchos_backend/validator_client.py` | Create | `ValidatorClient`: binary resolution, argv build, `asyncio.create_subprocess_exec`, `wait_for` timeout, exit-code + JSON/stderr capture. |
| `backend/src/sketchos_backend/validator_routes.py` | Create | `APIRouter` with `/extract-rules`, `/validate-geometry`, `/autocorrect`; status mapping; autocorrect `correct_model`. |
| `backend/src/sketchos_backend/main.py` | Modify | `app.include_router(validator_router)` next to the `/mcp` mount. |
| `backend/tests/test_validator_client.py` | Create | Mock subprocess: exit-code map, timeout, binary fallback, argv list-form. |
| `backend/tests/test_validator_routes.py` | Create | Endpoint contracts via FastAPI TestClient with injected fake client. |
| `validator_go/main.go` | Modify | Add `-print-defaults` flag, checked before the `-input` guard. |
| `validator_go/internal/report/report.go` | Modify | Add `ThresholdsJSON` struct + `WriteDefaults(w, Thresholds)`. |
| `validator_go/main_test.go` | Modify | `-print-defaults` exit-0/no-input test. |
| `validator_go/Makefile` | Modify | Add `install` target (build + copy to `$GOBIN`/`/usr/local/bin`). |

## Interfaces / Contracts

**argv composition** (list, never a string; thresholds always passed explicitly so `/extract-rules` and `/validate-geometry` share defaults):

```python
argv = [binary, "-input", tmp_path,
        "-min-height", f"{t.min_height}", "-max-height", f"{t.max_height}",
        "-min-thickness", f"{t.min_thickness}", "-max-thickness", f"{t.max_thickness}"]
proc = await asyncio.create_subprocess_exec(*argv, stdout=PIPE, stderr=PIPE)
stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=DEFAULT_TIMEOUT)
```

**Exit-code mapping**: `0 → pass`, `1 → violations`, `2 → parse error`. `status` is derived, the Go report is returned verbatim under `report`.

**Correction algorithm** (`correct_model`, pinned): for each violation, `wall_<id>` maps back to DSL wall `id` (name prefix matches `blender_client`'s `_add_cube("wall_"+wall.id, …)`); the violating dimension is set to the violation `threshold` (exact, no margin — min/max checks pass on equality). Unenforced bounds (`threshold == 0`) never produce a violation, so no zero-target correction.

```
wall_height_min → wall.height   = threshold   # raise short wall
wall_height_max → wall.height   = threshold   # lower tall wall
wall_thickness_min → wall.thickness = threshold  # thicken
wall_thickness_max → wall.thickness = threshold  # thin
```

**`-print-defaults`** prints `{"min_height":2.0,"max_height":0,"min_thickness":0.1,"max_thickness":0}` (0 = unenforced) and exits 0, before the `-input` guard:

```go
printDefaults := fs.Bool("print-defaults", false, "print thresholds as JSON and exit")
// after fs.Parse, before the *input == "" guard:
if *printDefaults { report.WriteDefaults(stdout, validate.DefaultThresholds()); return 0 }
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (Go) | `-print-defaults` prints 4 keys, exit 0, no `-input` | `main_test.go` `runValidator` + `json.Unmarshal` |
| Unit (Go) | thresholds JSON shape | report package golden/shape test |
| Unit (Py) | argv list-form + no shell; env-var vs PATH resolution | monkeypatch `create_subprocess_exec`, assert argv[0] |
| Unit (Py) | exit-code 0/1/2 mapping; timeout → 504; spawn fail → 503 | fake `Process` with canned stdout/returncode |
| Integration (Py) | endpoint contracts 200/422/503/504; temp file removed | FastAPI TestClient + injected fake `ValidatorClient` |

## Threat Matrix

Process integration (subprocess execution) is the only touched boundary. All VCS/PR and documentation-path classification rows are `N/A` (this change adds no git, push, commit, PR, or doc-execution path):

| Boundary | Applicability | Design response |
|----------|--------------|-----------------|
| Documentation-like paths | N/A — no doc/exec file classification introduced | — |
| Git repository selection | N/A — no git automation | — |
| Commit state | N/A — no commit automation | — |
| Push state | N/A — no push automation | — |
| PR commands | N/A — no PR automation | — |

Process-integration safe/failure behavior (RED-tested): argv passed as a list, `shell` never enabled (injection-safe); temp files in `tempfile.mkdtemp(prefix="sketchos-validator-")` removed in `finally`; spawn failure → 503 with "binary not found (set VALIDATOR_GO_BIN or run make install)"; timeout (`DEFAULT_TIMEOUT = 30s`) → 504 with subprocess terminated.

## Migration / Rollout

No migration required. Additive endpoints; `-print-defaults` is a new flag. Rollback = revert the three backend files + router registration and drop the flag (per proposal).

## Open Questions

- [ ] Confirm `DEFAULT_TIMEOUT` (30 s) as a constant vs. env-configurable.
- [ ] Rotated-wall thickness mapping is approximate (AABB inflation): autocorrect may leave a residual `wall_thickness_*` violation. Accepted for v1; note in response.

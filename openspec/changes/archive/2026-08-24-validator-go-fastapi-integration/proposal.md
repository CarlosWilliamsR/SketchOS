# Proposal: Connect Go Validator (validator_go) to FastAPI Backend via CLI Subprocess

## Intent

Expose the Go geometric validator to HTTP clients. Today `main.py` mounts only the FastMCP `/mcp` surface, and the validator is a report-only CLI with no HTTP path; Blender's `.obj` export lands on a different host than the backend, so validation cannot reach it. This change adds three endpoints backed by safe CLI subprocess execution.

## Scope

### In Scope
- `validator_client.py`: asyncio subprocess wrapper (list-form argv, never `shell=True`), threshold passthrough, stdout JSON + exit-code capture, timeout + error mapping.
- Three FastAPI endpoints: `/extract-rules`, `/validate-geometry`, `/autocorrect`.
- Go `-print-defaults` flag (extract-rules source of truth).
- `validator_go/Makefile` install target + env-var binary resolution.
- Tests mocking the subprocess boundary.

### Out of Scope
- Frontend; bidirectional sync; auth/persistence; distributed file transfer; Go mesh-editing autocorrect.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `backend-service`: add HTTP endpoints `/extract-rules`, `/validate-geometry`, `/autocorrect` plus a subprocess validator client.
- `geometry-validator`: add a `-print-defaults` flag emitting thresholds JSON.

## Approach

Subprocess invocation via `asyncio.create_subprocess_exec` with `asyncio.wait_for` timeout, temp-file staging of uploaded bytes, binary resolved env-var → PATH → repo path. Go stays a pure report-first CLI (no sidecar server). Autocorrect = backend re-codegen, re-validated by Go.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/src/sketchos_backend/validator_client.py` | New | Subprocess wrapper around the Go binary |
| `backend/src/sketchos_backend/validator_routes.py` | New | APIRouter for the three endpoints |
| `backend/src/sketchos_backend/main.py` | Modified | Register the router |
| `backend/tests/` | New | Mock subprocess; endpoint contract tests |
| `validator_go/main.go` | Modified | Add `-print-defaults` flag |
| `validator_go/Makefile` | Modified | Add install/build target |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Binary not built / not on PATH | Med | Env-var + PATH fallback; clear "run make install" error |
| Exit-code confusion (exit 1 = violations, not error) | Med | Explicit mapping: 0 pass, 1 violations, 2 parse error |
| Event-loop blocking | Med | `create_subprocess_exec` (async) |
| Command injection / arbitrary path | Low | List-form argv, no shell, temp-file staging |
| Threshold drift | Low | Go `-print-defaults` single source of truth |
| Autocorrect scope open | High | Default to backend re-codegen; confirm before sdd-spec |

## Rollback Plan

Revert the commit adding `validator_client.py`/`validator_routes.py` and the `main.py` router registration; drop the `-print-defaults` flag. No DB or schema migration; additive endpoints removable without touching `/mcp`.

## Dependencies

- Compiled `validator-go` binary (via `make install`) or on PATH.
- Existing `sketchos_backend` package layout.

## Success Criteria

- [ ] `GET /extract-rules` returns the four thresholds as JSON.
- [ ] `POST /validate-geometry` returns Go JSON + derived status for a sample `.obj`.
- [ ] Exit codes 0/1/2 map to pass/violations/parse-error with correct error surfaces.
- [ ] Subprocess-mocked tests pass; timeout and binary-missing paths covered.
- [ ] No `shell=True` anywhere in the new code.

## Open Decisions

Defaults recommended; orchestrator surfaces at the continue gate.

| # | Fork | Recommended default |
|---|------|---------------------|
| 1 | `.obj` transport | Uploaded bytes |
| 2 | Binary location/build | Env-var path + PATH fallback + `make install` |
| 3 | `/extract-rules` source of truth | New Go `-print-defaults` flag |
| 4 | `/autocorrect` scope | Backend/Blender re-codegen (Medium) |

# Proposal: Go CLI microservice — OBJ AABB + geometric-regulation validation

## Intent

Add a greenfield Go CLI (`validator_go/`) that parses Blender-exported `.obj` files, computes the Axis-Aligned Bounding Box (AABB), and validates geometric regulations (wall heights/thicknesses, building height) in milliseconds. Today the DSL only enforces positivity (`gt=0`); no min/max normativa exists, and no unit is declared. This change pins meters-by-convention and delivers a fast, static-binary validator the Python backend can later invoke via subprocess.

## Scope

### In Scope
- `validator_go/` Go module: `go.mod`, `main.go`, `internal/obj` (single-pass parser), `internal/aabb`, `internal/validate`.
- CLI flags: `-input`, `-format json|text`, optional min/max wall-height, min/max wall-thickness, max-building-height.
- JSON output: AABB (6 scalars + dx/dy/dz) + structured violations. Exit 0=pass, 1=violations, 2=parse error.
- Unit tests for parser, AABB, validation rules.

### Out of Scope
- Frontend, bidirectional sync, auth/persistence.
- Python-backend subprocess wiring; distributed file transfer.
- Floor/opening/volume CSG validation beyond walls.
- Root `Makefile` changes (kernel build — do NOT overload).

## Capabilities

### New Capabilities
- `geometry-validator`: OBJ parsing, AABB computation, and wall/height geometric-regulation validation with unit (meters) and Y-up axis convention.

### Modified Capabilities
- None.

## Approach

Standalone Go static binary (cold start ~2–5 ms), single-pass `bufio.Scanner` parse (no regexp) over `v` lines for min/max AABB. Classify per-object AABB by `o`/`g` name prefix (`wall_`, `floor_`, `volume_`). Walls read height from the OBJ **Y** axis (Blender default `forward_axis=NEGATIVE_Z`, `up_axis=Y`). Parser tolerates negative relative `f` indices, `f` forms `v`, `v/vt/vn`, `v//vn`, polygon fans, `usemtl`/`mtllib`/`vt`/`vn`, comments, line continuations, CRLF.

### First-Slice Boundary
Validator is a local CLI taking a local `.obj` path. Cross-host file transfer and exporter axis-pinning are deferred.

## Proposed Artifacts
- `validator_go/go.mod`, `main.go`
- `validator_go/internal/obj/{parser,parser_test}.go`
- `validator_go/internal/aabb/{aabb,aabb_test}.go`
- `validator_go/internal/validate/{rules,rules_test}.go`
- `validator_go/Makefile` (build/test/vet)

## Open Decisions (recommended defaults)
1. **Module path**: `github.com/sketchos/validator-go` (survives future remote; dotless local path breaks `go get`). Tradeoff: assumes org name.
2. **Runtime location**: local CLI boundary; co-located/single-host invocation. Defer cross-host.
3. **Unit + axis**: meters; validator reads OBJ as-is and treats **Y as up** (documented). Do NOT touch exporter. Tradeoff: exporter change later would require re-read.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Y-up vs Z-up height misread | High | Read height from Y; verify against a real exported file; document convention |
| Rotated walls inflate AABB thickness | Med | Document that thickness = AABB depth is exact only for axis-aligned walls |
| Object-name coupling (`wall_` prefix) | Med | Make prefix configurable via flag |
| No declared unit | Med | Pin meters explicitly in spec |

## Rollback Plan

`validator_go/` is additive and unreferenced by Python. Revert = delete the directory; no existing module depends on it.

## Dependencies

- Go toolchain `1.26.5` (installed). No external Go modules required.

## Success Criteria

- [ ] `go test ./...` passes in `validator_go/`.
- [ ] Parser computes correct AABB on a real Blender-exported `.obj`.
- [ ] Wall height is read from the Y axis and validates against thresholds.
- [ ] Typical architectural model validates in <50 ms wall-clock.

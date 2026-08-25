# Tasks: Go CLI validator — OBJ AABB + geometric-regulation validation

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~900–1100 authored (11 files) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (foundation) → PR 2 (validation+report) → PR 3 (CLI wiring) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

> **Non-blocking flag**: `-min-height` 2.0m and `-min-thickness` 0.1m are PROVISIONAL; `-max-height`/`-max-thickness` default 0 = unenforced (deferred). Final normativa values are a later product decision — do NOT block apply on them.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Module + AABB + streaming parser | PR 1 | `go test ./internal/aabb ./internal/objparse` | real `.obj` fixture fed through the visitor | delete `validator_go/` (additive, unreferenced) |
| 2 | Validation rules + JSON report | PR 2 | `go test ./internal/validate ./internal/report` | JSON printed for a wall fixture | revert `internal/validate` + `internal/report` only |
| 3 | CLI wiring + benchmark | PR 3 | `go test ./...` then `go run . -input fixture.obj` | end-to-end 10k-vertex run <50ms | revert `main.go` + `Makefile` only |

## Phase 1: Foundation (module + AABB + parser)

- [x] 1.1 Create `validator_go/go.mod` — module `github.com/sketchos/validator-go`, go 1.26, no external deps.
- [x] 1.2 Create `validator_go/internal/aabb/aabb.go` — `AABB{MinX,MinY,MinZ,MaxX,MaxY,MaxZ}`, `Dimensions()` (dx,dy,dz), accumulation. Req: AABB computation.
- [x] 1.3 Create `validator_go/internal/aabb/aabb_test.go` — table tests (go-testing): axis-aligned box + rotated-about-Y wall; assert 6 scalars + dx/dy/dz. Scenarios: Axis-aligned box, Non-axis-aligned wall.
- [x] 1.4 Create `validator_go/internal/objparse/parser.go` — streaming `bufio.Scanner` + `Visitor`; `strings.Fields`+`strconv.ParseFloat` (no regexp); `resolve(idx,seen)`; `ParseError`. Req: OBJ parsing.
- [x] 1.5 Create `validator_go/internal/objparse/parser_test.go` — fixture-string tables: happy path, negative relative indices, malformed non-`v` skipped, malformed `v` → ParseError. Scenarios: all 4 OBJ-parsing scenarios.

## Phase 2: Core (validation + report)

- [x] 2.1 Create `validator_go/internal/validate/rules.go` — `Violation`; height = maxY−minY; thickness = min(dx,dz); thresholds; `wall_`/`floor_`/`volume_` classification. Req: Wall height/thickness validation.
- [x] 2.2 Create `validator_go/internal/validate/rules_test.go` — tables: Y-height (not Z), height out of range, thickness below min. Scenarios: Y-axis height, Height out of range, Thickness below minimum.
- [x] 2.3 Create `validator_go/internal/report/report.go` — JSON encode AABB + objects + violations; map violations→exit 1. Req: JSON output.
- [x] 2.4 Create `validator_go/internal/report/report_test.go` — JSON decode shape + exit assertions (pass→0, violating→1). Scenarios: Passing model, Violating model.

## Phase 3: CLI wiring + performance

- [x] 3.1 Create `validator_go/main.go` — flags `-input/-output/-min-height/-max-height/-min-thickness/-max-thickness`; visitor→aabb→validate→report wiring; exit 0/1/2; diagnostics to stderr. Req: JSON output.
- [x] 3.2 Create `validator_go/Makefile` — `build`/`test`/`vet` targets (never the root kernel Makefile). *(pulled into PR 1 — slice-1 scope explicitly assigns the Makefile; see apply-progress.)*
- [x] 3.3 Add `BenchmarkParseAndValidate` (10k `v` lines) in objparse; assert <50ms wall-clock. Req: Performance — Millisecond validation.
- [x] 3.4 End-to-end verify: `go build ./... && go vet ./... && go test ./...` inside `validator_go/`.

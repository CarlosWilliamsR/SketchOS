# Design: Go CLI validator — OBJ AABB + geometric-regulation validation

## Technical Approach

Greenfield Go 1.26 module `github.com/sketchos/validator-go` under `validator_go/`. One static binary streams the `.obj`, accumulates global + per-object AABBs, applies wall rules, and prints JSON. Units meters; height from OBJ **Y** axis (Blender `wm.obj_export` default `up_axis=Y`). No external modules.

## Architecture Decisions

| Decision | Options | Tradeoff | Choice |
|---|---|---|---|
| Parser package | `obj` (proposal) vs `objparse` | `obj` collides with domain noun | `internal/objparse` |
| Tokenization | regexp vs `strings.Fields` + `strconv.ParseFloat` | slower; spec forbids | `strings.Fields` |
| Stream shape | buffer all vertices vs visitor callback | wastes memory; AABB online | visitor callback, O(1) memory |
| Height axis | Z vs Y | Blender `up_axis=Y` puts height on Y | Y: `maxY − minY` per wall |
| Thickness | `min(dx,dz)` vs `max(dx,dz)` | short horizontal extent | `min(dx,dz)`; exact only axis-aligned |
| Output format | `-format json/text` vs JSON only | spec needs JSON | JSON only |
| Thresholds | hardcode vs flags | values unfixed | flags |

## Data Flow

```
file ──► objparse (bufio.Scanner) ──Visitor──► aabb accumulate (global + per-object)
                                                   │
                                                   ▼
                                       validate (wall rules) ──► report (JSON)
                                                                   │
                                                   stdout / -output file + exit code
```

Parser emits vertex/object/face events wired by `main` into AABB accumulation. Faces are validated (index resolution) but discarded — AABB is vertex-only.

## File Changes

| File | Action | Description |
|---|---|---|
| `validator_go/go.mod` | Create | module `github.com/sketchos/validator-go`, go 1.26 |
| `validator_go/main.go` | Create | flag parsing, visitor wiring, exit-code mapping |
| `validator_go/internal/objparse/parser.go` | Create | streaming parser + `Visitor` |
| `validator_go/internal/objparse/parser_test.go` | Create | fixture `.obj` string tests |
| `validator_go/internal/aabb/aabb.go` | Create | `AABB` type + accumulation |
| `validator_go/internal/aabb/aabb_test.go` | Create | axis-aligned + rotated cases |
| `validator_go/internal/validate/rules.go` | Create | thresholds, `Violation`, per-wall measures |
| `validator_go/internal/validate/rules_test.go` | Create | threshold/Y-axis/thickness tables |
| `validator_go/internal/report/report.go` | Create | JSON encoding |
| `validator_go/internal/report/report_test.go` | Create | JSON shape + exit codes |
| `validator_go/Makefile` | Create | `build`/`test`/`vet` (NOT root kernel Makefile) |

## Interfaces / Contracts

```go
type Visitor interface {
    VisitVertex(x, y, z float64)
    VisitObject(name string)      // o / g line
    VisitFace(indices []int)      // AABB ignores
}

// 1-based positive idx -> idx-1 ; negative -k -> seen+k
func resolve(idx, seen int) int {
    if idx > 0 { return idx - 1 }
    return seen + idx
}

type AABB struct { MinX, MinY, MinZ, MaxX, MaxY, MaxZ float64 }
func (a *AABB) Dimensions() (dx, dy, dz float64)

type Violation struct {
    Type      string  `json:"type"`       // wall_height_min|wall_height_max|wall_thickness_min|wall_thickness_max
    Object    string  `json:"object"`
    Measured  float64 `json:"measured"`
    Threshold float64 `json:"threshold"`
    Message   string  `json:"message"`
}
```

Classification by name prefix `wall_`/`floor_`/`volume_` (matches `blender_client._add_cube`):

```json
{
  "aabb": {"min": {"x":0,"y":0,"z":0}, "max": {"x":0,"y":0,"z":0},
           "dimensions": {"dx":0,"dy":0,"dz":0}},
  "objects": [{"name":"wall_1","height":3.0,"thickness":0.25}],
  "violations": [{"type":"wall_height_min","object":"wall_1",
                  "measured":1.5,"threshold":2.0,"message":"..."}]
}
```

## CLI

| Flag | Default | Meaning |
|---|---|---|
| `-input` | required | local `.obj` path |
| `-output` | "" (stdout) | write JSON to file |
| `-min-height` | 2.0 | min wall height (m) |
| `-max-height` | 0 (unset) | max wall height (m) |
| `-min-thickness` | 0.1 | min wall thickness (m) |
| `-max-thickness` | 0 (unset) | max wall thickness (m) |

`0` = bound unenforced. JSON to stdout/`-output`; diagnostics to stderr. Exit 0 = pass, 1 = violations, 2 = parse error. `bufio.Scanner` buffer raised above 64 KB (long `f` fan lines).

## Error Handling

- `v` with <3 numeric fields → `ParseError` (exit 2).
- Unknown/malformed non-`v` line (`f`, `vt`, `vn`, `usemtl`, `mtllib`, `s`, `#`, blank, CRLF) → skipped.
- Negative relative index resolving before vertex 0 → `ParseError` (exit 2).

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit (objparse) | v/f/o/g, negative indices, malformed v vs non-v | fixture `.obj` strings, table tests |
| Unit (aabb) | axis-aligned + rotated-about-Y walls | table tests: 6 scalars + dx/dy/dz |
| Unit (validate) | Y-height (not Z), height/thickness thresholds | table tests per rule |
| Unit (report) | JSON schema + exit codes | JSON decode + exit assertions |
| Benchmark | 10k `v` lines <50 ms | `BenchmarkParseAndValidate` in `objparse` |

`go-testing` skill applies (table + golden; no Bubbletea). Build via `go build ./...` / `go test ./...` inside `validator_go/` — never the root NASM kernel `Makefile`.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary (Python subprocess wiring deferred).

## Migration / Rollout

No migration. Additive directory unreferenced by Python; rollback = delete `validator_go/`.

## Open Questions

- [ ] Final normativa thresholds (min/max height, thickness) — provisional defaults.
- [ ] Whether `-max-height`/`-max-thickness` are needed (max-building-height deferred).

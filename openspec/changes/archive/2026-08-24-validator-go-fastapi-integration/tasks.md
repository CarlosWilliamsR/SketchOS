# Tasks: Connect Go Validator (validator_go) to FastAPI Backend via CLI Subprocess

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~480–620 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Go `-print-defaults` + install target | PR 1 | `go test ./...` | `go run . -print-defaults` prints 4-key JSON, exit 0 | revert `validator_go/{main.go,internal/report/report.go,main_test.go,Makefile}` |
| 2 | Client + `/extract-rules` + `/validate-geometry` | PR 2 | `pytest backend/tests/test_validator_client.py backend/tests/test_validator_routes.py -k "not autocorrect"` | `make install` then curl `/extract-rules` and POST `/validate-geometry` | revert `validator_client.py`, `validator_routes.py` endpoints, `main.py` registration |
| 3 | `/autocorrect` re-codegen loop | PR 3 | `pytest backend/tests/test_validator_routes.py -k autocorrect` | POST `/autocorrect` DSL → re-validates clean | revert `validator_routes.py` autocorrect handler + test |

## Phase 1: Go `-print-defaults` (prerequisite for `/extract-rules`)

- [x] 1.1 RED: add failing test in `validator_go/main_test.go` — `-print-defaults` exits 0, prints four threshold keys, requires no `-input` (geometry-validator "Default thresholds flag" scenarios).
- [x] 1.2 Add `ThresholdsJSON` struct + `WriteDefaults(w, validate.Thresholds)` to `validator_go/internal/report/report.go`.
- [x] 1.3 Add `-print-defaults` flag to `validator_go/main.go` after `fs.Parse`, before the `*input == ""` guard.
- [x] 1.4 Add `install` target to `validator_go/Makefile` (build + copy to `$GOBIN`).

## Phase 2: Backend client + endpoints

- [x] 2.1 RED: write failing process-integration tests in `backend/tests/test_validator_client.py` — argv list-form, `shell` never enabled, env-var→PATH fallback, exit 0/1/2, temp-file removal in `finally`, spawn-fail 503, timeout 504 (threat-matrix boundary).
- [x] 2.2 Create `backend/src/sketchos_backend/validator_client.py`: list-form argv, no `shell=True`, `VALIDATOR_GO_BIN`→PATH fallback, `wait_for` timeout, exit-code map (spec: "Subprocess validator client", "Exit-code mapping", "Timeout and error handling").
- [x] 2.3 Create `backend/src/sketchos_backend/validator_routes.py` with `GET /extract-rules` (`-print-defaults`) and `POST /validate-geometry` (UploadFile bytes → temp file → 200 pass/violations, 422 parse error, 503/504).
- [x] 2.4 Register router in `backend/src/sketchos_backend/main.py` via `app.include_router(...)` next to the `/mcp` mount (spec: "Validator HTTP endpoints").
- [x] 2.5 Add `POST /autocorrect` to `validator_routes.py`: DSL → `ArchitectureModel` → `correct_model` → `server.build_architecture`/Blender re-codegen → re-validate (spec: "Autocorrect endpoint").

## Phase 3: Endpoint contract tests

- [x] 3.1 Create `backend/tests/test_validator_routes.py` (fake client): `/extract-rules` thresholds; `/validate-geometry` 200/422/503/504; `/autocorrect` clean re-validate.
- [x] 3.2 Run `go test ./...` and `pytest backend/tests/`; confirm all spec scenarios green.

## Phase 4: Cleanup

- [x] 4.1 Document `VALIDATOR_GO_BIN`/`make install`; note rotated-wall residual-thickness caveat in autocorrect response.

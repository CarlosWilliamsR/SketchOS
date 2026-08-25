# Apply Progress: validator-go-fastapi-integration

- **Phase**: sdd-apply
- **Batch**: Slice 3 of 3 (PR 3 — endpoint contract tests + docs) — FINAL
- **Mode**: Standard (strict_tdd not enabled — no `openspec/config.yaml`)
- **Delivery strategy**: ask-on-risk → resolved: chained PRs (`stacked-to-main`)
- **Current work unit**: Unit 3 — `/autocorrect` re-codegen loop contract tests + cleanup docs

## Cumulative Task State

### Phase 1: Go `-print-defaults` (prerequisite for `/extract-rules`) — Slice 1 DONE

- [x] 1.1 `validator_go/main_test.go` — `TestRunPrintDefaults` exits 0, prints four threshold keys, requires no `-input` — DONE
- [x] 1.2 `validator_go/internal/report/report.go` — `ThresholdsJSON` struct + `WriteDefaults(w, validate.Thresholds)` — DONE
- [x] 1.3 `validator_go/main.go` — `-print-defaults` flag after `fs.Parse`, before the `*input == ""` guard — DONE
- [x] 1.4 `validator_go/Makefile` — `install` target (`go install .` → `$GOBIN`/`$(go env GOPATH)/bin`) — DONE

### Phase 2: Backend client + endpoints — Slice 2 DONE

- [x] 2.1 `backend/tests/test_validator_client.py` — 11 process-integration tests (RED-first): argv list-form, `shell` never enabled, env-var→PATH fallback, exit 0/1/2 mapping, temp-file removal in `finally` (incl. on spawn failure), spawn-fail 503, timeout 504 — DONE
- [x] 2.2 `backend/src/sketchos_backend/validator_client.py` — `ValidatorClient` (list-form argv, `create_subprocess_exec`, `wait_for` timeout, exit-code map) — DONE
- [x] 2.3 `backend/src/sketchos_backend/validator_routes.py` — `GET /extract-rules` + `POST /validate-geometry` (200 pass/violations, 422 parse error, 503/504) — DONE
- [x] 2.4 `backend/src/sketchos_backend/main.py` — `app.include_router(validator_router)` next to the `/mcp` mount (mount untouched) — DONE
- [x] 2.5 `POST /autocorrect` — DSL → `ArchitectureModel` → `correct_model` (exact-threshold single-pass) → `build_architecture`/Blender re-codegen → re-validate — DONE

### Phase 3: Endpoint contract tests — Slice 3 DONE (this batch)

- [x] 3.1 `backend/tests/test_validator_routes.py` — 9 endpoint contract tests with an injected fake `ValidatorClient` (no real binary): `/extract-rules` thresholds; `/validate-geometry` 200 pass / 200 violations (exit 1 NOT an error) / 422 parse error / 503 spawn fail / 504 timeout; `/autocorrect` clean re-validate; endpoints discoverable via OpenAPI paths; `/mcp` mount preserved — DONE
- [x] 3.2 Full suites green — `uv run pytest tests -q` → **72 passed**; `go test ./...` → **ok (5 packages)** — DONE

### Phase 4: Cleanup — Slice 3 DONE (this batch)

- [x] 4.1 `backend/README.md` — documented `VALIDATOR_GO_BIN` env-var + `make install` usage and the rotated-wall residual-thickness caveat (accepted for v1, surfaced in the autocorrect `report`) — DONE

## Work Unit Evidence (Slice 3)

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `uv run pytest tests/test_validator_routes.py -q` (from `backend/`) → **9 passed**, exit 0 |
| Runtime harness command/scenario and exact result | N/A for a real Go/Blender run in this slice (contract suite uses an injected fake client, no binary); real-binary runtime path already proven in Slice 2. Full suite `uv run pytest tests -q` → **72 passed**; `go test ./...` → **ok (5 packages)** |
| Rollback boundary | revert `backend/tests/test_validator_routes.py` and the README validator-integration section; no production code, Go, or Blender files touched |

## TDD Cycle Evidence (RED → GREEN) — Slice 3

| Task | RED (test first) | GREEN (implementation) | REFACTOR |
|------|------------------|------------------------|----------|
| 3.1 | `test_validator_routes.py` written first against the existing routes (contract assertions) | All 9 contract tests pass against slice-2 production code with a fake client — no production change required | — |

Slice 3 is a pure test/documentation slice: production code (`validator_client.py`, `validator_routes.py`, `main.py`, `main.go`) was NOT modified. Tests were written against the already-landed slice-2 implementation and pass unchanged.

## Files Changed (Slice 3)

| File | Action | What Was Done |
|------|--------|---------------|
| `backend/tests/test_validator_routes.py` | Created | 9 endpoint contract tests with an injected fake `ValidatorClient`: `/extract-rules` thresholds; `/validate-geometry` 200/200/422/503/504; `/autocorrect` clean re-validate (2 validations, 1 fix); OpenAPI-path discoverability (NOT an `app.routes` scan — `include_router` registers an `_IncludedRouter` node, not individual APIRoutes); `/mcp` mount preserved |
| `backend/README.md` | Modified | Added "Geometry validator integration" section: `VALIDATOR_GO_BIN` env-var + `make install` guidance, and the rotated-wall residual-thickness caveat |
| `openspec/changes/validator-go-fastapi-integration/tasks.md` | Modified | Marked 3.1, 3.2, 4.1 `[x]` |

## Deviations from Design

- None — implementation matches design. Slice 3 added no production code; the contract tests and docs were exactly the planned Phase 3 + Phase 4 work.

## Issues Found

- None blocking. Both suites green. Two pre-existing deprecation warnings (Starlette `TestClient`→httpx2, pydantic_settings `lifespan` forward reference) are unrelated to this change.

## Verification Note (Slice 3)

- `uv run pytest tests/test_validator_routes.py -q` → **9 passed** (exit 0).
- `uv run pytest tests -q` (from `backend/`) → **72 passed** (63 prior + 9 new), exit 0.
- `go test ./...` (from `validator_go/`) → ok for all 5 packages, exit 0.
- OpenAPI `paths` include `/extract-rules`, `/validate-geometry`, `/autocorrect`; `app.routes` shows an `_IncludedRouter` node + `Mount /mcp` (confirming the OpenAPI-path assertion was the correct approach).

### Prior Slice 1 Evidence (carried forward)

- `go test ./...` → ok all 5 packages; `validator-go -print-defaults` → `{"min_height":2,"max_height":0,"min_thickness":0.1,"max_thickness":0}`, exit 0.

### Prior Slice 2 Evidence (carried forward)

- `uv run pytest tests -q` → 63 passed; real-binary runtime harness: `/extract-rules` 200; `/validate-geometry` pass 200 / violations 200 / parse-error 422; `/autocorrect` invalid-DSL 422. No `shell=True` in new code.

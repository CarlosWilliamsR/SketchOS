# Apply Progress: Editable Regulations (PR 1 — Backend Thresholds)

**Change**: editable-regulations
**Mode**: Strict TDD (`strict_tdd: true`, pytest runner)
**Artifact store**: hybrid (OpenSpec + Engram)
**Delivery**: auto-chain / stacked-to-main — this batch is PR #1 (backend slice)

## Summary

Implemented the backend threshold-passing slice (Phases 1–2): a shared pydantic
`Thresholds` model, optional thresholds on `/validate-geometry` (4 multipart
`Form` fields) and `/autocorrect` (JSON `thresholds` key), with `extract_rules()`
fallback when absent and 422 on invalid input (min > max, negative, non-finite).
No Go core change — `validator-go` already registers the four flags and they are
forwarded unchanged via `ValidatorClient.validate`.

## Completed Tasks

- [x] 1.1 RED — `Thresholds` model cases (min>max, negative, NaN/Inf → invalid; valid/all-None pass)
- [x] 1.2 GREEN — `Thresholds(BaseModel)` in `validator_routes.py`
- [x] 2.1 RED — `/validate-geometry` optional `Form` fields forwarded; absent → `extract_rules()`
- [x] 2.2 GREEN — `validate_geometry` accepts 4 optional `Form(...)` fields, resolve once, 422/503/504 mapping kept
- [x] 2.3 RED — `/autocorrect` `thresholds` key popped before `model_validate`; SAME thresholds on both passes
- [x] 2.4 GREEN — `autocorrect` pops `thresholds` first, resolves once, reuses one `thresholds` local
- [x] 2.5 RED — argv stays list-form with numeric strings (injection-safety)

## Files Changed

| File | Action | What Was Done |
|---|---|---|
| `backend/src/sketchos_backend/validator_routes.py` | Modified | `Thresholds` model; `_resolve_thresholds` helper; 4 optional `Form` fields on `validate_geometry`; `payload.pop("thresholds", None)` before `ArchitectureModel.model_validate` in `autocorrect` |
| `backend/tests/test_validator_routes.py` | Modified | 22 new tests (8 model + 8 validate-geometry + 6 autocorrect) |
| `openspec/changes/editable-regulations/tasks.md` | Modified | marked 1.1–2.5 `[x]` |

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 1.1–1.2 | `backend/tests/test_validator_routes.py` | Unit | ✅ 20/20 | ✅ ImportError (model absent) | ✅ 17 passed | ✅ 8 cases | ✅ Clean |
| 2.1–2.2 | `backend/tests/test_validator_routes.py` | Integration | ✅ 20/20 | ✅ failed (forwarding/422) | ✅ 31 passed | ✅ 8 cases | ✅ Clean |
| 2.3–2.4 | `backend/tests/test_validator_routes.py` | Integration | ✅ 20/20 | ✅ failed (pop/reuse/leak) | ✅ 31 passed | ✅ 6 cases | ✅ Clean |
| 2.5 | `backend/tests/test_validator_routes.py` | Integration | ✅ 20/20 | ✅ failed (injection/coerce) | ✅ 31 passed | ✅ 2 cases | ➖ None needed |

Phase 2 RED was written in one batch (tasks 2.1, 2.3, 2.5 together) and showed 10
failing tests; the single GREEN wiring pass (tasks 2.2, 2.4) resolved all of them.

### Test Summary

- **Total tests written**: 22
- **Total tests passing**: 22 new (full backend suite: 133 passed)
- **Layers used**: Unit (8), Integration (14)
- **Approval tests** (refactoring): None — no refactoring tasks
- **Pure functions created**: 1 (`_resolve_thresholds`)

## Work Unit Evidence

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `uv run pytest tests/test_validator_routes.py -q` → `31 passed` (exit 0) |
| Runtime harness command/scenario and exact result | Real `validator-go` smoke: `-print-defaults` → `{"min_height":2,"max_height":0,"min_thickness":0.1,"max_thickness":0}`; `validator-go -input smoke_wall.obj -min-height 2.5 ...` → exit 1, violation `threshold: 2.5` |
| Rollback boundary | Revert `backend/src/sketchos_backend/validator_routes.py` + `backend/tests/test_validator_routes.py` (and `tasks.md` checkbox marks); no unrelated files touched |

## Deviations from Design

None — implementation matches design (Thresholds model shape, `extra="forbid"`,
pop-before-validate, resolve-once, `0 = unenforced` truthiness semantics in
`_bounds`). `validator_client.py` unchanged (no behavior change), as designed.

## Issues Found

- `_num()` in `validator_client.py` uses `str(value)` which can emit scientific
  notation for extreme float magnitudes; pre-existing and unchanged (out of scope
  for this PR).
- Two autocorrect invalid-threshold tests initially passed for the wrong reason
  (the DSL `extra="forbid"` path also yields 422); they were strengthened to
  assert `"Invalid thresholds"` in the detail so they discriminate the new path.

## Workload / PR Boundary

- Mode: chained PR slice (PR 1 of 2, `stacked-to-main`)
- Current work unit: Backend thresholds (Phases 1–2)
- Boundary: backend-only; frontend (api.js / profiles.js / Regulations UI) deferred to PR 2
- Estimated review budget: ~396 changed lines (388 insertions + 8 deletions)

## Status

7/7 PR-1 tasks complete. Backend slice ready for verify; PR 2 (frontend) remains.

# Tasks: Editable Regulations

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~500–600 (backend ~220, frontend ~300, incl. tests) |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (backend) → PR 2 (frontend) |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | `Thresholds` model + optional thresholds on `/validate-geometry` & `/autocorrect` (422 invalid, extract_rules fallback) | PR 1 | `pytest backend/tests/test_validator_routes.py -q` | Fake `ValidatorClient` records `validate_thresholds`; real `validator-go` smoke | Revert `backend/src/sketchos_backend/validator_routes.py` + `test_validator_routes.py` |
| 2 | api.js threshold flow + `profiles.js` localStorage store + editable Regulations UI + profile CRUD | PR 2 | `vitest run src/lib/api.test.js src/lib/profiles.test.js src/components/ValidatorDashboard.test.jsx` | `npm run dev` → edit thresholds, validate `.obj`, save/load profile | Revert `api.js`, `profiles.js`, `ValidatorDashboard.jsx` + their tests |

## Phase 1: Backend Thresholds Model + Validation (PR 1)

- [x] 1.1 RED — `backend/tests/test_validator_routes.py`: cases for `Thresholds` — min>max, negative, NaN/Inf → 422; valid/all-None pass. Fails (model absent).
- [x] 1.2 GREEN — `backend/src/sketchos_backend/validator_routes.py`: add `Thresholds(BaseModel)` (`extra="forbid"`, `Field(None, ge=0, allow_inf_nan=False)`, after-validator min≤max).

## Phase 2: Backend Endpoint Wiring (PR 1)

- [x] 2.1 RED — tests: `/validate-geometry` optional `Form` fields forwarded to `client.validate`; absent → `extract_rules()` fallback.
- [x] 2.2 GREEN — `validate_geometry`: accept 4 optional `Form(...)` fields, build `Thresholds`, resolve once, forward; keep 422/503/504 mapping.
- [x] 2.3 RED — tests: `/autocorrect` `thresholds` key popped before `ArchitectureModel.model_validate`; SAME thresholds on both `_validate_model` passes.
- [x] 2.4 GREEN — `autocorrect`: `payload.pop("thresholds", None)` first, resolve once, reuse single `thresholds` local.
- [x] 2.5 RED — assert argv stays list-form with numeric strings (threat-matrix injection-safety).

## Phase 3: Frontend api.js + Profiles Store (PR 2)

- [ ] 3.1 RED — `frontend/src/lib/api.test.js`: `validateGeometry(file, t)` appends 4 fields; `autocorrect(dsl, t)` merges `thresholds` into JSON; `fetchRules` unchanged.
- [ ] 3.2 GREEN — `frontend/src/lib/api.js`: `validateGeometry(file, thresholds)`, `autocorrect(dsl, thresholds)`.
- [ ] 3.3 RED — `frontend/src/lib/profiles.test.js`: save/load/delete/active under `sketchos_regulation_profiles`; empty/duplicate name rejected.
- [ ] 3.4 GREEN — create `frontend/src/lib/profiles.js` (mirror BYOK pattern: `{profiles, activeName}`).

## Phase 4: Frontend Regulations UI (PR 2)

- [ ] 4.1 RED — `frontend/src/components/ValidatorDashboard.test.jsx`: editable inputs, "0 = no limit", client blocks min>max/negative/non-finite before backend.
- [ ] 4.2 GREEN — `ValidatorDashboard.jsx`: editable 4 inputs + "no limit" hint + client validation.
- [ ] 4.3 RED/GREEN — profile CRUD UI + active indicator wired to `profiles.js`; mount `fetchRules` populates inputs.

## Phase 5: Verification / Cleanup

- [ ] 5.1 Run `pytest`, `vitest`, `go test ./validator_go/...` — all green; TDD proof before archive.
- [ ] 5.2 Update docstrings/comments (`validator_routes.py`, `api.js`) to reflect threshold flow.

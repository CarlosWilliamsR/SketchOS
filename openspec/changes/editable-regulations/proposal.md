# Proposal: Editable Regulations

## Intent

Architects must validate geometry against their own thresholds (wall min/max height, min/max thickness), but today thresholds are hardcoded Go defaults (`DefaultThresholds()`), fetched read-only via `extract_rules()`, with no edit UI, no profiles, no persistence. This change lets architects edit the 4 thresholds and save/load named profiles ("CABA residencial", "Comercial") so validation reflects local normativa instead of one fixed rule set.

## Scope

### In Scope

- Editable 4 thresholds (wall min/max height, min/max thickness) in the Regulations tab.
- Named profiles: save/load/delete + active selection (frontend localStorage).
- Threshold validation: min ≤ max, non-negative, finite.
- Per-request threshold passing through all 3 endpoints (`/extract-rules`, `/validate-geometry`, `/autocorrect`).
- `extract_rules()` retained as sensible-defaults fallback when no thresholds supplied.
- `0 = unenforced` surfaced in the UI.

### Out of Scope

- Free rule editor (arbitrary expression rules).
- Backend-side profile store/persistence (no server DB) — deferred.
- Multi-element-type rules (walls only).

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `backend-service`: optional per-request thresholds on `/validate-geometry` (form/query) and `/autocorrect` (JSON), fallback to `extract_rules()`, server-side threshold validation.
- `frontend-validator-dashboard`: editable Regulations tab, named profile CRUD in localStorage, active-profile selection, `0 = unenforced` UX.
- `geometry-validator`: document per-call threshold flags already supported (clarification only; no Go behavior change).

## Approach

Per-request thresholds via existing Go flags + frontend localStorage profiles. Backend accepts optional thresholds, forwards to `client.validate()` (already builds argv from thresholds), falls back to `extract_rules()` when absent. Frontend persists named profiles in localStorage (mirroring the BYOK modal), sends the active profile's thresholds each request. `defaults.py` generation defaults stay decoupled.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/.../validator_routes.py` | Modified | Accept optional thresholds; stop hardcoding `extract_rules()` |
| `backend/.../validator_client.py` | Modified | Threshold validation + serialization |
| `frontend/.../ValidatorDashboard.jsx` | Modified | Editable Regulations tab |
| `frontend/.../api.js` | Modified | Forward thresholds on validate/autocorrect |
| `frontend/.../BYOKModal.jsx` | Reference | Reuse localStorage pattern for profiles |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `validate-geometry` is multipart; thresholds can't ride the JSON body | Med | Serialize as form fields/query params consistently |
| `0 = unenforced` confuses users | High | Explicit "no limit" label + helper text |
| Invalid thresholds reach Go | Med | Server-side validation (min ≤ max, ≥ 0, finite) |
| Autocorrect re-validate uses wrong thresholds | Med | Apply SAME custom thresholds on both passes |
| Stale specs | Med | Update 3 specs with MODIFIED requirements |

## Rollback Plan

Feature is additive and per-request; when thresholds are absent the endpoints fall back to `extract_rules()`, preserving current behavior. Revert frontend/backend diffs; localStorage profiles are non-destructive.

## Dependencies

None external.

## Success Criteria

- [ ] Architect edits 4 thresholds and validates geometry against them (no hardcoded fallback).
- [ ] Named profiles save/load/delete and persist across reloads.
- [ ] Invalid thresholds (min > max, negative, NaN) rejected with a clear message.
- [ ] `0` clearly labeled "no limit" in the UI.
- [ ] All 3 endpoints accept thresholds; absent thresholds fall back to defaults.
- [ ] Go/Python/Vitest tests pass (strict TDD).

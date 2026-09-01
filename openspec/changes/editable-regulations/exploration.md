# Exploration: editable-regulations

Let architects define their own geometric validation thresholds (wall min/max
height, min/max thickness) from the UI, and save/load NAMED PROFILES (e.g.
"CABA residencial", "Comercial"), instead of relying on the hardcoded Go
defaults.

## Current State

The 4 validation thresholds are enforced entirely inside the Go validator
(`validator_go/internal/validate/rules.go`): `Thresholds{MinHeight, MaxHeight,
MinThickness, MaxThickness}` and `DefaultThresholds()` returning
`{2.0, 0, 0.1, 0}` (0 = unenforced). The four rule constants are
`wall_height_min/max` and `wall_thickness_min/max`.

The threshold plumbing is ALREADY per-call, not compile-time-only:

- `validator_go/main.go` registers CLI flags `-min-height` (2.0),
  `-max-height` (0), `-min-thickness` (0.1), `-max-thickness` (0) and builds a
  `Thresholds` struct from them on every run. `-print-defaults` prints
  `DefaultThresholds()` and exits. So the Go binary can already validate
  against arbitrary thresholds supplied on the command line.
- `backend/.../validator_client.py` → `validate(obj_bytes, thresholds)` builds
  argv with all four flags (`-min-height` … `-max-thickness`) using
  `_num(...)`. `extract_rules()` runs `-print-defaults` and parses the JSON.
- `backend/.../validator_routes.py` — all three endpoints obtain thresholds by
  calling `client.extract_rules()`:
  - `GET /extract-rules` returns the defaults.
  - `POST /validate-geometry` calls `extract_rules()` then
    `client.validate(obj_bytes, thresholds)`.
  - `POST /autocorrect` calls `extract_rules()` then `_validate_model(...)`
    (which calls `client.validate(...)`), and `correct_model()` reads each
    violation's `threshold` field (so a custom threshold already flows into
    autocorrect corrections — no hardcoding there).

The real gap: the backend NEVER accepts user-supplied thresholds; it always
falls back to the Go defaults. There is no edit UI, no profile concept, and no
persistence.

Frontend:

- `frontend/src/components/ValidatorDashboard.jsx` — the "Regulations" tab
  renders thresholds read-only from `fetchRules()` (`rules.min_height`, etc.).
- `frontend/src/lib/api.js` — `fetchRules` (GET /extract-rules),
  `validateGeometry` (multipart), `autocorrect` (JSON DSL), `generateFromText`.
  `request()` injects `X-Gemini-Api-Key` from `localStorage.getItem('gemini_api_key')`.
- `frontend/src/components/BYOKModal.jsx` — the reusable localStorage
  persistence pattern (`STORAGE_KEY = 'gemini_api_key'`, `localStorage.getItem/
  setItem/removeItem`, masked display, modal save/clear/rotate).

Generation defaults (a DIFFERENT concept):

- `backend/.../defaults.py` — `DefaultParams` (wall_height=3.0,
  wall_thickness=0.3, floor_thickness=0.2, floor_to_floor_height=3.0),
  env-overridable via `SKETCHOS_DEFAULT_*`, injected into text-to-DSL prompts
  via `render_defaults_directive()`. These supply MISSING dimensions so a
  bare prompt still yields a schema-valid model. They are NOT validation
  thresholds.

Persistence landscape: the backend has NO user-data persistence (no DB, no
sqlite/sqlalchemy, no file store) — only env vars (`VALIDATOR_GO_BIN`,
`SKETCHOS_DEFAULT_*`, `GOOGLE_API_KEY`/`GEMINI_API_KEY`). The ONLY existing
user-data persistence is frontend `localStorage` (the BYOK key).

## Affected Areas

- `validator_go/internal/validate/rules.go` — `DefaultThresholds()` and the
  `Thresholds` struct (the "hardcoded" fallback values).
- `validator_go/main.go` — flag registration (already supports overrides);
  likely only needs new tests, not new flags.
- `validator_go/internal/report/report.go` — `ThresholdsJSON` / `WriteDefaults`
  (shape of `/extract-rules` output; reuse for defaults fallback).
- `backend/src/sketchos_backend/validator_routes.py` — accept optional
  thresholds on validate/autocorrect; fall back to `extract_rules()` when
  absent; optional profile endpoints.
- `backend/src/sketchos_backend/validator_client.py` — `validate()` already
  passes flags; may need a helper to normalize/validate a threshold dict.
- `frontend/src/components/ValidatorDashboard.jsx` — turn the Regulations tab
  from read-only into editable fields + profile save/load.
- `frontend/src/lib/api.js` — new `saveProfile`/`listProfiles`/`deleteProfile`
  (or localStorage-only) and pass thresholds on validate/autocorrect.
- `frontend/src/components/BYOKModal.jsx` — reusable localStorage pattern to
  mirror for profiles.
- Tests: `backend/tests/test_validator_routes.py`,
  `validator_go/main_test.go`, `validator_go/internal/validate/rules_test.go`,
  `frontend/src/components/ValidatorDashboard.test.jsx`.

## Approaches

1. **Per-request thresholds (Go flags, already supported) + frontend
   localStorage profiles** — Backend accepts optional thresholds on
   `validate-geometry` and `autocorrect` and forwards them to the existing Go
   flags; when absent it falls back to `extract_rules()` (sensible defaults).
   Named profiles live in frontend `localStorage` (mirror BYOK); the active
   profile's thresholds are sent on each request.
   - Pros: smallest surface — Go flags and `client.validate()` already exist;
     no new backend persistence layer; matches the BYOK localStorage precedent;
     cross-cutting "sensible defaults when no data" = keep `extract_rules()`
     fallback; profiles survive refresh.
   - Cons: profiles are per-browser only (not shared across devices/users); no
     server-side validation/single-source-of-truth for profiles.
   - Effort: Low–Medium

2. **Backend-side named-profile store (JSON file) + per-request thresholds** —
   Backend adds a small profile CRUD (file-backed or DB) plus an "active
   profile" concept; validate/autocorrect resolve thresholds server-side from
   the active/selected profile.
   - Pros: shared profiles, server-side validation, single source of truth,
     frontend stays thin.
   - Cons: introduces the first persistence layer (no precedent — no DB, no
     file store, no auth/user model in backend today); concurrency concerns on
     file writes; larger surface and more tests.
   - Effort: Medium–High

3. **Frontend-only localStorage, thresholds passed inline (no backend store)** —
   Same mechanics as (1) but framing profiles as purely client-side with no new
   backend endpoints beyond optional threshold acceptance.
   - Pros/Cons: identical to (1); this is really (1) restated.
   - Effort: Low–Medium

## Recommendation

**Approach 1** (per-request thresholds via existing Go flags + frontend
localStorage named profiles) is the cleanest fit for the current architecture:

- The Go CLI already accepts arbitrary thresholds via flags — no Go core change
  is required, only tests to lock the behavior.
- `validator_client.validate()` already forwards thresholds per-call — the
  backend only needs to accept them from the request and stop hardcoding
  `extract_rules()` as the sole source.
- Frontend already has the exact localStorage persistence pattern to reuse
  (BYOK) and an existing "Regulations" tab to make editable.
- The cross-cutting constraint ("nothing hardcoded; sensible defaults when no
  data provided") is satisfied by keeping `DefaultThresholds()` /
  `extract_rules()` as the fallback when no thresholds/profile is supplied.

Named profiles SHOULD persist in **frontend localStorage** for this change:
consistent with the only existing persistence mechanism, zero new backend
infrastructure, and sufficient for a single-architect workflow. Introduce a
backend-side profile store (Approach 2) only when cross-device sharing or
multi-user becomes a real requirement — flag it as a future extension, not part
of this change.

## Thresholds vs generation defaults (clarification)

- **Validation thresholds (this change)**: decide whether geometry PASSES or
  FAILS — min/max wall height and thickness. Owned by the Go validator
  (`rules.go`), flow via CLI flags → `validate` → report violations.
- **Generation defaults (`defaults.py`, from text-to-dsl)**: decide what
  dimensions are ASSUMED when a text prompt omits them (wall height 3.0 m, wall
  thickness 0.3 m, floor thickness, floor-to-floor). Owned by the backend,
  injected into Gemini prompts.

They must stay decoupled: editing a validation profile must NOT silently mutate
`SKETCHOS_DEFAULT_*` generation assumptions, and vice versa. One real
interaction: `POST /autocorrect` sets a violating dimension to the violation's
`threshold`, so a stricter custom `min_thickness`/`min_height` will produce
thicker/taller corrected walls — this is expected and already implemented
(`correct_model` reads `violation.threshold`).

## Risks

- **`validate-geometry` is multipart** — thresholds must ride as a form field
  (or query param), not a JSON body, unlike `autocorrect`. Need a consistent
  serialization for the threshold dict across both endpoints.
- **0 = unenforced convention** — the UI must communicate that 0 means "no
  limit" (e.g. empty/cleared max), or users will think "0 m" is a real bound.
- **Threshold validation** — min ≤ max, non-negative, finite, sensible ranges
  must be validated server-side to avoid nonsense profiles (e.g. negative
  thickness) reaching the Go binary.
- **localStorage size/limits** — trivial for 4 floats per profile, but profile
  names/JSON must be safely serialized (JSON.parse guards).
- **Autocorrect uses thresholds twice** — the re-validate loop must apply the
  SAME custom thresholds on both passes, or the "clean" result will be
  validated against different limits.
- **Stale specs** — `geometry-validator`, `backend-service`, and
  `frontend-validator-dashboard` specs currently describe the read-only
  thresholds flow; they must be updated with MODIFIED requirements.

## Ready for Proposal

Yes. The orchestrator can proceed to `sdd-propose` with scope: (a) backend
accepts optional per-request thresholds with `extract_rules()` fallback,
(b) frontend editable Regulations tab + localStorage named profiles + select
active profile, (c) threshold validation and 0=unenforced UX, (d) update the
three affected specs, (e) tests across Go, Python, and Vitest. No Go core
change strictly required (flags already exist), but Go tests should pin the
per-call override behavior.

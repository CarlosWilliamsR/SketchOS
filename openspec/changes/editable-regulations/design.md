# Design: Editable Regulations

## Technical Approach

Add per-request threshold passing over the existing Go flags (already per-call via `client.validate(obj_bytes, thresholds)`) and named profile persistence in frontend localStorage. Backend accepts optional thresholds, validates them, forwards to the Go binary, and falls back to `extract_rules()` defaults when absent. No Go core change: `main.go` already registers `-min-height/-max-height/-min-thickness/-max-thickness`; the gap is purely that `validator_routes.py` hardcodes `extract_rules()` as the only source.

## Architecture Decisions

| Option | Tradeoff | Decision |
|---|---|---|
| validate-geometry thresholds as 4 optional `Form` fields vs query params vs JSON-string field | Form fields keep all request data in the multipart body; FastAPI coerces/validates per-field; frontend `form.append()` is trivial | 4 optional `Form(...)` fields |
| autocorrect thresholds as `thresholds` object key vs query param | JSON endpoint → sibling key is idiomatic; must be **popped before `ArchitectureModel.model_validate`** (`extra="forbid"`) | `thresholds` key, popped first |
| Server-side validation: shared pydantic `Thresholds` model vs inline checks | pydantic centralizes coercion + rules; `allow_inf_nan=False` rejects NaN/Inf | pydantic model, `422` on failure |
| Error code for invalid thresholds | `400` = malformed syntax; `422` = well-formed but semantically invalid; matches existing DSL/parse-error `422` convention | `422` |
| Autocorrect threshold resolution | Resolve ONCE, reuse for both `_validate_model` passes (already one variable) | single `thresholds` local |
| Profile storage shape | Single JSON key keeps profiles + active name atomic; mirrors BYOK localStorage pattern | `sketchos_regulation_profiles` |
| api.js always-sends thresholds | Explicit per-request is the editable behavior; backend fallback still serves direct API consumers | dashboard always passes form thresholds |

## Data Flow

```
Regulations form ──► profile CRUD ──► localStorage (sketchos_regulation_profiles)
        │ active thresholds (4 floats)
        ▼
api.js: validateGeometry(file, t)  ──► FormData(file + 4 fields)
        autocorrect(dsl, t)         ──► JSON({...dsl, thresholds})
        ▼
validator_routes: Thresholds model (validate min≤max, ≥0, finite) ──► 422 on bad
        │ absent → client.extract_rules() defaults
        ▼
client.validate(bytes, t) ──► argv[..., "-min-height", _num(...)] ──► validator-go
```

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/.../validator_routes.py` | Modify | `Thresholds` pydantic model; accept optional thresholds on validate/autocorrect; resolve once; 422 on invalid |
| `backend/.../validator_client.py` | Modify | (no behavior change; keep `_num` list-form argv as-is) |
| `frontend/src/lib/api.js` | Modify | `validateGeometry(file, thresholds)`, `autocorrect(dsl, thresholds)`; `fetchRules` unchanged |
| `frontend/src/lib/profiles.js` | Create | localStorage profile store (load/save/delete/active) — mirrors BYOK |
| `frontend/src/components/ValidatorDashboard.jsx` | Modify | Editable Regulations inputs, "0 = no limit" hint, client validation, profile CRUD, active indicator |
| `backend/tests/test_validator_routes.py` | Modify | RED tests: threshold passing, validation 422, autocorrect both passes |
| `frontend/src/lib/api.test.js`, `ValidatorDashboard.test.jsx` | Modify | FormData/JSON contract, profile CRUD, validation UI |

## Interfaces / Contracts

Thresholds wire shape (both endpoints): `{min_height, max_height, min_thickness, max_thickness}` — all optional floats, `0` = unenforced.

```python
class Thresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min_height: float | None = Field(None, ge=0, allow_inf_nan=False)
    max_height: float | None = Field(None, ge=0, allow_inf_nan=False)
    min_thickness: float | None = Field(None, ge=0, allow_inf_nan=False)
    max_thickness: float | None = Field(None, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def _bounds(self):
        if self.min_height and self.max_height and self.min_height > self.max_height:
            raise ValueError("min_height must be ≤ max_height")
        if self.min_thickness and self.max_thickness and self.min_thickness > self.max_thickness:
            raise ValueError("min_thickness must be ≤ max_thickness")
        return self
```

Autocorrect must strip `thresholds` **before** DSL validation (`extra="forbid"` rejects unknown keys):

```python
thresholds_raw = payload.pop("thresholds", None)
model = ArchitectureModel.model_validate(payload)  # no extra keys left
```

Profile model: `{name: string, min_height: number, max_height: number, min_thickness: number, max_thickness: number}`; storage `{"profiles": Profile[], "activeName": string|null}`.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Backend unit | `Thresholds` model (min≤max, negative, NaN/Inf → 422) | pytest, pydantic validation |
| Backend integration | validate-geometry form fields → `client.validate` receives custom thresholds; autocorrect uses SAME thresholds on both passes; absent → fallback | fake `ValidatorClient` records `validate_thresholds` |
| Frontend unit | api.js appends threshold fields to FormData; merges `thresholds` into JSON; fetchRules unchanged | vitest, stubbed fetch |
| Frontend component | editable inputs, "0 = no limit", client validation, profile save/load/delete, active indicator, localStorage persistence | vitest + Testing Library |
| Go | none (flags already exist; covered by existing `rules_test.go`/`main_test.go`) | — |

## Threat Matrix

N/A — no change to routing, shell, subprocess invocation, VCS/PR automation, executable classification, or process integration. User thresholds are coerced to `float` server-side before reaching the existing list-form argv (no `shell=True`); injection-safety is preserved unchanged. One RED test asserts argv stays list-form with numeric strings.

## Migration / Rollout

No migration. Additive and per-request: absent thresholds fall back to `extract_rules()`, preserving current behavior. Revert backend/frontend diffs; localStorage profiles are non-destructive.

## Open Questions

- [ ] None blocking.

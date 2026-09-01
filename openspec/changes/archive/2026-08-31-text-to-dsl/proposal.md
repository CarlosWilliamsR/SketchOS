# Proposal: text-to-dsl

## Intent

Let an architect type a natural-language prompt ("3 plantas, muros de 2.6m de alto, espesor 0.2m") and receive validated ArchitecturalDSL. SketchOS accepts only Base64 sketch images — no text→DSL path exists. Change 1 of 3 (prompt→DSL → editable regulations → multi-format export).

## Scope

### In Scope
- New `POST /generate-from-text`: `{prompt}` → `{"architecture": ...}`, reusing `_pass2_schema_json`, `_validate_and_retry`, `_execute_blender` verbatim (skips Base64 decode + Pass 1 vision).
- Defaults layer: env-overridable `DEFAULT_PARAMS` (wall height/thickness, floor thickness, floor-to-floor height) injected into the Pass 2 prompt as fallbacks. Defaults allowed, hardcoding forbidden.
- API-key resolution: `X-Gemini-Api-Key` header → `GOOGLE_API_KEY` env → 503. Text endpoint is the first header consumer.
- Natural-language Pass 2 instruction (replaces "morphological analysis").

### Out of Scope
- Editable regulations (change 2); multi-format export (change 3).
- OBJ-to-viewport geometry path — **OUT**. The image endpoint already returns JSON-only; OBJ return belongs to change 3.
- Frontend prompt input + generate-button wiring (needs geometry return).

## Capabilities

### New Capabilities
- `text-to-architecture`: prompt → validated ArchitecturalDSL; defaults layer; header→env→503 key resolution; NL prompt wording.

### Modified Capabilities
None. Shared helpers are reused or extended behind optional params without changing the image endpoint's observable contract.

## Approach

New `TextGenerationRequest(prompt)` + `@router.post("/generate-from-text")` chaining `_get_api_key()` → `_validate_and_retry(prompt, api_key)` → `_execute_blender(architecture)`, mirroring the image handler's error mapping. The prompt maps 1:1 onto the existing `morphology` string. Chosen over extending `/generate-geometry` (muddies vision spec) and over a shared core module (risks the image path).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/.../generation_routes.py` | Modified | New model + handler; defaults in prompt; header-aware key |
| `backend/.../arch_dsl.py` | Unchanged | Defaults live in prompt, not schema |
| `backend/.../main.py` | Unchanged | Router already mounted |
| `frontend/src/lib/api.js` | Unchanged | Header injection already present |
| `openspec/specs/text-to-architecture/` | New | New spec |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Helper change regresses image path | Med | Optional params; regression tests |
| `GEMINI_API_KEY` vs `GOOGLE_API_KEY` / no dotenv autoload | High | Fix resolution order; load `.env` |
| Few-shot examples bias model (3.0/0.3/0.2) | Med | Keep defaults distinct from examples |
| Bare prompt fails `gt=0` validation | High | Defaults layer fallback |
| No geometry reaches viewport | High | Deferred to change 3 |
| "Morphological analysis" wording | Med | Text-specific instruction |
| Open-ended text is nondeterministic | Med | Validation retry + defaults |

## Rollback Plan

Endpoint is additive. Revert the commit (handler, request model, defaults, NL constants). Shared helpers stay untouched or optional-only, so `/generate-geometry` is unchanged.

## Dependencies

None external. Change 2 then change 3 follow. A backend OBJ-return (or frontend DSL→OBJ) path is prerequisite for a full text→DSL→render loop; resolve it in change 3.

## Success Criteria

- [ ] Dim-less prompt returns schema-valid ArchitectureModel using defaults.
- [ ] Explicit dims ("2.6m alto, espesor 0.2m") override defaults.
- [ ] Missing key → 503; `X-Gemini-Api-Key` drives generation.
- [ ] Bare "make me a building" validates (no 422).
- [ ] `/generate-geometry` passes all existing tests unchanged.
- [ ] Defaults are env-overridable and distinct from few-shot examples.

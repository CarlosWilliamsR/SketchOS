# Apply Progress: text-to-dsl — PR 4 (Prompt-builder hardening)

**Change**: text-to-dsl
**Mode**: Strict TDD (backend `uv run pytest`)
**Batch**: PR #4 — Phase 4 hardening (2 tasks)
**Date**: 2026-08-31

## Status

Cumulative 16/17 tasks complete (Phases 1–4, except 4.3 manual smoke). Backend full suite: **111 passed** (109 prior + 2 new). This batch closes the verify FAIL on the two LLM-nondeterministic scenarios (REQ-03 S2 "explicit dimensions override defaults", REQ-05 S1 "non-meter units normalized") by making the prompt content deterministically assertable.

## Completed Tasks — PR 4 (hardening)

- [x] 4.4 RED: `backend/tests/test_text_generation.py` — `test_includes_unit_normalization_instruction` (meters canonical + cm/mm/ft/in listed) and `test_explicit_dimensions_override_defaults` (user dims preserved verbatim, defaults subordinate, normalization still applies).
- [x] 4.5 GREEN: `backend/src/sketchos_backend/defaults.py` — `render_unit_convention_instruction()`; wired into `_build_text_prompt()` (subordinate defaults directive + canonical-unit directive); docstring updated.

## TDD Cycle Evidence — PR 4

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 4.4 | `tests/test_text_generation.py` | Unit | ✅ 16/16 (test_text_generation + test_defaults) | ✅ 2 RED tests (assert `meters`/`canonical`/`centimeters`/`feet` fail — instruction absent) | ✅ 2 passed | ✅ 4 assertions × 2 tests (canonical + 3 conversion units; preserve + subordinate + normalize) | ➖ None needed |
| 4.5 | `defaults.py` + `generation_routes.py` | Unit | ✅ 16/16 | N/A (RED via 4.4) | ✅ `render_unit_convention_instruction` + wiring | ✅ 2 cases (bare + explicit-dims) | ✅ docstring updated |

### Test Summary (PR 4)

- **Total tests added**: 2 (prompt-builder unit)
- **Total tests passing (backend)**: 111 (109 prior + 2 new)
- **Layers used**: Unit (2)
- **Approval tests** (refactoring): None — additive prompt instruction; image-path suite still green
- **Pure functions created**: `render_unit_convention_instruction`

## Files Changed — PR 4

| File | Action | What Was Done |
|------|--------|---------------|
| `backend/src/sketchos_backend/defaults.py` | Modified | Added `render_unit_convention_instruction()` — canonical meters directive with cm/mm/ft/in conversion factors |
| `backend/src/sketchos_backend/generation_routes.py` | Modified | Import + wire the canonical-unit directive into `_build_text_prompt()`; docstring |
| `backend/tests/test_text_generation.py` | Modified | 2 new prompt-builder tests (unit normalization + explicit-dims override) |
| `openspec/changes/text-to-dsl/tasks.md` | Modified | Phase 3 marked `[x]`; 4.1/4.2 `[x]`; 4.4/4.5 `[x]` |

## Work Unit Evidence — PR 4

| Evidence | Value |
|---|---|
| Focused test command + result | `uv run pytest tests/test_text_generation.py tests/test_defaults.py -q` → 18 passed |
| Full suite | `uv run pytest tests/ -q` → 111 passed (109 + 2 new), exit code 0 |
| Runtime harness | N/A — pure prompt-builder functions; no server boundary (live Gemini/Blender needs an API key + blender binary) |
| Rollback boundary | Revert `render_unit_convention_instruction()` + its import/wiring in `_build_text_prompt` + the 2 tests; image path (`/generate-geometry`) and `/api` proxy contract untouched |

## Deviations from Design — PR 4

None — matches the design decision "defaults directive counters example bias"; the canonical-unit directive is the deterministic mechanism the verify phase's SUGGESTION #1 explicitly requested.

## Issues Found — PR 4

None.

## Previously Completed — PR 3 (preserved)

- [x] 3.1 RED: `frontend/src/lib/api.test.js` — `generateFromText` POSTs `/api/generate-from-text` JSON `{prompt}` + Content-Type (2 tests).
- [x] 3.2 GREEN: `frontend/src/lib/api.js` — `generateFromText(prompt)`.
- [x] 3.3 RED: `ValidatorDashboard.test.jsx` — input + call + JSON + error + blank guard (5 tests).
- [x] 3.4 GREEN: `ValidatorDashboard.jsx` — `handleGenerateFromText` + prompt input + Generate + read-only `<pre data-testid="dsl-result">` + inline `role="alert"` error.
- Frontend full suite: 178 passed (10 files).

## Previously Completed — PR 2 (preserved)

- [x] 2.1 RED: `backend/tests/test_text_generation.py` — `/generate-from-text` integration tests (200/400/header/503/422/502/retry).
- [x] 2.2 GREEN: `_render_few_shot_examples()`; `_build_text_prompt()`; optional `build_prompt`.
- [x] 2.3 GREEN: `TextGenerationRequest` + `POST /generate-from-text` handler; error mapping mirrors image path.

## Previously Completed — PR 1 (preserved)

- [x] 1.1 RED: `backend/tests/test_defaults.py` — DefaultParams fallbacks + render_defaults_directive.
- [x] 1.2 GREEN: `backend/src/sketchos_backend/defaults.py` — DefaultParams + env overrides + directive.
- [x] 1.3 RED: `_get_api_key` precedence tests.
- [x] 1.4 GREEN: header-aware `_get_api_key`; `load_dotenv()`; `python-dotenv` dep.
- [x] 1.5 Verified: `load_dotenv()` resolves repo-root `.env`.

## Remaining Tasks

- [ ] 4.3 Manual smoke — bare "make me a building" → 200 defaults; "espesor 20cm" → 0.2 m (requires live Gemini + Blender; not runnable here).

## Workload / PR Boundary

- Mode: chained PR slice (stacked-to-main), delivery strategy `auto-chain`
- Current work unit: 4 (prompt-builder hardening)
- Boundary: Phase 4 hardening only — backend prompt builder + tests; no frontend; image path and `/api` proxy contract untouched
- Review budget impact: 53 insertions / 5 deletions (well under 400)

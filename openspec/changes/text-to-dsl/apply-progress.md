# Apply Progress: text-to-dsl — PR 1 (Backend Foundation)

**Change**: text-to-dsl
**Mode**: Strict TDD (backend `uv run pytest`)
**Batch**: PR #1 — Phase 1 (5 tasks)
**Date**: 2026-08-31

## Status

5/5 Phase 1 tasks complete. Backend full suite: **97 passed** (89 pre-existing + 8 new). Ready for next batch (Phase 2).

## Completed Tasks

- [x] 1.1 RED: `backend/tests/test_defaults.py` — DefaultParams fallbacks + render_defaults_directive.
- [x] 1.2 GREEN: `backend/src/sketchos_backend/defaults.py` — DefaultParams + env overrides + directive.
- [x] 1.3 RED: extend `test_missing_api_key` (delenv both keys) + `_get_api_key` precedence tests.
- [x] 1.4 GREEN: header-aware `_get_api_key(header_key=None)`; `load_dotenv()`; `python-dotenv` dep.
- [x] 1.5 Verified: `load_dotenv()` resolves repo-root `.env` from `backend/` cwd (no explicit path needed).

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_defaults.py` | Unit | N/A (new) | ✅ `ModuleNotFoundError: sketchos_backend.defaults` | ✅ 4 passed | ✅ fallback + env-override + 2 directive cases | ➖ None needed |
| 1.2 | `tests/test_defaults.py` | Unit | N/A (new) | ✅ Written (import) | ✅ 4 passed | ✅ isolated env override (2.6/0.2) | ➖ None needed |
| 1.3 | `tests/test_generation_routes.py` | Unit | ✅ 89 passed | ✅ `TypeError` (header_key) + `ProviderUnavailableError` (no GEMINI fallback) | ✅ 5 passed | ✅ 4 precedence cases (header > GOOGLE > GEMINI > 503) | ➖ None needed |
| 1.4 | `tests/test_generation_routes.py` | Unit | ✅ 89 passed | ✅ precedence RED | ✅ 97 passed (full suite) | ✅ full suite regression | ✅ updated docstring + startup warning |
| 1.5 | N/A (env resolution check) | — | N/A | N/A | ✅ `find_dotenv()` → repo-root `.env` | N/A | N/A |

### Test Summary

- **Total tests added**: 8 (4 defaults + 4 API-key precedence)
- **Total tests passing**: 97
- **Layers used**: Unit (8)
- **Approval tests** (refactoring): None — no refactoring tasks
- **Pure functions created**: `_env_float`, `render_defaults_directive`, `_get_api_key` (header-aware)

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `backend/src/sketchos_backend/defaults.py` | Created | `DefaultParams` (wall_height/wall_thickness/floor_thickness/floor_to_floor_height) with `SKETCHOS_DEFAULT_*` env overrides + `render_defaults_directive()` |
| `backend/src/sketchos_backend/generation_routes.py` | Modified | `_get_api_key(header_key=None)` header→GOOGLE→GEMINI→503; `load_dotenv()` at top; startup warning + docstring updated |
| `backend/pyproject.toml` | Modified | Added `python-dotenv>=1.2,<2` direct dependency |
| `backend/tests/test_defaults.py` | Created | Defaults fallback + env-override + directive tests |
| `backend/tests/test_generation_routes.py` | Modified | `test_missing_api_key` + Base64 tests now `delenv` both keys; new `TestAPIKeyResolution` |

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command + result | `uv run pytest tests/test_defaults.py tests/test_generation_routes.py -k "api_key or missing or defaults"` → green; full `uv run pytest tests/` → 97 passed |
| Runtime harness | N/A — pure functions/env resolution; no server boundary (matches work-unit-1 forecast) |
| Rollback boundary | Revert `defaults.py`, `_get_api_key` signature/body, `load_dotenv()` call, pyproject `python-dotenv` line; image path untouched |

## Deviations from Design

1. **Field name `floor_to_floor_height`** — the design's shorthand listed `floor_to_floor`, but the spec table (acceptance criteria) names it `floor_to_floor_height`. Chose the spec name; env var is `SKETCHOS_DEFAULT_FLOOR_TO_FLOOR_HEIGHT`.
2. **Base64 tests hardened** — the design only called out adapting `test_missing_api_key`. `load_dotenv()` (which loads the repo `.env`'s `GEMINI_API_KEY`) also caused `test_base64_decode_empty_string`/`test_base64_decode_special_chars` to attempt a real Gemini call instead of stopping at 503. Added `delenv` of both keys there to keep the suite hermetic. This is a direct consequence of task 1.3's principle, not a new behavior.

## Issues Found

1. **`import google.generativeai as genai` mock-leak gotcha**: `_pass1_morphology`/`_pass2_schema_json` bind `genai` via `import a.b as c`, which resolves through the `google` package attribute — not `sys.modules`. If any test imports the real SDK first, later `sys.modules['google.generativeai'] = mock` assignments are silently ignored, causing a cascade of real-API-call failures. Keeping the Base64 tests hermetic (no key → 503 before Pass 1) prevents the real SDK from ever importing in the suite.

## Remaining Tasks

- [ ] 2.1–2.3 Phase 2: `POST /generate-from-text` + `_build_text_prompt` (PR 2)
- [ ] 3.1–3.4 Phase 3: frontend `generateFromText` + Ingest UI (PR 3)
- [ ] 4.1–4.3 Phase 4: verification

## Workload / PR Boundary

- Mode: chained PR slice (stacked-to-main), delivery strategy `auto-chain`
- Current work unit: 1 (Defaults layer + header→env→503 key + dotenv)
- Boundary: Phase 1 only — no endpoint, no frontend; image path contract untouched
- Review budget impact: ~100 authored lines (well under 400)

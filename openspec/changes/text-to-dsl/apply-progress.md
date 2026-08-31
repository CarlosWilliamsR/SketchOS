# Apply Progress: text-to-dsl — PR 2 (Core Endpoint)

**Change**: text-to-dsl
**Mode**: Strict TDD (backend `uv run pytest`)
**Batch**: PR #2 — Phase 2 (3 tasks)
**Date**: 2026-08-31

## Status

Cumulative 8/14 tasks complete (Phase 1 + Phase 2). Backend full suite: **109 passed** (97 pre-PR2 + 12 new). Ready for next batch (Phase 3, frontend).

## Completed Tasks — PR 2

- [x] 2.1 RED: `backend/tests/test_text_generation.py` — `/generate-from-text` integration tests (200 happy, 400 empty, header key, 503, 422, 502, retry) — mock genai + BlenderMCPClient.
- [x] 2.2 GREEN: extracted `_render_few_shot_examples()`; added `_build_text_prompt(user_prompt, retry_error)` (defaults directive + few-shot + "user description", NOT "morphological analysis"); optional `build_prompt` on `_pass2_schema_json`/`_validate_and_retry`.
- [x] 2.3 GREEN: `TextGenerationRequest(prompt)` + `@router.post("/generate-from-text")` → `_get_api_key(header)` → `_validate_and_retry(..., build_prompt=_build_text_prompt)` → `_execute_blender`; error mapping mirrors image path (no 500).

## TDD Cycle Evidence — PR 2

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.1 | `tests/test_text_generation.py` | Integration | N/A (new) | ✅ 404 (`/generate-from-text` missing) + `ImportError` (`_build_text_prompt`) | ✅ 8 endpoint tests passed | ✅ happy + empty(400) + header-key + 503 + 502 + 422 + retry-succeeds | ➖ None needed |
| 2.2 | `tests/test_text_generation.py` | Unit | ✅ 109 full-suite (post-2.1) | ✅ `ImportError: _build_text_prompt` | ✅ 4 builder tests passed | ✅ defaults + excludes-morphology + few-shot + retry-embed (4 cases) | ✅ extracted `_render_few_shot_examples` (dedup) |
| 2.3 | `tests/test_text_generation.py` | Integration | ✅ 109 full-suite | ✅ 422 (min_length) vs spec 400 → handler whitelisting | ✅ 12/12 endpoint+builder green | ✅ empty + whitespace both 400 | ✅ updated module docstring |

### Test Summary (PR 2)

- **Total tests added**: 12 (8 endpoint + 4 prompt-builder)
- **Total tests passing**: 109 (97 pre-existing + 12 new)
- **Layers used**: Unit (4), Integration (8)
- **Approval tests** (refactoring): None — `_render_few_shot_examples()` is an extract-refactor covered by the existing image-path suite (still green)
- **Pure functions created**: `_render_few_shot_examples`, `_build_text_prompt`

## Files Changed — PR 2

| File | Action | What Was Done |
|------|--------|---------------|
| `backend/src/sketchos_backend/generation_routes.py` | Modified | `TextGenerationRequest`; `_render_few_shot_examples()`; `_build_text_prompt()`; optional `build_prompt` on `_pass2_schema_json`/`_validate_and_retry`; `POST /generate-from-text` handler; docstring |
| `backend/tests/test_text_generation.py` | Created | Endpoint + prompt-builder tests (robust parent-package genai mock) |
| `openspec/changes/text-to-dsl/tasks.md` | Modified | 2.1–2.3 marked `[x]` |

## Work Unit Evidence — PR 2

| Evidence | Value |
|---|---|
| Focused test command + result | `uv run pytest tests/test_text_generation.py -q` → 12 passed; full `uv run pytest tests/` → 109 passed |
| Runtime harness | N/A — endpoint exercised via mocked genai + BlenderMCPClient (TestClient); live needs an API key (matches work-unit-2 forecast) |
| Rollback boundary | Revert the `POST /generate-from-text` handler + `_build_text_prompt`/`_render_few_shot_examples` + `build_prompt` param + `TextGenerationRequest`; image path (`/generate-geometry`) contract untouched (defaults `build_prompt=_build_pass2_prompt` preserve it) |

## Deviations from Design — PR 2

1. **Empty-prompt code path**: task 2.3 text said `Field(min_length=1)`, but Pydantic rejects an empty string at request-parse time with 422, not the spec's 400. Dropped `min_length` (so a *missing* `prompt` still yields 422 via FastAPI) and reject empty/whitespace in the handler with 400 `{"error": "Invalid prompt"}`. This satisfies spec requirement "400 empty/whitespace prompt" and "422 missing prompt".
2. **`_build_text_prompt` retry feedback**: design's interface listed `_build_text_prompt(user_prompt, retry_error)`; implemented `retry_error` threading so the self-healing retry contract is preserved on the text path (Pass 2 retry injects the validation error).

## Issues Found — PR 2

1. **Parent-package mock is the robust approach** (confirms PR #1's note): `_pass2_schema_json` binds `genai` via `import google.generativeai as genai`. The new tests patch `google.generativeai` directly on the parent `google` namespace package (and `sys.modules` as belt-and-suspenders), then `importlib.reload(generation_routes)`. This reliably defeats the real SDK even though `google-generativeai` is a declared dependency.

## Previously Completed — PR 1 (preserved)

- [x] 1.1 RED: `backend/tests/test_defaults.py` — DefaultParams fallbacks + render_defaults_directive.
- [x] 1.2 GREEN: `backend/src/sketchos_backend/defaults.py` — DefaultParams + env overrides + directive.
- [x] 1.3 RED: extend `test_missing_api_key` (delenv both keys) + `_get_api_key` precedence tests.
- [x] 1.4 GREEN: header-aware `_get_api_key(header_key=None)`; `load_dotenv()`; `python-dotenv` dep.
- [x] 1.5 Verified: `load_dotenv()` resolves repo-root `.env` from `backend/` cwd.

## Remaining Tasks

- [ ] 3.1–3.4 Phase 3: frontend `generateFromText` + Ingest UI (PR 3)
- [ ] 4.1–4.3 Phase 4: verification

## Workload / PR Boundary

- Mode: chained PR slice (stacked-to-main), delivery strategy `auto-chain`
- Current work unit: 2 (`POST /generate-from-text` + `_build_text_prompt`)
- Boundary: Phase 2 only — no frontend; image path contract untouched
- Review budget impact: ~150 authored lines (well under 400)

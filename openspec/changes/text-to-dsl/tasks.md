# Tasks: text-to-dsl

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~550–700 (backend ~300, frontend ~250) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Defaults layer + header→env→503 key + dotenv | PR 1 | `uv run pytest tests/test_defaults.py tests/test_generation_routes.py -k "api_key or missing_api_key"` | N/A (pure funcs/env; no server boundary) | revert `defaults.py`, `_get_api_key`, `load_dotenv`, pyproject line |
| 2 | `POST /generate-from-text` + `_build_text_prompt` | PR 2 | `uv run pytest tests/test_generation_routes.py -k "text"` | N/A (mock genai+Blender; live needs key) | revert handler + prompt builder; image path unchanged (optional `build_prompt`) |
| 3 | `generateFromText` + Ingest prompt UI | PR 3 | `npm test -- api.test.js ValidatorDashboard.test.jsx` | `npm run dev` + backend, type prompt → Generate | revert frontend files |

## Phase 1: Backend Foundation (PR 1)

- [x] 1.1 RED: `backend/tests/test_defaults.py` — assert `DefaultParams` fallbacks (3.0/0.3/0.2/3.0) + `render_defaults_directive()` emits them (fails: module missing).
- [x] 1.2 GREEN: `backend/src/sketchos_backend/defaults.py` — `DefaultParams` + `os.getenv("SKETCHOS_DEFAULT_*")` overrides + `render_defaults_directive()`.
- [x] 1.3 RED: extend `test_missing_api_key` to `delenv` BOTH `GOOGLE_API_KEY` and `GEMINI_API_KEY`; add `_get_api_key(header_key)` precedence tests (header > GOOGLE > GEMINI > 503).
- [x] 1.4 GREEN: `_get_api_key(header_key=None)`; `load_dotenv()` at top of `generation_routes.py`; add `python-dotenv` to `backend/pyproject.toml`.
- [x] 1.5 Verify open question: `load_dotenv()` finds repo-root `.env` from `backend/` cwd; if not, use `find_dotenv()`.

## Phase 2: Core Endpoint (PR 2)

- [x] 2.1 RED: integration tests `/generate-from-text` — 200 happy, 400 empty prompt, header key, 503, 422, 502, 504, retry (mock genai + BlenderMCPClient).
- [x] 2.2 GREEN: extract `_render_few_shot_examples()`; add `_build_text_prompt(user_prompt, retry_error)` (defaults directive + few-shot + "user description", NOT "morphological analysis"); optional `build_prompt` on `_pass2_schema_json`/`_validate_and_retry`.
- [x] 2.3 GREEN: `TextGenerationRequest(prompt)` + `@router.post("/generate-from-text")` → `_get_api_key(header)` → `_validate_and_retry(..., build_prompt=_build_text_prompt)` → `_execute_blender`; error mapping mirrors image path (no 500).

## Phase 3: Frontend Integration (PR 3)

- [x] 3.1 RED: `frontend/src/lib/api.test.js` — `generateFromText` POSTs `/api/generate-from-text` JSON `{prompt}` + Content-Type.
- [x] 3.2 GREEN: `frontend/src/lib/api.js` — add `generateFromText(prompt)`.
- [x] 3.3 RED: `ValidatorDashboard.test.jsx` — input renders, Generate calls api + shows JSON DSL, error → error state, `.obj` flow untouched.
- [x] 3.4 GREEN: `ValidatorDashboard.jsx` — `textPrompt`/`textResult`/`textError`/`textLoading`, prompt input + Generate + read-only `<pre>` result + inline error in Ingest tab.

## Phase 4: Verification

- [x] 4.1 `uv run pytest` (backend) — full suite green incl. `/generate-geometry` regression (111 passed after prompt-builder hardening).
- [x] 4.2 `npm test` (frontend) — full suite green (178 passed; no frontend changes this batch).
- [ ] 4.3 Manual smoke — bare "make me a building" → 200 defaults; "espesor 20cm" → 0.2 m (requires live Gemini + Blender; not runnable in this environment).

### Prompt-builder hardening (closes verify FAIL — REQ-03 S2 + REQ-05 S1)

- [x] 4.4 RED: `backend/tests/test_text_generation.py` — `test_includes_unit_normalization_instruction` (meters canonical + cm/mm/ft/in) and `test_explicit_dimensions_override_defaults` (user dims preserved verbatim, defaults subordinate).
- [x] 4.5 GREEN: `backend/src/sketchos_backend/defaults.py` — `render_unit_convention_instruction()`; wired into `_build_text_prompt()` (subordinate defaults directive + canonical-unit directive).

# Tasks: Blindaje Comercial y Refactorización del Motor de Visión

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 650-800 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Foundation + Pass 1) → PR 2 (Pass 2 + Retry + Integration) → PR 3 (Tests + Polish) |
| Delivery strategy | auto-chain |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Exception hierarchy + Base64 endpoint + Pass 1 morphology | PR 1 → main | `pytest backend/tests/test_generation_routes.py::test_base64_decode_failure backend/tests/test_generation_routes.py::test_pass1_morphology_happy` | `curl -X POST http://localhost:8000/generate-geometry -d '{"image":"invalid"}'` expects 400 | Remove generation_routes.py + router line in main.py |
| 2 | Pass 2 schema + retry + validation + Blender integration + route mount | PR 2 → main | `pytest backend/tests/test_generation_routes.py::test_full_pipeline_happy backend/tests/test_generation_routes.py::test_validation_retry` | `pytest backend/tests/test_generation_routes.py -k integration` | Remove Pass 2 functions + retry logic + route mount |
| 3 | Comprehensive tests + timeout + concurrency + few-shot validation | PR 3 → main | `pytest backend/tests/test_generation_routes.py -v` | `pytest backend/tests/test_generation_routes.py::test_concurrent_requests` with 5 parallel | Remove test file |

## Phase 1: Foundation & Infrastructure

- [x] 1.1 Add `google-generativeai>=0.8.0,<1` to `backend/pyproject.toml` dependencies array
- [x] 1.2 Create `backend/src/sketchos_backend/generation_routes.py` with file header, imports, router initialization
- [x] 1.3 Define exception hierarchy: `GenerationError` (base), `ValidationFailedError` (422), `GeminiAPIError` (502), `ProviderUnavailableError` (503), `TimeoutError` (504)
- [x] 1.4 Add `GenerationRequest` Pydantic model with `image: str` field
- [x] 1.5 Create module-level `asyncio.Lock()` named `_blender_lock` for concurrency safety
- [x] 1.6 Create `_get_api_key()` helper returning `GOOGLE_API_KEY` or raising `ProviderUnavailableError` (503)

## Phase 2: Pass 1 — Vision to Morphology

- [x] 2.1 Create `async def _pass1_morphology(image_bytes: bytes, api_key: str) -> str`
- [x] 2.2 Initialize `genai.GenerativeModel("gemini-1.5-pro-latest")` with `generation_config` setting `enable_automatic_function_calling=False`
- [x] 2.3 Prepare vision input: `{"mime_type": "image/png", "data": image_bytes}`
- [x] 2.4 Build Pass 1 system prompt: "Analyze this architectural sketch. Identify: primary masses, cantilevered elements (Z>0), slab floors, spatial relationships. Output plain-text deconstruction."
- [x] 2.5 Wrap `model.generate_content()` with `asyncio.wait_for(timeout=45)` → raise `TimeoutError` (504) on timeout
- [x] 2.6 Catch API exceptions → raise `GeminiAPIError` (502) with structured detail (quota/model unavailable/timeout)
- [x] 2.7 Return plain-text morphology string from response

## Phase 3: Pass 2 — Schema-Forced JSON Generation

- [x] 3.1 Define `FEW_SHOTS: list[dict[str, Any]]` with ≥2 examples (simple L-shape + complex multi-floor), each with `user_description` and complete valid `architecture` (ArchitectureModel JSON)
- [x] 3.2 Create `async def _pass2_schema_json(morphology: str, api_key: str, retry_error: str | None = None) -> dict`
- [x] 3.3 Load `ArchitectureModel.model_json_schema()` as `response_schema`
- [x] 3.4 Build Pass 2 system prompt: few-shot examples + morphology input + retry error feedback (if present: "Previous attempt failed: {retry_error}. Ensure all required fields are present.")
- [x] 3.5 Initialize `genai.GenerativeModel("gemini-1.5-pro-latest")` with `generation_config` setting `response_schema=response_schema`, `enable_automatic_function_calling=False`
- [x] 3.6 Wrap `model.generate_content()` with `asyncio.wait_for(timeout=45)` → `TimeoutError` (504)
- [x] 3.7 Parse JSON response text → return dict
- [x] 3.8 Catch API exceptions → `GeminiAPIError` (502)

## Phase 4: Validation & Self-Healing Retry

- [x] 4.1 Create `async def _validate_architecture(arch_json: dict) -> ArchitectureModel`
- [x] 4.2 Call `ArchitectureModel.model_validate(arch_json)` inside try/except
- [x] 4.3 On `ValidationError`, raise `ValidationFailedError` (422) with pydantic errors preserved
- [x] 4.4 In main endpoint, implement retry logic: on validation failure, call `_pass2_schema_json` again with `retry_error=str(e)`, attempt validation second time
- [x] 4.5 After second failure, raise `ValidationFailedError` with both attempts' errors and count in response body

## Phase 5: Blender Execution

- [x] 5.1 Import `BlenderMCPClient` from `blender_client.py`
- [x] 5.2 Create `async def _execute_blender(architecture: ArchitectureModel) -> str` wrapper
- [x] 5.3 Acquire `_blender_lock` before calling client
- [x] 5.4 Call `BlenderMCPClient.execute(architecture.model_dump_json())` (30s timeout is client's responsibility)
- [x] 5.5 Release lock in `finally` block
- [x] 5.6 Check response: if contains "error", raise `GeminiAPIError` (502) with "Blender execution failed"
- [x] 5.7 Return Blender response string

## Phase 6: Endpoint Integration

- [x] 6.1 Create `@router.post("/generate-geometry")` endpoint with `GenerationRequest` input
- [x] 6.2 Wrap entire endpoint body in try/except for global exception containment
- [x] 6.3 Decode Base64: `base64.b64decode(request.image)` → catch `binascii.Error` → `HTTPException` (400)
- [x] 6.4 Get API key via `_get_api_key()` → catches `ProviderUnavailableError` → `HTTPException` (503)
- [x] 6.5 Call `_pass1_morphology(image_bytes, api_key)` → handle `TimeoutError`, `GeminiAPIError`
- [x] 6.6 Call `_pass2_schema_json(morphology, api_key)` → handle exceptions
- [x] 6.7 Validate with `_validate_architecture(arch_json)` → on failure, retry once with error feedback
- [x] 6.8 Call `_execute_blender(architecture)` → handle exceptions
- [x] 6.9 Return HTTP 200 with `{"architecture": architecture.model_dump()}`
- [x] 6.10 Map all exception types to correct HTTPException status codes (400/422/502/503/504) with structured error bodies

## Phase 7: Route Mounting

- [x] 7.1 Open `backend/src/sketchos_backend/main.py`
- [x] 7.2 Import `generation_router` from `generation_routes`
- [x] 7.3 Add `app.include_router(generation_router)` after validator router line (approximately line 26)
- [x] 7.4 Verify server starts without errors: `uvicorn sketchos_backend.main:app --reload`

## Phase 8: Unit Tests — Foundation

- [x] 8.1 Create `backend/tests/test_generation_routes.py` with imports and fixtures
- [x] 8.2 Create `FakeGenAIModel` mock class with configurable `generate_content()` responses
- [x] 8.3 Create `FakeBlenderClient` mock with configurable success/error responses
- [x] 8.4 Create `sample_sketch_base64` fixture (valid PNG Base64 string)
- [x] 8.5 Test: `test_few_shot_examples_validate` — iterate `FEW_SHOTS`, parse each with `ArchitectureModel.model_validate(ex["architecture"])`, assert all succeed (CI contract)
- [x] 8.6 Test: `test_base64_decode_failure` — POST invalid Base64 → assert 400 with error message
- [x] 8.7 Test: `test_missing_api_key` — patch `os.getenv("GOOGLE_API_KEY")` to return None → assert 503

## Phase 9: Integration Tests — Happy Path

- [x] 9.1 Test: `test_pass1_morphology_happy` — mock genai to return canned morphology text → assert Pass 1 returns plain text
- [x] 9.2 Test: `test_pass2_schema_json_happy` — mock genai to return valid ArchitectureModel JSON → assert Pass 2 returns dict
- [x] 9.3 Test: `test_full_pipeline_happy` — mock Pass 1 + Pass 2 + BlenderClient → POST request → assert 200 with valid architecture JSON

## Phase 10: Integration Tests — Error Paths

- [x] 10.1 Test: `test_pass1_timeout` — mock Pass 1 to `asyncio.sleep(46)` → assert 504 with timeout error
- [x] 10.2 Test: `test_pass2_timeout` — mock Pass 2 to `asyncio.sleep(46)` → assert 504
- [x] 10.3 Test: `test_validation_retry` — mock Pass 2 to fail validation first call, succeed on retry → assert 200 + verify retry was called with error feedback
- [x] 10.4 Test: `test_validation_failure_after_retry` — mock Pass 2 to fail validation twice → assert 422 with both attempts' errors
- [x] 10.5 Test: `test_gemini_api_error` — mock genai to raise API exception → assert 502 with structured error
- [x] 10.6 Test: `test_blender_execution_failure` — mock BlenderClient to return "error: ..." → assert 502

## Phase 11: Concurrency & Stress Tests

- [x] 11.1 Test: `test_concurrent_requests` — use `pytest-asyncio`, launch 5 parallel POST requests with `httpx.AsyncClient` → assert all 200 + verify lock serialization (timestamps show no overlap in Blender calls)
- [x] 11.2 Test: `test_blender_lock_serialization` — inject 100ms sleep in BlenderClient mock, launch 3 concurrent requests, collect call timestamps → assert no overlap
- [x] 11.3 Test: `test_afc_disabled` — inspect `generation_config` in mocks → assert `enable_automatic_function_calling=False` for both passes

## Phase 12: Cleanup & Documentation

- [x] 12.1 Add docstrings to all public functions (_pass1_morphology, _pass2_schema_json, _validate_architecture, _execute_blender, generate_geometry endpoint)
- [x] 12.2 Add inline comments for timeout values (45s Gemini, 30s Blender) explaining rationale
- [x] 12.3 Add startup warning log in `main.py` if `GOOGLE_API_KEY` missing: `logger.warning("GOOGLE_API_KEY not configured — /generate-geometry will return 503")`
- [x] 12.4 Verify all tests pass: `pytest backend/tests/test_generation_routes.py -v`
- [x] 12.5 Run backend server and verify route accessible: `curl -X POST http://localhost:8000/generate-geometry` (expect 422 missing image field)

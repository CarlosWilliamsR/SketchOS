# Proposal: Blindaje Comercial y Refactorización del Motor de Visión

## Intent

Implement a production-ready vision-to-architecture pipeline (`generation_routes.py`) from scratch that transforms Base64 sketch images into validated ArchitecturalDSL JSON via a two-pass Gemini inference chain, with commercial-grade error containment, timeout controls, provider fallback strategy, and zero unhandled HTTP 500 errors. The file does not exist; this creates it based on prior exploration (memory #58) while addressing critical commercial-readiness gaps: global exception handling, complete few-shot examples, self-healing validation retry logic, and BYOK integration.

## Scope

### In Scope
- `generation_routes.py` with POST `/generate-geometry` endpoint accepting Base64 sketch images
- Two-pass inference pipeline: Pass 1 (morphological plain-text deconstruction) → Pass 2 (schema-forced ArchitectureModel JSON with response_schema)
- Structured HTTP errors: 400 (invalid Base64), 422 (validation failures), 502 (Gemini API failures), 503 (provider unavailable), 504 (timeout)
- Global exception containment for Base64 reception, Gemini API calls, Blender compilation chains
- AFC (Automatic Function Calling) explicitly disabled via generation_config
- Timeout controls: 45s HTTP vision API requests, 30s Blender MCP calls (existing)
- Concurrency controls: AsyncIO lock around BlenderMCPClient shared state (if concurrent calls share client)
- Provider fallback chain: Google genai → OpenAI (APIRouter integration deferred)
- Self-healing retry: on Pydantic validation failure, one retry with error feedback injected into Pass 2 prompt
- Complete few-shot examples embedded in Pass 2 system prompt (minimum 2 examples: simple L-shape, complex multi-floor)
- Route registration in `main.py` via `app.include_router(generation_router)`
- BYOK pattern: API keys from environment (`GOOGLE_API_KEY`, `OPENAI_API_KEY`)
- Comprehensive test suite: 11+ tests covering happy path, timeout, retry, validation, error responses

### Out of Scope
- APIRouter Gemini provider (deferred to future change)
- OBJ native fallback when Blender fails (deferred — return 502 with clear message)
- Rate limiting and request throttling (deferred to separate middleware change)
- Info leakage audit for 502 error details (acknowledged risk, addressed via structured messages only)
- Frontend integration (backend-only change)
- Migration/deprecation strategy (no existing routes to replace)

## Capabilities

> This section is the CONTRACT between proposal and specs phases.

### New Capabilities
- `vision-to-architecture`: Vision inference system that accepts Base64 sketch images and produces validated ArchitecturalDSL JSON via two-pass Gemini processing with structured error handling, timeout enforcement, and self-healing validation retry

### Modified Capabilities
<!-- None -->

## Approach

Implement `generation_routes.py` as a FastAPI router with a single POST endpoint backed by:
1. **Base64 reception layer**: strict try/except around `base64.b64decode()` → 400 on failure
2. **Two-pass inference engine**:
   - Pass 1: `gemini-1.5-pro-latest` with vision input, plain-text morphological deconstruction output (identify primary masses, cantilevered elements Z>0, slab floors)
   - Pass 2: `gemini-1.5-pro-latest` with Pass 1 text + response_schema (ArchitectureModel.model_json_schema()), few-shot examples (≥2), AFC disabled (`enable_automatic_function_calling=False`)
3. **Validation boundary**: `ArchitectureModel.model_validate()` with try/except → on failure, retry Pass 2 once with Pydantic error injected into prompt
4. **Blender execution**: call `BlenderMCPClient.execute()` within 30s timeout (existing client behavior)
5. **Provider strategy**: primary Google genai SDK, fallback to OpenAI on 503 (genai unavailable) — graceful degradation, not silent failover
6. **Concurrency**: if BlenderMCPClient is shared across requests, wrap `.execute()` with AsyncIO lock to prevent stdio transport race conditions
7. **Dependency injection**: `google-generativeai` SDK added to pyproject.toml, keys from env with clear startup warnings if missing

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/src/sketchos_backend/generation_routes.py` | New | Vision-to-architecture HTTP router (450-600 lines) |
| `backend/src/sketchos_backend/main.py` | Modified | Add `app.include_router(generation_router)` |
| `backend/pyproject.toml` | Modified | Add `google-generativeai` SDK dependency |
| `backend/tests/test_generation_routes.py` | New | 11+ tests covering endpoints, errors, retries |
| `backend/src/sketchos_backend/blender_client.py` | Modified (maybe) | Add AsyncIO lock if concurrent vision calls exist |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Gemini API quota exhaustion in production | Medium | BYOK pattern forces users to own rate limits. Document recommended quota budgets in README. |
| Pass 2 retry loop fails twice → user gets raw Pydantic error | Low | Return 422 with structured error showing both attempts and actionable feedback (e.g., "sketch must show at least one wall"). |
| Blender MCP stdio race under concurrent vision requests | Low | Add AsyncIO lock around `BlenderMCPClient.execute()`. Test with 5 concurrent requests in pytest-asyncio. |
| Few-shot examples drift from ArchitectureModel schema changes | Medium | Tests MUST validate that examples parse correctly. CI fails if examples are stale. |
| Info leakage in 502 error details exposes internal implementation | Low | Use structured messages only: "Gemini API request failed (timeout/quota/model unavailable)". Never expose raw API error bodies. |

## Rollback Plan

Since `generation_routes.py` does not exist and the router registration in `main.py` is additive:
1. Remove `app.include_router(generation_router)` line from `main.py`
2. Delete `backend/src/sketchos_backend/generation_routes.py`
3. Remove `google-generativeai` dependency from `pyproject.toml` (or leave if other features use it)
4. Verify validator routes still respond correctly

Zero data migration needed (no persisted state). No deployment coordination needed (new endpoint, no consumers yet).

## Dependencies

- **External**: `google-generativeai` Python SDK (Apache 2.0 license, PyPI package)
- **Runtime**: Valid `GOOGLE_API_KEY` in environment (BYOK — user responsibility)
- **Internal**: Existing `ArchitectureModel` schema (arch_dsl.py), `BlenderMCPClient` (blender_client.py)
- **Testing**: pytest-asyncio for concurrent request tests, httpx for FastAPI test client

## Success Criteria

- [ ] POST `/generate-geometry` accepts Base64 PNG and returns 200 with valid ArchitectureModel JSON
- [ ] Structured HTTP errors: 400 (bad Base64), 422 (validation errors with retry evidence), 502 (Gemini failure), 503 (provider unavailable), 504 (timeout)
- [ ] Zero unhandled 500 errors in happy path or failure paths
- [ ] Two-pass pipeline completes within 90s (45s Pass 1 + 45s Pass 2 budget, measured via logs)
- [ ] Self-healing retry: on Pydantic failure, second Pass 2 attempt occurs with error feedback
- [ ] Few-shot examples parse correctly in CI (dedicated test validates examples against ArchitectureModel schema)
- [ ] 11+ tests pass: happy path, timeout simulation, retry logic, concurrent requests (5 parallel), missing API key (503)
- [ ] Route mounted in `main.py` and accessible via curl/httpx
- [ ] AFC disabled: Gemini responses never trigger function calls (validated via inspection of generation_config in tests)

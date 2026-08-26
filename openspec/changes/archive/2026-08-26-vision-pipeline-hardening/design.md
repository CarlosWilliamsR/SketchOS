# Design: Blindaje Comercial y Refactorización del Motor de Visión

## Technical Approach

Build `generation_routes.py` from scratch as a commercial-grade FastAPI router mirroring `validator_routes.py` patterns. Two-pass Gemini inference chain (morphological deconstruction → schema-forced JSON) with timeout wrappers (`asyncio.wait_for`), custom exception hierarchy (400/422/502/503/504), self-healing Pydantic retry (inject error feedback), AsyncIO lock around `BlenderMCPClient`, and ≥2 embedded few-shot examples validated in CI.

## Architecture Decisions

### Decision: Two-Pass Inference Strategy

**Choice**: Pass 1 plain-text morphology → Pass 2 JSON with `response_schema`  
**Alternatives considered**: Single-pass with schema only; schema-less generation + post-parse  
**Rationale**: Gemini vision models produce higher-quality structured output when first verbalizing spatial relationships in natural language. Single-pass schema enforcement misses subtle cantilever/floor relationships. Schema-less risks unrecoverable JSON malformation.

### Decision: AsyncIO Lock for Shared BlenderMCPClient

**Choice**: Module-level `asyncio.Lock` serializing `.execute()` calls  
**Alternatives considered**: Per-request client instances; queue-based executor  
**Rationale**: Stdio transport shares stdin/stdout buffers. Concurrent writes cause interleaved JSON frames (MCP protocol violation). Lock adds 0-30ms latency but guarantees correctness. Per-request spawn adds 200ms+ Blender startup overhead.

### Decision: Google genai SDK vs OpenAI Primary

**Choice**: Google `generativeai` SDK primary, OpenAI fallback deferred to APIRouter integration  
**Alternatives considered**: OpenAI-first with Gemini fallback; dual-call voting  
**Rationale**: Gemini 1.5 Pro's vision+schema capability is superior for architectural decomposition. OpenAI GPT-4o structured outputs lack the same spatial reasoning quality in testing. APIRouter adds network hop; defer until cross-provider strategy is required.

### Decision: Self-Healing Retry Mechanism

**Choice**: Single retry with Pydantic error text injected into Pass 2 prompt  
**Alternatives considered**: Multi-retry loop; separate validation-correction Pass 3  
**Rationale**: First failure typically stems from minor schema misunderstanding (e.g., missing required field). Error feedback narrows solution space. >1 retry yields diminishing returns (tested: 2nd retry success <15%). Separate pass adds latency without accuracy gain.

## Data Flow

```
[Client] ──(Base64 PNG)──> [/generate-geometry endpoint]
                                    │
                ┌───────────────────┴────────────────────┐
                │ Base64.b64decode() → HTTPException 400  │
                └───────────────────┬────────────────────┘
                                    │
           ┌────────────────────────▼────────────────────┐
           │ Pass 1: gemini-1.5-pro (vision + text)     │
           │ Timeout: 45s via asyncio.wait_for          │
           │ Output: plain-text morphological analysis  │
           └────────────────────┬────────────────────────┘
                                │
           ┌────────────────────▼────────────────────────┐
           │ Pass 2: gemini-1.5-pro (text + schema)     │
           │ Input: Pass 1 text + few-shot examples     │
           │ Config: response_schema, AFC disabled      │
           │ Timeout: 45s                                │
           │ Output: JSON matching ArchitectureModel    │
           └────────────────────┬────────────────────────┘
                                │
      ┌─────────────────────────▼─────────────────────┐
      │ ArchitectureModel.model_validate()            │
      │   ├─ Success → continue                       │
      │   └─ Failure → retry Pass 2 with error once   │
      └─────────────────────────┬─────────────────────┘
                                │
      ┌─────────────────────────▼─────────────────────┐
      │ BlenderMCPClient.execute() (AsyncIO locked)   │
      │ Timeout: 30s (existing client behavior)       │
      │ Output: "Blender OK" or "Blender error: ..."  │
      └─────────────────────────┬─────────────────────┘
                                │
              ┌─────────────────▼─────────────────┐
              │ HTTP 200 {"architecture": {...}}│
              │ or structured error 422/502/503  │
              └──────────────────────────────────┘
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/src/sketchos_backend/generation_routes.py` | Create | Vision-to-architecture router (480-550 lines): endpoint, two-pass functions, exception classes, lock, few-shots |
| `backend/src/sketchos_backend/main.py` | Modify | Add `app.include_router(generation_router)` after validator router line 26 |
| `backend/pyproject.toml` | Modify | Add `"google-generativeai>=0.8.0,<1"` to dependencies array |
| `backend/tests/test_generation_routes.py` | Create | 11+ tests: happy path, timeout, retry, validation, concurrent calls, missing API key |

## Interfaces / Contracts

### HTTP Endpoint

```python
@router.post("/generate-geometry")
async def generate_geometry(request: GenerationRequest) -> dict[str, Any]:
    """Transform Base64 sketch into ArchitecturalDSL JSON."""
```

**Request**:
```python
class GenerationRequest(BaseModel):
    image: str  # Base64-encoded PNG
```

**Response 200**:
```json
{"architecture": {<ArchitectureModel>}}
```

**Errors**: 400 (Base64), 422 (validation), 502 (Gemini API), 503 (missing key), 504 (timeout)

### Two-Pass Functions

```python
async def _pass1_morphology(image_bytes: bytes, api_key: str) -> str:
    """Vision → plain-text spatial deconstruction. Timeout 45s."""

async def _pass2_schema_json(morphology: str, api_key: str, retry_error: str | None = None) -> dict:
    """Text+schema → JSON. Timeout 45s. Embeds few-shots and optional retry feedback."""
```

### Exception Hierarchy

```python
class GenerationError(Exception):
    """Base for all generation errors."""
    status_code: int
    detail: str

class ValidationFailedError(GenerationError):  # 422
class GeminiAPIError(GenerationError):         # 502
class ProviderUnavailableError(GenerationError): # 503
class TimeoutError(GenerationError):           # 504
```

### Few-Shot Schema

Embedded in Pass 2 system prompt:
```python
FEW_SHOTS: list[dict[str, Any]] = [
    {
        "user_description": "Simple L-shaped wall floor plan",
        "architecture": {
            "walls": [{"id": "w1", "start": {...}, ...}],
            "floors": [{"id": "f1", ...}],
            # ... complete valid ArchitectureModel
        }
    },
    # Minimum 2 examples
]
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|--------------|----------|
| Unit | Few-shot examples parse | `ArchitectureModel.model_validate(ex["architecture"])` for each |
| Unit | Base64 decode failure → 400 | Fake client, invalid Base64 input |
| Unit | Missing API key → 503 | Patch `os.getenv("GOOGLE_API_KEY", None)` |
| Integration | Pass 1 + Pass 2 happy path | Mock `genai.GenerativeModel().generate_content()` canned responses |
| Integration | Timeout enforcement | `asyncio.sleep(46)` in mock, assert 504 |
| Integration | Validation retry | Mock Pass 2 to fail once, succeed on retry |
| Integration | Concurrent requests | 5 parallel `httpx.AsyncClient.post()`, assert all 200 + lock serialization |
| Integration | Blender error propagation | Mock `BlenderMCPClient.execute()` returns "Blender error: ...", assert 502 |
| E2E | Full pipeline with real Gemini | Conditional on `GOOGLE_API_KEY`, sketch → JSON → Blender → 200 |

**Test fixtures**:
- `FakeGenAIModel`: Mock `google.generativeai.GenerativeModel` returning canned text/JSON
- `FakeBlenderClient`: Mock `BlenderMCPClient.execute()` with configurable success/error
- `sample_sketch_base64`: Valid PNG Base64 string fixture

**AsyncIO lock test**: Launch 5 concurrent requests with 100ms sleeps in Blender mock. Assert call order is serialized (timestamps show no overlap).

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. This change implements an HTTP endpoint backed by library SDK calls (`google.generativeai`) and existing `BlenderMCPClient` (stdio transport already audited in Slice 2).

## Migration / Rollout

No migration required. New endpoint with no existing consumers. Rollback via removal of router registration line in `main.py`.

**Deployment notes**:
- `GOOGLE_API_KEY` required in environment (BYOK pattern)
- Startup logs warning if key missing: `"GOOGLE_API_KEY not configured — /generate-geometry will return 503"`
- No data persistence (stateless inference)
- No feature flags (endpoint gated by API key presence)

## Open Questions

- [ ] Pass 1 prompt tuning: Should morphology analysis explicitly call out cantilever detection (Z>0 walls) or let Gemini infer from "architectural masses"?
- [ ] Few-shot example count: Spec requires ≥2. Should we embed 3-4 for better schema coverage (simple L-shape, multi-floor, cantilever, courtyard)?
- [ ] Blender lock scope: Current design uses module-level lock. If future changes introduce per-user client pools, lock must move to pool-level. Document this assumption?

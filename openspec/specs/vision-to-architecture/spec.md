# Vision-to-Architecture Specification

## Purpose

Transform Base64 sketch images into validated ArchitecturalDSL JSON via two-pass Gemini inference with commercial-grade error containment.

## Requirements

### Requirement: HTTP Endpoint Contract

The system MUST provide POST `/generate-geometry` accepting Base64-encoded PNG images and returning ArchitecturalDSL JSON.

**Request**: `POST /generate-geometry` with body `{"image": "<base64-png>"}`  
**Success**: HTTP 200, body `{"architecture": <ArchitectureModel>}`

**Error Responses**:
| Status | Trigger | Response Body |
|--------|---------|---------------|
| 400 | Invalid Base64 | `{"error": "Invalid Base64 encoding", "detail": "<reason>"}` |
| 422 | Missing `image` field | `{"error": "Validation error", "detail": "Missing required field: image"}` |
| 422 | Validation failed (2 attempts) | `{"error": "Validation failed", "attempts": 2, "pydantic_errors": [...]}` |
| 502 | Gemini API failure | `{"error": "Gemini API failure", "detail": "quota exhausted\|model unavailable"}` |
| 503 | Missing API key | `{"error": "Provider unavailable", "detail": "GOOGLE_API_KEY not configured"}` |
| 504 | Timeout (45s) | `{"error": "Request timeout", "detail": "Gemini API request exceeded 45s", "pass": 1\|2}` |
| 504 | Blender timeout (30s) | `{"error": "Blender execution timeout", "detail": "MCP call exceeded 30s"}` |

#### Scenario: Valid request returns architecture

- GIVEN valid Base64 PNG sketch
- WHEN POST to `/generate-geometry`
- THEN HTTP 200 with schema-conformant ArchitectureModel JSON

### Requirement: Two-Pass Inference Pipeline

**Pass 1**: `gemini-1.5-pro-latest` with vision input → plain-text morphological deconstruction (masses, cantilevers Z>0, floors).  
**Pass 2**: `gemini-1.5-pro-latest` with Pass 1 text + `response_schema=ArchitectureModel.model_json_schema()` + ≥2 few-shot examples → JSON.  
**AFC**: MUST set `generation_config.enable_automatic_function_calling=False` for both passes.

#### Scenario: Two-pass execution produces valid JSON

- GIVEN valid sketch
- WHEN Pass 1 produces plain-text morphology AND Pass 2 applies response_schema with few-shots
- THEN Pass 2 output MUST be valid ArchitectureModel JSON

### Requirement: Self-Healing Validation Retry

The system MUST retry Pass 2 ONCE on Pydantic failure, injecting the error message into retry prompt.

#### Scenario: Validation retry with error feedback

- GIVEN Pass 2 fails `ArchitectureModel.model_validate()`
- WHEN retry executes with "Previous attempt failed: <error>" in prompt
- THEN retry SHOULD produce valid JSON OR return HTTP 422 after 2 attempts

### Requirement: Timeout Enforcement

**Pass 1/2**: 45s per Gemini request → HTTP 504 on timeout.  
**Blender**: 30s per MCP call → HTTP 504 on timeout.

#### Scenario: Pass timeout cancels request

- GIVEN Pass 1 or Pass 2 running
- WHEN 45s elapses
- THEN system MUST cancel request AND return HTTP 504

### Requirement: Few-Shot Example Validation

Pass 2 prompt MUST embed ≥2 few-shot examples. Tests MUST validate examples parse against ArchitectureModel schema.

#### Scenario: Examples conform to current schema

- GIVEN embedded few-shot examples
- WHEN tests parse with `ArchitectureModel.model_validate()`
- THEN all examples MUST succeed OR CI MUST fail

### Requirement: BYOK API Key Pattern

System MUST load `GOOGLE_API_KEY` from environment. Missing key → HTTP 503 with clear message.

#### Scenario: Missing API key at startup

- GIVEN `GOOGLE_API_KEY` unset
- WHEN FastAPI initializes
- THEN log warning AND return HTTP 503 on requests

### Requirement: Concurrency Safety

System MUST protect shared `BlenderMCPClient` state with AsyncIO lock when concurrent requests invoke `.execute()`.

#### Scenario: Concurrent requests with shared client

- GIVEN 5 concurrent requests
- WHEN Blender calls overlap
- THEN AsyncIO lock MUST serialize calls AND all 5 MUST succeed

### Requirement: Global Exception Containment

System MUST catch all exceptions in Base64 decode, Gemini API, validation, Blender execution. MUST NEVER return unhandled HTTP 500.

#### Scenario: Unexpected exception handling

- GIVEN unexpected exception during request
- WHEN exception propagates
- THEN return HTTP 502 with safe message AND log full trace internally

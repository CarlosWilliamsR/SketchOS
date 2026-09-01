"""Vision/text-to-architecture pipeline with two-pass Gemini inference.

This module provides two endpoints:
- POST /generate-geometry — transforms Base64 sketch images into validated
  ArchitecturalDSL JSON via two-pass Gemini processing (vision + schema JSON).
- POST /generate-from-text — transforms a natural-language prompt into the same
  validated ArchitecturalDSL JSON, skipping Base64 decode and Pass 1 vision.

## Architecture

The image pipeline consists of five stages:
1. **Base64 Decode**: Validate and decode PNG image from Base64
2. **Pass 1 (Morphology)**: Vision API → plain-text spatial analysis
3. **Pass 2 (Schema JSON)**: Text + response_schema → ArchitectureModel JSON
4. **Validation + Retry**: Pydantic validation with self-healing retry on failure
5. **Blender Execution**: Generate and execute Blender code via MCP (with AsyncIO lock)

The text pipeline reuses stages 3–5 verbatim: the raw prompt is fed through
``_build_text_prompt`` (defaults directive + few-shot examples + user
description) into Pass 2, then through validation/retry and Blender.

## Error Handling

Structured HTTP errors:
- 400: Invalid Base64 encoding (image) or empty prompt (text)
- 422: Validation failed after retry (with detailed error feedback)
- 502: Gemini API failure or Blender execution error
- 503: No API key configured (provider unavailable)
- 504: Timeout exceeded (45s Pass 1/2, 30s Blender)

## Concurrency Safety

BlenderMCPClient uses stdio transport (shared stdin/stdout). Concurrent calls
would cause interleaved JSON frames, violating MCP protocol. Module-level
AsyncIO lock (`_blender_lock`) serializes all `.execute()` calls.

## Few-Shot Examples

FEW_SHOT_EXAMPLES contains validated ArchitectureModel JSON snippets embedded
in Pass 2 prompts. CI test `test_few_shot_examples_validate_against_schema`
ensures examples stay in sync with schema changes.

## Environment Variables

- `X-Gemini-Api-Key` header (optional): per-request BYOK key (text endpoint only)
- `GOOGLE_API_KEY` (optional): Google Gemini API key (BYOK pattern)
- `GEMINI_API_KEY` (optional): fallback Google Gemini API key

Resolution order: header → `GOOGLE_API_KEY` → `GEMINI_API_KEY`. If none is
present, the endpoint returns 503 with a structured error message. The
repo-root `.env` is auto-loaded at import via `python-dotenv`.

## Usage

```python
from sketchos_backend.generation_routes import router
app.include_router(router)
```

POST /generate-geometry with `{"image": "<base64-png>"}` → 200 with architecture JSON
POST /generate-from-text with `{"prompt": "<natural language>"}` → 200 with architecture JSON
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from sketchos_backend.defaults import render_defaults_directive, render_unit_convention_instruction


# Configure logging
logger = logging.getLogger(__name__)


# Timeout constants (in seconds)
PASS1_TIMEOUT = 45.0  # Vision API request timeout
PASS2_TIMEOUT = 45.0  # Schema JSON generation timeout
BLENDER_TIMEOUT = 30.0  # Existing BlenderMCPClient timeout (set by client itself)


# Load repo-root .env (BYOK keys) before any environment reads below.
# find_dotenv() walks up from this module's file, so it resolves the repo-root
# .env even when uvicorn runs from backend/.
load_dotenv()


# Startup check: Warn if no API key is resolvable.
if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
    logger.warning(
        "No API key configured (GOOGLE_API_KEY or GEMINI_API_KEY) — generation "
        "endpoints will return 503. Set one to enable generation."
    )


# Exception hierarchy for structured error responses
class GenerationError(Exception):
    """Base exception for all generation errors."""
    
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class ValidationFailedError(GenerationError):
    """Pydantic validation failed after retry (HTTP 422)."""
    
    def __init__(self, detail: str):
        super().__init__(422, detail)


class GeminiAPIError(GenerationError):
    """Gemini API call failed (HTTP 502)."""
    
    def __init__(self, detail: str):
        super().__init__(502, detail)


class ProviderUnavailableError(GenerationError):
    """API provider unavailable - missing key (HTTP 503)."""
    
    def __init__(self, detail: str):
        super().__init__(503, detail)


class TimeoutError(GenerationError):
    """Request timeout exceeded (HTTP 504)."""
    
    def __init__(self, detail: str):
        super().__init__(504, detail)


# Pydantic models
class GenerationRequest(BaseModel):
    """Request payload for /generate-geometry endpoint."""
    image: str  # Base64-encoded PNG


class TextGenerationRequest(BaseModel):
    """Request payload for /generate-from-text endpoint.

    ``prompt`` is required (FastAPI returns 422 when absent); empty/whitespace
    prompts are rejected with 400 in the handler to mirror the image path's
    input-error code.
    """
    prompt: str


class GenerationResponse(BaseModel):
    """Response payload with validated architecture."""
    architecture: dict[str, Any]


# Router
router = APIRouter()


# Module-level AsyncIO lock for BlenderMCPClient concurrency safety
_blender_lock = asyncio.Lock()


# Few-shot examples for Pass 2 schema-forced JSON generation
FEW_SHOT_EXAMPLES: list[dict[str, Any]] = [
    {
        "user_description": "Simple L-shaped floor plan with two perpendicular walls",
        "architecture": {
            "walls": [
                {
                    "id": "w1",
                    "start": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "end": {"x": 5.0, "y": 0.0, "z": 0.0},
                    "height": 3.0,
                    "thickness": 0.3
                },
                {
                    "id": "w2",
                    "start": {"x": 5.0, "y": 0.0, "z": 0.0},
                    "end": {"x": 5.0, "y": 4.0, "z": 0.0},
                    "height": 3.0,
                    "thickness": 0.3
                }
            ],
            "floors": [
                {
                    "id": "f1",
                    "outline": [
                        {"x": 0.0, "y": 0.0, "z": 0.0},
                        {"x": 5.0, "y": 0.0, "z": 0.0},
                        {"x": 5.0, "y": 4.0, "z": 0.0},
                        {"x": 0.0, "y": 4.0, "z": 0.0}
                    ],
                    "thickness": 0.2,
                    "elevation": 0.0
                }
            ],
            "openings": [],
            "volumes": [],
            "relationships": []
        }
    },
    {
        "user_description": "Multi-floor building with cantilever and door opening",
        "architecture": {
            "walls": [
                {
                    "id": "w1",
                    "start": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "end": {"x": 8.0, "y": 0.0, "z": 0.0},
                    "height": 3.0,
                    "thickness": 0.3
                },
                {
                    "id": "w2",
                    "start": {"x": 0.0, "y": 0.0, "z": 3.0},
                    "end": {"x": 10.0, "y": 0.0, "z": 3.0},
                    "height": 3.0,
                    "thickness": 0.3
                }
            ],
            "floors": [
                {
                    "id": "f1",
                    "outline": [
                        {"x": 0.0, "y": 0.0, "z": 0.0},
                        {"x": 8.0, "y": 0.0, "z": 0.0},
                        {"x": 8.0, "y": 6.0, "z": 0.0},
                        {"x": 0.0, "y": 6.0, "z": 0.0}
                    ],
                    "thickness": 0.2,
                    "elevation": 0.0
                },
                {
                    "id": "f2",
                    "outline": [
                        {"x": 0.0, "y": 0.0, "z": 3.0},
                        {"x": 10.0, "y": 0.0, "z": 3.0},
                        {"x": 10.0, "y": 6.0, "z": 3.0},
                        {"x": 0.0, "y": 6.0, "z": 3.0}
                    ],
                    "thickness": 0.2,
                    "elevation": 3.0
                }
            ],
            "openings": [
                {
                    "id": "o1",
                    "wall_id": "w1",
                    "position": {"x": 2.0, "y": 0.0, "z": 0.0},
                    "width": 1.0,
                    "height": 2.2
                }
            ],
            "volumes": [],
            "relationships": [
                {
                    "source_id": "o1",
                    "target_id": "w1",
                    "kind": "opening_in"
                }
            ]
        }
    }
]


def _get_api_key(header_key: str | None = None) -> str:
    """Resolve the Gemini API key: header → GOOGLE_API_KEY → GEMINI_API_KEY.

    Args:
        header_key: Per-request BYOK key from the ``X-Gemini-Api-Key`` header.

    Returns:
        The resolved API key.

    Raises:
        ProviderUnavailableError: If no key resolves (header or env).
    """
    if header_key:
        return header_key
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ProviderUnavailableError(
            "No API key configured (set GOOGLE_API_KEY or GEMINI_API_KEY)"
        )
    return api_key


async def _pass1_morphology(image_bytes: bytes, api_key: str) -> str:
    """Pass 1: Vision to plain-text morphological deconstruction.
    
    Args:
        image_bytes: Raw PNG image bytes
        api_key: Google API key for Gemini
        
    Returns:
        Plain-text morphology description
        
    Raises:
        TimeoutError: If request exceeds 45s
        GeminiAPIError: If Gemini API call fails
    """
    try:
        # Import here to avoid import errors in tests before installing deps
        import google.generativeai as genai
        
        # Configure API key
        genai.configure(api_key=api_key)
        
        # Initialize model with AFC disabled
        model = genai.GenerativeModel(
            "gemini-1.5-pro-latest",
            generation_config={"enable_automatic_function_calling": False}
        )
        
        # Prepare vision input
        vision_input = {
            "mime_type": "image/png",
            "data": image_bytes
        }
        
        # System prompt for Pass 1
        prompt = (
            "Analyze this architectural sketch. Identify: primary masses, "
            "cantilevered elements (Z>0), slab floors, spatial relationships. "
            "Output plain-text deconstruction."
        )
        
        # Wrap with timeout (45s for vision API request)
        try:
            response = await asyncio.wait_for(
                model.generate_content_async([prompt, vision_input]),
                timeout=PASS1_TIMEOUT
            )
            return response.text
        except asyncio.TimeoutError:
            raise TimeoutError(f"Pass 1 timeout: Gemini API request exceeded {PASS1_TIMEOUT}s")
            
    except ImportError:
        raise GeminiAPIError("google-generativeai SDK not installed")
    except TimeoutError:
        raise  # Re-raise our TimeoutError
    except Exception as e:
        raise GeminiAPIError(f"Gemini API failure: {str(e)}")


def _render_few_shot_examples() -> str:
    """Serialize ``FEW_SHOT_EXAMPLES`` into a prompt-ready text block.

    Shared by both prompt builders so the image and text paths stay in sync on
    the example format.
    """
    import json

    examples_text = "Here are example architectural analyses:\n\n"
    for i, example in enumerate(FEW_SHOT_EXAMPLES, 1):
        examples_text += f"Example {i}: {example['user_description']}\n"
        examples_text += f"JSON Output:\n{json.dumps(example['architecture'], indent=2)}\n\n"
    return examples_text


def _build_pass2_prompt(morphology: str, retry_error: str | None = None) -> str:
    """Build Pass 2 prompt with few-shot examples and optional retry feedback.
    
    Args:
        morphology: Plain-text morphology from Pass 1
        retry_error: Optional Pydantic validation error from previous attempt
        
    Returns:
        Formatted prompt string with examples and instructions
    """
    # Start with few-shot examples
    examples_text = _render_few_shot_examples()
    
    # Build main instruction
    instruction = (
        f"{examples_text}"
        f"Now, based on this morphological analysis:\n\n"
        f"{morphology}\n\n"
        f"Generate a complete ArchitectureModel JSON with all required fields: "
        f"walls, floors, openings, volumes, relationships. "
        f"Follow the exact schema from the examples above."
    )
    
    # Add retry feedback if this is a second attempt
    if retry_error:
        instruction += (
            f"\n\nPREVIOUS ATTEMPT FAILED with error:\n{retry_error}\n\n"
            f"Please correct the error and ensure all required fields are present "
            f"and valid according to the schema."
        )
    
    return instruction


def _build_text_prompt(user_prompt: str, retry_error: str | None = None) -> str:
    """Build the natural-language Pass 2 prompt for the text-to-architecture path.

    Unlike ``_build_pass2_prompt`` (image path, "morphological analysis" wording),
    this describes the user's plain-language request, injects the env-overridable
    defaults directive (subordinate to any user-specified dimension), and the
    canonical-unit directive (all dimensions normalized to meters) so a
    dimension-less prompt still produces a valid model.

    Args:
        user_prompt: Raw natural-language description from the client.
        retry_error: Optional Pydantic validation error from a previous attempt.

    Returns:
        Formatted prompt string with defaults, canonical-unit rule, few-shot
        examples, and the user description.
    """
    instruction = (
        f"{render_defaults_directive()}\n\n"
        f"{render_unit_convention_instruction()}\n\n"
        f"{_render_few_shot_examples()}"
        f"Now, based on the user's natural-language description:\n\n"
        f"{user_prompt}\n\n"
        f"Generate a complete ArchitectureModel JSON with all required fields: "
        f"walls, floors, openings, volumes, relationships. "
        f"Follow the exact schema from the examples above."
    )

    if retry_error:
        instruction += (
            f"\n\nPREVIOUS ATTEMPT FAILED with error:\n{retry_error}\n\n"
            f"Please correct the error and ensure all required fields are present "
            f"and valid according to the schema."
        )

    return instruction


async def _pass2_schema_json(
    morphology: str,
    api_key: str,
    retry_error: str | None = None,
    build_prompt=_build_pass2_prompt,
) -> dict[str, Any]:
    """Pass 2: Text + schema → structured ArchitectureModel JSON.
    
    Args:
        morphology: Plain-text morphology from Pass 1
        api_key: Google API key for Gemini
        retry_error: Optional validation error feedback from previous attempt
        build_prompt: Prompt builder (defaults to the image-path builder;
            the text path passes ``_build_text_prompt``)
        
    Returns:
        Dictionary matching ArchitectureModel schema
        
    Raises:
        TimeoutError: If request exceeds 45s
        GeminiAPIError: If Gemini API call fails
    """
    try:
        # Import here to avoid import errors in tests
        import google.generativeai as genai
        from sketchos_backend.arch_dsl import ArchitectureModel
        
        # Configure API key
        genai.configure(api_key=api_key)
        
        # Get response schema from ArchitectureModel
        response_schema = ArchitectureModel.model_json_schema()
        
        # Initialize model with response_schema and AFC disabled
        model = genai.GenerativeModel(
            "gemini-1.5-pro-latest",
            generation_config={
                "response_schema": response_schema,
                "enable_automatic_function_calling": False
            }
        )
        
        # Build prompt with few-shots and optional retry feedback
        prompt = build_prompt(morphology, retry_error)
        
        # Wrap with timeout (45s for JSON generation)
        try:
            response = await asyncio.wait_for(
                model.generate_content_async(prompt),
                timeout=PASS2_TIMEOUT
            )
            # Parse JSON response
            import json
            return json.loads(response.text)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Pass 2 timeout: Gemini API request exceeded {PASS2_TIMEOUT}s")
            
    except ImportError:
        raise GeminiAPIError("google-generativeai SDK not installed")
    except TimeoutError:
        raise  # Re-raise our TimeoutError
    except json.JSONDecodeError as e:
        raise GeminiAPIError(f"Invalid JSON in Pass 2 response: {str(e)}")
    except Exception as e:
        raise GeminiAPIError(f"Gemini API failure in Pass 2: {str(e)}")


async def _validate_and_retry(
    morphology: str,
    api_key: str,
    build_prompt=_build_pass2_prompt,
) -> Any:
    """Validate Pass 2 output and retry once with error feedback if validation fails.
    
    This implements the self-healing retry logic: if Pydantic validation fails,
    we inject the error message back into Pass 2 prompt and retry once. This
    gives the model a chance to correct minor schema misunderstandings.
    
    Args:
        morphology: Plain-text morphology from Pass 1 (or the user prompt for
            the text path)
        api_key: Google API key for Gemini
        build_prompt: Prompt builder forwarded to ``_pass2_schema_json``
        
    Returns:
        Validated ArchitectureModel instance
        
    Raises:
        ValidationFailedError: If validation fails after 2 attempts (first + retry)
    """
    from pydantic import ValidationError
    from sketchos_backend.arch_dsl import ArchitectureModel
    
    # First attempt: Pass 2 without error feedback
    try:
        arch_json = await _pass2_schema_json(morphology, api_key, retry_error=None, build_prompt=build_prompt)
        return ArchitectureModel.model_validate(arch_json)
    except ValidationError as e:
        first_error = str(e)
        logger.info(f"First validation attempt failed, retrying with error feedback: {first_error[:100]}...")
        
        # Retry with error feedback injected into Pass 2 prompt
        try:
            arch_json = await _pass2_schema_json(morphology, api_key, retry_error=first_error, build_prompt=build_prompt)
            return ArchitectureModel.model_validate(arch_json)
        except ValidationError as e2:
            # Both attempts failed - return structured error with both attempts
            logger.error(f"Validation failed after 2 attempts. First: {first_error[:50]}..., Second: {str(e2)[:50]}...")
            raise ValidationFailedError(
                f"Validation failed after 2 attempts. "
                f"First error: {first_error}. "
                f"Second error: {str(e2)}"
            )


async def _execute_blender(architecture: Any) -> str:
    """Execute Blender code generation and MCP call with AsyncIO lock.
    
    CRITICAL: BlenderMCPClient uses stdio transport (shared stdin/stdout pipes).
    Concurrent MCP calls would cause interleaved JSON frames, violating protocol.
    The AsyncIO lock ensures serialized execution across concurrent HTTP requests.
    
    Args:
        architecture: Validated ArchitectureModel instance
        
    Returns:
        Blender execution result string
        
    Raises:
        TimeoutError: If Blender execution exceeds 30s
        GeminiAPIError: If Blender execution fails
    """
    from sketchos_backend.blender_client import BlenderMCPClient, generate_blender_code
    
    # Acquire lock to serialize Blender MCP calls (stdio transport safety)
    # Without this lock, concurrent requests would interleave stdout/stdin streams
    async with _blender_lock:
        logger.debug("Acquired Blender lock for execution")
        try:
            # Generate Blender code from ArchitectureModel
            blender_code = generate_blender_code(architecture)
            
            # Execute via MCP client with timeout
            client = BlenderMCPClient()
            try:
                result = await asyncio.wait_for(
                    client.execute(blender_code),
                    timeout=BLENDER_TIMEOUT
                )
                
                # Check for errors in result string
                if "error" in result.lower():
                    raise GeminiAPIError(f"Blender execution failed: {result}")
                
                logger.debug("Blender execution completed successfully")
                return result
                
            except asyncio.TimeoutError:
                logger.error(f"Blender execution timeout after {BLENDER_TIMEOUT}s")
                raise TimeoutError(f"Blender execution timeout: MCP call exceeded {BLENDER_TIMEOUT}s")
                
        except TimeoutError:
            raise  # Re-raise our TimeoutError
        except Exception as e:
            logger.error(f"Blender execution error: {str(e)}")
            raise GeminiAPIError(f"Blender execution error: {str(e)}")


@router.post("/generate-geometry")
async def generate_geometry(request: GenerationRequest) -> dict[str, Any]:
    """Transform Base64 sketch into ArchitecturalDSL JSON.
    
    Full two-pass pipeline:
    1. Decode Base64 image
    2. Pass 1: Vision → morphology (plain text)
    3. Pass 2: Morphology + schema → JSON (with few-shot examples)
    4. Validation with self-healing retry (inject error feedback on failure)
    5. Blender execution (with AsyncIO lock for stdio safety)
    
    Args:
        request: GenerationRequest with Base64 image
        
    Returns:
        Dict with 'architecture' key containing ArchitectureModel
        
    Raises:
        HTTPException: With appropriate status codes (400/422/502/503/504)
    """
    try:
        # Stage 1: Decode Base64 image
        try:
            image_bytes = base64.b64decode(request.image)
        except (binascii.Error, ValueError) as e:
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid Base64 encoding", "detail": str(e)}
            ) from e
        
        # Stage 2: Get API key (BYOK pattern)
        try:
            api_key = _get_api_key()
        except ProviderUnavailableError as e:
            raise HTTPException(
                status_code=503,
                detail={"error": "Provider unavailable", "detail": e.detail}
            ) from e
        
        # Stage 3: Pass 1 — Vision → morphology
        try:
            morphology = await _pass1_morphology(image_bytes, api_key)
            logger.info(f"Pass 1 completed: {len(morphology)} chars of morphology")
        except TimeoutError as e:
            raise HTTPException(
                status_code=504,
                detail={"error": "Request timeout", "detail": e.detail, "pass": 1}
            ) from e
        except GeminiAPIError as e:
            raise HTTPException(
                status_code=502,
                detail={"error": "Gemini API failure", "detail": e.detail}
            ) from e
        
        # Stage 4: Pass 2 + Validation with self-healing retry
        # This orchestrates: Pass 2 → validate → (if fail) Pass 2 with error → validate
        try:
            architecture = await _validate_and_retry(morphology, api_key)
            logger.info("Pass 2 + validation completed successfully")
        except ValidationFailedError as e:
            raise HTTPException(
                status_code=422,
                detail={"error": "Validation failed", "detail": e.detail}
            ) from e
        except TimeoutError as e:
            raise HTTPException(
                status_code=504,
                detail={"error": "Request timeout", "detail": e.detail, "pass": 2}
            ) from e
        except GeminiAPIError as e:
            raise HTTPException(
                status_code=502,
                detail={"error": "Gemini API failure", "detail": e.detail}
            ) from e
        
        # Stage 5: Blender execution (with AsyncIO lock)
        try:
            blender_result = await _execute_blender(architecture)
            logger.info("Blender execution completed")
        except TimeoutError as e:
            raise HTTPException(
                status_code=504,
                detail={"error": "Blender execution timeout", "detail": e.detail}
            ) from e
        except GeminiAPIError as e:
            raise HTTPException(
                status_code=502,
                detail={"error": "Blender execution failed", "detail": e.detail}
            ) from e
        
        # Return successful result
        return {"architecture": architecture.model_dump()}
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        # Global exception containment - never return 500
        # All unexpected errors are wrapped as 502 with structured detail
        logger.exception("Unexpected error in generate_geometry")
        raise HTTPException(
            status_code=502,
            detail={"error": "Unexpected error", "detail": str(e)}
        ) from e


@router.post("/generate-from-text")
async def generate_from_text(
    request: TextGenerationRequest,
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-Api-Key"),
) -> dict[str, Any]:
    """Transform a natural-language description into ArchitecturalDSL JSON.

    Mirrors the image pipeline but skips Base64 decode and Pass 1 vision: the
    prompt passes straight through to Pass 2 schema-forced JSON via
    ``_build_text_prompt`` (defaults directive + few-shot + user description),
    then through self-healing validation and Blender execution.

    Args:
        request: TextGenerationRequest with a natural-language ``prompt``.
        x_gemini_api_key: Per-request BYOK key from the ``X-Gemini-Api-Key`` header.

    Returns:
        Dict with 'architecture' key containing ArchitectureModel.

    Raises:
        HTTPException: With appropriate status codes (400/422/502/503/504).
    """
    try:
        # Stage 1: Reject empty/whitespace prompt (mirrors image-path 400).
        if not request.prompt or not request.prompt.strip():
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid prompt", "detail": "Prompt must not be empty"},
            )

        # Stage 2: Get API key (header → GOOGLE_API_KEY → GEMINI_API_KEY → 503).
        try:
            api_key = _get_api_key(header_key=x_gemini_api_key)
        except ProviderUnavailableError as e:
            raise HTTPException(
                status_code=503,
                detail={"error": "Provider unavailable", "detail": e.detail}
            ) from e

        # Stage 3: Pass 2 + Validation with self-healing retry.
        try:
            architecture = await _validate_and_retry(
                request.prompt, api_key, build_prompt=_build_text_prompt
            )
            logger.info("Text Pass 2 + validation completed successfully")
        except ValidationFailedError as e:
            raise HTTPException(
                status_code=422,
                detail={"error": "Validation failed", "detail": e.detail}
            ) from e
        except TimeoutError as e:
            raise HTTPException(
                status_code=504,
                detail={"error": "Request timeout", "detail": e.detail, "pass": 2}
            ) from e
        except GeminiAPIError as e:
            raise HTTPException(
                status_code=502,
                detail={"error": "Gemini API failure", "detail": e.detail}
            ) from e

        # Stage 4: Blender execution (with AsyncIO lock).
        try:
            await _execute_blender(architecture)
            logger.info("Blender execution completed")
        except TimeoutError as e:
            raise HTTPException(
                status_code=504,
                detail={"error": "Blender execution timeout", "detail": e.detail}
            ) from e
        except GeminiAPIError as e:
            raise HTTPException(
                status_code=502,
                detail={"error": "Blender execution failed", "detail": e.detail}
            ) from e

        # Return successful result
        return {"architecture": architecture.model_dump()}

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        # Global exception containment - never return 500
        logger.exception("Unexpected error in generate_from_text")
        raise HTTPException(
            status_code=502,
            detail={"error": "Unexpected error", "detail": str(e)}
        ) from e

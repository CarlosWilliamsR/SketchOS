"""Endpoint tests for generation_routes (vision-to-architecture pipeline).

These tests verify the POST /generate-geometry endpoint with mocked Gemini SDK
and BlenderMCPClient. No real API calls, no real Blender execution.
"""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from sketchos_backend.main import app


# Sample valid PNG Base64 (1x1 transparent PNG)
SAMPLE_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


class TestBase64Validation:
    """Test invalid Base64 input → 400 error."""

    def test_base64_decode_failure(self):
        """Invalid Base64 input should return 400 with error message."""
        from sketchos_backend.generation_routes import router
        
        # Create test client
        client = TestClient(app)
        
        # Send invalid Base64
        response = client.post(
            "/generate-geometry",
            json={"image": "not-valid-base64!!!"}
        )
        
        assert response.status_code == 400
        # FastAPI wraps the detail in a 'detail' key
        response_data = response.json()
        assert "detail" in response_data
        detail = response_data["detail"]
        assert "error" in detail
        assert "Base64" in detail["error"]
    
    def test_base64_decode_empty_string(self, monkeypatch):
        """Empty Base64 string should also fail gracefully."""
        # Clear both keys so the endpoint stops at key resolution instead of
        # attempting a real Gemini call (load_dotenv() may load GEMINI_API_KEY).
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        client = TestClient(app)
        
        response = client.post(
            "/generate-geometry",
            json={"image": ""}
        )
        
        # Empty string is technically valid Base64 but decodes to empty bytes
        # This should still work through the system
        assert response.status_code in (200, 400, 502, 503, 504)
    
    def test_base64_decode_special_chars(self, monkeypatch):
        """Base64 with spaces and special chars that fail decode."""
        # Clear both keys so the endpoint stops at key resolution instead of
        # attempting a real Gemini call (load_dotenv() may load GEMINI_API_KEY).
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        client = TestClient(app)
        
        # Use characters that are definitely not Base64
        response = client.post(
            "/generate-geometry",
            json={"image": "not-valid!!"}
        )
        
        # Could be 400 (bad Base64) or 503 (no API key) depending on decode leniency
        assert response.status_code in (400, 503)
        detail = response.json()["detail"]
        assert "error" in detail


class TestAPIKeyValidation:
    """Test missing GOOGLE_API_KEY → 503 error."""

    def test_missing_api_key(self, monkeypatch):
        """Missing both GOOGLE_API_KEY and GEMINI_API_KEY should return 503."""
        from sketchos_backend.generation_routes import router
        
        # Remove BOTH API keys from environment (the GEMINI fallback must not
        # silently satisfy the 503 path).
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        
        client = TestClient(app)
        response = client.post(
            "/generate-geometry",
            json={"image": SAMPLE_PNG_BASE64}
        )
        
        assert response.status_code == 503
        response_data = response.json()
        assert "detail" in response_data
        detail = response_data["detail"]
        assert "error" in detail
        assert "Provider unavailable" in detail["error"]


class TestAPIKeyResolution:
    """Test header → GOOGLE_API_KEY → GEMINI_API_KEY → 503 precedence order."""

    def test_header_key_takes_precedence(self, monkeypatch):
        """X-Gemini-Api-Key header wins over every env var."""
        from sketchos_backend.generation_routes import _get_api_key
        monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
        monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")

        assert _get_api_key(header_key="header-key") == "header-key"

    def test_google_env_precedes_gemini_env(self, monkeypatch):
        """GOOGLE_API_KEY wins when both env vars are set."""
        from sketchos_backend.generation_routes import _get_api_key
        monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
        monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")

        assert _get_api_key() == "google-key"

    def test_gemini_env_fallback(self, monkeypatch):
        """GEMINI_API_KEY is used when GOOGLE_API_KEY is absent."""
        from sketchos_backend.generation_routes import _get_api_key
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")

        assert _get_api_key() == "gemini-key"

    def test_missing_key_raises_503(self, monkeypatch):
        """No header and no env key raises ProviderUnavailableError (503)."""
        from sketchos_backend.generation_routes import (
            _get_api_key,
            ProviderUnavailableError,
        )
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        with pytest.raises(ProviderUnavailableError):
            _get_api_key()


class TestPass1Morphology:
    """Test Pass 1 vision-to-morphology with mocked Gemini."""

    def test_pass1_morphology_happy(self, monkeypatch):
        """Pass 1 should convert image to plain-text morphology."""
        from unittest.mock import AsyncMock, MagicMock
        from sketchos_backend import generation_routes
        
        # Mock the genai SDK at module level
        fake_response = MagicMock()
        fake_response.text = "Morphology: L-shaped floor plan with two perpendicular walls forming 90-degree angle."
        
        fake_model = MagicMock()
        fake_model.generate_content_async = AsyncMock(return_value=fake_response)
        
        fake_genai = MagicMock()
        fake_genai.GenerativeModel.return_value = fake_model
        fake_genai.configure = MagicMock()
        
        # Patch at import location in generation_routes
        import sys
        sys.modules['google.generativeai'] = fake_genai
        
        # Set API key
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key-for-testing")
        
        # Reimport to pick up the mocked module
        import importlib
        importlib.reload(generation_routes)
        from sketchos_backend.generation_routes import _pass1_morphology
        
        # Call Pass 1
        image_bytes = base64.b64decode(SAMPLE_PNG_BASE64)
        result = asyncio.run(_pass1_morphology(image_bytes, "fake-key"))
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Morphology" in result or "wall" in result.lower()
    
    def test_pass1_morphology_complex_response(self, monkeypatch):
        """Pass 1 with complex multi-line morphology text."""
        from unittest.mock import AsyncMock, MagicMock
        from sketchos_backend import generation_routes
        
        # Mock with longer, more complex response
        fake_response = MagicMock()
        fake_response.text = """Architectural Analysis:
Primary masses: Two rectangular volumes at ground level
Cantilevered elements: Upper floor extends 2m beyond ground footprint at Z=3.0m
Slab floors: Ground floor (Z=0), First floor (Z=3.0m)
Spatial relationships: Connected by vertical circulation core on west side"""
        
        fake_model = MagicMock()
        fake_model.generate_content_async = AsyncMock(return_value=fake_response)
        
        fake_genai = MagicMock()
        fake_genai.GenerativeModel.return_value = fake_model
        fake_genai.configure = MagicMock()
        
        import sys
        sys.modules['google.generativeai'] = fake_genai
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")
        
        import importlib
        importlib.reload(generation_routes)
        from sketchos_backend.generation_routes import _pass1_morphology
        
        image_bytes = base64.b64decode(SAMPLE_PNG_BASE64)
        result = asyncio.run(_pass1_morphology(image_bytes, "fake-key"))
        
        assert isinstance(result, str)
        assert "Cantilevered" in result
        assert "floor" in result.lower()
        assert len(result) > 100  # Complex response is longer


class TestTimeoutHandling:
    """Test timeout enforcement → 504 error."""

    def test_pass1_timeout(self, monkeypatch):
        """Pass 1 exceeding 45s should return 504."""
        from unittest.mock import AsyncMock, MagicMock
        from sketchos_backend import generation_routes
        
        # Mock genai to sleep longer than timeout
        async def slow_call(*args, **kwargs):
            await asyncio.sleep(46)  # Exceed 45s timeout
            return None
        
        fake_model = MagicMock()
        fake_model.generate_content_async = AsyncMock(side_effect=slow_call)
        
        fake_genai = MagicMock()
        fake_genai.GenerativeModel.return_value = fake_model
        fake_genai.configure = MagicMock()
        
        import sys
        sys.modules['google.generativeai'] = fake_genai
        
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")
        
        # Reimport
        import importlib
        importlib.reload(generation_routes)
        from sketchos_backend.generation_routes import _pass1_morphology, TimeoutError
        
        # Should raise TimeoutError
        image_bytes = base64.b64decode(SAMPLE_PNG_BASE64)
        with pytest.raises(TimeoutError):
            asyncio.run(_pass1_morphology(image_bytes, "fake-key"))


class TestPass2SchemaJSON:
    """Test Pass 2 schema-forced JSON generation with few-shots."""

    def test_pass2_schema_json_happy(self, monkeypatch):
        """Pass 2 should return valid ArchitectureModel JSON with response_schema."""
        from unittest.mock import AsyncMock, MagicMock
        from sketchos_backend import generation_routes
        
        # Mock valid ArchitectureModel JSON response
        valid_arch_json = {
            "walls": [{"id": "w1", "start": {"x": 0.0, "y": 0.0, "z": 0.0}, 
                       "end": {"x": 5.0, "y": 0.0, "z": 0.0}, "height": 3.0, "thickness": 0.3}],
            "floors": [{"id": "f1", "outline": [{"x": 0.0, "y": 0.0, "z": 0.0}], 
                        "thickness": 0.2, "elevation": 0.0}],
            "openings": [],
            "volumes": [],
            "relationships": []
        }
        
        fake_response = MagicMock()
        fake_response.text = json.dumps(valid_arch_json)
        
        fake_model = MagicMock()
        fake_model.generate_content_async = AsyncMock(return_value=fake_response)
        
        fake_genai = MagicMock()
        fake_genai.GenerativeModel.return_value = fake_model
        fake_genai.configure = MagicMock()
        
        import sys
        sys.modules['google.generativeai'] = fake_genai
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")
        
        import importlib
        importlib.reload(generation_routes)
        from sketchos_backend.generation_routes import _pass2_schema_json
        
        # Call Pass 2
        morphology = "Simple L-shaped wall with floor"
        result = asyncio.run(_pass2_schema_json(morphology, "fake-key"))
        
        assert isinstance(result, dict)
        assert "walls" in result
        assert "floors" in result
        assert len(result["walls"]) > 0


class TestValidationRetry:
    """Test self-healing validation with retry logic."""

    def test_validation_retry_success(self, monkeypatch):
        """First Pass 2 fails validation, retry with error feedback succeeds."""
        from unittest.mock import AsyncMock, MagicMock
        from sketchos_backend import generation_routes
        
        # First call: invalid JSON (missing required fields)
        invalid_json = {
            "walls": [],
            "floors": [],
            # Missing openings, volumes, relationships
        }
        
        # Second call: valid JSON
        valid_json = {
            "walls": [],
            "floors": [],
            "openings": [],
            "volumes": [],
            "relationships": []
        }
        
        responses = [
            MagicMock(text=json.dumps(invalid_json)),
            MagicMock(text=json.dumps(valid_json))
        ]
        
        fake_model = MagicMock()
        fake_model.generate_content_async = AsyncMock(side_effect=responses)
        
        fake_genai = MagicMock()
        fake_genai.GenerativeModel.return_value = fake_model
        fake_genai.configure = MagicMock()
        
        import sys
        sys.modules['google.generativeai'] = fake_genai
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")
        
        import importlib
        importlib.reload(generation_routes)
        from sketchos_backend.generation_routes import _validate_and_retry
        
        # Should succeed on retry
        result = asyncio.run(_validate_and_retry("morphology", "fake-key"))
        
        assert result is not None
        assert "walls" in result.model_dump()
        
    def test_validation_retry_exhausted(self, monkeypatch):
        """Both validation attempts fail → should raise ValidationFailedError."""
        from unittest.mock import AsyncMock, MagicMock
        from sketchos_backend import generation_routes
        
        # Both calls return invalid JSON
        invalid_json = {"walls": []}  # Missing required fields
        
        fake_response = MagicMock(text=json.dumps(invalid_json))
        fake_model = MagicMock()
        fake_model.generate_content_async = AsyncMock(return_value=fake_response)
        
        fake_genai = MagicMock()
        fake_genai.GenerativeModel.return_value = fake_model
        fake_genai.configure = MagicMock()
        
        import sys
        sys.modules['google.generativeai'] = fake_genai
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")
        
        import importlib
        importlib.reload(generation_routes)
        from sketchos_backend.generation_routes import _validate_and_retry, ValidationFailedError
        
        # Should raise ValidationFailedError after 2 attempts
        with pytest.raises(ValidationFailedError):
            asyncio.run(_validate_and_retry("morphology", "fake-key"))


class TestBlenderExecution:
    """Test Blender execution with AsyncIO lock and timeout."""

    def test_blender_execution_success(self, monkeypatch):
        """Successful Blender execution should return result string."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from sketchos_backend.arch_dsl import ArchitectureModel
        
        # Create valid architecture
        arch = ArchitectureModel(
            walls=[], floors=[], openings=[], volumes=[], relationships=[]
        )
        
        # Mock blender_client module
        mock_generate = MagicMock(return_value="bpy.ops.mesh...")
        mock_client = MagicMock()
        mock_client.execute = AsyncMock(return_value="Blender execution completed successfully")
        mock_client_class = MagicMock(return_value=mock_client)
        
        with patch('sketchos_backend.blender_client.generate_blender_code', mock_generate):
            with patch('sketchos_backend.blender_client.BlenderMCPClient', mock_client_class):
                # Now import after patching
                import importlib
                from sketchos_backend import generation_routes
                importlib.reload(generation_routes)
                from sketchos_backend.generation_routes import _execute_blender
                
                result = asyncio.run(_execute_blender(arch))
                
                assert isinstance(result, str)
                assert "success" in result.lower() or "completed" in result.lower()
    
    def test_blender_timeout(self, monkeypatch):
        """Blender execution exceeding 30s should raise TimeoutError."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from sketchos_backend.arch_dsl import ArchitectureModel
        
        arch = ArchitectureModel(
            walls=[], floors=[], openings=[], volumes=[], relationships=[]
        )
        
        # Mock Blender to timeout
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(31)  # Exceed 30s timeout
            return "too slow"
        
        mock_generate = MagicMock(return_value="bpy.ops.mesh...")
        mock_client = MagicMock()
        mock_client.execute = AsyncMock(side_effect=slow_execute)
        mock_client_class = MagicMock(return_value=mock_client)
        
        with patch('sketchos_backend.blender_client.generate_blender_code', mock_generate):
            with patch('sketchos_backend.blender_client.BlenderMCPClient', mock_client_class):
                import importlib
                from sketchos_backend import generation_routes
                importlib.reload(generation_routes)
                from sketchos_backend.generation_routes import _execute_blender, TimeoutError
                
                # Should raise TimeoutError
                with pytest.raises(TimeoutError):
                    asyncio.run(_execute_blender(arch))


class TestFullPipeline:
    """Test complete end-to-end pipeline integration."""

    def test_full_pipeline_end_to_end(self, monkeypatch):
        """Complete pipeline: Base64 → Pass1 → Pass2 → Validate → Blender → 200."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from sketchos_backend import generation_routes
        
        # Mock Pass 1 response
        morphology_text = "L-shaped architectural plan with two walls"
        
        # Mock Pass 2 response (valid ArchitectureModel)
        valid_arch_json = {
            "walls": [{"id": "w1", "start": {"x": 0.0, "y": 0.0, "z": 0.0},
                       "end": {"x": 5.0, "y": 0.0, "z": 0.0}, "height": 3.0, "thickness": 0.3}],
            "floors": [],
            "openings": [],
            "volumes": [],
            "relationships": []
        }
        
        # Mock genai
        fake_responses = [
            MagicMock(text=morphology_text),  # Pass 1
            MagicMock(text=json.dumps(valid_arch_json))  # Pass 2
        ]
        
        fake_model = MagicMock()
        fake_model.generate_content_async = AsyncMock(side_effect=fake_responses)
        
        fake_genai = MagicMock()
        fake_genai.GenerativeModel.return_value = fake_model
        fake_genai.configure = MagicMock()
        
        import sys
        sys.modules['google.generativeai'] = fake_genai
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")
        
        # Mock Blender
        mock_generate = MagicMock(return_value="bpy.ops.mesh...")
        mock_client = MagicMock()
        mock_client.execute = AsyncMock(return_value="Blender OK")
        mock_client_class = MagicMock(return_value=mock_client)
        
        with patch('sketchos_backend.blender_client.generate_blender_code', mock_generate):
            with patch('sketchos_backend.blender_client.BlenderMCPClient', mock_client_class):
                import importlib
                importlib.reload(generation_routes)
                
                # Send full request
                client = TestClient(app)
                response = client.post(
                    "/generate-geometry",
                    json={"image": SAMPLE_PNG_BASE64}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "architecture" in data
                assert "walls" in data["architecture"]


class TestFewShotExamples:
    """Test few-shot examples validate against ArchitectureModel schema (CI contract)."""
    
    def test_few_shot_examples_validate_against_schema(self):
        """CI CONTRACT: Few-shot examples MUST validate against ArchitectureModel schema.
        
        This test FAILS if examples drift from schema changes. This is intentional.
        If this test fails, update FEW_SHOT_EXAMPLES in generation_routes.py.
        """
        from sketchos_backend.generation_routes import FEW_SHOT_EXAMPLES
        from sketchos_backend.arch_dsl import ArchitectureModel
        from pydantic import ValidationError
        
        for i, example in enumerate(FEW_SHOT_EXAMPLES):
            try:
                # Validate architecture field against schema
                ArchitectureModel.model_validate(example["architecture"])
            except ValidationError as e:
                pytest.fail(
                    f"Few-shot example {i+1} ('{example['user_description']}') "
                    f"is INVALID against ArchitectureModel schema:\n{str(e)}\n\n"
                    f"This means the schema changed but examples were not updated. "
                    f"Update FEW_SHOT_EXAMPLES in generation_routes.py to fix."
                )


class TestAdditionalErrorPaths:
    """Test comprehensive error paths: API failures, malformed responses, missing fields."""
    
    def test_gemini_api_failure_502(self, monkeypatch):
        """Gemini API raising exception should return 502."""
        from unittest.mock import AsyncMock, MagicMock
        from sketchos_backend import generation_routes
        
        # Mock genai to raise exception
        async def failing_call(*args, **kwargs):
            raise Exception("Gemini API quota exceeded")
        
        fake_model = MagicMock()
        fake_model.generate_content_async = AsyncMock(side_effect=failing_call)
        
        fake_genai = MagicMock()
        fake_genai.GenerativeModel.return_value = fake_model
        fake_genai.configure = MagicMock()
        
        import sys
        sys.modules['google.generativeai'] = fake_genai
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")
        
        import importlib
        importlib.reload(generation_routes)
        
        client = TestClient(app)
        response = client.post(
            "/generate-geometry",
            json={"image": SAMPLE_PNG_BASE64}
        )
        
        assert response.status_code == 502
        detail = response.json()["detail"]
        assert "error" in detail
        assert "Gemini API" in detail["error"]
    
    def test_missing_required_field_422(self, monkeypatch):
        """Pass 2 returning JSON without required fields should trigger 422 after retry."""
        from unittest.mock import AsyncMock, MagicMock
        from sketchos_backend import generation_routes
        
        # Mock Pass 1 success
        morphology_response = MagicMock(text="Simple wall")
        
        # Mock Pass 2 with missing fields (both attempts)
        invalid_json = {"walls": []}  # Missing floors, openings, volumes, relationships
        invalid_response = MagicMock(text=json.dumps(invalid_json))
        
        # Return morphology once, then invalid JSON twice (first attempt + retry)
        fake_responses = [
            morphology_response,
            invalid_response,
            invalid_response
        ]
        
        fake_model = MagicMock()
        fake_model.generate_content_async = AsyncMock(side_effect=fake_responses)
        
        fake_genai = MagicMock()
        fake_genai.GenerativeModel.return_value = fake_model
        fake_genai.configure = MagicMock()
        
        import sys
        sys.modules['google.generativeai'] = fake_genai
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")
        
        import importlib
        importlib.reload(generation_routes)
        
        client = TestClient(app)
        response = client.post(
            "/generate-geometry",
            json={"image": SAMPLE_PNG_BASE64}
        )
        
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert "error" in detail
        assert "Validation failed" in detail["error"]


class TestConcurrency:
    """Test concurrent request handling with AsyncIO lock serialization."""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, monkeypatch):
        """5 parallel requests should serialize Blender calls via AsyncIO lock.
        
        This test proves:
        1. Multiple concurrent requests can be processed
        2. Blender execution is serialized (lock prevents concurrent MCP calls)
        3. All requests complete successfully without race conditions
        """
        from unittest.mock import AsyncMock, MagicMock, patch
        from sketchos_backend import generation_routes
        import time
        
        # Track execution order
        execution_times = []
        
        # Mock Pass 1 response
        morphology_text = "L-shaped plan"
        
        # Mock Pass 2 response (valid ArchitectureModel)
        valid_arch_json = {
            "walls": [],
            "floors": [],
            "openings": [],
            "volumes": [],
            "relationships": []
        }
        
        # Mock genai - need separate responses for each request (2 calls per request: Pass1 + Pass2)
        fake_model = MagicMock()
        fake_model.generate_content_async = AsyncMock(side_effect=[
            MagicMock(text=morphology_text),
            MagicMock(text=json.dumps(valid_arch_json)),
            MagicMock(text=morphology_text),
            MagicMock(text=json.dumps(valid_arch_json)),
            MagicMock(text=morphology_text),
            MagicMock(text=json.dumps(valid_arch_json)),
            MagicMock(text=morphology_text),
            MagicMock(text=json.dumps(valid_arch_json)),
            MagicMock(text=morphology_text),
            MagicMock(text=json.dumps(valid_arch_json)),
        ])
        
        fake_genai = MagicMock()
        fake_genai.GenerativeModel.return_value = fake_model
        fake_genai.configure = MagicMock()
        
        import sys
        sys.modules['google.generativeai'] = fake_genai
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")
        
        # Mock Blender with delay to make serialization visible
        async def slow_blender(*args, **kwargs):
            start = time.time()
            await asyncio.sleep(0.05)  # 50ms delay
            end = time.time()
            execution_times.append((start, end))
            return "Blender OK"
        
        mock_generate = MagicMock(return_value="bpy.ops.mesh...")
        mock_client = MagicMock()
        mock_client.execute = AsyncMock(side_effect=slow_blender)
        mock_client_class = MagicMock(return_value=mock_client)
        
        with patch('sketchos_backend.blender_client.generate_blender_code', mock_generate):
            with patch('sketchos_backend.blender_client.BlenderMCPClient', mock_client_class):
                import importlib
                importlib.reload(generation_routes)
                
                # Use FastAPI's TestClient but run requests via async tasks
                from sketchos_backend.main import app as fastapi_app
                
                # Import ASGI transport for httpx
                from httpx import ASGITransport, AsyncClient
                
                # Create async client with ASGI transport
                transport = ASGITransport(app=fastapi_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    # Launch 5 concurrent requests
                    tasks = [
                        client.post("/generate-geometry", json={"image": SAMPLE_PNG_BASE64})
                        for _ in range(5)
                    ]
                    responses = await asyncio.gather(*tasks)
                
                # All requests should succeed
                for response in responses:
                    assert response.status_code == 200
                    data = response.json()
                    assert "architecture" in data
                
                # Verify serialization: execution windows should NOT overlap
                # (each start time should be after the previous end time)
                assert len(execution_times) == 5, f"Expected 5 Blender executions, got {len(execution_times)}"
                execution_times.sort()
                for i in range(1, len(execution_times)):
                    prev_start, prev_end = execution_times[i-1]
                    curr_start, curr_end = execution_times[i]
                    # Current should start after previous ended (allowing small margin for timing jitter)
                    assert curr_start >= prev_end - 0.01, \
                        f"Blender calls overlapped: call {i-1} ended at {prev_end:.3f}, call {i} started at {curr_start:.3f}"

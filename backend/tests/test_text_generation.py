"""Endpoint + prompt-builder tests for the text-to-architecture path.

These tests verify POST /generate-from-text and its natural-language prompt
builder (``_build_text_prompt``) with a fully mocked Gemini SDK and Blender
client. No real API calls, no real Blender execution.

Mock hygiene (see PR #1 apply-progress): ``_pass2_schema_json`` binds ``genai``
via ``import google.generativeai as genai``. That resolves through the parent
``google`` package attribute, NOT ``sys.modules``, so a real SDK import would
silently defeat a ``sys.modules`` patch. We therefore patch
``google.generativeai`` directly on the parent ``google`` package and reload the
routes module to rebind the import.
"""

from __future__ import annotations

import importlib
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from sketchos_backend.main import app


# Minimal schema-valid ArchitectureModel JSON reused by the mock Pass 2.
VALID_ARCH_JSON: dict[str, Any] = {
    "walls": [
        {
            "id": "w1",
            "start": {"x": 0.0, "y": 0.0, "z": 0.0},
            "end": {"x": 5.0, "y": 0.0, "z": 0.0},
            "height": 3.0,
            "thickness": 0.3,
        }
    ],
    "floors": [
        {
            "id": "f1",
            "outline": [
                {"x": 0.0, "y": 0.0, "z": 0.0},
                {"x": 5.0, "y": 0.0, "z": 0.0},
                {"x": 5.0, "y": 4.0, "z": 0.0},
                {"x": 0.0, "y": 4.0, "z": 0.0},
            ],
            "thickness": 0.2,
            "elevation": 0.0,
        }
    ],
    "openings": [],
    "volumes": [],
    "relationships": [],
}

# A Pass-2 payload that fails validation: walls/floors present but openings,
# volumes, relationships omitted (extra="forbid" still accepts missing lists —
# this shape fails because required list fields are absent).
INVALID_ARCH_JSON: dict[str, Any] = {
    "walls": [
        {
            "id": "w1",
            "start": {"x": 0.0, "y": 0.0, "z": 0.0},
            "end": {"x": 5.0, "y": 0.0, "z": 0.0},
            "height": 3.0,
            "thickness": 0.3,
        }
    ],
    "floors": [],
}


def _patch_genai_and_blender(
    monkeypatch: pytest.MonkeyPatch,
    *,
    responses: list[Any],
    key: str = "test-key",
) -> None:
    """Patch the parent ``google`` package's ``generativeai`` attribute and the
    Blender client, then reload ``generation_routes`` so the local ``genai``
    import rebinds to the fake.

    ``responses`` is a list of values returned by successive
    ``generate_content_async`` calls (each with a ``.text`` attribute).
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    fake_model = MagicMock()
    fake_model.generate_content_async = AsyncMock(side_effect=responses)

    fake_genai = MagicMock()
    fake_genai.GenerativeModel.return_value = fake_model
    fake_genai.configure = MagicMock()

    import google

    # Patch both the parent-package attribute (what ``import google.generativeai
    # as genai`` resolves through) and sys.modules (belt and suspenders).
    monkeypatch.setattr(google, "generativeai", fake_genai, raising=False)
    import sys

    monkeypatch.setitem(sys.modules, "google.generativeai", fake_genai)

    # Blender client mocks.
    mock_generate = MagicMock(return_value="bpy.ops.mesh.primitive_cube_add()")
    mock_client = MagicMock()
    mock_client.execute = AsyncMock(return_value="Blender execution completed successfully")
    mock_client_class = MagicMock(return_value=mock_client)
    monkeypatch.setattr(
        "sketchos_backend.blender_client.generate_blender_code", mock_generate
    )
    monkeypatch.setattr(
        "sketchos_backend.blender_client.BlenderMCPClient", mock_client_class
    )

    monkeypatch.setenv("GOOGLE_API_KEY", key)

    from sketchos_backend import generation_routes

    importlib.reload(generation_routes)

    # Store the fake genai on the monkeypatch context so tests can assert on it.
    monkeypatch.fake_genai = fake_genai


def _ok_response() -> Any:
    """A MagicMock whose ``.text`` holds a valid ArchitectureModel JSON string."""
    from unittest.mock import MagicMock

    return MagicMock(text=json.dumps(VALID_ARCH_JSON))


class TestGenerateFromTextEndpoint:
    """POST /generate-from-text integration tests (mocked Gemini + Blender)."""

    def test_valid_prompt_returns_architecture(self, monkeypatch):
        """A non-empty prompt with a resolvable key returns 200 + architecture."""
        _patch_genai_and_blender(monkeypatch, responses=[_ok_response()])

        client = TestClient(app)
        response = client.post("/generate-from-text", json={"prompt": "make me a building"})

        assert response.status_code == 200
        data = response.json()
        assert "architecture" in data
        assert "walls" in data["architecture"]
        assert "floors" in data["architecture"]

    def test_bare_prompt_applies_defaults(self, monkeypatch):
        """A dimension-less prompt still produces a valid model (defaults directive)."""
        _patch_genai_and_blender(monkeypatch, responses=[_ok_response()])

        client = TestClient(app)
        response = client.post("/generate-from-text", json={"prompt": "make me a building"})

        assert response.status_code == 200
        assert "architecture" in response.json()

    def test_empty_prompt_returns_400(self, monkeypatch):
        """An empty prompt is rejected with 400 before any Gemini call."""
        _patch_genai_and_blender(monkeypatch, responses=[_ok_response()])

        client = TestClient(app)
        response = client.post("/generate-from-text", json={"prompt": ""})

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "error" in detail

    def test_missing_key_returns_503(self, monkeypatch):
        """Neither header nor env key resolves → 503."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        client = TestClient(app)
        response = client.post("/generate-from-text", json={"prompt": "a building"})

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert "Provider unavailable" in detail["error"]

    def test_header_key_drives_gemini_call(self, monkeypatch):
        """The X-Gemini-Api-Key header value reaches genai.configure."""
        monkeypatch.setenv("GOOGLE_API_KEY", "env-key")
        _patch_genai_and_blender(monkeypatch, responses=[_ok_response()], key="env-key")

        client = TestClient(app)
        response = client.post(
            "/generate-from-text",
            json={"prompt": "a building"},
            headers={"X-Gemini-Api-Key": "header-key"},
        )

        assert response.status_code == 200
        configured_keys = [
            call.kwargs.get("api_key")
            for call in monkeypatch.fake_genai.configure.call_args_list
        ]
        assert "header-key" in configured_keys

    def test_gemini_failure_returns_502(self, monkeypatch):
        """Gemini raising → 502, never 500."""

        def failing_call(*args, **kwargs):
            raise RuntimeError("Gemini API quota exceeded")

        from unittest.mock import MagicMock

        resp = MagicMock()
        resp.generate_content_async = MagicMock(side_effect=failing_call)
        _patch_genai_and_blender(monkeypatch, responses=[resp])

        client = TestClient(app)
        response = client.post("/generate-from-text", json={"prompt": "a building"})

        assert response.status_code == 502
        detail = response.json()["detail"]
        assert "error" in detail

    def test_validation_failure_returns_422(self, monkeypatch):
        """Both Pass-2 attempts invalid → 422 after retry."""
        from unittest.mock import MagicMock

        invalid = MagicMock(text=json.dumps(INVALID_ARCH_JSON))
        _patch_genai_and_blender(monkeypatch, responses=[invalid, invalid])

        client = TestClient(app)
        response = client.post("/generate-from-text", json={"prompt": "a building"})

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert "Validation failed" in detail["error"]

    def test_retry_succeeds_after_first_failure(self, monkeypatch):
        """First Pass-2 attempt invalid, retry valid → 200."""
        from unittest.mock import MagicMock

        invalid = MagicMock(text=json.dumps(INVALID_ARCH_JSON))
        _patch_genai_and_blender(monkeypatch, responses=[invalid, _ok_response()])

        client = TestClient(app)
        response = client.post("/generate-from-text", json={"prompt": "a building"})

        assert response.status_code == 200
        assert "architecture" in response.json()


class TestBuildTextPrompt:
    """Unit tests for the natural-language prompt builder."""

    def test_includes_defaults_directive(self, monkeypatch):
        """The text prompt must inject the defaults directive."""
        monkeypatch.delenv("SKETCHOS_DEFAULT_WALL_HEIGHT", raising=False)
        monkeypatch.delenv("SKETCHOS_DEFAULT_WALL_THICKNESS", raising=False)
        monkeypatch.delenv("SKETCHOS_DEFAULT_FLOOR_THICKNESS", raising=False)
        monkeypatch.delenv("SKETCHOS_DEFAULT_FLOOR_TO_FLOOR_HEIGHT", raising=False)

        from sketchos_backend.generation_routes import _build_text_prompt

        prompt = _build_text_prompt("make me a building")

        assert "wall height 3.0 m" in prompt
        assert "wall thickness 0.3 m" in prompt
        assert "floor thickness 0.2 m" in prompt

    def test_excludes_morphological_analysis_wording(self, monkeypatch):
        """The text path must NOT reuse the image-oriented wording."""
        from sketchos_backend.generation_routes import _build_text_prompt

        prompt = _build_text_prompt("make me a building")

        assert "morphological analysis" not in prompt.lower()

    def test_includes_few_shot_examples(self, monkeypatch):
        """Few-shot examples must be rendered into the text prompt."""
        from sketchos_backend.generation_routes import _build_text_prompt

        prompt = _build_text_prompt("make me a building")

        assert "Example 1:" in prompt
        assert "Example 2:" in prompt

    def test_embeds_user_prompt_and_retry_error(self, monkeypatch):
        """The user description and retry feedback must both appear."""
        from sketchos_backend.generation_routes import _build_text_prompt

        prompt = _build_text_prompt("two parallel walls", retry_error="wall height must be > 0")

        assert "two parallel walls" in prompt
        assert "wall height must be > 0" in prompt

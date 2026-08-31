"""Unit tests for the env-overridable defaults layer (defaults.py).

These defaults are injected into text-to-architecture prompts so dimension-less
requests still produce a schema-valid model. They MUST be env-overridable and
kept distinct from FEW_SHOT_EXAMPLES (validated schema snippets).
"""

from __future__ import annotations

from sketchos_backend.defaults import DefaultParams, render_defaults_directive

_ENV_VARS = (
    "SKETCHOS_DEFAULT_WALL_HEIGHT",
    "SKETCHOS_DEFAULT_WALL_THICKNESS",
    "SKETCHOS_DEFAULT_FLOOR_THICKNESS",
    "SKETCHOS_DEFAULT_FLOOR_TO_FLOOR_HEIGHT",
)


def _clear_env(monkeypatch) -> None:
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)


class TestDefaultParams:
    def test_literal_fallbacks(self, monkeypatch):
        """DefaultParams() yields the spec defaults when no env vars are set."""
        _clear_env(monkeypatch)

        p = DefaultParams()

        assert p.wall_height == 3.0
        assert p.wall_thickness == 0.3
        assert p.floor_thickness == 0.2
        assert p.floor_to_floor_height == 3.0

    def test_env_override_isolated(self, monkeypatch):
        """Env vars override individual fields without affecting the others."""
        _clear_env(monkeypatch)
        monkeypatch.setenv("SKETCHOS_DEFAULT_WALL_HEIGHT", "2.6")
        monkeypatch.setenv("SKETCHOS_DEFAULT_WALL_THICKNESS", "0.2")

        p = DefaultParams.from_env()

        assert p.wall_height == 2.6
        assert p.wall_thickness == 0.2
        # Untouched fields retain their literal fallbacks.
        assert p.floor_thickness == 0.2
        assert p.floor_to_floor_height == 3.0


class TestRenderDefaultsDirective:
    def test_emits_every_default(self, monkeypatch):
        """The directive must serialize each default dimension."""
        _clear_env(monkeypatch)

        directive = render_defaults_directive()

        assert "wall height 3.0 m" in directive
        assert "wall thickness 0.3 m" in directive
        assert "floor thickness 0.2 m" in directive
        assert "floor-to-floor height 3.0 m" in directive

    def test_reflects_env_override(self, monkeypatch):
        """The directive must reflect overrides, not hardcoded values."""
        _clear_env(monkeypatch)
        monkeypatch.setenv("SKETCHOS_DEFAULT_WALL_HEIGHT", "2.6")

        directive = render_defaults_directive()

        assert "wall height 2.6 m" in directive

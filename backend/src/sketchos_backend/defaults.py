"""Environment-overridable default architectural dimensions.

These defaults are injected into text-to-architecture prompts so dimension-less
requests still produce a schema-valid model. They are intentionally distinct
from ``FEW_SHOT_EXAMPLES`` (validated schema snippets in ``generation_routes.py``):
the examples bias the model toward concrete shapes, while these defaults supply
missing measurements so validation can still succeed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DefaultParams:
    """Default architectural dimensions in meters.

    Literal fallbacks live here; each field is overridable via the
    corresponding ``SKETCHOS_DEFAULT_*`` environment variable.
    """

    wall_height: float = 3.0
    wall_thickness: float = 0.3
    floor_thickness: float = 0.2
    floor_to_floor_height: float = 3.0

    @classmethod
    def from_env(cls) -> "DefaultParams":
        """Build params from ``SKETCHOS_DEFAULT_*`` env vars, with literal fallbacks."""
        return cls(
            wall_height=_env_float("SKETCHOS_DEFAULT_WALL_HEIGHT", 3.0),
            wall_thickness=_env_float("SKETCHOS_DEFAULT_WALL_THICKNESS", 0.3),
            floor_thickness=_env_float("SKETCHOS_DEFAULT_FLOOR_THICKNESS", 0.2),
            floor_to_floor_height=_env_float("SKETCHOS_DEFAULT_FLOOR_TO_FLOOR_HEIGHT", 3.0),
        )


def _env_float(name: str, fallback: float) -> float:
    """Read a float env var, returning ``fallback`` when unset or malformed."""
    raw = os.getenv(name)
    if raw is None or raw == "":
        return fallback
    try:
        return float(raw)
    except ValueError:
        return fallback


def render_defaults_directive(params: DefaultParams | None = None) -> str:
    """Serialize the defaults into a natural-language instruction fragment.

    The fragment is prepended to text-to-architecture prompts so a bare prompt
    still yields valid, non-zero dimensions.
    """
    p = params if params is not None else DefaultParams.from_env()
    return (
        "If the user's description omits dimensions, apply these defaults: "
        f"wall height {p.wall_height} m, "
        f"wall thickness {p.wall_thickness} m, "
        f"floor thickness {p.floor_thickness} m, "
        f"floor-to-floor height {p.floor_to_floor_height} m."
    )


def render_unit_convention_instruction() -> str:
    """Serialize the canonical-unit rule into an instruction fragment.

    Meters are the canonical DSL unit (spec REQ-05). This directive tells the
    model to normalize every non-meter dimension to meters before emitting
    JSON, so the prompt content deterministically encodes the unit convention
    instead of leaving it to model interpretation. The conversion factors are
    the canonical SI convention, not user data — nothing here is hardcoded
    per-request.
    """
    return (
        "All dimensions MUST be expressed in meters, the canonical DSL unit. "
        "Convert other units to meters before output: centimeters → divide by "
        "100 (e.g. 20cm → 0.2 m), millimeters → divide by 1000, feet → "
        "multiply by 0.3048, inches → multiply by 0.0254. A dimension given "
        "without a unit is already in meters."
    )

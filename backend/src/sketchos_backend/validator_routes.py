"""HTTP endpoints wrapping the Go validator over an asyncio subprocess.

Three endpoints, all backed by :class:`ValidatorClient` (list-form argv, never
``shell=True``):

- ``GET /extract-rules`` exposes the validator's ``-print-defaults`` thresholds.
- ``POST /validate-geometry`` validates uploaded ``.obj`` bytes.
- ``POST /autocorrect`` re-codegens corrected geometry through the existing
  ``build_architecture``/Blender path and re-validates it (the Go binary never
  edits meshes).

Status mapping is centralized here: spawn failure → 503, timeout → 504, parse
error (exit 2) → 422, violations/pass → 200.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from sketchos_backend.arch_dsl import ArchitectureModel
from sketchos_backend.blender_client import BlenderMCPClient
from sketchos_backend.server import build_architecture
from sketchos_backend.validator_client import (
    ValidatorClient,
    ValidatorSpawnError,
    ValidatorTimeoutError,
)

router = APIRouter()

#: Temp dir prefix shared with the client for autocorrect export staging.
_TEMP_DIR_PREFIX = "sketchos-validator-"

#: The four per-request threshold keys (wire shape shared by both endpoints).
_THRESHOLD_KEYS = ("min_height", "max_height", "min_thickness", "max_thickness")


class Thresholds(BaseModel):
    """Optional per-request validator thresholds.

    Each bound is optional (``None`` = absent) and, when present, must be finite
    and non-negative; ``0`` means "unenforced". ``extra="forbid"`` rejects
    unknown keys; the after-validator enforces ``min ≤ max`` per paired bound.
    A ``0`` bound is "unenforced" (not a real bound), so it is never compared —
    ``min=3`` with ``max=0`` is valid ("no upper limit").
    """

    model_config = ConfigDict(extra="forbid")

    min_height: float | None = Field(None, ge=0, allow_inf_nan=False)
    max_height: float | None = Field(None, ge=0, allow_inf_nan=False)
    min_thickness: float | None = Field(None, ge=0, allow_inf_nan=False)
    max_thickness: float | None = Field(None, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def _bounds(self) -> "Thresholds":
        if self.min_height and self.max_height and self.min_height > self.max_height:
            raise ValueError("min_height must be ≤ max_height")
        if self.min_thickness and self.max_thickness and self.min_thickness > self.max_thickness:
            raise ValueError("min_thickness must be ≤ max_thickness")
        return self


def _make_client() -> ValidatorClient:
    """Build the default validator subprocess client."""
    return ValidatorClient()


def get_validator_client() -> ValidatorClient:
    """FastAPI dependency yielding the validator client (injectable in tests)."""
    return _make_client()


def correct_model(model: ArchitectureModel, violations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply exact-threshold corrections to ``model`` for wall violations.

    Each violation's ``object`` names a Blender object ``wall_<id>`` (matching
    ``blender_client``'s ``_add_cube("wall_"+wall.id, …)``); the id maps back to
    the DSL wall. The violating dimension is set to the violation ``threshold``
    (exact, no margin — min/max checks pass on equality). Unenforced bounds
    (``threshold == 0``) never produce a violation, so no zero-target
    correction. Returns the list of applied fixes.
    """
    walls_by_id = {wall.id: wall for wall in model.walls}
    fixes: list[dict[str, Any]] = []
    for violation in violations:
        obj = violation.get("object", "")
        if not obj.startswith("wall_"):
            continue
        wall = walls_by_id.get(obj[len("wall_"):])
        if wall is None:
            continue

        rule = violation.get("type", "")
        dimension: str | None
        if rule in ("wall_height_min", "wall_height_max"):
            dimension = "height"
        elif rule in ("wall_thickness_min", "wall_thickness_max"):
            dimension = "thickness"
        else:
            continue

        threshold = float(violation.get("threshold", 0))
        before = getattr(wall, dimension)
        setattr(wall, dimension, threshold)
        fixes.append(
            {
                "wall_id": wall.id,
                "rule": rule,
                "dimension": dimension,
                "from": before,
                "to": threshold,
            }
        )
    return fixes


async def _resolve_thresholds(
    client: ValidatorClient,
    raw: dict[str, Any] | None,
) -> dict[str, float]:
    """Resolve the effective thresholds for a request.

    When no threshold is supplied (``raw`` is empty/``None``), fall back to the
    validator's ``-print-defaults`` rules. Otherwise validate the supplied set
    through :class:`Thresholds` (raising :class:`ValidationError` on negative,
    non-finite, or min > max bounds) and merge it over the defaults so every
    bound is present for ``client.validate``. Invalid thresholds raise BEFORE
    any Go invocation (``extract_rules``/``validate``).
    """
    if not raw:
        return await client.extract_rules()
    model = Thresholds.model_validate(raw)
    resolved = dict(await client.extract_rules())
    for key in _THRESHOLD_KEYS:
        value = getattr(model, key)
        if value is not None:
            resolved[key] = value
    return resolved


async def _validate_model(
    model: ArchitectureModel,
    thresholds: dict[str, float],
    client: ValidatorClient,
) -> Any:
    """Build ``model`` through Blender, export to a temp ``.obj``, and validate it."""
    blender = BlenderMCPClient()
    with tempfile.TemporaryDirectory(prefix=_TEMP_DIR_PREFIX) as tmp_dir:
        obj_path = os.path.join(tmp_dir, "model.obj")
        out = await build_architecture(model.model_dump(), blender, export_path=obj_path)
        if out.startswith("Blender error:"):
            raise HTTPException(status_code=502, detail=out)
        with open(obj_path, "rb") as fh:
            return await client.validate(fh.read(), thresholds)


@router.get("/extract-rules")
async def extract_rules(
    client: ValidatorClient = Depends(get_validator_client),
) -> dict[str, float]:
    """Return the normativa thresholds printed by ``validator-go -print-defaults``."""
    try:
        return await client.extract_rules()
    except ValidatorSpawnError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValidatorTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc


@router.post("/validate-geometry")
async def validate_geometry(
    file: UploadFile = File(...),
    min_height: float | None = Form(None),
    max_height: float | None = Form(None),
    min_thickness: float | None = Form(None),
    max_thickness: float | None = Form(None),
    client: ValidatorClient = Depends(get_validator_client),
) -> dict[str, Any]:
    """Validate uploaded ``.obj`` bytes against optional per-request thresholds.

    Thresholds are supplied as four optional multipart form fields; when all
    are omitted, the validator's ``-print-defaults`` rules are used. Invalid
    thresholds (negative, non-finite, min > max) are rejected with 422 before
    the Go binary is invoked.
    """
    obj_bytes = await file.read()
    raw = {
        "min_height": min_height,
        "max_height": max_height,
        "min_thickness": min_thickness,
        "max_thickness": max_thickness,
    }
    raw = {key: value for key, value in raw.items() if value is not None}
    try:
        thresholds = await _resolve_thresholds(client, raw)
        result = await client.validate(obj_bytes, thresholds)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid thresholds: {exc}") from exc
    except ValidatorSpawnError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValidatorTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc

    if result.status == "parse_error":
        detail = result.stderr.strip() or "validator could not parse the .obj file"
        raise HTTPException(status_code=422, detail=detail)

    return {"status": result.status, "report": result.report}


@router.post("/autocorrect")
async def autocorrect(
    payload: dict[str, Any],
    client: ValidatorClient = Depends(get_validator_client),
) -> dict[str, Any]:
    """Re-codegen corrected geometry and re-validate it (single-pass correction).

    The optional ``thresholds`` key is popped BEFORE ``ArchitectureModel``
    validation (``extra="forbid"`` would otherwise reject it); the SAME resolved
    thresholds apply to both re-validate passes. Absent thresholds fall back to
    ``extract_rules()``.
    """
    thresholds_raw = payload.pop("thresholds", None)
    try:
        model = ArchitectureModel.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid DSL: {exc}") from exc

    try:
        thresholds = await _resolve_thresholds(client, thresholds_raw)
        result = await _validate_model(model, thresholds, client)
        fixes: list[dict[str, Any]] = []
        if result.status == "violations":
            fixes = correct_model(model, result.report["violations"])
            result = await _validate_model(model, thresholds, client)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid thresholds: {exc}") from exc
    except ValidatorSpawnError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValidatorTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc

    if result.status == "parse_error":
        detail = result.stderr.strip() or "validator could not parse the generated .obj file"
        raise HTTPException(status_code=422, detail=detail)

    return {"status": result.status, "report": result.report, "fixes": fixes}

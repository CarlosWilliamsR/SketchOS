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

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import ValidationError

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
    client: ValidatorClient = Depends(get_validator_client),
) -> dict[str, Any]:
    """Validate uploaded ``.obj`` bytes and return the Go JSON report + status."""
    obj_bytes = await file.read()
    try:
        thresholds = await client.extract_rules()
        result = await client.validate(obj_bytes, thresholds)
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

    The DSL payload is validated, built through Blender, exported, and validated
    by Go. On violations the dimensions are corrected to their exact thresholds
    and the model is re-codegen'd and re-validated once.
    """
    try:
        model = ArchitectureModel.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid DSL: {exc}") from exc

    try:
        thresholds = await client.extract_rules()
        result = await _validate_model(model, thresholds, client)
        fixes: list[dict[str, Any]] = []
        if result.status == "violations":
            fixes = correct_model(model, result.report["violations"])
            result = await _validate_model(model, thresholds, client)
    except ValidatorSpawnError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValidatorTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc

    if result.status == "parse_error":
        detail = result.stderr.strip() or "validator could not parse the generated .obj file"
        raise HTTPException(status_code=422, detail=detail)

    return {"status": result.status, "report": result.report, "fixes": fixes}

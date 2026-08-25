"""Endpoint contract tests for ``validator_routes`` (Slice 3 / PR 3).

These tests exercise the three HTTP endpoints against an injected FAKE
:class:`ValidatorClient` — no real Go binary, no Blender, no subprocess. The
fake returns canned :class:`ValidationResult` objects so the status mapping
(0 → pass, 1 → violations, 2 → parse error, spawn → 503, timeout → 504) and the
autocorrect re-validate loop can be asserted deterministically.

Key gotcha: with ``app.include_router``, the validator routes appear in
``app.openapi()['paths']`` but NOT as individual ``app.routes`` entries (FastAPI
registers an ``_IncludedRouter`` node instead). The "endpoints discoverable"
assertion therefore inspects the OpenAPI paths, never an ``app.routes`` scan.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sketchos_backend import validator_routes
from sketchos_backend.main import app
from sketchos_backend.validator_client import (
    ValidationResult,
    ValidatorSpawnError,
    ValidatorTimeoutError,
)


DEFAULT_THRESHOLDS = {
    "min_height": 2,
    "max_height": 0,
    "min_thickness": 0.1,
    "max_thickness": 0,
}

PASS_REPORT = {"aabb": {}, "objects": [], "violations": []}
VIOLATION_REPORT = {
    "aabb": {},
    "objects": [],
    "violations": [
        {
            "type": "wall_height_min",
            "object": "wall_w1",
            "measured": 1.5,
            "threshold": 2,
            "message": 'wall_height_min: object "wall_w1" measured 1.500 m, limit 2.000 m',
        }
    ],
}


def make_dsl_payload() -> dict:
    """A minimal valid DSL payload with one short wall (height 1.5 < min 2)."""
    return {
        "walls": [
            {
                "id": "w1",
                "start": {"x": 0, "y": 0, "z": 0},
                "end": {"x": 5, "y": 0, "z": 0},
                "height": 1.5,
                "thickness": 0.25,
            }
        ],
        "floors": [],
        "openings": [],
        "volumes": [],
        "relationships": [],
    }


class FakeValidatorClient:
    """In-memory stand-in for ``ValidatorClient`` (no binary, no subprocess)."""

    def __init__(
        self,
        rules: dict[str, float] | None = None,
        validate_results: list[ValidationResult] | None = None,
        extract_error: Exception | None = None,
    ) -> None:
        self.rules = dict(rules or DEFAULT_THRESHOLDS)
        self.validate_results = list(validate_results or [])
        self.extract_error = extract_error
        self.extract_calls = 0
        self.validate_calls = 0
        self.validate_bytes: list[bytes] = []
        self.validate_thresholds: list[dict[str, float]] = []

    async def extract_rules(self) -> dict[str, float]:
        self.extract_calls += 1
        if self.extract_error is not None:
            raise self.extract_error
        return dict(self.rules)

    async def validate(
        self, obj_bytes: bytes, thresholds: dict[str, float]
    ) -> ValidationResult:
        self.validate_calls += 1
        self.validate_bytes.append(obj_bytes)
        self.validate_thresholds.append(thresholds)
        if self.validate_results:
            return self.validate_results.pop(0)
        return ValidationResult(
            status="pass", report=dict(PASS_REPORT), returncode=0, stderr=""
        )


@pytest.fixture
def client():
    """A TestClient whose validator dependency is overridden per-test."""
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def use_fake(fake: FakeValidatorClient) -> None:
    """Override the validator dependency to return ``fake``."""
    app.dependency_overrides[validator_routes.get_validator_client] = lambda: fake


async def fake_build_architecture(payload, blender, user_prompt="", export_path=""):
    """Stand-in for ``build_architecture``: write fake .obj bytes, return success."""
    if export_path:
        with open(export_path, "wb") as fh:
            fh.write(b"v 0 0 0\n")
    return "built"


# --------------------------------------------------------------------------- #
# Endpoint discoverability (OpenAPI paths, not an app.routes scan)
# --------------------------------------------------------------------------- #


def test_endpoints_discoverable_via_openapi():
    paths = app.openapi()["paths"]
    assert "/extract-rules" in paths
    assert "/validate-geometry" in paths
    assert "/autocorrect" in paths


def test_mcp_mount_preserved():
    mounted = [r.path for r in app.routes if getattr(r, "path", None) == "/mcp"]
    assert mounted == ["/mcp"]


# --------------------------------------------------------------------------- #
# GET /extract-rules
# --------------------------------------------------------------------------- #


def test_extract_rules_returns_thresholds(client):
    fake = FakeValidatorClient(rules=DEFAULT_THRESHOLDS)
    use_fake(fake)

    resp = client.get("/extract-rules")

    assert resp.status_code == 200
    assert resp.json() == DEFAULT_THRESHOLDS
    assert fake.extract_calls == 1


# --------------------------------------------------------------------------- #
# POST /validate-geometry
# --------------------------------------------------------------------------- #


def test_validate_geometry_pass(client):
    fake = FakeValidatorClient(validate_results=[])
    use_fake(fake)

    resp = client.post(
        "/validate-geometry",
        files={"file": ("m.obj", b"v 0 0 0\n", "text/plain")},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "pass"
    assert resp.json()["report"]["violations"] == []


def test_validate_geometry_violations_exit_1_is_not_an_error(client):
    violations = ValidationResult(
        status="violations", report=dict(VIOLATION_REPORT), returncode=1, stderr=""
    )
    fake = FakeValidatorClient(validate_results=[violations])
    use_fake(fake)

    resp = client.post(
        "/validate-geometry",
        files={"file": ("m.obj", b"v 0 0 0\n", "text/plain")},
    )

    # exit 1 (violations) is a normal 200, NOT an error.
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "violations"
    assert body["report"]["violations"][0]["type"] == "wall_height_min"


def test_validate_geometry_parse_error_422(client):
    parse_error = ValidationResult(
        status="parse_error", report=None, returncode=2, stderr="obj: bad vertex\n"
    )
    fake = FakeValidatorClient(validate_results=[parse_error])
    use_fake(fake)

    resp = client.post(
        "/validate-geometry",
        files={"file": ("m.obj", b"not an obj\n", "text/plain")},
    )

    assert resp.status_code == 422
    assert "bad vertex" in resp.json()["detail"]


def test_validate_geometry_spawn_fail_503(client):
    fake = FakeValidatorClient(
        extract_error=ValidatorSpawnError(
            "validator binary not found (set VALIDATOR_GO_BIN or run make install)"
        )
    )
    use_fake(fake)

    resp = client.post(
        "/validate-geometry",
        files={"file": ("m.obj", b"v 0 0 0\n", "text/plain")},
    )

    assert resp.status_code == 503
    assert "binary not found" in resp.json()["detail"]


def test_validate_geometry_timeout_504(client):
    fake = FakeValidatorClient(
        extract_error=ValidatorTimeoutError("validator timed out after 30.0s")
    )
    use_fake(fake)

    resp = client.post(
        "/validate-geometry",
        files={"file": ("m.obj", b"v 0 0 0\n", "text/plain")},
    )

    assert resp.status_code == 504
    assert "timed out" in resp.json()["detail"]


# --------------------------------------------------------------------------- #
# POST /autocorrect
# --------------------------------------------------------------------------- #


def test_autocorrect_revalidates_clean(client, monkeypatch):
    monkeypatch.setattr(validator_routes, "build_architecture", fake_build_architecture)
    violations = ValidationResult(
        status="violations", report=dict(VIOLATION_REPORT), returncode=1, stderr=""
    )
    clean = ValidationResult(
        status="pass", report=dict(PASS_REPORT), returncode=0, stderr=""
    )
    fake = FakeValidatorClient(validate_results=[violations, clean])
    use_fake(fake)

    resp = client.post("/autocorrect", json=make_dsl_payload())

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pass"
    # The short wall (height 1.5 → threshold 2.0) produced one fix.
    assert len(body["fixes"]) == 1
    assert body["fixes"][0]["wall_id"] == "w1"
    assert body["fixes"][0]["dimension"] == "height"
    # One thresholds lookup + two validations (violations then clean re-validate).
    assert fake.extract_calls == 1
    assert fake.validate_calls == 2

"""Server tests: validation-before-execution, tool wiring, and transport containment."""

import asyncio

import pytest

from sketchos_backend import server
from sketchos_backend.blender_client import BlenderClientError, generate_blender_code
from sketchos_backend.server import build_architecture, mcp


class SpyClient:
    """A spy stand-in for ``BlenderMCPClient`` recording every ``execute`` call."""

    def __init__(self, result: str = "ok", error: Exception | None = None) -> None:
        self._result = result
        self._error = error
        self.calls: list[dict] = []

    async def execute(self, code: str, user_prompt: str = "") -> str:
        self.calls.append({"code": code, "user_prompt": user_prompt})
        if self._error is not None:
            raise self._error
        return self._result


def make_valid_payload() -> dict:
    """Return a fully valid ArchitecturalDSL payload as a plain dict."""
    return {
        "walls": [
            {
                "id": "w1",
                "start": {"x": 0, "y": 0, "z": 0},
                "end": {"x": 5, "y": 0, "z": 0},
                "height": 3,
                "thickness": 0.25,
            }
        ],
        "floors": [
            {
                "id": "f1",
                "outline": [
                    {"x": 0, "y": 0, "z": 0},
                    {"x": 5, "y": 0, "z": 0},
                    {"x": 5, "y": 5, "z": 0},
                    {"x": 0, "y": 5, "z": 0},
                ],
                "thickness": 0.2,
                "elevation": 0,
            }
        ],
        "openings": [
            {
                "id": "o1",
                "wall_id": "w1",
                "position": {"x": 2.5, "y": 0, "z": 1},
                "width": 1,
                "height": 2.1,
            }
        ],
        "volumes": [
            {"id": "v1", "origin": {"x": 0, "y": 0, "z": 0}, "size": {"x": 5, "y": 5, "z": 3}}
        ],
        "relationships": [],
    }


def make_invalid_payload() -> dict:
    """Return an invalid DSL payload (negative wall thickness)."""
    payload = make_valid_payload()
    payload["walls"][0]["thickness"] = -0.25
    return payload


# --------------------------------------------------------------------------- #
# Validation-before-execution (core function with an injected client)
# --------------------------------------------------------------------------- #


def test_invalid_dsl_does_not_call_execute():
    spy = SpyClient()
    out = asyncio.run(build_architecture(make_invalid_payload(), spy))

    assert out.startswith("Invalid DSL:")
    assert spy.calls == []


def test_valid_dsl_calls_execute_with_generated_code():
    payload = make_valid_payload()
    spy = SpyClient(result="geometry built")

    out = asyncio.run(build_architecture(payload, spy))

    assert out == "geometry built"
    assert len(spy.calls) == 1
    # The code passed to execute must be exactly the generated code for the model.
    from sketchos_backend.arch_dsl import ArchitectureModel

    model = ArchitectureModel.model_validate(payload)
    assert spy.calls[0]["code"] == generate_blender_code(model)
    assert spy.calls[0]["user_prompt"] == ""


def test_transport_failure_is_contained():
    spy = SpyClient(error=BlenderClientError("unreachable"))

    # Must NOT raise: the server returns an error string and keeps running.
    out = asyncio.run(build_architecture(make_valid_payload(), spy))

    assert out.startswith("Blender error:")
    assert "unreachable" in out


# --------------------------------------------------------------------------- #
# Export path forwarding (validation-before-execution holds regardless)
# --------------------------------------------------------------------------- #


def test_export_path_is_forwarded_to_codegen():
    spy = SpyClient(result="exported")
    out = asyncio.run(
        build_architecture(make_valid_payload(), spy, export_path="/tmp/out.obj")
    )

    assert out == "exported"
    assert len(spy.calls) == 1
    code = spy.calls[0]["code"]
    assert "wm.obj_export" in code
    assert "/tmp/out.obj" in code


def test_no_export_path_means_no_export():
    spy = SpyClient(result="built")
    out = asyncio.run(build_architecture(make_valid_payload(), spy))

    assert out == "built"
    assert len(spy.calls) == 1
    assert "wm.obj_export" not in spy.calls[0]["code"]


def test_empty_export_path_means_no_export():
    spy = SpyClient(result="built")
    out = asyncio.run(
        build_architecture(make_valid_payload(), spy, export_path="")
    )

    assert out == "built"
    assert len(spy.calls) == 1
    assert "wm.obj_export" not in spy.calls[0]["code"]


def test_invalid_dsl_ignores_export_path_and_does_not_call_execute():
    spy = SpyClient()
    out = asyncio.run(
        build_architecture(make_invalid_payload(), spy, export_path="/tmp/out.obj")
    )

    assert out.startswith("Invalid DSL:")
    assert spy.calls == []


# --------------------------------------------------------------------------- #
# Tool wiring
# --------------------------------------------------------------------------- #


def test_build_architecture_tool_registered():
    tools = asyncio.run(mcp.list_tools())
    names = [t.name for t in tools]
    assert "build_architecture" in names


def test_tool_end_to_end_with_spy_client(monkeypatch):
    spy = SpyClient(result="geometry built")
    monkeypatch.setattr(server, "_make_client", lambda: spy)

    res = asyncio.run(
        mcp.call_tool(
            "build_architecture",
            {"payload": make_valid_payload(), "user_prompt": "build a wall"},
        )
    )

    # call_tool returns (content_blocks, structured_result).
    assert res[1]["result"] == "geometry built"
    assert len(spy.calls) == 1
    assert spy.calls[0]["user_prompt"] == "build a wall"


def test_tool_invalid_dsl_never_calls_client(monkeypatch):
    spy = SpyClient()
    monkeypatch.setattr(server, "_make_client", lambda: spy)

    res = asyncio.run(
        mcp.call_tool("build_architecture", {"payload": make_invalid_payload()})
    )

    assert res[1]["result"].startswith("Invalid DSL:")
    assert spy.calls == []


def test_tool_forwards_export_path(monkeypatch):
    spy = SpyClient(result="exported")
    monkeypatch.setattr(server, "_make_client", lambda: spy)

    res = asyncio.run(
        mcp.call_tool(
            "build_architecture",
            {"payload": make_valid_payload(), "export_path": "/tmp/out.obj"},
        )
    )

    assert res[1]["result"] == "exported"
    assert len(spy.calls) == 1
    assert "wm.obj_export" in spy.calls[0]["code"]
    assert "/tmp/out.obj" in spy.calls[0]["code"]


# --------------------------------------------------------------------------- #
# FastAPI mount
# --------------------------------------------------------------------------- #


def test_main_mounts_streamable_http_surface():
    from sketchos_backend.main import app

    mounted = [r.path for r in app.routes if getattr(r, "path", None) == "/mcp"]
    assert mounted == ["/mcp"]


def test_streamable_http_app_is_importable_without_blender():
    # Building the ASGI app must not spawn a blender-mcp process.
    starlette_app = mcp.streamable_http_app()
    assert starlette_app is not None

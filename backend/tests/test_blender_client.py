"""Unit tests for blender_client: deterministic codegen + transport isolation."""

import asyncio
import math

import pytest

from sketchos_backend.arch_dsl import (
    ArchitectureModel,
    Floor,
    Opening,
    Vec3,
    Volume,
    Wall,
)
from sketchos_backend import blender_client as bc
from sketchos_backend.blender_client import (
    BlenderClientError,
    BlenderMCPClient,
    generate_blender_code,
)


def make_model() -> ArchitectureModel:
    """Return a fully valid model with one of each element type."""
    return ArchitectureModel(
        walls=[
            Wall(
                id="w1",
                start=Vec3(x=0, y=0, z=0),
                end=Vec3(x=5, y=0, z=0),
                height=3,
                thickness=0.25,
            )
        ],
        floors=[
            Floor(
                id="f1",
                outline=[
                    Vec3(x=0, y=0, z=0),
                    Vec3(x=5, y=0, z=0),
                    Vec3(x=5, y=5, z=0),
                    Vec3(x=0, y=5, z=0),
                ],
                thickness=0.2,
                elevation=0,
            )
        ],
        openings=[
            Opening(
                id="o1",
                wall_id="w1",
                position=Vec3(x=2.5, y=0, z=1),
                width=1,
                height=2.1,
            )
        ],
        volumes=[Volume(id="v1", origin=Vec3(x=0, y=0, z=0), size=Vec3(x=5, y=5, z=3))],
        relationships=[],
    )


# --------------------------------------------------------------------------- #
# Codegen
# --------------------------------------------------------------------------- #


def test_generate_emits_wall_floor_opening_volume_ops():
    code = generate_blender_code(make_model())
    assert "bpy.ops.mesh.primitive_cube_add" in code
    assert '_add_cube("wall_w1"' in code
    assert '_add_cube("floor_f1"' in code
    assert '_add_cube("cutter_o1"' in code
    assert '_add_cube("volume_v1"' in code
    assert '_boolean_difference("wall_w1", "cutter_o1", "opening_o1")' in code


def test_wall_geometry_exact():
    code = generate_blender_code(make_model())
    assert '_add_cube("wall_w1", (2.5, 0, 1.5), (5, 0.25, 3), 0)' in code


def test_floor_geometry_exact():
    code = generate_blender_code(make_model())
    assert '_add_cube("floor_f1", (2.5, 2.5, 0.1), (5, 5, 0.2), 0)' in code


def test_opening_cutout_overextends_wall_thickness():
    code = generate_blender_code(make_model())
    # Cutter depth = wall thickness (0.25) + OPENING_OVEREXTEND (0.2); z-centered.
    assert '_add_cube("cutter_o1", (2.5, 0, 2.05), (1, 0.45, 2.1), 0)' in code
    assert '_add_cube("opening_o1"' not in code


def test_volume_geometry_exact():
    code = generate_blender_code(make_model())
    assert '_add_cube("volume_v1", (2.5, 2.5, 1.5), (5, 5, 3), 0)' in code


def test_opening_falls_back_to_default_depth_on_dangling_wall():
    model = ArchitectureModel(
        walls=[],
        floors=[],
        openings=[
            Opening(
                id="o2",
                wall_id="missing",
                position=Vec3(x=1, y=1, z=1),
                width=1,
                height=2,
            )
        ],
        volumes=[],
        relationships=[],
    )
    code = generate_blender_code(model)
    assert '_add_cube("opening_o2", (1, 1, 1), (1, 0.3, 2), 0)' in code


def test_codegen_is_deterministic():
    model = make_model()
    assert generate_blender_code(model) == generate_blender_code(model)


def test_empty_model_emits_only_header():
    model = ArchitectureModel(walls=[], floors=[], openings=[], volumes=[], relationships=[])
    code = generate_blender_code(model)
    assert code.startswith("import bpy\n")
    assert "wall_" not in code
    assert "floor_" not in code
    assert "opening_" not in code
    assert "volume_" not in code
    assert "primitive_cube_add" in code  # header still defines the helper


def make_angled_model() -> ArchitectureModel:
    """A single wall along dx=4, dy=3 with one opening (rotation atan2(3, 4))."""
    return ArchitectureModel(
        walls=[
            Wall(
                id="w1",
                start=Vec3(x=0, y=0, z=0),
                end=Vec3(x=4, y=3, z=0),
                height=3,
                thickness=0.25,
            )
        ],
        floors=[],
        openings=[
            Opening(
                id="o1",
                wall_id="w1",
                position=Vec3(x=2, y=1.5, z=1),
                width=1,
                height=2.1,
            )
        ],
        volumes=[],
        relationships=[],
    )


def test_angled_wall_cutout_rotated_to_wall_angle():
    code = generate_blender_code(make_angled_model())
    expected_angle = bc._fmt(math.atan2(3, 4))
    assert f'_add_cube("cutter_o1", (2, 1.5, 2.05), (1, 0.45, 2.1), {expected_angle})' in code
    assert '_boolean_difference("wall_w1", "cutter_o1", "opening_o1")' in code
    # Wall itself is also rotated to atan2(3, 4).
    assert f'_add_cube("wall_w1", (2, 1.5, 1.5), (5, 0.25, 3), {expected_angle})' in code


def test_export_emitted_after_cutout():
    code = generate_blender_code(make_model(), export_path="/tmp/out.obj")
    assert "bpy.ops.wm.obj_export" in code
    assert 'filepath="/tmp/out.obj"' in code
    boolean_idx = code.index("_boolean_difference")
    export_idx = code.index("bpy.ops.wm.obj_export")
    assert boolean_idx < export_idx


def test_no_export_by_default():
    code = generate_blender_code(make_model())
    assert "obj_export" not in code


# --------------------------------------------------------------------------- #
# Client — transport isolation
# --------------------------------------------------------------------------- #


class _FakeTextContent:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeToolResult:
    def __init__(self, *texts: str) -> None:
        self.content = [_FakeTextContent(t) for t in texts]


class _FakeSession:
    def __init__(self, result: _FakeToolResult) -> None:
        self._result = result
        self.called: dict = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def initialize(self) -> None:
        pass

    async def call_tool(self, name: str, arguments=None, **kwargs):
        self.called = {"name": name, "arguments": arguments}
        return self._result


class _FakeStdioContext:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return ("read", "write")

    async def __aexit__(self, *exc):
        return False


def test_execute_returns_tool_text(monkeypatch):
    session = _FakeSession(_FakeToolResult("ok"))
    monkeypatch.setattr(bc, "stdio_client", _FakeStdioContext)
    monkeypatch.setattr(bc, "ClientSession", lambda *a, **k: session)

    client = BlenderMCPClient()
    out = asyncio.run(client.execute("import bpy", user_prompt="build a wall"))

    assert out == "ok"
    assert session.called["name"] == "execute_blender_code"
    assert session.called["arguments"] == {"code": "import bpy", "user_prompt": "build a wall"}


def test_execute_transport_failure_is_contained(monkeypatch):
    def broken_stdio(*args, **kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(bc, "stdio_client", broken_stdio)

    client = BlenderMCPClient()
    with pytest.raises(BlenderClientError) as excinfo:
        asyncio.run(client.execute("import bpy"))

    assert "transport" in str(excinfo.value)
    assert "connection refused" in str(excinfo.value.__cause__)


def test_execute_blender_client_error_passes_through(monkeypatch):
    async def failing_execute(self, code, user_prompt):
        raise BlenderClientError("boom")

    monkeypatch.setattr(bc.BlenderMCPClient, "_execute_via_mcp", failing_execute)

    client = BlenderMCPClient()
    with pytest.raises(BlenderClientError) as excinfo:
        asyncio.run(client.execute("import bpy"))

    assert str(excinfo.value) == "boom"


def test_call_tool_text_joins_and_handles_empty():
    assert bc._call_tool_text(_FakeToolResult("first", "second")) == "first\nsecond"
    assert bc._call_tool_text(_FakeToolResult()) == ""

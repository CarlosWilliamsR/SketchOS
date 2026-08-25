"""Blender code generation and a transport-isolated Blender MCP client.

``generate_blender_code`` turns a validated ``ArchitectureModel`` into
deterministic Blender Python (bpy) source. ``BlenderMCPClient`` exposes a single
``execute`` method that calls ``blender-mcp``'s ``execute_blender_code`` over the
MCP stdio transport.

This module imports neither FastAPI nor FastMCP and does NOT validate the DSL
(the server validates first). Any transport/execution failure is raised as
``BlenderClientError`` so the backend can catch it and keep running.
"""

from __future__ import annotations

import json
import math
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult

from sketchos_backend import arch_macros
from sketchos_backend.arch_dsl import ArchitectureModel, Floor, Opening, Volume, Wall

#: Command used to spawn the ``blender-mcp`` server on the stdio transport.
_BLENDER_MCP_COMMAND = "blender-mcp"

#: Fallback depth (in Blender units) for an opening whose wall cannot be
#: resolved. A validated model always resolves, but the generator stays
#: defensive rather than crashing on a dangling ``wall_id``.
DEFAULT_OPENING_DEPTH = 0.3

#: Generated-script header. Emits the ``_add_cube`` and ``_boolean_difference``
#: helpers (the boolean helper is composed from ``arch_macros``) so the body can
#: stay a flat, deterministic list of calls. ``_add_cube`` returns the created
#: object so a boolean modifier can reference it; ``_boolean_difference`` sets
#: the target active, applies the DIFFERENCE modifier, then deletes the cutter.
_HEADER = "\n\n\n".join(
    (
        "import bpy",
        (
            "def _add_cube(name, location, size, rotation_z=0.0):\n"
            "    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)\n"
            "    obj = bpy.context.active_object\n"
            "    obj.name = name\n"
            "    obj.scale = size\n"
            "    obj.rotation_euler = (0.0, 0.0, rotation_z)\n"
            "    return obj"
        ),
        arch_macros.emit_boolean_header(),
    )
)


class BlenderClientError(Exception):
    """Raised when the Blender MCP transport or code execution fails."""


def _fmt(value: float) -> str:
    """Format a float deterministically with trailing zeros stripped."""
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def _vec(values: tuple[float, float, float]) -> str:
    """Format a 3-tuple as a bpy-style ``(x, y, z)`` literal."""
    return "(" + ", ".join(_fmt(v) for v in values) + ")"


def _cube_line(name: str, location: tuple[float, float, float],
               size: tuple[float, float, float], rotation_z: float = 0.0) -> str:
    return f"_add_cube({json.dumps(name)}, {_vec(location)}, {_vec(size)}, {_fmt(rotation_z)})"


def _wall_box(wall: Wall) -> tuple[tuple[float, float, float], tuple[float, float, float], float]:
    """Return (location, size, rotation_z) for a wall as an axis-aligned box."""
    dx = wall.end.x - wall.start.x
    dy = wall.end.y - wall.start.y
    length = math.hypot(dx, dy)
    angle = math.atan2(dy, dx)
    cx = (wall.start.x + wall.end.x) / 2.0
    cy = (wall.start.y + wall.end.y) / 2.0
    cz = (wall.start.z + wall.end.z) / 2.0 + wall.height / 2.0
    return (cx, cy, cz), (length, wall.thickness, wall.height), angle


def _floor_box(floor: Floor) -> tuple[tuple[float, float, float], tuple[float, float, float], float]:
    """Return (location, size, rotation_z) for a floor as its outline bounding box."""
    xs = [v.x for v in floor.outline]
    ys = [v.y for v in floor.outline]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    cz = floor.elevation + floor.thickness / 2.0
    return (cx, cy, cz), (max_x - min_x, max_y - min_y, floor.thickness), 0.0


def _volume_box(volume: Volume) -> tuple[tuple[float, float, float], tuple[float, float, float], float]:
    """Return (location, size, rotation_z) for a volume box from origin + size."""
    cx = volume.origin.x + volume.size.x / 2.0
    cy = volume.origin.y + volume.size.y / 2.0
    cz = volume.origin.z + volume.size.z / 2.0
    return (cx, cy, cz), (volume.size.x, volume.size.y, volume.size.z), 0.0


def generate_blender_code(model: ArchitectureModel, export_path: str | None = None) -> str:
    """Generate deterministic Blender Python for a validated architecture model.

    Walls, floors, and volumes are emitted as axis-aligned boxes. Openings are
    emitted as CSG boolean ``DIFFERENCE`` cutouts: a cutter box overextending
    past the wall thickness and rotated to the wall's ``atan2(dy, dx)`` angle
    is cut out of the wall and then deleted. When ``export_path`` is set, a
    trailing ``bpy.ops.wm.obj_export`` call is emitted after all cutouts.

    A dangling ``wall_id`` (opening referencing a missing wall) keeps the
    defensive plain-marker fallback so the generator never crashes.
    """
    lines: list[str] = [_HEADER]
    walls_by_id = {wall.id: wall for wall in model.walls}

    for wall in model.walls:
        location, size, rotation_z = _wall_box(wall)
        lines.append(_cube_line(f"wall_{wall.id}", location, size, rotation_z))

    for floor in model.floors:
        location, size, rotation_z = _floor_box(floor)
        lines.append(_cube_line(f"floor_{floor.id}", location, size, rotation_z))

    for opening in model.openings:
        wall = walls_by_id.get(opening.wall_id)
        if wall is not None:
            lines.append(arch_macros.emit_opening_cutout(wall, opening))
        else:
            location = (opening.position.x, opening.position.y, opening.position.z)
            size = (opening.width, DEFAULT_OPENING_DEPTH, opening.height)
            lines.append(_cube_line(f"opening_{opening.id}", location, size, 0.0))

    for volume in model.volumes:
        location, size, rotation_z = _volume_box(volume)
        lines.append(_cube_line(f"volume_{volume.id}", location, size, rotation_z))

    if export_path:
        lines.append(arch_macros.emit_export_obj(export_path))

    return "\n".join(lines) + "\n"


def _default_server_params() -> StdioServerParameters:
    """Build the default stdio transport params for the ``blender-mcp`` server."""
    return StdioServerParameters(command=_BLENDER_MCP_COMMAND, args=[])


def _call_tool_text(result: CallToolResult) -> str:
    """Extract the joined text content from an MCP ``CallToolResult``."""
    parts: list[str] = []
    for item in result.content:
        text = getattr(item, "text", None)
        if text is not None:
            parts.append(text)
    return "\n".join(parts)


class BlenderMCPClient:
    """Transport-isolated client for ``blender-mcp``'s ``execute_blender_code``.

    The single public entry point is :meth:`execute`. Everything transport
    related lives behind it, and any failure is raised as
    :class:`BlenderClientError`.
    """

    def __init__(self, server_params: Optional[StdioServerParameters] = None) -> None:
        self._server_params = server_params or _default_server_params()

    async def execute(self, code: str, user_prompt: str = "") -> str:
        """Send ``code`` to Blender via ``execute_blender_code`` and return the text result.

        Raises :class:`BlenderClientError` if the transport or execution fails.
        """
        try:
            return await self._execute_via_mcp(code, user_prompt)
        except BlenderClientError:
            raise
        except Exception as exc:  # noqa: BLE001 - containment boundary
            raise BlenderClientError(f"Blender MCP transport failed: {exc}") from exc

    async def _execute_via_mcp(self, code: str, user_prompt: str) -> str:
        async with stdio_client(self._server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(
                    "execute_blender_code",
                    arguments={"code": code, "user_prompt": user_prompt},
                )
                return _call_tool_text(result)

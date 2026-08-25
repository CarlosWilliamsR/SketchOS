"""FastMCP server for SketchOS: owns the ``build_architecture`` tool.

This module composes the two lower layers:

- ``arch_dsl`` validates an incoming DSL payload (Pydantic v2).
- ``blender_client`` generates Blender Python and executes it via
  ``blender-mcp``'s ``execute_blender_code`` tool.

The hard boundary enforced here is *validation-before-execution*: an invalid
DSL is rejected before ``BlenderMCPClient.execute`` is ever called, so invalid
input never reaches Blender. Transport/execution failures are caught and
returned as an error string so the server keeps running.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from sketchos_backend.arch_dsl import ArchitectureModel
from sketchos_backend.blender_client import (
    BlenderClientError,
    BlenderMCPClient,
    generate_blender_code,
)

#: FastMCP owns the tools; FastAPI (``main.py``) mounts the HTTP surface.
#: ``streamable_http_path="/"`` keeps the mounted surface at a clean ``/mcp``
#: path when FastAPI mounts this app (avoids a ``/mcp/mcp`` double path).
mcp = FastMCP(
    "SketchOS",
    instructions=(
        "SketchOS backend service. Use ``build_architecture`` to validate an "
        "ArchitecturalDSL payload and drive Blender geometry via blender-mcp."
    ),
    streamable_http_path="/",
)


async def build_architecture(
    payload: dict[str, Any],
    client: BlenderMCPClient,
    user_prompt: str = "",
    export_path: str = "",
) -> str:
    """Validate ``payload``, generate Blender code, and execute it via ``client``.

    Validation-before-execution is the enforcement point: if ``payload`` is not
    a valid :class:`ArchitectureModel`, an error string is returned and
    ``client.execute`` is never called — regardless of ``export_path``.

    ``export_path`` is an optional OBJ output path forwarded verbatim to code
    generation. An empty/missing value means no export; the forwarded value is
    embedded as an operator argument (never executed).
    """
    try:
        model = ArchitectureModel.model_validate(payload)
    except ValidationError as exc:
        return f"Invalid DSL: {exc}"

    code = generate_blender_code(model, export_path=export_path or None)
    try:
        return await client.execute(code, user_prompt=user_prompt)
    except BlenderClientError as exc:
        return f"Blender error: {exc}"


def _make_client() -> BlenderMCPClient:
    """Build the default Blender MCP client used by the tool."""
    return BlenderMCPClient()


@mcp.tool(name="build_architecture")
async def build_architecture_tool(
    payload: dict[str, Any], user_prompt: str = "", export_path: str = ""
) -> str:
    """Build SketchOS architecture geometry in Blender from an ArchitecturalDSL payload.

    Args:
        payload: An ArchitecturalDSL JSON object (walls, floors, openings,
            volumes, relationships). Validated before any Blender code runs.
        user_prompt: Optional user intent, forwarded verbatim to blender-mcp.
        export_path: Optional OBJ output path; when set, the generated script
            exports the built geometry to this path via ``bpy.ops.wm.obj_export``.
    """
    return await build_architecture(
        payload, _make_client(), user_prompt=user_prompt, export_path=export_path
    )

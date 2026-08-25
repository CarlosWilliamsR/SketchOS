"""FastAPI entrypoint for the SketchOS backend.

FastMCP owns the tools; FastAPI mounts the streamable-HTTP surface so the
service can be served by uvicorn on a standard ASGI interface. ``build_architecture``
and the rest of the tool surface live on the mounted ``/mcp`` app.
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from sketchos_backend.server import mcp
from sketchos_backend.validator_routes import router as validator_router

app = FastAPI(
    title="SketchOS Backend",
    description="FastAPI surface for the SketchOS FastMCP server.",
    version="0.1.0",
)

# Mount the FastMCP streamable-HTTP app as the HTTP surface for MCP tools.
app.mount("/mcp", mcp.streamable_http_app())

# Register the validator endpoints (subprocess-backed, never shell).
app.include_router(validator_router)


def main() -> None:
    """Run the SketchOS backend with uvicorn."""
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()

# SketchOS Backend

Standalone Python service that owns SketchOS domain logic: a FastAPI/FastMCP
service defining the ArchitecturalDSL (Pydantic), validating architectural
models, and driving Blender geometry via the `blender-mcp` server's
`execute_blender_code` tool.

## Layout

```
backend/
├── pyproject.toml
├── src/sketchos_backend/
│   ├── __init__.py
│   └── arch_dsl.py      # Pure Pydantic v2 DSL models + validation
└── tests/
    └── test_arch_dsl.py
```

## Development

```sh
uv sync
uv run pytest tests
```

`arch_dsl.py` is a pure Pydantic v2 domain model with no I/O and no MCP or
Blender dependency. Validation happens before any code generation or Blender
execution.

## Geometry validator integration

Three endpoints (`GET /extract-rules`, `POST /validate-geometry`,
`POST /autocorrect`) wrap the Go `validator-go` CLI as an asyncio subprocess
(`validator_client.py`, `validator_routes.py`). The Go binary is resolved from
the `VALIDATOR_GO_BIN` environment variable first, then falls back to
`validator-go` on `PATH`.

To build and install the binary:

```sh
cd ../validator_go
make install        # `go install .` → $GOBIN (or $(go env GOPATH)/bin)
```

If a validation endpoint returns 503 with "binary not found", set
`VALIDATOR_GO_BIN=/path/to/validator-go` or run `make install` and ensure
`$GOBIN` is on `PATH`.

> **Rotated-wall caveat**: wall geometry is exported as an axis-aligned box, so
> wall *thickness* is approximated for rotated walls (AABB inflation).
> `POST /autocorrect` may therefore leave a residual `wall_thickness_*`
> violation after a correction pass. This is accepted for v1 and surfaced in
> the endpoint response's `report`; it is not treated as an error.

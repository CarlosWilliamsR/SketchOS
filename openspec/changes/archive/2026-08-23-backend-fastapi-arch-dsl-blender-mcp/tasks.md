# Tasks: Implement base FastAPI backend, ArchitecturalDSL Pydantic schema, and Blender MCP client integration

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~500 (range 450–550) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (scaffold+DSL) → PR 2 (client+codegen) → PR 3 (server+wiring) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: No (resolved: stacked-to-main)
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Installable scaffold + validated DSL | PR 1 | `uv run pytest backend/tests/test_arch_dsl.py -q` | N/A — pure Pydantic, no I/O | delete `backend/pyproject.toml`, `arch_dsl.py`, `test_arch_dsl.py` |
| 2 | Codegen + transport-isolated client | PR 2 | `uv run pytest backend/tests/test_blender_client.py -q` | N/A — pure string codegen, no live Blender | delete `blender_client.py`, `test_blender_client.py` |
| 3 | FastMCP server + tool + entrypoint | PR 3 | `uv run pytest backend/tests/test_server.py -q` | `uv run python -m sketchos_backend.main` boots; mocked transport keeps loop alive | delete `server.py`, `main.py`, `test_server.py` |

## Phase 1: Foundation / DSL schema

- [x] 1.1 Create `backend/pyproject.toml` — src-layout, deps `mcp>=1.9.0,<2`, `fastapi`, `uvicorn`, `pydantic>=2`, Python `>=3.10`; run `uv lock`. (backend-service: Server bootstrapping)
- [x] 1.2 Create `backend/src/sketchos_backend/__init__.py` package marker.
- [x] 1.3 Create `backend/src/sketchos_backend/arch_dsl.py` — `Vec3`, `Wall`, `Floor`, `Opening`, `Volume`, `Relationship`, `ArchitectureModel`; all `extra="forbid"`, dims `Field(gt=0)`. (arch-dsl: DSL schema, Validation)
- [x] 1.4 Write `backend/tests/test_arch_dsl.py` — valid parse, negative dim rejected, missing field rejected, JSON round-trip. (arch-dsl: all 4 scenarios)

## Phase 2: Client / codegen

- [x] 2.1 Create `backend/src/sketchos_backend/blender_client.py` — `generate_blender_code(model)`; `BlenderClientError`; `BlenderMCPClient.execute(code, user_prompt="")` via MCP `stdio_client` calling `execute_blender_code`. (blender-mcp-client: Code generation, Transport isolation)
- [x] 2.2 Write `backend/tests/test_blender_client.py` — codegen emits wall/floor/opening bpy ops; string assertions, no live Blender. (blender-mcp-client: Geometry generated for DSL elements)

## Phase 3: Server / wiring

- [x] 3.1 Create `backend/src/sketchos_backend/server.py` — FastMCP `SketchOS` server; `build_architecture` tool validates → generates → executes; on `ValidationError` return error without calling client; mount streamable-HTTP app. (backend-service: Tool registration; blender-mcp-client: Validation before execution, Blender MCP invocation)
- [x] 3.2 Create `backend/src/sketchos_backend/main.py` — FastAPI/uvicorn entrypoint. (backend-service: Server bootstrapping)
- [x] 3.3 Write `backend/tests/test_server.py` — invalid DSL ⇒ `execute` NOT called; valid DSL ⇒ `execute` called with generated code; unreachable transport ⇒ `BlenderClientError` surfaced and loop alive. (blender-mcp-client: Invalid DSL is not sent to Blender, Round-trip to Blender, Transport failure is contained)

## Phase 4: Verification

- [x] 4.1 Run `uv run pytest backend/tests -q` — all green.
- [x] 4.2 Boot `uv run python -m sketchos_backend.main` — starts without error; `build_architecture` listed among tools.

Note: Threat matrix is N/A (no shell/subprocess/VCS boundary in backend code); no RED tests required.

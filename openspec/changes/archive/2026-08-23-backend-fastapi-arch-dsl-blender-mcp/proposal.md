# Proposal: Implement base FastAPI backend, ArchitecturalDSL Pydantic schema, and Blender MCP client integration

## Intent

SketchOS is currently a C/C++ kernel skeleton (`src/boot`, `src/kernel`) with no architecture tooling. We need a standalone Python backend that owns SketchOS domain logic: a FastAPI/FastMCP service defining an Architectural DSL (Pydantic), validating architectural models, and driving Blender geometry via the existing `blender-mcp` server's `execute_blender_code` tool.

## Scope

### In Scope (first slice)
- New `backend/` Python project (FastAPI + FastMCP + Pydantic) with scaffolding.
- `backend/arch_dsl.py`: Pydantic models for the ArchitecturalDSL (walls, floors, openings) with validation.
- `backend/blender_client.py`: connects to `blender-mcp`, generates Blender Python from a DSL instance, calls `execute_blender_code`.
- One SketchOS MCP tool (`build_architecture`) exposing the DSL→Blender round-trip.

### Out of Scope (non-goals)
- Frontend (Astro + React + Three.js).
- Geometric validation in Go (`validator_go`).
- Bidirectional Blender→backend event streaming / scene sync.
- Auth, multi-user, model persistence.

## Capabilities

### New Capabilities
- `backend-service`: FastAPI/FastMCP SketchOS server exposing SketchOS tools.
- `arch-dsl`: Pydantic ArchitecturalDSL schema and validation rules.
- `blender-mcp-client`: client translating DSL to Blender Python via `execute_blender_code`.

### Modified Capabilities
- None.

## Approach

Standalone Python service in `backend/`. FastMCP (`mcp.server.fastmcp`) exposes SketchOS tools; FastAPI mounts the HTTP surface. `arch_dsl.py` defines validated Pydantic models. A client uses the MCP client SDK to call `blender-mcp`'s `execute_blender_code`, generating Blender Python from a validated DSL instance. Match the `blender-mcp` stack (`mcp>=1.9.0,<2`, Python >=3.10).

## Proposed Artifacts

- `proposal.md` (this), then `specs/`, `design.md`, `tasks.md`, `verify-report.md` for this change.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/` | New | New FastAPI/FastMCP project |
| `backend/arch_dsl.py` | New | Pydantic ArchitecturalDSL schema |
| `backend/blender_client.py` | New | Blender MCP client + code generation |
| `blender-mcp/src/blender_mcp/server.py` | Read-only | Existing MCP server (client target) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Two MCP servers add transport complexity | Med | Isolate client behind one interface; pin transport |
| `execute_blender_code` serialization overhead on large models | Med | Batch/parametrize generated code; validate before send |
| Version drift vs `blender-mcp` (`mcp` API) | Low | Pin `mcp>=1.9.0,<2`; lock deps with uv |
| Artifact location mismatch (`sdd/` vs `openspec/changes/`) | Low | Reconcile convention before spec phase |

## Rollback Plan

Delete the `backend/` directory and revert dependency-file additions. No existing files are modified, so rollback is a clean directory removal.

## Dependencies

- Existing `blender-mcp` server running with its `mcp` dependency (`>=1.9.0,<2`).
- Python >=3.10 environment with uv for dependency management.

## Success Criteria

- [ ] `backend/` installs and boots a FastMCP server without error.
- [ ] `arch_dsl.py` validates a sample architectural model and rejects an invalid one.
- [ ] `build_architecture` round-trips a sample DSL into Blender via `execute_blender_code`.
- [ ] Unit tests cover DSL validation and client code generation.

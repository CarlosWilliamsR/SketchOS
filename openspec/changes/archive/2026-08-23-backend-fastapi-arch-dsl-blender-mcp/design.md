# Design: Implement base FastAPI backend, ArchitecturalDSL Pydantic schema, and Blender MCP client integration

## Technical Approach

Standalone Python service in `backend/` using a src-layout that mirrors the sibling `blender-mcp` project. FastMCP (`mcp.server.fastmcp`) exposes the `build_architecture` tool; the HTTP surface is FastMCP's streamable-HTTP app mounted under FastAPI/uvicorn. `arch_dsl.py` is a pure Pydantic v2 domain model with no I/O and no MCP dependency. `blender_client.py` holds a pure code generator plus a transport-isolated MCP client that calls blender-mcp's `execute_blender_code`. Validation is the hard boundary: an invalid DSL never reaches Blender.

## Architecture Decisions

| Decision | Option A | Option B | Choice & Rationale |
|---|---|---|---|
| Package layout | src-layout `backend/src/sketchos_backend/` | flat `backend/` modules | A — matches `blender-mcp` src layout, installable via uv |
| Schema style | Pydantic v2 models, `Field(gt=0)`, `extra="forbid"` | manual `__init__` validation | A — declarative; `ValidationError` and JSON round-trip for free |
| Transport isolation | `BlenderMCPClient.execute(code) -> str` single method | inline `stdio_client` in tool | A — one interface; spec requires transport isolation |
| Client transport | MCP client SDK `stdio_client` (spawns blender-mcp) | raw socket to Blender addon | A — reuses `execute_blender_code`, no socket-protocol coupling |
| HTTP surface | FastMCP streamable-HTTP app under FastAPI | duplicate tools in separate FastAPI app | A — single source of truth for tools |

## Data Flow

```
MCP client ──build_architecture(JSON)──▶ server.build_architecture
                                            │ 1. ArchitectureModel.model_validate(payload)
                                            │    └─ ValidationError → return error (STOP, no Blender)
                                            │ 2. generate_blender_code(model) → bpy code
                                            │ 3. BlenderMCPClient.execute(code)
                                            │    └─ BlenderClientError → return error (no crash)
                                            ▼
                                   execute_blender_code → Blender addon
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/pyproject.toml` | Create | deps `mcp>=1.9.0,<2`, `fastapi`, `uvicorn`, `pydantic>=2`; uv lock |
| `backend/src/sketchos_backend/__init__.py` | Create | package marker |
| `backend/src/sketchos_backend/arch_dsl.py` | Create | Pydantic DSL: `Vec3`, `Wall`, `Floor`, `Opening`, `Volume`, `Relationship`, `ArchitectureModel` |
| `backend/src/sketchos_backend/blender_client.py` | Create | `generate_blender_code()` + `BlenderMCPClient` |
| `backend/src/sketchos_backend/server.py` | Create | FastMCP `SketchOS` server, `build_architecture` tool, HTTP app |
| `backend/src/sketchos_backend/main.py` | Create | entrypoint |
| `backend/tests/*` | Create | test files (see Testing Strategy) |
| `blender-mcp/src/blender_mcp/server.py` | None | read-only target; `execute_blender_code(ctx, code, user_prompt="")` |

## Interfaces / Contracts

`arch_dsl.py` (public surface, all models `extra="forbid"`):

```python
class Vec3(BaseModel): x: float; y: float; z: float
class Wall(BaseModel): id: str; start: Vec3; end: Vec3; height: float = Field(gt=0); thickness: float = Field(gt=0)
class Floor(BaseModel): id: str; outline: list[Vec3]; thickness: float = Field(gt=0); elevation: float = 0
class Opening(BaseModel): id: str; wall_id: str; position: Vec3; width: float = Field(gt=0); height: float = Field(gt=0)
class Volume(BaseModel): id: str; origin: Vec3; size: Vec3
class Relationship(BaseModel): source_id: str; target_id: str; kind: Literal["contains", "adjacent", "opening_in"]
class ArchitectureModel(BaseModel):
    walls: list[Wall]; floors: list[Floor]; openings: list[Opening]
    volumes: list[Volume]; relationships: list[Relationship]
```

`blender_client.py`:

```python
def generate_blender_code(model: ArchitectureModel) -> str: ...
class BlenderClientError(Exception): ...
class BlenderMCPClient:
    async def execute(self, code: str, user_prompt: str = "") -> str: ...
```

Contract: `blender_client.py` receives only an already-validated `ArchitectureModel`. The tool parses/validates first; on `ValidationError` it returns an error and never invokes the client — this is what enforces "invalid DSL is not sent to Blender".

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit (arch_dsl) | valid parse; negative dims rejected; missing field rejected; JSON round-trip equality | pytest, `pytest.raises(ValidationError)`, `model_dump_json`/`model_validate_json` |
| Unit (blender_client) | codegen emits wall/floor/opening bpy ops | pure-function string assertions; no live Blender |
| Unit (server) | invalid DSL → error, `execute` NOT called; valid DSL → `execute` called with generated code | mock `BlenderMCPClient`; spy asserts no-call on invalid |
| Integration | unreachable blender-mcp → `BlenderClientError` surfaced, server keeps running | mock transport raising; assert error string returned and loop alive |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, or executable-file classification boundary in the backend's own code. The MCP SDK's internal process spawn is library-managed, not our shell/command construction; code-execution safety is enforced by validate-before-generate/execute.

## Migration / Rollout

No migration required. New directory; rollback is deleting `backend/`.

## Open Questions

- [ ] Single combined bpy script per model vs. batched per-element `execute_blender_code` calls (perf on large models).

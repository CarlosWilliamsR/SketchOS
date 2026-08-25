# Apply Progress: backend-fastapi-arch-dsl-blender-mcp

- schemaName: gentle-ai.sdd-apply-progress
- change: backend-fastapi-arch-dsl-blender-mcp
- mode: Standard (strict_tdd not active; no RED tests required — threat matrix N/A)
- delivery: stacked-to-main, chained PR slices (3 slices)
- slice applied: 3 of 3 (PR 3 — server + wiring)

## Slice 1 Scope (COMPLETE)

Installable backend scaffold + validated ArchitecturalDSL (pure Pydantic v2).

## Slice 2 Scope (COMPLETE)

Pure Blender-Python codegen (`generate_blender_code`) + transport-isolated
`BlenderMCPClient`. Nothing else.

## Slice 3 Scope (COMPLETE)

FastMCP `SketchOS` server (`server.py`) exposing the `build_architecture` tool,
plus the FastAPI/uvicorn entrypoint (`main.py`) that mounts the streamable-HTTP
surface. Enforces validation-before-execution: invalid DSL never reaches the
Blender client.

## Work Unit Evidence

### Unit 1 — scaffold + DSL (slice 1)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `uv run pytest backend/tests -q` → `9 passed in 0.21s` (exit 0) |
| Runtime harness command/scenario and exact result | `N/A` — pure Pydantic models, no I/O boundary, no server in slice 1 |
| Rollback boundary | delete `backend/pyproject.toml`, `backend/src/sketchos_backend/arch_dsl.py`, `backend/tests/test_arch_dsl.py` (plus generated `backend/uv.lock`) |

### Unit 2 — codegen + transport-isolated client (slice 2)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `uv run pytest backend/tests/test_blender_client.py -q` → `12 passed` (exit 0) |
| Runtime harness command/scenario and exact result | `N/A` — pure string codegen + mocked stdio transport; no live Blender or blender-mcp server needed |
| Rollback boundary | delete `backend/src/sketchos_backend/blender_client.py`, `backend/tests/test_blender_client.py` |

### Unit 3 — FastMCP server + tool + entrypoint (slice 3)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `uv run pytest backend/tests/test_server.py -q` → `8 passed in 0.40s` (exit 0) |
| Runtime harness command/scenario and exact result | `uv run python -m sketchos_backend.main` → uvicorn logs "Application startup complete" + "Uvicorn running on http://127.0.0.1:8000" (bounded boot, killed after startup; no Blender spawned) |
| Rollback boundary | delete `backend/src/sketchos_backend/server.py`, `backend/src/sketchos_backend/main.py`, `backend/tests/test_server.py` |

Combined suite: `uv run pytest backend/tests -q` → `29 passed in 0.42s` (exit 0).

## Task Status

### Phase 1: Foundation / DSL schema (slice 1 — COMPLETE)

- [x] 1.1 `backend/pyproject.toml` — src-layout, deps `mcp>=1.9.0,<2`, `fastapi`, `uvicorn`, `pydantic>=2`, Python `>=3.10`; uv.lock generated (mcp 1.29.0, pydantic 2.13.4).
- [x] 1.2 `backend/src/sketchos_backend/__init__.py` package marker.
- [x] 1.3 `backend/src/sketchos_backend/arch_dsl.py` — Vec3, Wall, Floor, Opening, Volume, Relationship, ArchitectureModel; extra="forbid", dims Field(gt=0).
- [x] 1.4 `backend/tests/test_arch_dsl.py` — 9 tests: valid parse, negative dim, missing field, extra field, JSON round-trip.

### Phase 2: Client / codegen (slice 2 — COMPLETE)

- [x] 2.1 `backend/src/sketchos_backend/blender_client.py` — `generate_blender_code(model)` deterministic bpy generator (walls/floors/openings/volumes as axis-aligned boxes); `BlenderClientError`; `BlenderMCPClient.execute(code, user_prompt="")` via MCP `stdio_client` calling `execute_blender_code`; transport failures contained and re-raised as `BlenderClientError`.
- [x] 2.2 `backend/tests/test_blender_client.py` — codegen string assertions (wall/floor/opening/volume exact literals, determinism, empty-model header, dangling-wall fallback) + transport isolation (mock stdio: success returns tool text, failure contained, BlenderClientError passthrough, _call_tool_text join/empty). 12 tests.

### Phase 3: Server / wiring (slice 3 — COMPLETE)

- [x] 3.1 `backend/src/sketchos_backend/server.py` — FastMCP `SketchOS` server; `build_architecture` tool validates → generates → executes; on `ValidationError` returns error without calling client; mounts streamable-HTTP app (via `streamable_http_path="/"`).
- [x] 3.2 `backend/src/sketchos_backend/main.py` — FastAPI/uvicorn entrypoint mounting the FastMCP streamable-HTTP app at `/mcp`.
- [x] 3.3 `backend/tests/test_server.py` — 8 tests: invalid DSL ⇒ execute NOT called; valid DSL ⇒ execute called with generated code; transport failure ⇒ `BlenderClientError` contained (error string returned, no raise); tool registration; tool end-to-end via `call_tool` with spy client; FastAPI `/mcp` mount; ASGI app importable without Blender.

### Phase 4: Verification (COMPLETE)

- [x] 4.1 `uv run pytest backend/tests -q` — `29 passed in 0.42s` (exit 0).
- [x] 4.2 Boot `uv run python -m sketchos_backend.main` — uvicorn starts clean; `build_architecture` listed among tools.

## Deviations from Design

- (slice 1) Added README.md and dev pytest dependency group; uv installed via astral.sh installer (uv sync generated uv.lock).
- (slice 2) Openings emitted as geometry markers (boxes sized width × wall_thickness × height at position), not boolean cutouts — deferred, documented in generate_blender_code docstring.
- (slice 2) Floors emitted as outline bounding-box slabs, not exact outline polygons — documented in code.
- (slice 2) Generated script uses a shared `_add_cube` helper so the body stays a flat deterministic list of one-line calls; numbers formatted to 6 decimals with trailing zeros stripped.
- (slice 3) FastMCP constructed with `streamable_http_path="/"` so the FastAPI mount yields a clean `/mcp` endpoint (avoids FastMCP's default `/mcp` route producing a `/mcp/mcp` double path).
- (slice 3) `build_architecture` core logic extracted as an async function taking an injected `BlenderMCPClient` (validation → generate → execute); the registered tool delegates via a `_make_client()` factory, monkeypatched in tests for spy-client assertions. No production `arch_dsl.py`/`blender_client.py` change was required.

## Issues Found

None blocking. `openspec/config.yaml` remains absent (only `openspec/changes/` exists), so `rules.apply` and `strict_tdd` still have no config; resolved mode to Standard.

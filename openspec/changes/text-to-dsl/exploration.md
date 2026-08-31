# Exploration: text-to-dsl

## Current State

SketchOS can already turn a Base64 sketch **image** into validated ArchitecturalDSL via a two-pass Gemini pipeline, but there is **no** text-prompt path: the UI has no prompt field and the backend exposes no text→DSL endpoint.

The existing image pipeline lives in `backend/src/sketchos_backend/generation_routes.py`:

1. **Base64 decode** → `image_bytes`
2. **Pass 1 (vision)** — `_pass1_morphology(image_bytes, api_key)` sends the PNG to `gemini-1.5-pro-latest` and returns a *plain-text morphological deconstruction*.
3. **Pass 2 (schema JSON)** — `_pass2_schema_json(morphology, api_key, retry_error)` feeds that *text* plus `ArchitectureModel.model_json_schema()` (`response_schema`) and two few-shot examples into Gemini, returning JSON.
4. **Validation + retry** — `_validate_and_retry(morphology, api_key)` runs `ArchitectureModel.model_validate`, and on failure re-runs Pass 2 once with the Pydantic error injected.
5. **Blender execution** — `_execute_blender(architecture)` runs `generate_blender_code` + `BlenderMCPClient.execute` under a module-level AsyncIO lock.

The crucial observation for text→DSL: **Pass 2 already consumes plain text.** `_pass2_schema_json(morphology, …)` takes a string. A natural-language prompt ("3 plantas, muros de 2.6m de alto, espesor 0.2m") is functionally identical to the morphology string — the only stages the text path must drop are Base64 decode and Pass 1 (vision). Pass 2, the retry loop, and Blender execution are directly reusable as-is.

Error containment is centralized: `GenerationError` subclasses map to HTTP 400/422/502/503/504; a global `except Exception` wrapper guarantees no unhandled 500. Timeouts are `PASS1_TIMEOUT=45s`, `PASS2_TIMEOUT=45s`, `BLENDER_TIMEOUT=30s`. The key is read from `GOOGLE_API_KEY` via `_get_api_key()` (503 when missing).

## Affected Areas

- `backend/src/sketchos_backend/generation_routes.py` — hosts the pipeline to reuse; either a new sibling endpoint here or a shared core module. `_pass2_schema_json`, `_validate_and_retry`, `_execute_blender`, the error hierarchy, and `_blender_lock` are all reusable.
- `backend/src/sketchos_backend/arch_dsl.py` — pure Pydantic v2 schema (Vec3, Wall, Floor, Opening, Volume, Relationship, ArchitectureModel). `extra="forbid"`. **Wall.height/thickness and Floor.thickness have no defaults** (`Field(gt=0)` required) — relevant to the "sensible defaults, no hardcoding" constraint.
- `backend/src/sketchos_backend/main.py` — mounts routers; a new text router (or the same `generation_router`) must be `include_router`-ed here.
- `backend/src/sketchos_backend/server.py` / `blender_client.py` / `arch_macros.py` — the DSL→Blender execution path (unchanged, but the source of the geometry the frontend ultimately needs).
- `frontend/src/lib/api.js` — needs a `generateFromText(prompt)` function; already has the `request()` wrapper with BYOK header injection.
- `frontend/src/components/ValidatorDashboard.jsx` — the Ingest tab is where a prompt input + "Generate" button belongs (it currently has the "Drop a 2D sketch here" placeholder).
- `frontend/src/components/GeometryScene.jsx` + `frontend/src/contexts/SceneStatsContext.jsx` — consume `.obj` text + a Go validation `report` to render; see the geometry-flow gap below.

## Approaches

1. **New endpoint `POST /generate-from-text` (recommended)**
   - A new `TextGenerationRequest(prompt: str)` model and `@router.post("/generate-from-text")` handler that calls `_get_api_key()` → `_validate_and_retry(prompt, api_key)` → `_execute_blender(architecture)` and returns `{"architecture": …}`, reusing the exact error mapping (503/422/504/502).
   - Pros: does not disturb the already-spec'd `/generate-geometry` contract; the text prompt maps 1:1 onto the existing `morphology` string parameter; minimal new surface; mirrors the existing "one router per concern" convention (validator vs generation); separate error/prompt semantics (no Base64, no vision timeout).
   - Cons: one more endpoint to document/test; the prompt wording for Pass 2 differs (natural language vs morphological deconstruction) so it needs its own Pass 2 instruction text.
   - Effort: Low

2. **Extend `/generate-geometry` to accept image OR text**
   - Make `GenerationRequest` a discriminated union (`image` XOR `prompt`) and branch inside the handler.
   - Pros: single endpoint, single place for the frontend to call.
   - Cons: muddies the published vision-to-architecture spec (which is explicitly image-oriented); complicates request validation (400 vs 422 semantics) and error mapping; couples two different failure modes (vision timeout vs text) in one handler; harder to reason about concurrency/timeout defaults.
   - Effort: Medium

3. **Extract a shared `generation_core.py` used by both endpoints**
   - Move `_pass2_schema_json`, `_validate_and_retry`, `_execute_blender`, error hierarchy, and `_blender_lock` into a shared module; image and text routers both call it.
   - Pros: cleanest long-term; avoids duplication as more modalities (voice, file upload) are added; the cross-cutting "defaults" logic has one home.
   - Cons: larger upfront refactor and test churn; higher risk to the currently working image path without clear immediate payoff.
   - Effort: Medium/High

## Recommendation

**Approach 1 — a new `POST /generate-from-text` endpoint**, reusing the existing `_pass2_schema_json` / `_validate_and_retry` / `_execute_blender` helpers directly (no forced shared-module extraction yet). The text prompt is passed straight through as the "morphology" input to Pass 2.

Two things must accompany the endpoint, both stemming from the cross-cutting "no hardcoding / sensible defaults" constraint and from the current frontend/backend disconnect:

1. **Defaults layer.** `Wall.height/thickness` and `Floor.thickness` are required (`gt=0`, no defaults). A prompt like "3 plantas" (no wall dims) would produce a model that fails Pydantic validation. Add a `DEFAULT_PARAMS` mapping (wall height, wall thickness, floor thickness, floor-to-floor height) injected into the Pass 2 system prompt as authoritative fallbacks ("if the user does not specify X, use Y"), rather than baking values into code paths. Config overridable (env), never hardcoded.
2. **API-key resolution.** The frontend already injects `X-Gemini-Api-Key` from localStorage, but `_get_api_key()` reads only `os.getenv("GOOGLE_API_KEY")` and ignores the header. For the UI-driven text flow to work with the user's own key, the text endpoint should resolve the key as: `X-Gemini-Api-Key` header (if present) → `GOOGLE_API_KEY` env → 503. (The image path has the same latent gap; flagging it here since the text flow is the first UI-reachable generation path.)

**Open geometry-flow question for the follow-up changes (this is change 1 of 3):** `/generate-geometry` returns only `{"architecture": …}` — no `.obj` geometry. `GeometryScene` renders exclusively from `.obj` text + a Go `report`. So making the generated volumetry visible in the viewport requires either (a) the backend exporting+returning OBJ bytes/text (it already emits `bpy.ops.wm.obj_export` via `export_path`), or (b) a frontend DSL→OBJ conversion. This should be scoped as its own change and not silently folded into the endpoint work.

## Risks

- **BYOK header is currently dead on arrival**: `api.js` sends `X-Gemini-Api-Key`, but the backend never reads it. Until resolved, a UI-entered key cannot drive generation — the text endpoint must be the first consumer of the header.
- **`.env` naming mismatch**: `.env` exports `GEMINI_API_KEY`, but all backend code reads `GOOGLE_API_KEY` (and nothing auto-loads `.env`; `python-dotenv` appears only as a transitive dep in `uv.lock`, never imported). A misconfigured local env will return 503 confusingly.
- **Hardcoded few-shot examples**: `FEW_SHOT_EXAMPLES` hardcode `height: 3.0`, `thickness: 0.3/0.2`, and fixed coordinates. These are examples, not defaults, but any "sensible defaults" mechanism must be kept distinct from them or the model will bias toward the example values.
- **Schema has no dimension defaults**: required `gt=0` fields mean a bare "make me a building" prompt (no data) fails validation unless the defaults layer is applied before/at validation.
- **No geometry returned to the viewport**: text→DSL → 3D render is not possible today without a new OBJ return path or frontend conversion; must be planned, not assumed.
- **Pass 2 prompt wording**: the existing instruction says "based on this morphological analysis"; the text path needs a natural-language-specific instruction ("based on this user description") and its own few-shot orientation, or output quality will suffer.

## Ready for Proposal

Yes. The orchestrator should tell the user: text→DSL is a **new backend endpoint** that reuses the existing schema-forced JSON generation (skipping the vision pass), plus a defaults layer and API-key header resolution. It is the first of three changes and does **not** yet cover rendering the result in the 3D viewport — that (plus the frontend prompt input + generate button wiring) is a separate follow-up.

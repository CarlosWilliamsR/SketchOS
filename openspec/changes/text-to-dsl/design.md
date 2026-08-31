# Design: text-to-dsl

## Technical Approach

Add a new `POST /generate-from-text` endpoint reusing the existing schema-forced JSON stage (`_pass2_schema_json`), self-healing retry (`_validate_and_retry`), and Blender execution (`_execute_blender`) verbatim — skipping only Base64 decode and the Pass 1 vision call. The user prompt passes straight through as Pass 2's text input. A defaults layer (env-overridable) is injected before generation so dimension-less prompts still validate. API-key resolution becomes header-aware. The frontend adds a prompt input + Generate button in the Ingest tab and shows the returned JSON DSL as read-only text (viewport rendering is change 3).

## Architecture Decisions

### Decision: New endpoint, not a `/generate-geometry` extension

| Option | Tradeoff | Decision |
|---|---|---|
| Extend `/generate-geometry` (image XOR prompt) | Muddies the image-only vision spec; couples vision vs text errors | Rejected |
| Shared `generation_core.py` | DRYest but larger refactor + test churn, risk to image path | Deferred |
| New `POST /generate-from-text` in the same router | Additive; zero image-path risk; same error hierarchy/lock | **Chosen** |

The endpoint lives in the existing `generation_routes.py` router (already mounted in `main.py`).

### Decision: Defaults live in a dedicated `defaults.py` module

Not Pydantic `Field` defaults on the DSL (would weaken the validator's validation boundary) and not a bare inline constant (must stay distinct from `FEW_SHOT_EXAMPLES`). `defaults.py` holds `DefaultParams` (wall_height, wall_thickness, floor_thickness, floor_to_floor) loaded via `os.getenv("SKETCHOS_DEFAULT_*")` with literal fallbacks, plus `render_defaults_directive()` serializing them into the instruction.

### Decision: API key — header → GOOGLE_API_KEY → GEMINI_API_KEY → 503

`_get_api_key(header_key: str | None = None)` resolves in that order. `python-dotenv` becomes a direct dependency; `load_dotenv()` runs at the top of `generation_routes.py`. The image handler keeps calling `_get_api_key()` header-less (unchanged; the GEMINI fallback strictly improves it too). The header flows via FastAPI `Header(None, alias="X-Gemini-Api-Key")` in the text handler only.

### Decision: Reuse FEW_SHOT_EXAMPLES; text-specific instruction only

Extract `_render_few_shot_examples()` (shared by both prompt builders). `_build_text_prompt(user_prompt, retry_error)` prepends defaults directive + few-shot examples + a "user description" instruction (not "morphological analysis") + the raw prompt. A text-specific few-shot set is rejected (duplicate schema JSON to sync); the defaults directive counters example bias.

## Data Flow

```
TextGenerationRequest{prompt} ─▶ _get_api_key(header) ─▶ _validate_and_retry(prompt, key, build_prompt=_build_text_prompt)
                                                               │  _pass2_schema_json(prompt, key, build_prompt)
                                                               │      └─ _build_text_prompt → defaults + few-shot + prompt
                                                               ▼
                                                        ArchitectureModel ─▶ _execute_blender ─▶ {"architecture": …}
```

Helpers gain optional `build_prompt=_build_pass2_prompt` (default = current behavior); the image path never passes it, so its contract is unchanged.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/src/sketchos_backend/defaults.py` | Create | `DefaultParams` + env load + `render_defaults_directive()` |
| `backend/src/sketchos_backend/generation_routes.py` | Modify | Header-aware key; `load_dotenv()`; `_render_few_shot_examples()`; `_build_text_prompt()`; optional `build_prompt`; `TextGenerationRequest` + handler |
| `backend/pyproject.toml` | Modify | Add `python-dotenv` direct dependency |
| `backend/tests/test_generation_routes.py` | Modify | Adapt `test_missing_api_key`; add text-endpoint tests |
| `backend/tests/test_defaults.py` | Create | Defaults env-override + fallback tests |
| `frontend/src/lib/api.js` | Modify | Add `generateFromText(prompt)` |
| `frontend/src/lib/api.test.js` | Modify | Tests for `generateFromText` |
| `frontend/src/components/ValidatorDashboard.jsx` | Modify | Prompt input + Generate + JSON result display |
| `frontend/src/components/ValidatorDashboard.test.jsx` | Modify | Input + call + result/error tests |

## Interfaces / Contracts

```python
class TextGenerationRequest(BaseModel):
    prompt: str = Field(min_length=1)

# Response identical to image endpoint (no OBJ — viewport render is change 3):
#   {"architecture": <ArchitectureModel.model_dump()>}

def _get_api_key(header_key: str | None = None) -> str
def _build_text_prompt(user_prompt: str, retry_error: str | None = None) -> str
async def _validate_and_retry(morphology, api_key, build_prompt=_build_pass2_prompt) -> Any
```

```js
export function generateFromText(prompt) {
  return request('/generate-from-text', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  });
}
```

Frontend: new state `textPrompt`/`textResult`/`textError`/`textLoading`, orthogonal to the `.obj` phase machine. On success `textResult = JSON.stringify(data.architecture, null, 2)` renders in a read-only `<pre>` in the Ingest tab; errors surface inline. Text generation never touches `objText`/`phase`.

## Testing Strategy (strict TDD)

| Layer | What | Approach |
|---|---|---|
| Backend unit | `_get_api_key` precedence; `_build_text_prompt` wording/defaults; defaults env-override | pytest, monkeypatch |
| Backend integration | `/generate-from-text` happy path, header key, 503/422/502/504, retry | Mock genai + BlenderMCPClient |
| Backend regression | `/generate-geometry` unchanged | Existing suite + adapted `test_missing_api_key` |
| Frontend unit | `generateFromText` URL/body/header | Stub `fetch` |
| Frontend component | Input → call → JSON output; error; viewport untouched | vitest + testing-library |

RED tests are written before any production change (`strict_tdd: true`).

## Threat Matrix

N/A — new HTTP route only; no new shell, subprocess, VCS/PR automation, or executable-classification boundary. Blender MCP is reused unchanged under the existing `_blender_lock`.

## Migration / Rollout

No migration. Additive endpoint; rollback = revert commit.

## Open Questions

- [ ] Confirm `load_dotenv()` default search reliably finds repo-root `.env` when uvicorn runs from `backend/`.
- [ ] Whether the image endpoint should also consume the BYOK header (deferred — out of scope).

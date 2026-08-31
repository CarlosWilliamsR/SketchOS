# text-to-architecture Specification

## Purpose

Add a natural-language generation path: an architect types a prompt and receives schema-valid ArchitecturalDSL JSON. It mirrors the image pipeline but skips Base64 decode and Pass 1 vision, reusing Pass 2 schema-forced JSON, self-healing validation, and Blender execution. Nothing is hardcoded; sensible defaults apply when the prompt omits data.

## Requirements

### Requirement: Text Prompt Endpoint Contract

The system SHALL provide `POST /generate-from-text` accepting `{"prompt": "<natural language>"}` and returning HTTP 200 with `{"architecture": <ArchitectureModel>}`. Errors SHALL mirror the image path: 400 empty/whitespace prompt, 422 missing `prompt` or validation-failed-after-retry, 502 Gemini/Blender failure, 503 missing API key, 504 timeout (Pass 2 45s / Blender 30s). Error bodies SHALL use `{"error": "<kind>", "detail": "<reason>"}`. The system SHALL NEVER return HTTP 500; unexpected errors SHALL wrap as 502.

#### Scenario: Valid prompt returns architecture

- GIVEN a non-empty prompt and a resolvable API key
- WHEN POST to `/generate-from-text`
- THEN HTTP 200 with schema-conformant ArchitectureModel JSON

#### Scenario: Empty prompt rejected

- GIVEN a blank prompt
- WHEN POST to `/generate-from-text`
- THEN HTTP 400 with an "Invalid prompt" error

### Requirement: BYOK Header Resolution

The system SHALL read the `X-Gemini-Api-Key` header first, then fall back to `GOOGLE_API_KEY` env. If neither is present, it SHALL return HTTP 503.

#### Scenario: Header key takes precedence

- GIVEN both `X-Gemini-Api-Key` and `GOOGLE_API_KEY` are set
- WHEN a generation request is made
- THEN the header value drives the Gemini call

#### Scenario: Missing key returns 503

- GIVEN neither header nor `GOOGLE_API_KEY` is present
- WHEN a generation request is made
- THEN HTTP 503 with "Provider unavailable"

### Requirement: Defaults Layer

The system SHALL inject sensible default parameters when the prompt omits dimensions. Defaults SHALL be configurable (a settings object, environment-overridable), not hardcoded. A bare prompt SHALL produce a valid model, not fail `gt=0`.

| Default | Value |
|---------|-------|
| wall_height | 3.0 m |
| wall_thickness | 0.3 m |
| floor_thickness | 0.2 m |
| floor_to_floor_height | 3.0 m |

#### Scenario: Bare prompt uses defaults

- GIVEN the prompt "make me a building" with no dimensions
- WHEN generation runs
- THEN walls and floors receive the configured defaults and validation succeeds

#### Scenario: Explicit dimensions override defaults

- GIVEN the prompt "muros de 2.6m de alto, espesor 0.2m"
- WHEN generation runs
- THEN the stated dimensions are used instead of defaults

### Requirement: Natural-Language Instruction

The text path SHALL use its own natural-language instruction and SHALL NOT reuse the "morphological analysis" wording. Few-shot examples SHALL stay distinct from the defaults to avoid biasing the model.

#### Scenario: Text-specific instruction

- GIVEN a text prompt
- WHEN the Pass 2 prompt is built
- THEN the instruction describes the natural-language request, not morphological analysis
- AND few-shot examples do not duplicate the default dimensions

### Requirement: Dimension Unit Conventions

The system SHALL treat meters as the canonical DSL unit. Dimensions in other units (cm, mm, ft, in) SHALL normalize to meters; a unit-less dimension SHALL be meters.

#### Scenario: Non-meter units normalized

- GIVEN the prompt "espesor 20cm"
- WHEN generation runs
- THEN the thickness is interpreted as 0.2 m

### Requirement: Frontend Text Prompt Integration

The Ingest tab SHALL provide a text prompt input and a "Generate" button. On generate, the UI SHALL POST to `/generate-from-text` and route the result through the existing state machine (idle → loading → loaded/empty → error), surfacing the architecture JSON. The `.obj` geometry-to-viewport path is OUT of scope.

#### Scenario: Generate from prompt

- GIVEN the Ingest tab with a prompt entered
- WHEN the user clicks "Generate"
- THEN the prompt posts to `/generate-from-text` and the returned architecture JSON is visible

#### Scenario: Generation error surfaced

- GIVEN generation fails (e.g., 503 missing key)
- WHEN the request completes
- THEN a visible error message is shown and the state machine enters `error`

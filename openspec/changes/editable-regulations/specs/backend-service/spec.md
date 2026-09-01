# Delta for backend-service

## ADDED Requirements

### Requirement: Threshold parsing and validation

The system SHALL parse optional thresholds on `/validate-geometry` and `/autocorrect`, and SHALL validate that every supplied value is finite, non-negative, and that no minimum exceeds its maximum. Invalid thresholds SHALL be rejected with a 4xx error and a clear message BEFORE the Go validator is invoked.

#### Scenario: Minimum exceeds maximum

- GIVEN a request with min height greater than max height
- WHEN the endpoint parses thresholds
- THEN a 4xx error with a clear message is returned and the Go binary is not invoked

#### Scenario: Negative threshold

- GIVEN a request with a negative threshold value
- WHEN the endpoint parses thresholds
- THEN a 4xx error is returned and the Go binary is not invoked

#### Scenario: Non-finite threshold

- GIVEN a request with a NaN or infinite threshold value
- WHEN the endpoint parses thresholds
- THEN a 4xx error is returned and the Go binary is not invoked

## MODIFIED Requirements

### Requirement: Geometry validation endpoint

The system SHALL implement `POST /validate-geometry`, which SHALL accept uploaded `.obj` bytes plus OPTIONAL custom thresholds as multipart form fields or query parameters, write the bytes to a temporary file, run the validator against that file using the supplied thresholds, and return the Go JSON report plus a derived status. When thresholds are absent, the endpoint SHALL fall back to `extract_rules()` defaults.

(Previously: accepted only `.obj` bytes and always used `extract_rules()` defaults.)

#### Scenario: Passing model

- GIVEN `.obj` bytes whose validation finds no violations
- WHEN `POST /validate-geometry` is called
- THEN the endpoint returns the Go JSON report with status `pass`

#### Scenario: Violating model

- GIVEN `.obj` bytes whose validation finds one or more violations
- WHEN `POST /validate-geometry` is called
- THEN the endpoint returns the Go JSON report with status `violations`

#### Scenario: Unparseable model

- GIVEN `.obj` bytes the validator cannot parse
- WHEN `POST /validate-geometry` is called
- THEN the endpoint returns a 4xx error carrying the validator's stderr diagnostic

#### Scenario: Temp file lifecycle

- GIVEN `.obj` bytes are uploaded
- WHEN validation runs
- THEN the backend writes the bytes to a temporary file and removes it after the subprocess exits

#### Scenario: Custom thresholds forwarded

- GIVEN `.obj` bytes and valid custom thresholds in the request
- WHEN `POST /validate-geometry` is called
- THEN the validator runs with the custom thresholds, not `extract_rules()` defaults

#### Scenario: Thresholds absent fall back to defaults

- GIVEN `.obj` bytes and no thresholds in the request
- WHEN `POST /validate-geometry` is called
- THEN the validator runs with `extract_rules()` defaults

### Requirement: Autocorrect endpoint

The system SHALL implement `POST /autocorrect`, which SHALL accept a JSON payload containing the DSL plus OPTIONAL custom thresholds, re-codegen corrected geometry through the existing `build_architecture`/Blender path, and re-validate the result. The autocorrect re-validate loop SHALL apply the SAME custom thresholds on both validation passes. When thresholds are absent, the endpoint SHALL fall back to `extract_rules()` defaults. The Go validator SHALL NOT edit meshes.

(Previously: always used `extract_rules()` defaults for both passes.)

#### Scenario: Corrected output re-validates clean

- GIVEN a DSL payload whose geometry produces violations
- WHEN `POST /autocorrect` is called
- THEN the backend re-codegens corrected dimensions via Blender
- AND the corrected result is re-validated with no violations

#### Scenario: Custom thresholds applied on both passes

- GIVEN a DSL payload and valid custom thresholds in the request
- WHEN `POST /autocorrect` runs
- THEN the initial and re-validation passes both use the same custom thresholds

#### Scenario: Thresholds absent fall back to defaults

- GIVEN a DSL payload and no thresholds in the request
- WHEN `POST /autocorrect` runs
- THEN both validation passes use `extract_rules()` defaults

# Delta for backend-service

## ADDED Requirements

### Requirement: Validator HTTP endpoints

The system MUST register three HTTP endpoints on the FastAPI app — `GET /extract-rules`, `POST /validate-geometry`, and `POST /autocorrect` — while preserving the existing `/mcp` mount.

#### Scenario: Endpoints are discoverable

- GIVEN a running backend server
- WHEN a client lists the FastAPI routes
- THEN `/extract-rules`, `/validate-geometry`, and `/autocorrect` are present
- AND the `/mcp` mount remains intact

### Requirement: Rule extraction endpoint

The system SHALL implement `GET /extract-rules`, which SHALL invoke the Go validator's `-print-defaults` flag and return the normativa thresholds it prints.

#### Scenario: Returns thresholds

- GIVEN a working `validator-go` binary
- WHEN `GET /extract-rules` is called
- THEN the response contains min/max height and min/max thickness thresholds as JSON

### Requirement: Geometry validation endpoint

The system SHALL implement `POST /validate-geometry`, which SHALL accept uploaded `.obj` bytes, write them to a temporary file, run the validator against that file, and return the Go JSON report plus a derived status.

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

### Requirement: Autocorrect endpoint

The system SHALL implement `POST /autocorrect`, which SHALL re-codegen corrected geometry through the existing `build_architecture`/Blender path and re-validate the result. The Go validator SHALL NOT edit meshes.

#### Scenario: Corrected output re-validates clean

- GIVEN a DSL payload whose geometry produces violations
- WHEN `POST /autocorrect` is called
- THEN the backend re-codegens corrected dimensions via Blender
- AND the corrected result is re-validated with no violations

### Requirement: Subprocess validator client

The system SHALL invoke the Go validator via an asyncio subprocess client, using list-form argv and never `shell=True`. The binary path SHALL resolve from the `VALIDATOR_GO_BIN` environment variable, falling back to `validator-go` on PATH.

#### Scenario: Env var resolves binary

- GIVEN `VALIDATOR_GO_BIN` points to a working binary
- WHEN the validator client runs
- THEN the configured binary path is executed

#### Scenario: PATH fallback

- GIVEN `VALIDATOR_GO_BIN` is unset and `validator-go` is on PATH
- WHEN the validator client runs
- THEN the PATH binary is executed

#### Scenario: No shell interpolation

- GIVEN any validator invocation
- WHEN the subprocess is created
- THEN argv is passed as a list and `shell` is never enabled

### Requirement: Exit-code mapping

The system SHALL map validator exit codes to outcomes: 0 = pass, 1 = violations with valid JSON, 2 = parse error with no JSON. This distinction SHALL be preserved.

#### Scenario: Exit 0

- GIVEN the validator exits 0
- WHEN the result is mapped
- THEN the outcome is `pass` with a parsed JSON report

#### Scenario: Exit 1

- GIVEN the validator exits 1
- WHEN the result is mapped
- THEN the outcome is `violations` with a parsed JSON report

#### Scenario: Exit 2

- GIVEN the validator exits 2
- WHEN the result is mapped
- THEN the outcome is a parse error and no JSON report is parsed

### Requirement: Timeout and error handling

The system SHALL enforce a timeout on validator subprocesses and SHALL return a 5xx error when the subprocess cannot be spawned, times out, or fails.

#### Scenario: Subprocess timeout

- GIVEN a validation that exceeds the timeout
- WHEN the timeout elapses
- THEN the subprocess is terminated and a 5xx error is returned

#### Scenario: Binary missing

- GIVEN no resolvable validator binary
- WHEN a validation endpoint is called
- THEN a 5xx error is returned with a clear "binary not found" message

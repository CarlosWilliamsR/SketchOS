# geometry-validator Specification

## Purpose

Defines the Go CLI that parses Blender-exported `.obj` files, computes the Axis-Aligned Bounding Box (AABB), and validates geometric regulations for wall height and thickness in milliseconds. Units are meters; wall height is read from the OBJ Y axis (Y-up).

## Requirements

### Requirement: OBJ parsing

The system SHALL parse an OBJ file in a single streaming pass, extracting vertex coordinates and object/group names, without regex.

#### Scenario: Happy path

- GIVEN an OBJ with `v`, `f`, and `o`/`g` lines plus `vt`, `vn`, `usemtl`, `mtllib`, comment, and blank lines
- WHEN the file is parsed
- THEN all vertex coordinates are extracted and the current object name is tracked

#### Scenario: Negative relative indices

- GIVEN faces using negative relative indices such as `f -1 -2 -3`
- WHEN the file is parsed
- THEN indices resolve relative to previously declared vertices and parsing succeeds

#### Scenario: Malformed non-vertex line

- GIVEN a malformed or unknown non-vertex line
- WHEN the file is parsed
- THEN the line is skipped without aborting

#### Scenario: Malformed vertex line

- GIVEN a `v` line with fewer than three numeric fields
- WHEN the file is parsed
- THEN parsing fails with a parse error

### Requirement: AABB computation

The system SHALL compute the AABB as min/max over all parsed vertices, reporting six scalars and dimensions dx/dy/dz.

#### Scenario: Axis-aligned box

- GIVEN vertices forming an axis-aligned box
- WHEN the AABB is computed
- THEN min/max scalars and dx/dy/dz match the box extents

#### Scenario: Non-axis-aligned wall

- GIVEN a wall rotated about the Y axis
- WHEN the AABB is computed
- THEN the box bounds the rotated geometry by its true min/max extents

### Requirement: Wall height and thickness validation

The system SHALL validate wall height and thickness against min/max thresholds, reading wall height from the Y axis, and SHALL report each violation.

#### Scenario: Y-axis height

- GIVEN a wall whose vertical extent lies along the OBJ Y axis
- WHEN its height is measured
- THEN height equals the Y extent, not the Z extent

#### Scenario: Height out of range

- GIVEN a wall whose Y extent is below min or above max wall height
- WHEN validation runs
- THEN a violation with the wall id and measured height is reported

#### Scenario: Thickness below minimum

- GIVEN a wall whose AABB thickness is below the minimum threshold
- WHEN validation runs
- THEN a violation with the wall id and measured thickness is reported

### Requirement: JSON output

The system SHALL emit a JSON summary containing the AABB and violations, exiting 0 on pass, 1 on violations, and 2 on parse error.

#### Scenario: Passing model

- GIVEN a model with no violations
- WHEN validation runs
- THEN JSON with the AABB and an empty violations list is emitted and the exit code is 0

#### Scenario: Violating model

- GIVEN a model with one or more violations
- WHEN validation runs
- THEN JSON with a non-empty violations list is emitted and the exit code is 1

### Requirement: Performance

The system SHALL validate a typical architectural model in milliseconds using a single-pass streaming parse.

#### Scenario: Millisecond validation

- GIVEN an OBJ with on the order of ten thousand vertex lines
- WHEN the validator runs end-to-end
- THEN it completes in under 50 ms wall-clock

### Requirement: Default thresholds flag

The system SHALL support a `-print-defaults` flag that prints the current normativa thresholds — minimum height, maximum height, minimum thickness, maximum thickness — as JSON to stdout and exits 0.

#### Scenario: Prints thresholds

- GIVEN `validator-go` invoked with `-print-defaults`
- WHEN the flag runs
- THEN the four thresholds are printed as JSON to stdout
- AND the process exits 0

#### Scenario: Runs without input file

- GIVEN `validator-go -print-defaults` without an `-input` argument
- WHEN the flag runs
- THEN the command succeeds without requiring an input `.obj` file
- AND the process exits 0

#### Scenario: Unenforced bounds

- GIVEN a threshold whose value is 0 (unenforced)
- WHEN `-print-defaults` runs
- THEN the JSON reports that threshold as unenforced (value 0)

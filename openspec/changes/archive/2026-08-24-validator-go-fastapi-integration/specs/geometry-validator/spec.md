# Delta for geometry-validator

## ADDED Requirements

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

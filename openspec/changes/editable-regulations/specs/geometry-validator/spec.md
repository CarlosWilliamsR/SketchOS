# Delta for geometry-validator

## ADDED Requirements

### Requirement: Per-call threshold flags

The system SHALL accept wall height and thickness thresholds per invocation via the CLI flags `-min-height`, `-max-height`, `-min-thickness`, and `-max-thickness`. Each threshold SHALL be a finite, non-negative number, and a value of `0` SHALL mean "unenforced" (no bound applied). When a flag is omitted, the system SHALL fall back to the corresponding `DefaultThresholds()` value.

#### Scenario: Custom thresholds override defaults

- GIVEN `validator-go` invoked with `-min-height 2.6 -max-height 0 -min-thickness 0.2 -max-thickness 0.5`
- WHEN validation runs
- THEN walls are checked against the supplied thresholds, not `DefaultThresholds()`

#### Scenario: Omitted flags fall back to defaults

- GIVEN `validator-go` invoked without any threshold flags
- WHEN validation runs
- THEN `DefaultThresholds()` values apply

#### Scenario: Zero means unenforced

- GIVEN a threshold flag set to `0`
- WHEN validation runs
- THEN that bound is not enforced and no violation is reported against it

### Requirement: Threshold input validation

The system SHALL reject invalid threshold inputs and SHALL NOT run validation with them. An input is invalid when any threshold is negative, non-finite (NaN or ±Inf), or when a minimum exceeds its maximum.

#### Scenario: Minimum exceeds maximum

- GIVEN `-min-height 3.0 -max-height 2.0`
- WHEN the CLI parses thresholds
- THEN the run fails with a clear error and exits non-zero without validating

#### Scenario: Negative threshold

- GIVEN a threshold flag set to a negative value
- WHEN the CLI parses thresholds
- THEN the run fails with a clear error and exits non-zero

#### Scenario: Non-finite threshold

- GIVEN a threshold flag set to `NaN` or `Inf`
- WHEN the CLI parses thresholds
- THEN the run fails with a clear error and exits non-zero

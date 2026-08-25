# arch-dsl Specification

## Purpose

Defines the ArchitecturalDSL: Pydantic models and validation rules for architectural models composed of walls, floors, openings, volumes, and relationships.

## Requirements

### Requirement: DSL schema

The system MUST define Pydantic models for an ArchitecturalDSL that represent walls, floors, openings, volumes, and relationships between elements.

#### Scenario: Valid model parses

- GIVEN valid wall, floor, and opening data with a relationship linking them
- WHEN the data is parsed into the ArchitecturalDSL models
- THEN parsing succeeds without error

### Requirement: Validation

The system MUST reject invalid architectural models with a clear validation error.

#### Scenario: Invalid dimensions rejected

- GIVEN a wall with a negative thickness or height
- WHEN the wall model is validated
- THEN validation fails with an error

#### Scenario: Missing required field rejected

- GIVEN a floor missing a required field
- WHEN the floor model is validated
- THEN validation fails with an error

### Requirement: Serialization

The system SHALL serialize a validated DSL instance to JSON and deserialize it back losslessly.

#### Scenario: Round-trip serialization

- GIVEN a validated ArchitecturalDSL instance
- WHEN it is serialized to JSON and deserialized back
- THEN the resulting instance equals the original

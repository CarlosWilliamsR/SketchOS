# blender-mcp-client Specification

## Purpose

Defines the client that translates a validated ArchitecturalDSL into Blender Python and executes it via `blender-mcp`'s `execute_blender_code` tool.

## Requirements

### Requirement: Code generation

The system MUST generate Blender Python (bpy) code from a validated DSL instance covering walls, floors, and openings.

#### Scenario: Geometry generated for DSL elements

- GIVEN a validated DSL containing a wall, a floor, and an opening
- WHEN the client generates Blender code
- THEN the generated code includes operations creating the wall, floor, and opening geometry

### Requirement: Validation before execution

The system MUST validate the DSL before generating or executing any Blender code.

#### Scenario: Invalid DSL is not sent to Blender

- GIVEN an invalid DSL instance
- WHEN the `build_architecture` tool runs
- THEN no code is sent to Blender
- AND an error is returned to the caller

### Requirement: Blender MCP invocation

The system MUST call `blender-mcp`'s `execute_blender_code` tool with the generated code.

#### Scenario: Round-trip to Blender

- GIVEN a validated DSL instance and a running `blender-mcp` server
- WHEN the `build_architecture` tool runs
- THEN `execute_blender_code` is invoked with the generated Blender code
- AND the result is returned to the caller

### Requirement: Transport isolation

The system SHALL isolate the MCP client transport behind a single interface so transport changes do not ripple into the backend.

#### Scenario: Transport failure is contained

- GIVEN the `blender-mcp` server is unreachable
- WHEN the client attempts to call `execute_blender_code`
- THEN the failure is surfaced as a clear error
- AND the backend server continues running

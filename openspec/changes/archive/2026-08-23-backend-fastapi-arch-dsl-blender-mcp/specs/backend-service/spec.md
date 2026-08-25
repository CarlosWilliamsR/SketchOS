# backend-service Specification

## Purpose

Defines the SketchOS backend service: a FastAPI/FastMCP server that owns SketchOS domain logic and exposes SketchOS MCP tools to clients.

## Requirements

### Requirement: Server bootstrapping

The system MUST boot a FastMCP server on Python >=3.10 without error, using `mcp>=1.9.0,<2`.

#### Scenario: Server boots cleanly

- GIVEN the backend dependencies are installed in a Python >=3.10 environment
- WHEN the backend server is started
- THEN the server starts without error
- AND the `mcp` dependency resolves within `>=1.9.0,<2`

### Requirement: Tool registration

The system SHALL register SketchOS tools on the FastMCP server, including `build_architecture`.

#### Scenario: Tool is discoverable

- GIVEN a running backend server
- WHEN a client lists available MCP tools
- THEN `build_architecture` appears in the tool list

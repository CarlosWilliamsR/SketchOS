# Delta for backend-service

## MODIFIED Requirements

### Requirement: Tool registration

The system SHALL register SketchOS tools on the FastMCP server, including `build_architecture`, whose tool signature SHALL accept an optional `export_path` parameter.

(Previously: `build_architecture` accepted only `payload` and an optional `user_prompt`; there was no OBJ export surface.)

#### Scenario: Tool is discoverable

- GIVEN a running backend server
- WHEN a client lists available MCP tools
- THEN `build_architecture` appears in the tool list

#### Scenario: Tool exposes optional export path

- GIVEN a running backend server
- WHEN a client inspects the `build_architecture` tool schema
- THEN the tool accepts an optional `export_path` parameter
- AND omitting `export_path` is valid and disables export

## ADDED Requirements

### Requirement: Optional OBJ export

The system MUST accept an optional `export_path` on `build_architecture` and forward it to Blender code generation so the built geometry is exported to that path via `bpy.ops.wm.obj_export`. An empty or missing `export_path` MUST mean no export. Validation-before-execution MUST hold regardless of `export_path`: an invalid DSL is rejected before any client call is made.

#### Scenario: Export path forwarded

- GIVEN a valid ArchitecturalDSL payload and a non-empty `export_path`
- WHEN `build_architecture` runs
- THEN the generated Blender code includes `bpy.ops.wm.obj_export` with the supplied filepath

#### Scenario: No export when path absent

- GIVEN a valid ArchitecturalDSL payload and no `export_path`
- WHEN `build_architecture` runs
- THEN the generated Blender code does not include `bpy.ops.wm.obj_export`

#### Scenario: Invalid DSL still never reaches Blender

- GIVEN an invalid ArchitecturalDSL payload and a non-empty `export_path`
- WHEN `build_architecture` runs
- THEN an `Invalid DSL:` error is returned
- AND no Blender client call is made

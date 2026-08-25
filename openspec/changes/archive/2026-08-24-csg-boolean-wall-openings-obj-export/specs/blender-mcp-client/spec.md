# Delta for blender-mcp-client

## MODIFIED Requirements

### Requirement: Code generation

The system MUST generate Blender Python (bpy) code from a validated DSL instance covering walls, floors, and openings, where openings are emitted as rotated boolean DIFFERENCE cutouts, and MAY include OBJ export.

(Previously: openings were emitted as unrotated box markers with no boolean cutout and no export support.)

#### Scenario: Geometry generated for DSL elements

- GIVEN a validated DSL containing a wall, a floor, and an opening
- WHEN the client generates Blender code
- THEN the generated code includes operations creating the wall, floor, and opening geometry

#### Scenario: Opening emits boolean cutout

- GIVEN a validated DSL with an opening on a non-axis-aligned wall
- WHEN the client generates Blender code
- THEN the generated code emits a cutter rotated to the wall angle
- AND applies a `BOOLEAN` `DIFFERENCE` modifier on the wall
- AND deletes the cutter after applying it

#### Scenario: Optional OBJ export

- GIVEN a validated DSL and an export request with a filepath
- WHEN the client generates Blender code
- THEN the generated code includes `bpy.ops.wm.obj_export` with that filepath
- AND the export call appears after modifier application

## ADDED Requirements

### Requirement: Opening cutout geometry

The system MUST overextend the cutter box past the wall thickness and share the wall's rotation angle to avoid coplanar degeneracy.

#### Scenario: Cutter clears both wall faces

- GIVEN a wall with a known thickness
- WHEN the opening cutter is emitted
- THEN the cutter extends beyond both wall faces along the cut axis
- AND the cutter rotation equals the wall's `atan2(dy, dx)` angle

### Requirement: Deterministic modifier lifecycle

The system MUST apply the boolean modifier and delete the cutter in a deterministic order within a single script.

#### Scenario: Apply-then-delete ordering

- GIVEN an opening cutout
- WHEN the script is generated
- THEN the modifier application precedes the cutter deletion
- AND the ordering is stable across regenerations

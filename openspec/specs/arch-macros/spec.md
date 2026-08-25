# arch-macros Specification

## Purpose

Defines the pure bpy code-emitting helpers that produce deterministic Blender Python strings for CSG boolean DIFFERENCE cutters, wall rotation, and OBJ export preparation. The module imports no Blender and its output composes into a single self-contained script.

## Requirements

### Requirement: Deterministic emission

The system MUST emit deterministic bpy code strings without importing Blender, so identical arguments yield byte-identical output.

#### Scenario: Identical arguments produce identical output

- GIVEN the same macro arguments
- WHEN a macro emits its code string
- THEN the returned string is identical across calls
- AND the module imports in an environment with no running Blender

### Requirement: Boolean DIFFERENCE cutter

The system MUST emit code that creates a cutter box overextending past the wall thickness, rotated to the wall's `atan2(dy, dx)` angle, that applies a `BOOLEAN` `DIFFERENCE` modifier on the wall and then deletes the cutter.

#### Scenario: Cutter overextends wall thickness

- GIVEN a wall with a known thickness and an opening on it
- WHEN the cutter emission runs
- THEN the cutter size exceeds the wall thickness along the cut axis

#### Scenario: Cutter shares wall rotation

- GIVEN a non-axis-aligned wall
- WHEN the cutter emission runs
- THEN the cutter rotation equals the wall's `atan2(dy, dx)` angle

### Requirement: Self-contained script embedding

The system MUST emit every helper inline so the generated script runs under a fresh `exec(code, {"bpy": bpy})` namespace with no cross-call state.

#### Scenario: Single-script execution

- GIVEN a generated script
- WHEN it executes in a fresh namespace
- THEN all helpers resolve from within the same script string
- AND no variable or function persists from a prior call

### Requirement: OBJ export preparation

The system MUST emit Blender 4.x `bpy.ops.wm.obj_export` with the caller-supplied filepath, placed after modifiers are applied and meshes joined.

#### Scenario: Export operator emitted with filepath

- GIVEN a caller-supplied filepath
- WHEN export emission runs
- THEN the generated code calls `bpy.ops.wm.obj_export` with that filepath

#### Scenario: Export after modifier application

- GIVEN a model with openings and an export request
- WHEN the script is generated
- THEN modifiers are applied and cutters deleted before the export call

# viewport-controls Specification

## Purpose

CAD/BIM viewport with 4 camera presets, Z+Y section clipping planes, PBR matte materials with edge highlighting, and a HUD status bar showing geometry metrics. All viewport controls live inside GeometryScene.

## Requirements

### Requirement: PBR material and edge highlighting

The system SHALL render all geometry with PBR `meshStandardMaterial` (roughness: 0.85, metalness: 0.0, color: `#94a3b8`). EdgesGeometry wireframes SHALL overlay geometry with `#60a5fa` stroke at `renderOrder: 1` to simulate architectural clay render with edge highlighting.

#### Scenario: Clay material renders on loaded geometry

- GIVEN geometry is loaded from an `.obj` file
- WHEN the scene renders
- THEN all meshes display with matte `#94a3b8` color and roughness 0.85
- AND wireframe edges render in `#60a5fa` with distinct render order

### Requirement: Camera view presets

The system SHALL provide 4 view preset buttons with SVG icons: Top-Down Plan (camera at [0, maxY, 0] looking down), Front Elevation ([0, 0, maxZ] looking forward), Side Elevation ([maxX, 0, 0] looking sideways), Isometric ([maxX, maxY, maxZ] at 45°). Transitions SHALL use `camera.position.lerp` with factor 0.1 over requestAnimationFrame. Active preset SHALL display with accent highlight.

#### Scenario: Switch to Top-Down Plan

- GIVEN geometry is loaded and the camera is at its default auto-fit position
- WHEN the user clicks the Top-Down Plan button
- THEN the camera animates to a position above the model looking down the Y axis
- AND the Top-Down Plan button shows the active accent state

#### Scenario: Active state indicator

- GIVEN the Isometric preset was last clicked
- WHEN the viewport HUD renders
- THEN only the Isometric button shows the active accent highlight

### Requirement: Section clipping planes

The system SHALL support two independent clipping planes: Z-axis horizontal cut (`new THREE.Plane(new THREE.Vector3(0, 0, 1))`) and Y-axis vertical cut (`new THREE.Plane(new THREE.Vector3(0, 1, 0))`). Each plane SHALL have an independent boolean toggle. The renderer's `clippingPlanes` SHALL be set via array concatenation: `[zPlane].concat(yPlane ? [yPlane] : [])` when Z is enabled, or `[yPlane]` when only Y is enabled. Plane position SHALL be adjustable via slider input.

#### Scenario: Both clipping planes active simultaneously

- GIVEN geometry is loaded with both Z and Y clip toggles enabled
- WHEN the scene renders
- THEN `renderer.clippingPlanes` contains both `[zPlane, yPlane]` in the array
- AND geometry is sliced on both axes

#### Scenario: Individual plane toggle independent

- GIVEN only the Z clip toggle is enabled
- WHEN the scene renders
- THEN `renderer.clippingPlanes` contains only `[zPlane]`
- AND Y-axis slice does not affect geometry

#### Scenario: Plane position slider updates cut

- GIVEN the Z clip toggle is enabled with slider at 50%
- WHEN the user drags the Z clip slider to 75%
- THEN `zPlane.constant` updates and the horizontal cut moves upward

### Requirement: HUD metrics bar with SceneStatsContext

The system SHALL provide a SceneStatsContext that exposes `{ triangles, objects, aabbMs }`. The context SHALL require an explicit `setStats` call on geometry load — no implicit ref-to-state propagation. A bottom HUD bar SHALL consume the context and display three metric values in JetBrains Mono: Triangles, Objects, and AABB time (ms). Update frequency SHALL be capped at once per geometry load (not per frame).

#### Scenario: metrics display after geometry load

- GIVEN geometry is parsed and AABB computation completes
- WHEN `setStats({ triangles: 15420, objects: 47, aabbMs: 3.2 })` is called
- THEN the HUD bar renders "Triangles: 15,420 | Objects: 47 | AABB: 3.2ms"
- AND the values use JetBrains Mono with tabular-nums

#### Scenario: Empty state shows dash (—)

- GIVEN no geometry has been loaded or `setStats` has never been called
- WHEN the HUD bar renders
- THEN all three metrics display "—" (not numeric zero)
- AND the HUD uses `aria-live="polite"` for screen reader announcements

#### Scenario: Context does not update implicitly

- GIVEN SceneStatsContext is mounted with default `{ triangles: 0, objects: 0, aabbMs: 0 }`
- WHEN geometry is loaded but `setStats` is not called
- THEN the HUD bar continues to show "—" for all three values

### Requirement: OrbitControls interaction guard

The system SHALL set `pointerEvents: 'none'` on the Drei `Html` wrapper that renders HUD buttons, and SHALL set `pointerEvents: 'auto'` on each interactive child (buttons, sliders) to prevent OrbitControls from capturing HUD clicks.

#### Scenario: HUD button click does not orbit

- GIVEN the HUD buttons are rendered over the viewport
- WHEN the user clicks a View Preset button
- THEN the camera preset activates without triggering an OrbitControls drag
# frontend-validator-dashboard Specification

## Purpose

Defines the Astro 5 + React 19 browser UI (`frontend/`) that uploads an `.obj`, renders it in an interactive SketchUp-style 3D viewport, overlays per-object AABB boxes (green pass / red violation), and lists violations. The UI consumes the FastAPI backend through a Vite dev proxy (`/api` → `127.0.0.1:8000`): `GET /extract-rules` (thresholds), `POST /validate-geometry` (multipart `.obj`), and `POST /autocorrect` (JSON DSL). Geometry is Y-up.

## Requirements

### Requirement: Project scaffold and dev proxy

The system SHALL scaffold a `frontend/` Astro 5 project with React integration and SHALL configure a Vite proxy mapping `/api/*` to `127.0.0.1:8000`.

#### Scenario: Build succeeds

- GIVEN Node.js and npm are installed
- WHEN `npm run build` is executed
- THEN the frontend builds successfully with no errors

#### Scenario: Node.js prerequisite missing

- GIVEN the runtime lacks Node.js/npm
- WHEN the scaffold is installed or built
- THEN the operation fails and surfaces the missing Node.js runtime as the prerequisite to resolve

### Requirement: 3D viewer

The system SHALL render parsed `.obj` geometry in an interactive viewport with Y-up orientation, orbit/pan/zoom controls, a SketchUp-style reference grid, and a camera that auto-fits the loaded geometry.

#### Scenario: Geometry renders

- GIVEN a valid `.obj` file has been uploaded and parsed
- WHEN the viewer mounts
- THEN the geometry renders in the viewport with Y-up orientation
- AND orbit, pan, and zoom controls respond to pointer input

#### Scenario: Auto-fit camera

- GIVEN loaded geometry with non-zero extents
- WHEN the geometry first renders
- THEN the camera frames the entire model so it is fully visible

### Requirement: AABB overlays

The system SHALL compute a per-object AABB client-side from the parsed geometry and SHALL render each box green when its object passes validation and red when the object matches a reported violation (matched by object name).

#### Scenario: Passing object

- GIVEN a validated object with no matching violation
- WHEN the report renders
- THEN the object's AABB overlay renders green

#### Scenario: Violating object

- GIVEN an object whose name matches a violation in the report
- WHEN the report renders
- THEN the object's AABB overlay renders red

### Requirement: Validation data flow

The system SHALL fetch `/api/extract-rules` on mount, SHALL upload the `.obj` to `/api/validate-geometry` as multipart FormData, SHALL render the returned report (geometry, overlays, violations panel), and SHALL re-validate via `/api/autocorrect` with a DSL payload, re-rendering the corrected result.

#### Scenario: Thresholds on mount

- GIVEN the dashboard loads
- WHEN the component mounts
- THEN thresholds are fetched from `/api/extract-rules`

#### Scenario: Upload and validate

- GIVEN a user selects a `.obj` file
- WHEN the upload completes
- THEN the file posts to `/api/validate-geometry` and the returned report renders the geometry, overlays, and violations panel

#### Scenario: Autocorrect re-validate

- GIVEN a rendered violation report
- WHEN the user triggers `/autocorrect` with the DSL payload
- THEN the corrected report re-renders the geometry and overlays

### Requirement: Loading, empty, and error states

The system SHALL present a loading state during network operations and SHALL surface a visible error when the backend is unreachable, the upload fails, or the report is empty.

#### Scenario: Loading

- GIVEN an in-flight request
- WHEN the response is pending
- THEN a loading indicator is shown

#### Scenario: Backend unreachable

- GIVEN the backend is down or the `/api` proxy cannot connect
- WHEN a request is made
- THEN a visible error message indicates the backend is unreachable

#### Scenario: Upload error

- GIVEN an invalid or unreadable upload
- WHEN validation fails
- THEN a visible error message is shown

#### Scenario: Empty report

- GIVEN a report with no objects or an empty geometry
- WHEN it renders
- THEN the viewport shows the empty state without crashing

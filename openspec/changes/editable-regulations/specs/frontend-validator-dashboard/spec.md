# Delta for frontend-validator-dashboard

## ADDED Requirements

### Requirement: Editable regulations tab

The system SHALL render the Regulations tab with four editable threshold inputs (wall min/max height, min/max thickness). Inputs SHALL accept finite, non-negative numbers and SHALL surface a value of `0` as "no limit". The system SHALL validate client-side that each minimum does not exceed its maximum and that all values are non-negative and finite, and SHALL block validate/autocorrect requests with a clear message when thresholds are invalid.

#### Scenario: Edit thresholds and validate

- GIVEN the user edits one or more threshold inputs
- WHEN the user triggers validation
- THEN the edited threshold values are sent with the request

#### Scenario: Zero surfaced as no limit

- GIVEN a threshold input with value `0`
- WHEN the Regulations tab renders
- THEN the input is labeled "no limit" so the user knows the bound is not enforced

#### Scenario: Minimum exceeds maximum blocked client-side

- GIVEN min height greater than max height in the inputs
- WHEN the user triggers validation or autocorrect
- THEN the request is blocked with a clear message and never reaches the backend

#### Scenario: Negative value blocked client-side

- GIVEN a negative value in a threshold input
- WHEN the user triggers validation or autocorrect
- THEN the request is blocked with a clear message and never reaches the backend

#### Scenario: Non-finite value blocked client-side

- GIVEN a NaN or infinite value in a threshold input
- WHEN the user triggers validation or autocorrect
- THEN the request is blocked with a clear message and never reaches the backend

### Requirement: Named normativa profiles

The system SHALL allow saving, loading, and deleting named threshold profiles in `localStorage`. A profile SHALL store the four threshold values under a non-empty name. The system SHALL persist profiles across page reloads and SHALL show which profile is currently active.

#### Scenario: Save profile persists across reload

- GIVEN the user saves a named profile
- WHEN the page is reloaded
- THEN the profile is still listed and selectable

#### Scenario: Load profile sets inputs and active state

- GIVEN a saved profile
- WHEN the user loads it
- THEN the four threshold inputs populate with the profile's values
- AND the active profile indicator shows the loaded profile's name

#### Scenario: Delete profile

- GIVEN a saved profile
- WHEN the user deletes it
- THEN the profile is removed from the list and `localStorage`

#### Scenario: Empty profile name rejected

- GIVEN the user attempts to save a profile with an empty name
- WHEN the save is triggered
- THEN the save is rejected with a clear message and no profile is stored

#### Scenario: Duplicate profile name rejected

- GIVEN an existing profile name
- WHEN the user attempts to save a new profile with the same name
- THEN the save is rejected with a clear message and no duplicate is created

## MODIFIED Requirements

### Requirement: 3-tab sidebar navigation

The system SHALL replace the sequential `<section>` layout with a 3-tab sidebar: Tab 1 "Ingest" (file upload + 2D sketch dropzone), Tab 2 "Regulations" (editable thresholds + named profiles), Tab 3 "Diagnostics" (violations list + AABB status). Only one tab panel SHALL be visible at a time. Tab state SHALL persist in a React `useState` with `activeTab` (0-indexed). Keyboard navigation: ArrowLeft/ArrowRight SHALL move between tabs; Home/End SHALL jump to first/last tab.

(Previously: Tab 2 was a read-only display of extracted rules.)

#### Scenario: Tab switch renders correct panel

- GIVEN the dashboard is on Tab 1 (Ingest)
- WHEN the user clicks Tab 3 (Diagnostics)
- THEN the Ingest panel hides and the Diagnostics panel renders
- AND Tab 3 button shows the active accent state

#### Scenario: Keyboard navigation between tabs

- GIVEN focus is on Tab 1 button
- WHEN the user presses ArrowRight
- THEN focus moves to Tab 2 button and its panel renders

#### Scenario: Tab state survives data load

- GIVEN the user is on Tab 2 (Regulations) editing thresholds
- WHEN a file upload completes and results arrive
- THEN the active tab remains Tab 2 (does not reset to Tab 1)

### Requirement: Validation data flow

The system SHALL fetch `/api/extract-rules` on mount as the default thresholds, SHALL upload the `.obj` to `/api/validate-geometry` as multipart FormData carrying the current threshold values, SHALL render the returned report (geometry, overlays, violations panel), and SHALL re-validate via `/api/autocorrect` with a DSL payload and the SAME current threshold values, re-rendering the corrected result.

(Previously: fetched thresholds read-only and sent no thresholds with validate/autocorrect.)

#### Scenario: Thresholds on mount

- GIVEN the dashboard loads
- WHEN the component mounts
- THEN default thresholds are fetched from `/api/extract-rules` and populate the inputs

#### Scenario: Upload and validate with thresholds

- GIVEN a user selects a `.obj` file
- WHEN the upload completes
- THEN the file posts to `/api/validate-geometry` with the current threshold values and the returned report renders the geometry, overlays, and violations panel

#### Scenario: Autocorrect re-validate with thresholds

- GIVEN a rendered violation report
- WHEN the user triggers `/autocorrect` with the DSL payload
- THEN the request carries the current threshold values and the corrected report re-renders the geometry and overlays

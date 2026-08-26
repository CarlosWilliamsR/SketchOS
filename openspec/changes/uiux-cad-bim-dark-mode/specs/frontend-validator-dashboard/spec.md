# Delta for frontend-validator-dashboard

## ADDED Requirements

### Requirement: 3-tab sidebar navigation

The system SHALL replace the sequential `<section>` layout with a 3-tab sidebar: Tab 1 "Ingest" (file upload + 2D sketch dropzone), Tab 2 "Regulations" (extracted rules display), Tab 3 "Diagnostics" (violations list + AABB status). Only one tab panel SHALL be visible at a time. Tab state SHALL persist in a React `useState` with `activeTab` (0-indexed). Keyboard navigation: ArrowLeft/ArrowRight SHALL move between tabs; Home/End SHALL jump to first/last tab.

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

- GIVEN the user is on Tab 2 (Regulations) viewing thresholds
- WHEN a file upload completes and results arrive
- THEN the active tab remains Tab 2 (does not reset to Tab 1)

### Requirement: SVG icon headers

The system SHALL render a minimal technical SVG icon (16×16 viewBox, `currentColor` fill, `1.5px` stroke) next to each tab label and each panel section header. Available icons: `UploadIcon`, `SketchIcon`, `RulesIcon`, `DiagnosticsIcon`, `WarningIcon`, `PassIcon`, `ApiKeyIcon`. Icons SHALL inherit color from the parent element via `currentColor` and SHALL scale with `--space-md` width/height.

#### Scenario: Icons render next to tab labels

- GIVEN the dashboard renders with 3 tabs
- WHEN each tab button mounts
- THEN each tab label has an SVG icon to its left with color matching `--text-secondary`

#### Scenario: Icon color inherits from CSS variable

- GIVEN a violation section header uses `color: var(--violation)`
- WHEN the WarningIcon renders inside that header
- THEN the icon stroke/fill matches the red `--violation` color

### Requirement: Dark-themed panel styles

The system SHALL style the sidebar panel with `--bg-secondary` background, `--border` separators, `--text-primary` headings, and `--text-secondary` body text. Upload inputs, buttons, textareas, and status banners SHALL reference dark-theme CSS tokens exclusively. No light-theme values (`#f5f5f5`, `#202124`) SHALL remain in panel selectors.

#### Scenario: Sidebar renders dark theme

- GIVEN the dark theme CSS tokens are loaded
- WHEN the dashboard mounts
- THEN the sidebar background is `var(--bg-secondary)`
- AND all text colors are `var(--text-primary)` or `var(--text-secondary)`
- AND no `#f5f5f5` or `#202124` hardcoded colors are visible

#### Scenario: Upload button styled for dark theme

- GIVEN the dark theme is active
- WHEN the file upload input renders
- THEN it uses `var(--accent)` for border/focus and `var(--bg-tertiary)` for background
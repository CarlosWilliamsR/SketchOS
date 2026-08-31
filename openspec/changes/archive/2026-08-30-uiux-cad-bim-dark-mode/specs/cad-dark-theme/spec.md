# cad-dark-theme Specification

## Purpose

Global CAD/BIM dark studio theme: CSS custom properties for colors, spacing, and typography matching professional architectural software conventions. Loads Inter (UI) and JetBrains Mono (metrics) via Google Fonts in Layout.astro.

## Requirements

### Requirement: Dark palette CSS custom properties

The system SHALL define `:root` CSS custom properties for a dark CAD/BIM palette:
- `--bg-primary: #0b0f19`, `--bg-secondary: #111827`, `--bg-tertiary: #1e293b`
- `--accent: #2563eb`, `--accent-hover: #1d4ed8`
- `--text-primary: #f1f5f9`, `--text-secondary: #94a3b8`, `--text-muted: #64748b`
- `--border: #334155`, `--pass: #22c55e`, `--violation: #ef4444`
- `--viewport-bg: #0b0f19`, `--panel-bg: #111827`

And SHALL apply them to `html, body` as `background: var(--bg-primary); color: var(--text-primary)`.

#### Scenario: Dark palette renders on load

- GIVEN the page loads with no user interaction
- WHEN the CSS applies `:root` tokens
- THEN the viewport background is `#0b0f19`
- AND sidebar panels render with `#111827` background and `#334155` borders

#### Scenario: Old selectors survive palette change

- GIVEN existing component selectors reference `--pass` and `--violation`
- WHEN the new `:root` block is loaded
- THEN AABB overlays still render green for passing and red for violating objects

### Requirement: Typography tokens

The system SHALL define font-family tokens: `--font-sans: 'Inter', sans-serif` for UI text and `--font-mono: 'JetBrains Mono', monospace` for numeric metrics. Body text SHALL use `--font-sans`. Metrics displays SHALL use `--font-mono` with tabular-nums.

#### Scenario: Inter font renders for UI labels

- GIVEN Inter is loaded via Google Fonts
- WHEN a tab label or button renders
- THEN the text uses the Inter sans-serif font family

#### Scenario: JetBrains Mono renders for metric values

- GIVEN JetBrains Mono is loaded via Google Fonts
- WHEN a numeric metric (triangles, objects, ms) renders
- THEN the value uses JetBrains Mono with `font-variant-numeric: tabular-nums`

### Requirement: Spacing tokens

The system SHALL define spacing scale tokens: `--space-xs: 4px`, `--space-sm: 8px`, `--space-md: 16px`, `--space-lg: 24px`, `--space-xl: 32px`.

#### Scenario: Consistent spacing across components

- GIVEN the spacing tokens are defined in `:root`
- WHEN any component (tabs, HUD, modal) applies padding or gap
- THEN spacing references a `--space-*` token, not a raw pixel value

### Requirement: Layout.astro font loading

The system SHALL load Inter (weights 400, 500, 600) and JetBrains Mono (weight 400) from Google Fonts via `<link>` tags in `<head>` of Layout.astro, and SHALL preconnect to `fonts.googleapis.com` and `fonts.gstatic.com`.

#### Scenario: Fonts load before first paint

- GIVEN the frontend is served from Layout.astro
- WHEN the browser parses `<head>`
- THEN preconnect hints and font `<link>` tags appear before any render-blocking CSS
- AND Inter and JetBrains Mono are available when the first component mounts
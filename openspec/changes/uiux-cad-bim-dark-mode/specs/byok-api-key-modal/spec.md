# byok-api-key-modal Specification

## Purpose

Bring-Your-Own-Key modal for Gemini API key entry, localStorage persistence, validation, masked display, and graceful fallback. Injects `X-Gemini-Api-Key` header into all fetch requests via `api.js`.

## Requirements

### Requirement: Modal open, close, and trigger

The system SHALL render a trigger button labeled "⚙️ API Key" in the dashboard sidebar header. On click, the button SHALL open a modal overlay; pressing Escape or clicking the backdrop SHALL close it.

#### Scenario: Open modal

- GIVEN the dashboard is loaded and no key is stored
- WHEN the user clicks "⚙️ API Key"
- THEN a modal overlay with the BYOK form renders, focused on the key input

#### Scenario: Close via Escape

- GIVEN the BYOK modal is open
- WHEN the user presses Escape
- THEN the modal closes and focus returns to the trigger button

### Requirement: Key input and localStorage persistence

The system SHALL provide a `<input type="password">` for key entry. On save, the key SHALL be stored in `localStorage` under the key `gemini_api_key`. On mount, the modal SHALL read from `localStorage` and display a masked version (`••••` + last 4 chars when key > 4 chars).

#### Scenario: Save API key

- GIVEN the modal is open with a valid key entered
- WHEN the user clicks "Save"
- THEN the key persists to `localStorage` under `gemini_api_key`
- AND the input shows a masked display

#### Scenario: Pre-filled on re-open

- GIVEN a key was previously saved
- WHEN the modal opens again
- THEN the input shows `••••xxxx` (last 4 chars of stored key)

### Requirement: Key validation

The system SHALL validate that the key is non-empty and at least 10 characters. An empty or too-short key SHALL show an inline error and disable the Save button.

#### Scenario: Save blocked for empty key

- GIVEN the modal is open with an empty input
- WHEN the user clicks "Save"
- THEN the button is disabled and an inline error "Key must be at least 10 characters" is shown

### Requirement: Clear and rotate

The system SHALL provide a "Clear" button that removes the key from `localStorage` and empties the input. A "Rotate" action SHALL clear the existing key and keep the modal open for a new key.

#### Scenario: Clear stored key

- GIVEN a key is stored in localStorage
- WHEN the user clicks "Clear"
- THEN the key is removed from localStorage and the input is empty

### Requirement: Graceful fallback when key is missing

The system SHALL render the trigger button with a warning style (`--violation` accent) when no key is stored. If a fetch response returns 401/403, the dashboard SHALL surface the missing/invalid key state without crashing.

#### Scenario: Warning when no key stored

- GIVEN `gemini_api_key` is absent from localStorage
- WHEN the dashboard mounts
- THEN the "⚙️ API Key" button renders with a warning indicator

### Requirement: Header injection in api.js

The `fetch` wrapper in `api.js` SHALL read `gemini_api_key` from `localStorage` on every request. If present and non-empty, the wrapper SHALL inject the header `X-Gemini-Api-Key: {value}`. The proxy rewrite `/api` → `''` SHALL be preserved.

#### Scenario: Header injected on all requests

- GIVEN a key is stored in localStorage
- WHEN any `api.js` function makes a fetch request
- THEN the `X-Gemini-Api-Key` header is present with the stored key value
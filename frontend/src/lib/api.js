// API client for the SketchOS validator backend.
//
// Every request goes through the same-origin `/api/*` prefix; the Astro Vite
// dev proxy rewrites `/api` off and forwards to FastAPI on 127.0.0.1:8000.
// Error responses carry a FastAPI `detail` string (422 parse error, 503 spawn
// failure, 504 timeout) that we surface to the user.

/** Error raised for non-2xx responses or network failure. */
export class ApiError extends Error {
  constructor(status, detail, cause) {
    super(detail || `Request failed with status ${status}`);
    this.name = 'ApiError';
    this.status = status;
    if (cause) this.cause = cause;
  }
}

async function request(path, options) {
  // Inject BYOK header from localStorage on every request.
  const apiKey = localStorage.getItem('gemini_api_key');
  if (apiKey && apiKey.length > 0) {
    if (!options) options = {};
    if (!options.headers) options.headers = {};
    options.headers['X-Gemini-Api-Key'] = apiKey;
  }

  let response;
  try {
    response = await fetch(`/api${path}`, options);
  } catch (cause) {
    // Network failure (backend down or proxy unreachable).
    throw new ApiError(0, 'Backend unreachable — is the server running?', cause);
  }

  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json();
      if (typeof body?.detail === 'string') detail = body.detail;
    } catch {
      // Non-JSON error body; fall back to the status-derived message below.
    }
    throw new ApiError(response.status, detail);
  }

  return response.json();
}

/**
 * Fetch the normativa thresholds from the backend.
 * @returns {Promise<{min_height:number, max_height:number, min_thickness:number, max_thickness:number}>}
 */
export function fetchRules() {
  return request('/extract-rules');
}

/**
 * The four per-request threshold keys (wire shape shared by both endpoints).
 * Each value is a number; `0` means "unenforced" (no limit).
 */
const THRESHOLD_KEYS = ['min_height', 'max_height', 'min_thickness', 'max_thickness'];

/**
 * Upload an `.obj` File and validate it against optional per-request thresholds.
 * @param {File} file The selected `.obj` file.
 * @param {{min_height?:number, max_height?:number, min_thickness?:number, max_thickness?:number}} [thresholds]
 *   Optional thresholds; supplied fields are appended as form fields, omitted
 *   fields fall back to the backend defaults. `0` is sent as "0" (unenforced).
 * @returns {Promise<{status: string, report: object}>}
 */
export function validateGeometry(file, thresholds) {
  const form = new FormData();
  form.append('file', file, file.name);
  if (thresholds) {
    for (const key of THRESHOLD_KEYS) {
      const value = thresholds[key];
      if (value !== undefined && value !== null) {
        form.append(key, String(value));
      }
    }
  }
  return request('/validate-geometry', { method: 'POST', body: form });
}

/**
 * Generate a schema-valid ArchitecturalDSL from a natural-language prompt.
 * @param {string} prompt The architect's natural-language description.
 * @returns {Promise<{architecture: object}>}
 */
export function generateFromText(prompt) {
  return request('/generate-from-text', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  });
}

/**
 * Re-codegen corrected geometry from a full DSL payload and re-validate it.
 * @param {object} dsl Full ArchitecturalDSL payload (JSON-serializable).
 * @param {{min_height?:number, max_height?:number, min_thickness?:number, max_thickness?:number}} [thresholds]
 *   Optional thresholds merged into the JSON body under a `thresholds` key;
 *   the SAME thresholds apply to both the re-validate passes.
 * @returns {Promise<{status: string, report: object, fixes: object[]}>}
 */
export function autocorrect(dsl, thresholds) {
  return request('/autocorrect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...dsl, ...(thresholds ? { thresholds } : {}) }),
  });
}

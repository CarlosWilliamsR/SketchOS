// Integration tests for the API client in api.js.
//
// `fetch` is stubbed so we can assert the exact URL, method, and body shape
// without a running backend. Node's global FormData / File / Response are used
// directly — the production code path is exercised end-to-end up to the fetch
// boundary.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fetchRules, validateGeometry, autocorrect, ApiError } from './api.js';

let fetchMock;

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('fetchRules', () => {
  it('GETs /api/extract-rules with no body', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ min_height: 2.0, max_height: 0.0 }));

    const rules = await fetchRules();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/extract-rules');
    expect(options).toBeUndefined();
    expect(rules).toEqual({ min_height: 2.0, max_height: 0.0 });
  });
});

describe('validateGeometry', () => {
  it('POSTs multipart FormData with a `file` field to /api/validate-geometry', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ status: 'pass', report: { objects: [] } }));

    const file = new File(['v 0 0 0\n'], 'wall.obj', { type: 'text/plain' });
    const result = await validateGeometry(file);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/validate-geometry');
    expect(options.method).toBe('POST');

    const form = options.body;
    expect(form).toBeInstanceOf(FormData);
    expect(form.has('file')).toBe(true);
    expect(form.get('file').name).toBe('wall.obj');

    expect(result).toEqual({ status: 'pass', report: { objects: [] } });
  });
});

describe('autocorrect', () => {
  it('POSTs a JSON DSL body with Content-Type application/json to /api/autocorrect', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ status: 'violations', report: {}, fixes: [{ wall_id: 'w1' }] }),
    );

    const dsl = { walls: [{ id: 'wall_1', height: 1.5 }], floors: [] };
    const result = await autocorrect(dsl);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/autocorrect');
    expect(options.method).toBe('POST');
    expect(options.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(options.body)).toEqual(dsl);

    expect(result).toEqual({ status: 'violations', report: {}, fixes: [{ wall_id: 'w1' }] });
  });
});

describe('error handling', () => {
  it('throws ApiError with status and FastAPI detail on a non-2xx response', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ detail: 'stderr: parse failure' }, 422),
    );

    await expect(validateGeometry(new File(['x'], 'x.obj'))).rejects.toMatchObject({
      name: 'ApiError',
      status: 422,
      message: 'stderr: parse failure',
    });
  });

  it('throws ApiError with status 0 when the network is unreachable', async () => {
    fetchMock.mockRejectedValue(new TypeError('fetch failed'));

    await expect(fetchRules()).rejects.toMatchObject({
      name: 'ApiError',
      status: 0,
      message: expect.stringContaining('Backend unreachable'),
    });
  });

  it('falls back to a status-derived message on a non-JSON error body', async () => {
    fetchMock.mockResolvedValue(new Response('Internal Server Error', { status: 500 }));

    await expect(fetchRules()).rejects.toMatchObject({
      name: 'ApiError',
      status: 500,
      message: 'Request failed with status 500',
    });
  });

  it('ApiError extends Error', () => {
    const err = new ApiError(503, 'spawn failed');
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe('ApiError');
  });
});

describe('BYOK header injection', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('injects X-Gemini-Api-Key header when key is in localStorage', async () => {
    localStorage.setItem('gemini_api_key', 'sk-test-key-123456');
    fetchMock.mockResolvedValue(jsonResponse({ min_height: 2.0 }));

    await fetchRules();

    const [, options] = fetchMock.mock.calls[0];
    expect(options).toBeDefined();
    expect(options.headers).toBeDefined();
    expect(options.headers['X-Gemini-Api-Key']).toBe('sk-test-key-123456');
  });

  it('does not inject X-Gemini-Api-Key header when no key in localStorage', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ min_height: 2.0 }));

    await fetchRules();

    const [, options] = fetchMock.mock.calls[0];
    // When no key is stored, the function may be called with undefined options
    // (GET with no body) or with options that don't include the header.
    if (options) {
      expect(options.headers?.['X-Gemini-Api-Key']).toBeUndefined();
    }
  });

  it('does not inject header when localStorage key is empty string', async () => {
    localStorage.setItem('gemini_api_key', '');
    fetchMock.mockResolvedValue(jsonResponse({ min_height: 2.0 }));

    await fetchRules();

    const [, options] = fetchMock.mock.calls[0];
    if (options) {
      expect(options.headers?.['X-Gemini-Api-Key']).toBeUndefined();
    }
  });

  it('preserves /api proxy prefix on all requests', async () => {
    localStorage.setItem('gemini_api_key', 'sk-key');
    // Each fetch call must return a fresh response (body can only be consumed once)
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ min_height: 2.0 }))
      .mockResolvedValueOnce(jsonResponse({ status: 'pass', report: {}, fixes: [] }));

    await fetchRules();
    expect(fetchMock.mock.calls[0][0]).toBe('/api/extract-rules');

    const dsl = { walls: [] };
    await autocorrect(dsl);
    expect(fetchMock.mock.calls[1][0]).toBe('/api/autocorrect');
  });

  it('injects header on POST requests with existing headers', async () => {
    localStorage.setItem('gemini_api_key', 'sk-post-key');
    fetchMock.mockResolvedValue(jsonResponse({ status: 'pass', report: {}, fixes: [] }));

    const dsl = { walls: [{ id: 'w1', height: 2.0 }] };
    await autocorrect(dsl);

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers['Content-Type']).toBe('application/json');
    expect(options.headers['X-Gemini-Api-Key']).toBe('sk-post-key');
  });
});

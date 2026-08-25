// Vitest configuration for the SketchOS validator dashboard.
//
// Tests are pure logic (OBJ vertex grouping / AABB / color mapping in obj.js
// and the API client URL/FormData/body shape in api.js) and run in a Node
// environment — no browser, DOM, WebGL, or R3F rendering is required.

import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.js'],
  },
});

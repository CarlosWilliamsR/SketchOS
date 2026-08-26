// Vitest configuration for the SketchOS validator dashboard.
//
// Tests use jsdom so component tests can access DOM APIs (CSS custom properties,
// computed styles, render output). Pure-logic tests (obj.js, api.js) also run
// correctly under jsdom — they don't require a browser, DOM, WebGL, or R3F.

import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.js', 'src/**/*.test.jsx'],
  },
});

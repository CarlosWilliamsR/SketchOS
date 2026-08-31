// Layout.astro Google Fonts loading test.
//
// Astro layouts compile to static HTML at build time, so the simplest and most
// robust way to verify the font preconnects and the stylesheet link is a
// source-content assertion on the .astro file itself — the same approach
// global.css.test.js uses to read the shipped CSS. Runtime font resolution is
// covered by the `npm run build` / `npm run dev` render harness.

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const layoutPath = resolve(import.meta.dirname, '../Layout.astro');
const layoutContent = readFileSync(layoutPath, 'utf-8');

describe('Layout.astro Google Fonts loading', () => {
  it('preconnects to the Google Fonts CSS origin', () => {
    expect(layoutContent).toContain(
      'rel="preconnect" href="https://fonts.googleapis.com"',
    );
  });

  it('preconnects to the Google Fonts static origin with crossorigin', () => {
    expect(layoutContent).toContain(
      'rel="preconnect" href="https://fonts.gstatic.com" crossorigin',
    );
  });

  it('loads Inter at weights 400, 500, 600 via the stylesheet link', () => {
    expect(layoutContent).toMatch(/family=Inter:wght@400;500;600/);
  });

  it('loads JetBrains Mono at weight 400 via the stylesheet link', () => {
    expect(layoutContent).toMatch(/family=JetBrains\+Mono:wght@400/);
  });

  it('declares a stylesheet link against the Google Fonts css2 endpoint', () => {
    expect(layoutContent).toMatch(
      /href="https:\/\/fonts\.googleapis\.com\/css2\?family=Inter/,
    );
    expect(layoutContent).toContain('rel="stylesheet"');
  });
});

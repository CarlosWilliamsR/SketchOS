// Dark-theme CSS custom property tests.
//
// jsdom does NOT resolve CSS custom properties via getComputedStyle
// (known limitation). Instead we parse the global.css :root block and
// verify every token declaration directly against the spec values.
// This proves the tokens exist in the shipped CSS — the runtime
// resolution is verified by the browser render harness (`npm run dev`).

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const cssPath = resolve(import.meta.dirname, '../global.css');
const cssContent = readFileSync(cssPath, 'utf-8');

/** Extract the :root block from CSS (first one found). */
function extractRootBlock(css) {
  const match = css.match(/:root\s*\{([^}]*)\}/s);
  if (!match) return '';
  return match[1];
}

/** Parse a CSS declaration block into a Map of property → value. */
function parseDeclarations(block) {
  const map = new Map();
  const re = /(--[\w-]+)\s*:\s*([^;]+)/g;
  let m;
  while ((m = re.exec(block)) !== null) {
    map.set(m[1].trim(), m[2].trim());
  }
  return map;
}

const rootBlock = extractRootBlock(cssContent);
const declarations = parseDeclarations(rootBlock);

describe('dark palette :root tokens', () => {
  const darkTokens = {
    '--bg-primary': '#0b0f19',
    '--bg-secondary': '#111827',
    '--bg-tertiary': '#1e293b',
    '--accent': '#2563eb',
    '--accent-hover': '#1d4ed8',
    '--text-primary': '#f1f5f9',
    '--text-secondary': '#94a3b8',
    '--text-muted': '#64748b',
    '--border': '#334155',
    '--pass': '#22c55e',
    '--violation': '#ef4444',
    '--viewport-bg': '#0b0f19',
  };

  it.each(Object.entries(darkTokens))(
    '%s is defined as %s',
    (varName, expectedValue) => {
      expect(declarations.has(varName)).toBe(true);
      expect(declarations.get(varName)).toBe(expectedValue);
    },
  );

  it(':root block exists and contains at least 20 custom properties', () => {
    expect(rootBlock.length).toBeGreaterThan(0);
    expect(declarations.size).toBeGreaterThanOrEqual(20);
  });
});

describe('typography tokens', () => {
  it('--font-sans is defined as Inter', () => {
    expect(declarations.get('--font-sans')).toBe("'Inter', sans-serif");
  });

  it('--font-mono is defined as JetBrains Mono', () => {
    expect(declarations.get('--font-mono')).toBe("'JetBrains Mono', monospace");
  });
});

describe('spacing tokens', () => {
  const spacingTokens = {
    '--space-xs': '4px',
    '--space-sm': '8px',
    '--space-md': '16px',
    '--space-lg': '24px',
    '--space-xl': '32px',
  };

  it.each(Object.entries(spacingTokens))(
    '%s is defined as %s',
    (varName, expectedValue) => {
      expect(declarations.get(varName)).toBe(expectedValue);
    },
  );
});

describe('hardcoded color removal', () => {
  // The entire CSS file after :root should reference only var(--...) for
  // colors — no hex values from the old light theme should leak.
  const afterRoot = cssContent.slice(cssContent.indexOf('}', cssContent.indexOf(':root')) + 1);

  const forbiddenColors = ['#f5f5f5', '#202124', '#5f6368', '#c9ccd0', '#e6f4ea', '#fce8e6'];

  it.each(forbiddenColors)(
    'does not contain old light-theme hex %s outside :root',
    (hex) => {
      expect(afterRoot).not.toContain(hex);
    },
  );

  it('does not contain #fff in structural background roles', () => {
    // #fff is still valid on button text (accent background + white text
    // works on dark theme). But structural backgrounds (upload, banners)
    // should use tokens. Verify the upload-control no longer has `background: #fff`.
    const uploadRule = cssContent.match(/\.upload-control\s*\{[^}]*}/s);
    if (uploadRule) {
      expect(uploadRule[0]).not.toContain('#fff');
    }
  });
});

describe('legacy var(--pass) and var(--violation) survival', () => {
  it('selectors reference var(--pass) for green indicators', () => {
    expect(cssContent).toMatch(/var\(--pass\)/);
  });

  it('selectors reference var(--violation) for red indicators', () => {
    expect(cssContent).toMatch(/var\(--violation\)/);
  });
});
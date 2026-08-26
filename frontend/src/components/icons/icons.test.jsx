// SVG icon component tests.
//
// Each icon is a React component that renders an inline SVG. Tests verify:
// - 16×16 viewBox
// - currentColor fill/stroke (inherits from parent)
// - 1.5px stroke-width
// - No emoji or text content (purely geometric)
// - Accessible role="img" with aria-label
//
// Uses render() container queries to avoid DOM pollution across describe.each.

import React from 'react';
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';

import { UploadIcon } from './UploadIcon.jsx';
import { SketchIcon } from './SketchIcon.jsx';
import { RulesIcon } from './RulesIcon.jsx';
import { DiagnosticsIcon } from './DiagnosticsIcon.jsx';
import { WarningIcon } from './WarningIcon.jsx';
import { PassIcon } from './PassIcon.jsx';
import { ApiKeyIcon } from './ApiKeyIcon.jsx';

const icons = [
  { name: 'UploadIcon', Component: UploadIcon, label: 'Upload' },
  { name: 'SketchIcon', Component: SketchIcon, label: 'Sketch' },
  { name: 'RulesIcon', Component: RulesIcon, label: 'Rules' },
  { name: 'DiagnosticsIcon', Component: DiagnosticsIcon, label: 'Diagnostics' },
  { name: 'WarningIcon', Component: WarningIcon, label: 'Warning' },
  { name: 'PassIcon', Component: PassIcon, label: 'Pass' },
  { name: 'ApiKeyIcon', Component: ApiKeyIcon, label: 'API Key' },
];

describe.each(icons)('$name', ({ Component, label }) => {
  function getSvg(container) {
    const svg = container.querySelector('svg');
    if (!svg) throw new Error(`No SVG found in container for ${label}`);
    return svg;
  }

  it('renders an SVG with 16×16 viewBox', () => {
    const { container } = render(<Component />);
    const svg = getSvg(container);
    expect(svg.tagName).toBe('svg');
    expect(svg.getAttribute('viewBox')).toBe('0 0 16 16');
  });

  it('uses currentColor and fill=none', () => {
    const { container } = render(<Component />);
    const svg = getSvg(container);
    expect(svg.getAttribute('fill')).toBe('none');
    expect(svg.getAttribute('stroke')).toBe('currentColor');
  });

  it('has 1.5px stroke-width', () => {
    const { container } = render(<Component />);
    const svg = getSvg(container);
    expect(svg.getAttribute('stroke-width')).toBe('1.5');
  });

  it('contains only geometric elements — no emoji or text', () => {
    const { container } = render(<Component />);
    const svg = getSvg(container);
    const innerHTML = svg.innerHTML;
    // No emoji ranges: U+1F300–U+1FAFF, U+2600–U+27BF
    const emojiPattern = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u;
    expect(innerHTML).not.toMatch(emojiPattern);
    // Must have at least one geometric element
    const hasGeometry =
      innerHTML.includes('<path') ||
      innerHTML.includes('<line') ||
      innerHTML.includes('<circle') ||
      innerHTML.includes('<rect') ||
      innerHTML.includes('<polyline') ||
      innerHTML.includes('<polygon');
    expect(hasGeometry).toBe(true);
  });

  it('accepts a custom className', () => {
    const { container } = render(<Component className="my-icon" />);
    const svg = getSvg(container);
    expect(svg.classList.contains('my-icon')).toBe(true);
  });

  it('has role=img and the correct aria-label', () => {
    const { container } = render(<Component />);
    const svg = getSvg(container);
    expect(svg.getAttribute('role')).toBe('img');
    expect(svg.getAttribute('aria-label')).toBe(label);
  });
});
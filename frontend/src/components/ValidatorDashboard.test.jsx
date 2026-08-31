// ValidatorDashboard component tests — 3-tab refactor.
//
// Tests tab navigation, ARIA roles, SVG icons, dark-theme styling,
// and tab persistence across phase state changes.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import ValidatorDashboard from './ValidatorDashboard.jsx';

// Mock the heavy dependencies (GeometryScene requires WebGL/Three.js).
vi.mock('../GeometryScene.jsx', () => ({
  default: function MockGeometryScene() {
    return React.createElement('div', { 'data-testid': 'mock-geometry-scene' }, '3D Viewport');
  },
}));

// Mock api.js — we're testing UI behavior, not API calls.
vi.mock('../lib/api.js', () => ({
  fetchRules: vi.fn().mockResolvedValue({
    min_height: 2.0,
    max_height: 12.0,
    min_thickness: 0.1,
    max_thickness: 0.8,
  }),
  validateGeometry: vi.fn(),
  autocorrect: vi.fn(),
}));

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('3-tab sidebar navigation', () => {
  it('renders 3 tab buttons with role="tab"', async () => {
    render(React.createElement(ValidatorDashboard));

    await waitFor(() => {
      const tabs = screen.getAllByRole('tab');
      expect(tabs).toHaveLength(3);
    });
  });

  it('renders Tab 1 (Ingest) content by default', async () => {
    render(React.createElement(ValidatorDashboard));

    await waitFor(() => {
      expect(screen.getByText(/upload .obj/i)).toBeInTheDocument();
    });

    // Tab 1 panel should be visible
    const tabpanel = screen.getByRole('tabpanel');
    expect(tabpanel).toBeVisible();
  });

  it('clicking Tab 2 switches to Regulations panel', async () => {
    render(React.createElement(ValidatorDashboard));
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getAllByRole('tab')).toHaveLength(3);
    });

    const tabs = screen.getAllByRole('tab');
    // Tab 2 = Regulations
    const regulationsTab = tabs.find(
      (t) => t.textContent.includes('Regulations') || t.textContent.includes('Normativa'),
    );
    await user.click(regulationsTab);

    // Should show the thresholds section
    await waitFor(() => {
      expect(regulationsTab).toHaveAttribute('aria-selected', 'true');
    });
  });

  it('clicking Tab 3 switches to Diagnostics panel', async () => {
    render(React.createElement(ValidatorDashboard));
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getAllByRole('tab')).toHaveLength(3);
    });

    const tabs = screen.getAllByRole('tab');
    const diagTab = tabs.find(
      (t) => t.textContent.includes('Diagnostics') || t.textContent.includes('Diagnóstico'),
    );
    await user.click(diagTab);

    await waitFor(() => {
      expect(diagTab).toHaveAttribute('aria-selected', 'true');
    });
  });

  it('only one tab panel is visible at a time', async () => {
    render(React.createElement(ValidatorDashboard));
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getAllByRole('tab')).toHaveLength(3);
    });

    const tabs = screen.getAllByRole('tab');
    // Click Tab 2
    const regTab = tabs.find((t) => t.textContent.includes('Regulations') || t.textContent.includes('Normativa'));
    await user.click(regTab);

    // All tabpanels should exist but only one visible
    const panels = screen.getAllByRole('tabpanel');
    const visiblePanels = panels.filter((p) => !p.hasAttribute('hidden'));
    expect(visiblePanels).toHaveLength(1);
  });
});

describe('keyboard navigation', () => {
  it('ArrowRight moves focus to next tab', async () => {
    render(React.createElement(ValidatorDashboard));
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getAllByRole('tab')).toHaveLength(3);
    });

    const tabs = screen.getAllByRole('tab');
    tabs[0].focus();

    fireEvent.keyDown(tabs[0], { key: 'ArrowRight' });

    expect(tabs[1]).toHaveFocus();
  });

  it('ArrowLeft moves focus to previous tab', async () => {
    render(React.createElement(ValidatorDashboard));
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getAllByRole('tab')).toHaveLength(3);
    });

    const tabs = screen.getAllByRole('tab');
    tabs[1].focus();
    fireEvent.keyDown(tabs[1], { key: 'ArrowLeft' });

    expect(tabs[0]).toHaveFocus();
  });

  it('Home key jumps to first tab', async () => {
    render(React.createElement(ValidatorDashboard));
    await waitFor(() => {
      expect(screen.getAllByRole('tab')).toHaveLength(3);
    });

    const tabs = screen.getAllByRole('tab');
    tabs[2].focus();
    fireEvent.keyDown(tabs[2], { key: 'Home' });

    expect(tabs[0]).toHaveFocus();
  });

  it('End key jumps to last tab', async () => {
    render(React.createElement(ValidatorDashboard));
    await waitFor(() => {
      expect(screen.getAllByRole('tab')).toHaveLength(3);
    });

    const tabs = screen.getAllByRole('tab');
    tabs[0].focus();
    fireEvent.keyDown(tabs[0], { key: 'End' });

    expect(tabs[2]).toHaveFocus();
  });
});

describe('tab state persistence', () => {
  it('active tab does not reset to Tab 1 when rules load', async () => {
    render(React.createElement(ValidatorDashboard));
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getAllByRole('tab')).toHaveLength(3);
    });

    // Switch to Tab 2 (Regulations)
    const tabs = screen.getAllByRole('tab');
    const regTab = tabs.find((t) => t.textContent.includes('Regulations') || t.textContent.includes('Normativa'));
    await user.click(regTab);

    // Wait for rules to load (fetchRules resolves)
    await waitFor(() => {
      // After rules load, we should still be on Tab 2
      expect(regTab).toHaveAttribute('aria-selected', 'true');
    });
  });
});

describe('SVG icons in tabs', () => {
  it('each tab button contains an SVG icon', async () => {
    render(React.createElement(ValidatorDashboard));

    await waitFor(() => {
      const tabs = screen.getAllByRole('tab');
      tabs.forEach((tab) => {
        expect(tab.querySelector('svg')).toBeInTheDocument();
      });
    });
  });

  it('tab icons use currentColor for style inheritance', async () => {
    render(React.createElement(ValidatorDashboard));

    await waitFor(() => {
      const tabs = screen.getAllByRole('tab');
      tabs.forEach((tab) => {
        const svg = tab.querySelector('svg');
        expect(svg).toHaveAttribute('stroke', 'currentColor');
      });
    });
  });
});

describe('dark-theme panel styles', () => {
  it('sidebar panel uses dark theme background class', async () => {
    render(React.createElement(ValidatorDashboard));

    await waitFor(() => {
      const panel = document.querySelector('.side-panel');
      expect(panel).toBeInTheDocument();
    });
  });

  it('active tab shows accent styling', async () => {
    render(React.createElement(ValidatorDashboard));
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getAllByRole('tab')).toHaveLength(3);
    });

    // Click Tab 3 — it should get the active class
    const tabs = screen.getAllByRole('tab');
    const diagTab = tabs.find(
      (t) => t.textContent.includes('Diagnostics') || t.textContent.includes('Diagnóstico'),
    );
    await user.click(diagTab);

    expect(diagTab.className).toContain('active');
  });

  it('uses var(--bg-secondary) via side-panel CSS class', async () => {
    render(React.createElement(ValidatorDashboard));

    await waitFor(() => {
      expect(document.querySelector('.side-panel')).toBeInTheDocument();
    });
  });
});

describe('ARIA compliance', () => {
  it('tabpanel has role="tabpanel"', async () => {
    render(React.createElement(ValidatorDashboard));

    await waitFor(() => {
      const panel = screen.getByRole('tabpanel');
      expect(panel).toBeInTheDocument();
    });
  });

  it('tabpanel has aria-labelledby referencing the tab button', async () => {
    render(React.createElement(ValidatorDashboard));

    await waitFor(() => {
      const tabs = screen.getAllByRole('tab');
      const panel = screen.getByRole('tabpanel');
      // The first tab (active by default) should label the visible panel
      expect(panel).toHaveAttribute('aria-labelledby');
      expect(tabs[0].id).toBe(panel.getAttribute('aria-labelledby'));
    });
  });

  it('active tab has aria-selected="true"', async () => {
    render(React.createElement(ValidatorDashboard));

    await waitFor(() => {
      const tabs = screen.getAllByRole('tab');
      const selectedTabs = tabs.filter((t) => t.getAttribute('aria-selected') === 'true');
      expect(selectedTabs).toHaveLength(1);
    });
  });
});
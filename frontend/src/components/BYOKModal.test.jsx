// BYOK Modal component tests.
//
// Verifies modal open/close, localStorage CRUD, masked display,
// validation, and warning state when no API key is stored.
//
// jsdom provides localStorage — no mocking needed.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { BYOKModal } from './BYOKModal.jsx';

// Wrap in a container that simulates the dashboard sidebar header
// where the trigger button lives.
function TestHarness() {
  return (
    <div>
      <header className="side-panel-header">
        <BYOKModal />
      </header>
      {/* Portal destination for createPortal */}
    </div>
  );
}

beforeEach(() => {
  localStorage.clear();
  // jsdom does not support HTMLDialogElement.showModal by default.
  // We polyfill it so FireEvent/Escape work correctly.
  HTMLDialogElement.prototype.showModal = vi.fn(function () {
    this.open = true;
  });
  HTMLDialogElement.prototype.close = vi.fn(function () {
    this.open = false;
    this.dispatchEvent(new Event('close'));
  });
});

afterEach(() => {
  // Portal + container cleanup is handled by the global @testing-library
  // cleanup registered in vitest.setup.js. Manual document.body removal here
  // would race React's unmount (removing portal nodes twice → NotFoundError).
  vi.restoreAllMocks();
});

describe('BYOKModal open/close', () => {
  it('renders the trigger button with a key icon', () => {
    render(<TestHarness />);

    const trigger = screen.getByRole('button', { name: /api key/i });
    expect(trigger).toBeInTheDocument();
    expect(trigger.querySelector('svg')).toBeInTheDocument();
  });

  it('opens the modal when trigger button is clicked', async () => {
    render(<TestHarness />);
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: /api key/i }));

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByLabelText(/gemini api key/i)).toBeInTheDocument();
  });

  it('closes the modal on Escape key press', async () => {
    render(<TestHarness />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /api key/i }));

    const dialog = screen.getByRole('dialog');
    fireEvent.keyDown(dialog, { key: 'Escape' });

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('closes the modal when backdrop is clicked', async () => {
    render(<TestHarness />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /api key/i }));

    const backdrop = screen.getByTestId('byok-backdrop');
    await user.click(backdrop);

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });
});

describe('BYOKModal localStorage persistence', () => {
  it('saves the API key to localStorage on Save click', async () => {
    render(<TestHarness />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /api key/i }));

    const input = screen.getByLabelText(/gemini api key/i);
    await user.clear(input);
    await user.type(input, 'sk-test-key-1234567890');

    await user.click(screen.getByRole('button', { name: /^Save$/i }));

    expect(localStorage.getItem('gemini_api_key')).toBe('sk-test-key-1234567890');
  });

  it('shows masked display (last 4 chars) after save', async () => {
    localStorage.setItem('gemini_api_key', 'sk-test-key-abcdef');
    render(<TestHarness />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /api key/i }));

    // Input should show masked value with last 4 chars
    const input = screen.getByLabelText(/gemini api key/i);
    expect(input.value).toContain('cdef');
  });

  it('pre-fills the modal input on re-open with masked value', async () => {
    localStorage.setItem('gemini_api_key', 'sk-existing-key-67890');
    render(<TestHarness />);
    const user = userEvent.setup();

    // Open modal — should show masked key
    await user.click(screen.getByRole('button', { name: /api key/i }));
    let input = screen.getByLabelText(/gemini api key/i);
    expect(input.value).toContain('7890');

    // Close modal
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    // Re-open — should still show masked value
    await user.click(screen.getByRole('button', { name: /api key/i }));
    input = screen.getByLabelText(/gemini api key/i);
    expect(input.value).toContain('7890');
  });
});

describe('BYOKModal validation', () => {
  it('disables Save button and shows error for empty key', async () => {
    render(<TestHarness />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /api key/i }));

    const input = screen.getByLabelText(/gemini api key/i);
    await user.clear(input);

    const saveButton = screen.getByRole('button', { name: /^Save$/i });
    expect(saveButton).toBeDisabled();

    expect(
      screen.getByText(/key must be at least 10 characters/i),
    ).toBeInTheDocument();
  });

  it('disables Save button and shows error for key shorter than 10 chars', async () => {
    render(<TestHarness />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /api key/i }));

    const input = screen.getByLabelText(/gemini api key/i);
    await user.clear(input);
    await user.type(input, 'short');

    const saveButton = screen.getByRole('button', { name: /^Save$/i });
    expect(saveButton).toBeDisabled();

    expect(
      screen.getByText(/key must be at least 10 characters/i),
    ).toBeInTheDocument();
  });

  it('enables Save button when key is at least 10 characters', async () => {
    render(<TestHarness />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /api key/i }));

    const input = screen.getByLabelText(/gemini api key/i);
    await user.clear(input);
    await user.type(input, 'sk-valid-key-123');

    const saveButton = screen.getByRole('button', { name: /^Save$/i });
    expect(saveButton).not.toBeDisabled();
  });
});

describe('BYOKModal clear and rotate', () => {
  it('Clear button removes key from localStorage and empties input', async () => {
    localStorage.setItem('gemini_api_key', 'sk-to-be-cleared-xxx');
    render(<TestHarness />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /api key/i }));

    await user.click(screen.getByRole('button', { name: /^Clear$/i }));

    expect(localStorage.getItem('gemini_api_key')).toBeNull();
    const input = screen.getByLabelText(/gemini api key/i);
    expect(input.value).toBe('');
  });

  it('Rotate button clears stored key and keeps modal open for new key', async () => {
    localStorage.setItem('gemini_api_key', 'sk-rotating-key-zzz');
    render(<TestHarness />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /api key/i }));

    await user.click(screen.getByRole('button', { name: /^Rotate$/i }));

    // Key removed from localStorage
    expect(localStorage.getItem('gemini_api_key')).toBeNull();
    // Modal stays open
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    // Input is empty for new key entry
    const input = screen.getByLabelText(/gemini api key/i);
    expect(input.value).toBe('');
  });
});

describe('BYOKModal warning state', () => {
  it('trigger button shows warning style when no key is stored', () => {
    render(<TestHarness />);

    const trigger = screen.getByRole('button', { name: /api key/i });
    // When no key, the button should have a data attribute or class indicating warning
    expect(trigger.dataset.warning).toBe('true');
  });

  it('trigger button does NOT show warning when key is stored', () => {
    localStorage.setItem('gemini_api_key', 'sk-stored-key-abcdef');
    render(<TestHarness />);

    const trigger = screen.getByRole('button', { name: /api key/i });
    expect(trigger.dataset.warning).toBe('false');
  });

  it('trigger button updates warning state after key is saved', async () => {
    render(<TestHarness />);
    const trigger = screen.getByRole('button', { name: /api key/i });
    expect(trigger.dataset.warning).toBe('true');

    // Open modal and save a key
    const user = userEvent.setup();
    await user.click(trigger);
    const input = screen.getByLabelText(/gemini api key/i);
    await user.clear(input);
    await user.type(input, 'sk-newly-saved-key');
    await user.click(screen.getByRole('button', { name: /^Save$/i }));

    // Trigger should no longer show warning
    const triggerAfter = screen.getByRole('button', { name: /api key/i });
    expect(triggerAfter.dataset.warning).toBe('false');
  });
});

describe('BYOKModal aria and accessibility', () => {
  it('modal dialog has aria-modal="true" and aria-label', async () => {
    render(<TestHarness />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /api key/i }));

    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-label');
  });

  it('input has type="password" for masked entry', async () => {
    render(<TestHarness />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /api key/i }));

    const input = screen.getByLabelText(/gemini api key/i);
    expect(input).toHaveAttribute('type', 'password');
  });

  it('focus returns to trigger button after modal closes', async () => {
    render(<TestHarness />);
    const user = userEvent.setup();
    const trigger = screen.getByRole('button', { name: /api key/i });

    await user.click(trigger);
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });

    await waitFor(() => {
      expect(trigger).toHaveFocus();
    });
  });
});
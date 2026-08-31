// BYOK (Bring Your Own Key) modal for Gemini API key management.
//
// Portal-based modal with localStorage persistence, masked display,
// validation, and warning indicator. Injects X-Gemini-Api-Key via api.js.

import { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { ApiKeyIcon } from './icons/ApiKeyIcon.jsx';

const STORAGE_KEY = 'gemini_api_key';
const MIN_KEY_LENGTH = 10;

/** Mask a stored key for display: "••••" + last 4 chars. */
function maskKey(key) {
  if (!key || key.length <= 4) return key || '';
  return '•'.repeat(Math.max(0, key.length - 4)) + key.slice(-4);
}

export function BYOKModal() {
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [storedKey, setStoredKey] = useState(() => localStorage.getItem(STORAGE_KEY) || '');
  const [displayValue, setDisplayValue] = useState('');
  const inputRef = useRef(null);
  const triggerRef = useRef(null);

  // Sync localStorage reads on mount and after external changes.
  useEffect(() => {
    const current = localStorage.getItem(STORAGE_KEY) || '';
    setStoredKey(current);
  }, [open]);

  // Pre-fill masked value when modal opens with a stored key.
  useEffect(() => {
    if (open && storedKey) {
      setDisplayValue(maskKey(storedKey));
      setInputValue(storedKey);
    } else if (open) {
      setDisplayValue('');
      setInputValue('');
    }
  }, [open, storedKey]);

  // Focus input when modal opens.
  useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus();
    }
  }, [open]);

  const validationError =
    inputValue.length < MIN_KEY_LENGTH ? `Key must be at least ${MIN_KEY_LENGTH} characters` : null;
  const isValid = inputValue.length >= MIN_KEY_LENGTH;

  const handleOpen = useCallback(() => {
    setOpen(true);
  }, []);

  const handleClose = useCallback(() => {
    setOpen(false);
  }, []);

  const handleSave = useCallback(() => {
    if (!isValid) return;
    localStorage.setItem(STORAGE_KEY, inputValue);
    setStoredKey(inputValue);
    setDisplayValue(maskKey(inputValue));
    setOpen(false);
  }, [inputValue, isValid]);

  const handleClear = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setStoredKey('');
    setInputValue('');
    setDisplayValue('');
  }, []);

  const handleRotate = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setStoredKey('');
    setInputValue('');
    setDisplayValue('');
    // Modal stays open for new key entry.
  }, []);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        handleClose();
      }
    },
    [handleClose],
  );

  // Return focus to trigger on close.
  useEffect(() => {
    if (!open && triggerRef.current) {
      triggerRef.current.focus();
    }
  }, [open]);

  const hasKey = storedKey.length > 0;

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className={`byok-trigger${hasKey ? '' : ' byok-warning'}`}
        data-warning={hasKey ? 'false' : 'true'}
        onClick={handleOpen}
        aria-label="API Key"
        title="Manage API Key"
      >
        <ApiKeyIcon size={16} />
        <span>API Key</span>
      </button>

      {open &&
        createPortal(
          <>
            <div
              className="byok-backdrop"
              data-testid="byok-backdrop"
              onClick={handleClose}
            />
            <div
              role="dialog"
              aria-modal="true"
              aria-label="Manage API Key"
              className="byok-modal"
              onKeyDown={handleKeyDown}
            >
              <h2>Gemini API Key</h2>

              <label htmlFor="byok-input">
                API Key
                <input
                  ref={inputRef}
                  id="byok-input"
                  type="password"
                  value={displayValue}
                  onChange={(e) => {
                    const raw = e.target.value;
                    setInputValue(raw);
                    setDisplayValue(raw);
                  }}
                  placeholder="Enter your Gemini API key"
                  aria-label="Gemini API key"
                />
              </label>

              {validationError && (
                <p className="byok-error" role="alert">
                  {validationError}
                </p>
              )}

              <div className="byok-actions">
                <button
                  type="button"
                  className="button"
                  onClick={handleSave}
                  disabled={!isValid}
                >
                  Save
                </button>
                <button
                  type="button"
                  className="button byok-secondary"
                  onClick={handleClear}
                  disabled={!hasKey}
                >
                  Clear
                </button>
                <button
                  type="button"
                  className="button byok-secondary"
                  onClick={handleRotate}
                  disabled={!hasKey}
                >
                  Rotate
                </button>
              </div>
            </div>
          </>,
          document.body,
        )}
    </>
  );
}
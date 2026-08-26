import React from 'react';

// API key icon — key symbol for BYOK modal trigger.

export function ApiKeyIcon({ className, size = 16 }) {
  return (
    <svg
      role="img"
      aria-label="API Key"
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <circle cx="5.5" cy="7" r="2.5" />
      <line x1="7.5" y1="7" x2="13" y2="7" />
      <line x1="10" y1="4.5" x2="10" y2="9.5" />
    </svg>
  );
}
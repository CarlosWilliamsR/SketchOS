import React from 'react';

// Warning icon — exclamation triangle for violations/alerts.

export function WarningIcon({ className, size = 16 }) {
  return (
    <svg
      role="img"
      aria-label="Warning"
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
      <path d="M8 2 1 14h14Z" />
      <line x1="8" y1="6.5" x2="8" y2="9.5" />
      <circle cx="8" cy="12" r="0.4" fill="currentColor" stroke="none" />
    </svg>
  );
}
import React from 'react';

// Diagnostics icon — wrench/screwdriver tool for troubleshooting.

export function DiagnosticsIcon({ className, size = 16 }) {
  return (
    <svg
      role="img"
      aria-label="Diagnostics"
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
      <path d="M14.5 14.5 11 11" />
      <circle cx="7" cy="7" r="4.5" />
      <line x1="7" y1="4.5" x2="7" y2="9.5" />
      <line x1="4.5" y1="7" x2="9.5" y2="7" />
    </svg>
  );
}
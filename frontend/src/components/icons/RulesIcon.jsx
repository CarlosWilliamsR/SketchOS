import React from 'react';

// Rules icon — clipboard/checklist for building regulations.

export function RulesIcon({ className, size = 16 }) {
  return (
    <svg
      role="img"
      aria-label="Rules"
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
      <rect x="3" y="1" width="10" height="14" rx="1" />
      <line x1="8" y1="4" x2="8" y2="4.01" />
      <path d="M6 7h4" />
      <path d="M6 9.5h3" />
      <path d="M6 12h2" />
    </svg>
  );
}
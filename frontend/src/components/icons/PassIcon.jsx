import React from 'react';

// Pass icon — checkmark circle for validation success.

export function PassIcon({ className, size = 16 }) {
  return (
    <svg
      role="img"
      aria-label="Pass"
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
      <circle cx="8" cy="8" r="7" />
      <polyline points="5 8 7.5 10.5 11 5.5" />
    </svg>
  );
}
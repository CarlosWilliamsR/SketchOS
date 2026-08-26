import React from 'react';

// Upload icon — arrow pointing up into a tray (file upload).

export function UploadIcon({ className, size = 16 }) {
  return (
    <svg
      role="img"
      aria-label="Upload"
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
      <path d="M8 11V3" />
      <polyline points="5 6 8 3 11 6" />
      <path d="M2 11v2a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-2" />
    </svg>
  );
}
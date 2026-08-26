import React from 'react';

// Sketch icon — pencil/pen tool for 2D sketch drawing.

export function SketchIcon({ className, size = 16 }) {
  return (
    <svg
      role="img"
      aria-label="Sketch"
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
      <path d="M11.5 2.5 13.5 4.5 5 13H3v-2Z" />
      <line x1="10" y1="4" x2="12.5" y2="6.5" />
    </svg>
  );
}
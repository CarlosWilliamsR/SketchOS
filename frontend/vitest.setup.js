import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// @testing-library/react auto-cleanup depends on a global `afterEach`, which
// vitest does not expose unless `globals: true` is set. Register cleanup here
// so each test starts from a fresh DOM (prevents role-query pollution across
// the many `render()` calls in a single test file).
afterEach(() => {
  cleanup();
});
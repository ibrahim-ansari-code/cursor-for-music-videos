/// <reference types="vitest" />
/// <reference types="vite/client" />
/// <reference types="@testing-library/jest-dom" />

import '@testing-library/jest-dom';
import 'vitest/globals';

declare module 'vitest' {
  export interface Assertion extends jest.Matchers<void> {}
  export interface AsymmetricMatchersContaining extends jest.AsymmetricMatchers {}
}

declare global {
  const vi: typeof import('vitest')['vi'];
  const expect: typeof import('vitest')['expect'];
  const describe: typeof import('vitest')['describe'];
  const it: typeof import('vitest')['it'];
  const beforeEach: typeof import('vitest')['beforeEach'];
  const afterEach: typeof import('vitest')['afterEach'];
  const beforeAll: typeof import('vitest')['beforeAll'];
  const afterAll: typeof import('vitest')['afterAll'];
}
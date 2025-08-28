# Frontend Testing Guide

## Test Structure

Our tests are organized in a centralized `tests/` directory that mirrors the source code structure:

```
tests/
├── components/     # Component tests
├── utils/          # Utility function tests
├── config/         # Build and configuration tests
└── setup/          # Test setup and configuration files
    ├── setup.ts    # Global test setup
    └── vitest-env.d.ts  # TypeScript definitions for tests
```

## Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run specific test file
npm test -- tests/components/ProductionErrorBoundary.test.tsx

# Run tests with coverage
npm run test:coverage

# Run tests with UI
npm run test:ui
```

## Test Categories

### Component Tests (`tests/components/`)
- Tests for React components
- Includes rendering, user interaction, and error boundary tests
- Uses React Testing Library

### Utility Tests (`tests/utils/`)
- Tests for utility functions and helpers
- Focus on pure functions and data transformations

### Config Tests (`tests/config/`)
- **vite-chunking.test.ts**: Validates Vite bundling strategy
- **build-verification.test.ts**: Verifies build outputs and security

## Critical Tests for Production

These tests are run in CI/CD to prevent production issues:

1. **Chunking Strategy** - Ensures React loads in correct order
2. **Build Verification** - Validates no global namespace pollution
3. **Error Boundary** - Confirms error handling works correctly

## Writing Tests

### Component Test Example
```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import MyComponent from '@/components/MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
});
```

### Utility Test Example
```js
import { describe, it, expect } from 'vitest';
import { myUtility } from '@/utils/myUtility';

describe('myUtility', () => {
  it('processes data correctly', () => {
    expect(myUtility('input')).toBe('expected output');
  });
});
```

## Test Stack

- **Vitest**: Test runner (faster than Jest, built for Vite)
- **React Testing Library**: Component testing
- **@testing-library/jest-dom**: Additional matchers
- **jsdom**: Browser environment simulation

## CI/CD Integration

Tests are automatically run in GitHub Actions:
- On every pull request
- Before deployment to production
- Includes build verification and security checks

## Best Practices

1. **Co-location**: Keep test files in centralized `tests/` folder
2. **Naming**: Use `.test.ts(x)` or `.spec.ts(x)` suffix
3. **Coverage**: Aim for 80%+ coverage on new code
4. **Isolation**: Tests should not depend on each other
5. **Mocking**: Mock external dependencies and API calls
6. **Performance**: Keep tests fast and focused
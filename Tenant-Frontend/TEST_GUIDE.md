# Tenant Frontend Testing Guide

This document provides comprehensive information about the testing infrastructure and practices for the Brikli Tenant Frontend.

## Test Infrastructure

### Framework Stack

- **Test Runner**: Vitest 3.x
- **Testing Library**: React Testing Library 16.x
- **Environment**: jsdom for DOM simulation
- **Mocking**: Vitest built-in mocking capabilities
- **Coverage**: c8 coverage provider

### Configuration

- **Config File**: `vitest.config.js`
- **Setup File**: `src/test/setup.jsx`
- **Test Utils**: `src/test/utils.jsx`

## Running Tests

### Commands

```bash
# Run all tests once
npm run test:run

# Run tests in watch mode (recommended for development)
npm run test:watch

# Run tests with UI interface
npm run test:ui

# Generate coverage report
npm run test:coverage

# Run specific test file
npm run test:run src/components/__tests__/Sidebar.test.jsx

# Run tests matching pattern
npm run test:run -- --reporter=verbose
```

### Test Scripts

- `npm test` - Interactive test mode
- `npm run test:run` - Single test run with results
- `npm run test:watch` - Watch mode for development
- `npm run test:coverage` - Coverage report generation
- `npm run test:ui` - Visual test interface

## Test Structure

### Directory Organization

```text
src/
├── components/
│   └── __tests__/          # Component tests
│       ├── Sidebar.test.jsx
│       ├── Layout.test.jsx
│       ├── DashboardContent.test.jsx
│       └── ErrorBoundary.test.jsx
├── contexts/
│   └── __tests__/          # Context tests
│       └── AuthContext.test.jsx
└── test/
    ├── setup.jsx           # Global test setup
    └── utils.jsx           # Test utilities and mocks
```

### Naming Conventions

- Test files: `ComponentName.test.jsx`
- Test directories: `__tests__/`
- Mock files: `__mocks__/`
- Utilities: `test/utils.jsx`

## Test Categories

### 1. Component Tests

**Location**: `src/components/__tests__/`

**Coverage**:

- Rendering behavior
- User interactions
- Props handling
- State changes
- Event handling

**Example**:

```javascript
import { renderWithProviders, mockAuthContext } from '../../test/utils';
import ComponentName from '../ComponentName';

describe('ComponentName', () => {
  it('renders correctly', () => {
    renderWithProviders(<ComponentName />);
    expect(screen.getByText('Expected Text')).toBeInTheDocument();
  });
});
```

### 2. Context Tests

**Location**: `src/contexts/__tests__/`

**Coverage**:

- State management
- Provider functionality
- Hook behavior
- Error handling

### 3. Integration Tests

**Coverage**:

- Component interactions
- Route navigation
- API integration
- Error boundaries

## Testing Utilities

### Custom Render Function

```javascript
import { renderWithProviders } from '../test/utils';

// Renders component with all necessary providers
renderWithProviders(<Component />, {
  authContextValue: mockAuthContext,
  initialEntries: ['/dashboard']
});
```

### Mock Data

```javascript
import { 
  mockUser, 
  mockAuthContext, 
  createMockUser 
} from '../test/utils';

// Use predefined mocks or create custom ones
const customUser = createMockUser({ first_name: 'Alice' });
```

### API Mocking

```javascript
import { mockFetch, mockApiResponse } from '../test/utils';

// Mock API responses
mockFetch({ data: 'response' }, 200);
```

## Mocking Strategy

### 1. Supabase Auth

```javascript
vi.mock('../../utils/supabaseClient', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
      signInWithPassword: vi.fn(),
      signOut: vi.fn()
    }
  }
}));
```

### 2. React Router

```javascript
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useLocation: () => ({ pathname: '/dashboard' })
  };
});
```

### 3. API Calls

```javascript
vi.mock('../../utils/api/auth', () => ({
  getCurrentUser: vi.fn()
}));
```

## Testing Best Practices

### 1. Test Organization

- Group related tests in `describe` blocks
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Clean up after each test

### 2. User-Centric Testing

```javascript
// Good: Test user behavior
fireEvent.click(screen.getByRole('button', { name: 'Login' }));
expect(screen.getByText('Welcome!')).toBeInTheDocument();

// Avoid: Testing implementation details
expect(component.state.isLoggedIn).toBe(true);
```

### 3. Async Testing

```javascript
// Use waitFor for async operations
await waitFor(() => {
  expect(screen.getByText('Data loaded')).toBeInTheDocument();
});

// Use act for state updates
await act(async () => {
  fireEvent.click(loginButton);
});
```

### 4. Error Testing

```javascript
// Test error boundaries
render(
  <ErrorBoundary>
    <ComponentThatThrows />
  </ErrorBoundary>
);
expect(screen.getByText('Something went wrong')).toBeInTheDocument();
```

## Coverage Targets

### Current Coverage

- **Test Files**: 5/5 (100%)
- **Test Cases**: 56/56 passing (100%)
- **Components**: All major components covered
- **Contexts**: Authentication context covered
- **Error Handling**: Error boundaries tested

### Coverage Goals

- **Line Coverage**: >80%
- **Branch Coverage**: >75%
- **Function Coverage**: >85%
- **Statement Coverage**: >80%

## Common Testing Patterns

### 1. Component Rendering

```javascript
it('renders component with props', () => {
  renderWithProviders(
    <Component title="Test" onAction={mockFn} />
  );
  expect(screen.getByText('Test')).toBeInTheDocument();
});
```

### 2. User Interactions

```javascript
it('handles button click', () => {
  const mockFn = vi.fn();
  renderWithProviders(<Button onClick={mockFn} />);
  
  fireEvent.click(screen.getByRole('button'));
  expect(mockFn).toHaveBeenCalledOnce();
});
```

### 3. Form Testing

```javascript
it('submits form with valid data', async () => {
  renderWithProviders(<Form onSubmit={mockSubmit} />);
  
  fireEvent.change(screen.getByLabelText('Email'), {
    target: { value: 'test@example.com' }
  });
  
  fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
  
  await waitFor(() => {
    expect(mockSubmit).toHaveBeenCalledWith({
      email: 'test@example.com'
    });
  });
});
```

### 4. Navigation Testing

```javascript
it('navigates to correct route', () => {
  const mockNavigate = vi.fn();
  vi.mocked(useNavigate).mockReturnValue(mockNavigate);
  
  renderWithProviders(<Component />);
  fireEvent.click(screen.getByText('Go to Dashboard'));
  
  expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
});
```

### 5. Loading States

```javascript
it('shows loading spinner', () => {
  renderWithProviders(<Component />, {
    authContextValue: mockLoadingAuthContext
  });
  
  expect(screen.getByRole('progressbar')).toBeInTheDocument();
});
```

## Debugging Tests

### 1. Debug Rendering

```javascript
import { screen } from '@testing-library/react';

// Debug what's rendered
screen.debug();

// Debug specific element
screen.debug(screen.getByTestId('my-element'));
```

### 2. Query Debugging

```javascript
// See available queries
screen.logTestingPlaygroundURL();

// Check what roles are available
screen.getByRole(); // Will show available roles in error message
```

### 3. Test Isolation

```javascript
beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  // Reset any global state
});
```

## Continuous Integration

### Test Pipeline

1. **Install Dependencies**: `npm ci`
2. **Run Linting**: `npm run lint`
3. **Run Tests**: `npm run test:run`
4. **Generate Coverage**: `npm run test:coverage`
5. **Build Application**: `npm run build`

### Quality Gates

- All tests must pass
- No linting errors
- Coverage thresholds met
- Build succeeds

## Troubleshooting

### Common Issues

1. **Mock Not Working**

   ```javascript
   // Ensure mock is hoisted
   vi.mock('./module', () => ({
     default: vi.fn()
   }));
   ```

2. **Async Test Failures**

   ```javascript
   // Wrap in act for state updates
   await act(async () => {
     // async operation
   });
   ```

3. **Component Not Found**

   ```javascript
   // Check if component is wrapped in providers
   renderWithProviders(<Component />);
   ```

4. **Environment Issues**

   ```javascript
   // Ensure jsdom environment
   // @vitest-environment jsdom
   ```

### Debug Commands

```bash
# Run with verbose output
npm run test:run -- --reporter=verbose

# Run specific test with debug
npm run test:run -- --reporter=verbose Sidebar.test.jsx

# Check test coverage
npm run test:coverage

# Run in watch mode for debugging
npm run test:watch
```

## Performance Tips

1. **Parallel Execution**: Tests run in parallel by default
2. **Mock External Dependencies**: Reduce test execution time
3. **Shallow Testing**: Focus on component behavior, not implementation
4. **Test Isolation**: Ensure tests don't affect each other
5. **Selective Running**: Use patterns to run specific tests during development

## Future Improvements

1. **Visual Regression Testing**: Add screenshot testing
2. **E2E Testing**: Implement Playwright tests
3. **Performance Testing**: Add performance benchmarks
4. **Accessibility Testing**: Enhanced a11y testing
5. **API Contract Testing**: Mock API contract validation

---

For more information, see:

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Jest DOM Matchers](https://github.com/testing-library/jest-dom)

import React from 'react';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';
import { vi } from 'vitest';

// Mock user data for testing
export const mockUser = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  email: 'test@example.com',
  first_name: 'John',
  last_name: 'Doe',
  user_type: 'TENANT',
  phone: '+1234567890',
  is_active: true,
  created_at: '2023-01-01T00:00:00Z',
  updated_at: '2023-01-01T00:00:00Z'
};

// Mock auth context values
export const mockAuthContext = {
  user: mockUser,
  loading: false,
  error: null,
  isAuthenticated: true,
  signIn: vi.fn(() => Promise.resolve({ data: mockUser, error: null })),
  signOut: vi.fn(() => Promise.resolve()),
  clearError: vi.fn()
};

// Custom render function that includes providers
export const renderWithProviders = (ui, { 
  authContextValue = mockAuthContext,
  initialEntries = ['/dashboard'],
  ...renderOptions 
} = {}) => {
  const Wrapper = ({ children }) => (
    <MemoryRouter initialEntries={initialEntries}>
      <AuthContext.Provider value={authContextValue}>
        {children}
      </AuthContext.Provider>
    </MemoryRouter>
  );

  return render(ui, { wrapper: Wrapper, ...renderOptions });
};

// Helper to create mock auth context with different states
export const createMockAuthContext = (overrides = {}) => ({
  ...mockAuthContext,
  ...overrides
});

// Helper to create mock user with different properties
export const createMockUser = (overrides = {}) => ({
  ...mockUser,
  ...overrides
});

// Helper for testing loading states
export const mockLoadingAuthContext = createMockAuthContext({
  loading: true,
  user: null,
  isAuthenticated: false
});

// Helper for testing error states
export const mockErrorAuthContext = createMockAuthContext({
  error: 'Authentication failed',
  user: null,
  isAuthenticated: false,
  loading: false
});

// Helper for testing unauthenticated state
export const mockUnauthenticatedContext = createMockAuthContext({
  user: null,
  isAuthenticated: false,
  loading: false
});

// Mock API responses
export const mockApiResponse = (data, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: () => Promise.resolve(data),
  text: () => Promise.resolve(JSON.stringify(data))
});

// Helper to mock fetch with different responses
export const mockFetch = (responseData, status = 200) => {
  vi.stubGlobal('fetch', vi.fn(() => 
    Promise.resolve(mockApiResponse(responseData, status))
  ));
};

// Helper to wait for async operations in tests
export const customWaitFor = (fn, { timeout = 1000, interval = 50 } = {}) => {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    
    const check = () => {
      try {
        const result = fn();
        if (result) {
          resolve(result);
          return;
        }
      } catch {
        // Continue checking
      }
      
      if (Date.now() - startTime >= timeout) {
        reject(new Error('customWaitFor timeout'));
        return;
      }
      
      setTimeout(check, interval);
    };
    
    check();
  });
};

// eslint-disable-next-line react-refresh/only-export-components
export * from '@testing-library/react';
export { userEvent } from '@testing-library/user-event';
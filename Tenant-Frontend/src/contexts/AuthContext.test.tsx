import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AuthContext } from './AuthContext';
import { useAuth } from '@/hooks/useAuth';
import type { AuthContextValue } from '@/types';

// Test component that uses useAuth hook
const TestConsumer: React.FC = () => {
  const auth = useAuth();
  return (
    <div>
      <span data-testid="user-email">{auth.user?.email || 'no-user'}</span>
      <span data-testid="loading">{auth.loading ? 'loading' : 'not-loading'}</span>
      <span data-testid="authenticated">{auth.isAuthenticated ? 'yes' : 'no'}</span>
    </div>
  );
};

describe('AuthContext', () => {
  it('provides auth context values to consumers', () => {
    const mockAuthValue: AuthContextValue = {
      user: {
        id: 'test-id',
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
        user_type: 'TENANT',
        profile_image_url: null,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      loading: false,
      error: null,
      isAuthenticated: true,
      signIn: async () => ({ data: null, error: null }),
      signOut: async () => {},
      clearError: () => {},
    };

    render(
      <AuthContext.Provider value={mockAuthValue}>
        <TestConsumer />
      </AuthContext.Provider>
    );

    expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');
    expect(screen.getByTestId('loading')).toHaveTextContent('not-loading');
    expect(screen.getByTestId('authenticated')).toHaveTextContent('yes');
  });

  it('provides loading state correctly', () => {
    const mockAuthValue: AuthContextValue = {
      user: null,
      loading: true,
      error: null,
      isAuthenticated: false,
      signIn: async () => ({ data: null, error: null }),
      signOut: async () => {},
      clearError: () => {},
    };

    render(
      <AuthContext.Provider value={mockAuthValue}>
        <TestConsumer />
      </AuthContext.Provider>
    );

    expect(screen.getByTestId('loading')).toHaveTextContent('loading');
    expect(screen.getByTestId('authenticated')).toHaveTextContent('no');
  });

  it('provides unauthenticated state correctly', () => {
    const mockAuthValue: AuthContextValue = {
      user: null,
      loading: false,
      error: null,
      isAuthenticated: false,
      signIn: async () => ({ data: null, error: null }),
      signOut: async () => {},
      clearError: () => {},
    };

    render(
      <AuthContext.Provider value={mockAuthValue}>
        <TestConsumer />
      </AuthContext.Provider>
    );

    expect(screen.getByTestId('user-email')).toHaveTextContent('no-user');
    expect(screen.getByTestId('authenticated')).toHaveTextContent('no');
  });
});

describe('useAuth hook', () => {
  it('throws error when used outside AuthProvider', () => {
    // We need to suppress the error boundary and console.error for this test
    const originalError = console.error;
    console.error = () => {};

    expect(() => {
      render(<TestConsumer />);
    }).toThrow('useAuth must be used within an AuthProvider');

    console.error = originalError;
  });
});


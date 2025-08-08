import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { AuthProvider } from '../AuthProvider';
import { useAuth } from '../useAuth';
// Removed unused imports

// Mock supabase client
vi.mock('../../utils/supabaseClient', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
      signInWithPassword: vi.fn(),
      signOut: vi.fn(),
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } }))
    }
  }
}));

// Mock API calls
vi.mock('../../utils/api/auth', () => ({
  getCurrentUser: vi.fn()
}));

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;

  it('initializes with loading state', async () => {
    const { supabase } = await import('../../utils/supabaseClient');
    supabase.auth.getSession.mockResolvedValue({ data: { session: null } });
    
    const { result } = renderHook(() => useAuth(), { wrapper });
    
    // Wait for initial load to complete deterministically
    await waitFor(() => expect(result.current.loading).toBe(false));
    
    expect(result.current.user).toBe(null);
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('provides auth methods', async () => {
    const { supabase } = await import('../../utils/supabaseClient');
    supabase.auth.getSession.mockResolvedValue({ data: { session: null } });
    
    const { result } = renderHook(() => useAuth(), { wrapper });
    
    await waitFor(() => expect(result.current.loading).toBe(false));
    
    expect(typeof result.current.signIn).toBe('function');
    expect(typeof result.current.signOut).toBe('function');
    expect(typeof result.current.clearError).toBe('function');
  });

  it('handles successful sign in', async () => {
    const mockUser = {
      id: '123',
      email: 'test@example.com',
      first_name: 'John',
      last_name: 'Doe',
      user_type: 'TENANT'
    };

    const { supabase } = await import('../../utils/supabaseClient');
    supabase.auth.getSession.mockResolvedValue({ data: { session: null } });
    supabase.auth.signInWithPassword.mockResolvedValue({
      data: { user: mockUser, session: { access_token: 'token123' } },
      error: null
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      const response = await result.current.signIn('test@example.com', 'password');
      expect(response.error).toBe(null);
    });

    expect(supabase.auth.signInWithPassword).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password'
    });
  });

  it('handles sign out', async () => {
    const { supabase } = await import('../../utils/supabaseClient');
    supabase.auth.getSession.mockResolvedValue({ data: { session: null } });
    supabase.auth.signOut.mockResolvedValue({ error: null });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.signOut();
    });

    expect(supabase.auth.signOut).toHaveBeenCalled();
  });

  it('clears error when clearError is called', async () => {
    const { supabase } = await import('../../utils/supabaseClient');
    // Mock a failed sign-in to create an error state
    supabase.auth.signInWithPassword.mockResolvedValue({ 
      data: { user: null }, 
      error: { message: 'Test error' } 
    });
    supabase.auth.getSession.mockResolvedValue({ data: { session: null } });
    
    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.loading).toBe(false));

    // First create an error by trying to sign in
    await act(async () => {
      await result.current.signIn('test@example.com', 'password');
    });

    // Verify error was set
    expect(result.current.error).toBe('Test error');

    // Test clearError function clears the error
    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBe(null);
  });
});
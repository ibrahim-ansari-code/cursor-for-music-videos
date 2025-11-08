import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import MicrosoftSignInButton from '../../../src/components/auth/MicrosoftSignInButton';
import * as supabaseClient from '../../../src/supabaseClient';

// Mock supabase client
vi.mock('../../../src/supabaseClient', () => ({
  supabase: {
    auth: {
      signInWithOAuth: vi.fn(),
    },
  },
}));

describe('MicrosoftSignInButton', () => {
  const mockSetLoading = vi.fn();
  const mockSetError = vi.fn();
  const mockSignInWithOAuth = vi.mocked(supabaseClient.supabase.auth.signInWithOAuth);

  beforeEach(() => {
    vi.clearAllMocks();
    // Suppress console logs in tests
    vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the Microsoft sign-in button', () => {
    render(
      <MicrosoftSignInButton 
        setLoading={mockSetLoading} 
        setError={mockSetError} 
      />
    );

    expect(screen.getByText('Continue with Microsoft')).toBeInTheDocument();
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('calls signInWithOAuth with azure provider when clicked', async () => {
    mockSignInWithOAuth.mockResolvedValue({ 
      data: { provider: 'azure', url: 'https://login.microsoftonline.com/...' }, 
      error: null 
    });

    render(
      <MicrosoftSignInButton 
        setLoading={mockSetLoading} 
        setError={mockSetError} 
      />
    );

    const button = screen.getByRole('button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(true);
      expect(mockSignInWithOAuth).toHaveBeenCalledWith({
        provider: 'azure',
      });
    });
  });

  it('handles OAuth errors correctly', async () => {
    const mockError = { 
      message: 'OAuth failed',
      code: 'oauth_error',
      status: 400,
      __isAuthError: true,
      name: 'AuthError'
    };
    mockSignInWithOAuth.mockResolvedValue({ 
      data: { provider: 'azure', url: null }, 
      error: mockError as any
    });

    render(
      <MicrosoftSignInButton 
        setLoading={mockSetLoading} 
        setError={mockSetError} 
      />
    );

    const button = screen.getByRole('button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(mockSetError).toHaveBeenCalledWith('OAuth failed');
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });
  });

  it('handles unexpected errors correctly', async () => {
    mockSignInWithOAuth.mockRejectedValue(new Error('Network error'));

    render(
      <MicrosoftSignInButton 
        setLoading={mockSetLoading} 
        setError={mockSetError} 
      />
    );

    const button = screen.getByRole('button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(mockSetError).toHaveBeenCalledWith('An unexpected error occurred. Please try again.');
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });
  });

  it('does not reset loading state on successful OAuth (user gets redirected)', async () => {
    mockSignInWithOAuth.mockResolvedValue({ 
      data: { provider: 'azure', url: 'https://login.microsoftonline.com/...' }, 
      error: null 
    });

    render(
      <MicrosoftSignInButton 
        setLoading={mockSetLoading} 
        setError={mockSetError} 
      />
    );

    const button = screen.getByRole('button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(true);
      // On successful OAuth, loading stays true because user will be redirected
      expect(mockSetLoading).not.toHaveBeenCalledWith(false);
    });
  });
});


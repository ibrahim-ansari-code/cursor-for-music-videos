import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithProviders, mockLoadingAuthContext, mockUnauthenticatedContext, createMockUser } from '../../test/utils';
import Layout from '../Layout';

describe('Layout Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the layout with sidebar and header', () => {
    renderWithProviders(<Layout />);
    
    // Check for sidebar
    expect(screen.getByRole('navigation')).toBeInTheDocument();
    
    // Check for header
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getAllByText('Dashboard')).toHaveLength(2); // One in sidebar, one in header
    
    // Check for main content area
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('displays loading state when user is loading', () => {
    renderWithProviders(<Layout />, { authContextValue: mockLoadingAuthContext });
    
    // Should show loading skeleton instead of spinner
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });

  it('displays error state when user is not loaded', () => {
    renderWithProviders(<Layout />, { authContextValue: mockUnauthenticatedContext });
    
    expect(screen.getByText('Unable to load user data')).toBeInTheDocument();
    expect(screen.getByText('Return to Login')).toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });

  it('displays correct page title based on route', () => {
    // Just test the default dashboard route since we're mocking useLocation in setup
    renderWithProviders(<Layout />);
    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument();
  });

  it('displays user information correctly', () => {
    const testUser = createMockUser({
      first_name: 'Alice',
      last_name: 'Brown'
    });
    
    renderWithProviders(<Layout />, { 
      authContextValue: { ...mockLoadingAuthContext, user: testUser, loading: false, isAuthenticated: true }
    });
    
    expect(screen.getByText('Alice Brown')).toBeInTheDocument();
    expect(screen.getByText('Tenant')).toBeInTheDocument();
  });

  it('handles missing user name gracefully', () => {
    const testUser = createMockUser({
      first_name: null,
      last_name: null
    });
    
    renderWithProviders(<Layout />, { 
      authContextValue: { ...mockLoadingAuthContext, user: testUser, loading: false, isAuthenticated: true }
    });
    
    expect(screen.getByText('User')).toBeInTheDocument();
  });

  it('displays user initials when no profile image', () => {
    const testUser = createMockUser({
      first_name: 'Alice',
      last_name: 'Brown',
      profile_image_url: null
    });
    
    renderWithProviders(<Layout />, { 
      authContextValue: { ...mockLoadingAuthContext, user: testUser, loading: false, isAuthenticated: true }
    });
    
    expect(screen.getByText('AB')).toBeInTheDocument();
  });

  it('displays fallback initials when no name provided', () => {
    const testUser = createMockUser({
      first_name: null,
      last_name: null,
      profile_image_url: null
    });
    
    renderWithProviders(<Layout />, { 
      authContextValue: { ...mockLoadingAuthContext, user: testUser, loading: false, isAuthenticated: true }
    });
    
    expect(screen.getByText('?')).toBeInTheDocument();
  });

  it('calls signOut when logout button is clicked', () => {
    const mockSignOut = vi.fn();
    renderWithProviders(<Layout />, { 
      authContextValue: { ...mockLoadingAuthContext, user: createMockUser(), loading: false, isAuthenticated: true, signOut: mockSignOut }
    });
    
    const logoutButton = screen.getByText('Logout');
    fireEvent.click(logoutButton);
    
    expect(mockSignOut).toHaveBeenCalledOnce();
  });

  it('calls signOut when return to login is clicked in error state', () => {
    const mockSignOut = vi.fn();
    renderWithProviders(<Layout />, { 
      authContextValue: { ...mockUnauthenticatedContext, signOut: mockSignOut }
    });
    
    const returnButton = screen.getByText('Return to Login');
    fireEvent.click(returnButton);
    
    expect(mockSignOut).toHaveBeenCalledOnce();
  });

  it('has functional notifications bell link', () => {
    renderWithProviders(<Layout />);
    
    // Target the header bell specifically via its aria-label
    const notificationsBell = screen.getByLabelText('View notifications');
    expect(notificationsBell).toHaveAttribute('href', '/notifications');
  });

  it('has functional settings link from user avatar', () => {
    renderWithProviders(<Layout />);
    
    // Find the settings link (should be the avatar/name area)
    const settingsLinks = screen.getAllByRole('link').filter(link => 
      link.getAttribute('href') === '/settings'
    );
    
    expect(settingsLinks.length).toBeGreaterThan(0);
  });

  it('applies correct CSS classes for layout structure', () => {
    renderWithProviders(<Layout />);
    
    // Check main layout structure
    const layoutContainer = screen.getByRole('banner').closest('.flex.h-screen.bg-gray-50');
    expect(layoutContainer).toBeInTheDocument();
    
    // Check header styling
    const header = screen.getByRole('banner');
    expect(header).toHaveClass('bg-white', 'border-b', 'border-gray-200', 'z-10', 'h-16');
    
    // Check main content area
    const main = screen.getByRole('main');
    expect(main).toHaveClass('flex-1', 'overflow-auto', 'bg-gray-50', 'p-4');
  });

  it('renders outlet for nested routes', () => {
    renderWithProviders(<Layout />);
    
    // The Layout should render an Outlet component for nested routing
    // This is handled by React Router, so we just verify the main content area exists
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('maintains responsive design classes', () => {
    renderWithProviders(<Layout />);
    
    // Check for responsive classes on user info using user name from mock
    const user = createMockUser();
    const mockUserName = `${user.first_name} ${user.last_name}`;
    const userInfoContainer = screen.getByText(mockUserName.trim()).closest('.hidden.md\\:block');
    expect(userInfoContainer).toBeInTheDocument();
  });
});
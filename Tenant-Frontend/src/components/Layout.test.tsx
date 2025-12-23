import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import Layout from './Layout';
import { AuthContext } from '@/contexts/AuthContext';
import { NotificationContext, type NotificationContextValue } from '@/contexts/notificationContextTypes';
import type { AuthContextValue, User } from '@/types';

// Mock user data
const mockUser: User = {
  id: 'test-user-id',
  email: 'tenant@example.com',
  first_name: 'John',
  last_name: 'Doe',
  phone: null,
  user_type: 'TENANT',
  profile_image_url: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

// Create mock auth context
const createMockAuthContext = (overrides: Partial<AuthContextValue> = {}): AuthContextValue => ({
  user: mockUser,
  loading: false,
  error: null,
  isAuthenticated: true,
  signIn: vi.fn().mockResolvedValue({ data: null, error: null }),
  signOut: vi.fn().mockResolvedValue(undefined),
  clearError: vi.fn(),
  refreshUser: vi.fn().mockResolvedValue(undefined),
  ...overrides,
});

// Create mock notification context
const createMockNotificationContext = (): NotificationContextValue => ({
  notifications: [],
  unreadCount: 0,
  isLoading: false,
  error: null,
  fetchNotifications: vi.fn(),
  fetchUnreadCount: vi.fn(),
  markNotificationAsRead: vi.fn(),
  markAllNotificationsAsRead: vi.fn(),
  dismissNotification: vi.fn(),
});

// Wrapper component with all required providers
const renderWithProviders = (
  component: React.ReactNode,
  { authValue = createMockAuthContext(), initialRoute = '/dashboard' } = {}
) => {
  return render(
    <AuthContext.Provider value={authValue}>
      <NotificationContext.Provider value={createMockNotificationContext()}>
        <MemoryRouter initialEntries={[initialRoute]}>
          <Routes>
            <Route element={component}>
              <Route path="/dashboard" element={<div>Dashboard Content</div>} />
              <Route path="/payments" element={<div>Payments Content</div>} />
              <Route path="/documents" element={<div>Documents Content</div>} />
              <Route path="/maintenance" element={<div>Maintenance Content</div>} />
              <Route path="/notifications" element={<div>Notifications Content</div>} />
              <Route path="/settings" element={<div>Settings Content</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </NotificationContext.Provider>
    </AuthContext.Provider>
  );
};

describe('Layout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the sidebar', () => {
    renderWithProviders(<Layout />);
    
    // Use getAllByText since "Dashboard" appears in both sidebar and header
    const dashboardElements = screen.getAllByText('Dashboard');
    expect(dashboardElements.length).toBeGreaterThanOrEqual(1);
    
    // Verify sidebar navigation is present
    expect(screen.getByText('Rent & Payments')).toBeInTheDocument();
  });

  it('renders the header with page title', () => {
    renderWithProviders(<Layout />, { initialRoute: '/dashboard' });
    
    // The header should show "Dashboard" as the page title
    const headers = screen.getAllByText('Dashboard');
    expect(headers.length).toBeGreaterThan(0);
  });

  it('displays user name in header', () => {
    renderWithProviders(<Layout />);
    
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('displays user initials when no profile image', () => {
    renderWithProviders(<Layout />);
    
    expect(screen.getByText('JD')).toBeInTheDocument();
  });

  it('renders logout button', () => {
    renderWithProviders(<Layout />);
    
    expect(screen.getByRole('button', { name: /sign out/i })).toBeInTheDocument();
  });

  it('calls signOut when logout button is clicked', () => {
    const signOutMock = vi.fn().mockResolvedValue(undefined);
    const authValue = createMockAuthContext({ signOut: signOutMock });
    
    renderWithProviders(<Layout />, { authValue });
    
    const logoutButton = screen.getByRole('button', { name: /sign out/i });
    fireEvent.click(logoutButton);
    
    expect(signOutMock).toHaveBeenCalled();
  });

  it('shows loading skeleton when loading', () => {
    const authValue = createMockAuthContext({ loading: true, user: null });
    
    renderWithProviders(<Layout />, { authValue });
    
    // Should show loading skeleton elements
    expect(screen.queryByText('John Doe')).not.toBeInTheDocument();
  });

  it('shows error state when user is null and not loading', () => {
    const authValue = createMockAuthContext({ user: null, loading: false });
    
    renderWithProviders(<Layout />, { authValue });
    
    expect(screen.getByText('Unable to load user data')).toBeInTheDocument();
    expect(screen.getByText('Return to Login')).toBeInTheDocument();
  });

  it('renders notification bell button', () => {
    renderWithProviders(<Layout />);

    // NotificationBell renders as a button, not a link
    const notificationButton = screen.getByRole('button', { name: /notifications/i });
    expect(notificationButton).toBeInTheDocument();
  });

  it('renders settings link on avatar', () => {
    renderWithProviders(<Layout />);
    
    const settingsLink = screen.getByRole('link', { name: /go to settings/i });
    expect(settingsLink).toHaveAttribute('href', '/settings');
  });

  it('displays correct page title for payments route', () => {
    renderWithProviders(<Layout />, { initialRoute: '/payments' });
    
    // Payments page intentionally has no header title (empty string)
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('');
  });

  it('displays correct page title for documents route', () => {
    renderWithProviders(<Layout />, { initialRoute: '/documents' });

    // Documents page intentionally has no header title (empty string)
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('');
  });

  it('displays correct page title for maintenance route', () => {
    renderWithProviders(<Layout />, { initialRoute: '/maintenance' });
    
    // Maintenance page intentionally has no header title (empty string)
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('');
  });

  it('renders child route content via Outlet', () => {
    renderWithProviders(<Layout />, { initialRoute: '/dashboard' });
    
    expect(screen.getByText('Dashboard Content')).toBeInTheDocument();
  });

  it('displays Tenant role label', () => {
    renderWithProviders(<Layout />);
    
    expect(screen.getByText('Tenant')).toBeInTheDocument();
  });
});


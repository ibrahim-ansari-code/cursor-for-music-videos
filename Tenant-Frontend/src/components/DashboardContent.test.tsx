import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import DashboardContent from './DashboardContent';
import { AuthContext } from '@/contexts/AuthContext';
import type { AuthContextValue, User } from '@/types';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock user data
const mockUser: User = {
  id: 'test-user-id',
  email: 'tenant@example.com',
  first_name: 'Jane',
  last_name: 'Smith',
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

// Wrapper component with providers
const renderWithProviders = (
  component: React.ReactNode,
  { authValue = createMockAuthContext() } = {}
) => {
  return render(
    <AuthContext.Provider value={authValue}>
      <MemoryRouter>
        {component}
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('DashboardContent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders welcome message with user first name', async () => {
    renderWithProviders(<DashboardContent />);
    
    await waitFor(() => {
      expect(screen.getByText(/Welcome back, Jane!/)).toBeInTheDocument();
    });
  });

  it('renders welcome message with default name when user has no first name', async () => {
    const userWithoutName: User = {
      ...mockUser,
      first_name: null,
    };
    const authValue = createMockAuthContext({ user: userWithoutName });
    
    renderWithProviders(<DashboardContent />, { authValue });
    
    await waitFor(() => {
      expect(screen.getByText(/Welcome back, Tenant!/)).toBeInTheDocument();
    });
  });

  it('renders dashboard info cards', async () => {
    renderWithProviders(<DashboardContent />);
    
    await waitFor(() => {
      expect(screen.getByText('My Unit')).toBeInTheDocument();
      expect(screen.getByText('Monthly Rent')).toBeInTheDocument();
      expect(screen.getByText('Next Payment')).toBeInTheDocument();
      expect(screen.getByText('Maintenance Requests')).toBeInTheDocument();
    });
  });

  it('renders quick action buttons', async () => {
    renderWithProviders(<DashboardContent />);
    
    await waitFor(() => {
      expect(screen.getByText('Make a Payment')).toBeInTheDocument();
      expect(screen.getByText('Request Maintenance')).toBeInTheDocument();
      expect(screen.getByText('View Documents')).toBeInTheDocument();
    });
  });

  it('navigates to payments when Make a Payment is clicked', async () => {
    renderWithProviders(<DashboardContent />);
    
    await waitFor(() => {
      const paymentButton = screen.getByText('Make a Payment').closest('button');
      expect(paymentButton).toBeInTheDocument();
      if (paymentButton) {
        fireEvent.click(paymentButton);
        expect(mockNavigate).toHaveBeenCalledWith('/payments');
      }
    });
  });

  it('navigates to maintenance when Request Maintenance is clicked', async () => {
    renderWithProviders(<DashboardContent />);
    
    await waitFor(() => {
      const maintenanceButton = screen.getByText('Request Maintenance').closest('button');
      expect(maintenanceButton).toBeInTheDocument();
      if (maintenanceButton) {
        fireEvent.click(maintenanceButton);
        expect(mockNavigate).toHaveBeenCalledWith('/maintenance');
      }
    });
  });

  it('navigates to documents when View Documents is clicked', async () => {
    renderWithProviders(<DashboardContent />);
    
    await waitFor(() => {
      const documentsButton = screen.getByText('View Documents').closest('button');
      expect(documentsButton).toBeInTheDocument();
      if (documentsButton) {
        fireEvent.click(documentsButton);
        expect(mockNavigate).toHaveBeenCalledWith('/documents');
      }
    });
  });

  it('renders Recent Payments section', async () => {
    renderWithProviders(<DashboardContent />);
    
    await waitFor(() => {
      expect(screen.getByText('Recent Payments')).toBeInTheDocument();
    });
  });

  it('renders View All link for payments', async () => {
    renderWithProviders(<DashboardContent />);
    
    await waitFor(() => {
      const viewAllButton = screen.getByRole('button', { name: /view all/i });
      expect(viewAllButton).toBeInTheDocument();
    });
  });

  it('navigates to payments when View All is clicked', async () => {
    renderWithProviders(<DashboardContent />);
    
    await waitFor(() => {
      const viewAllButton = screen.getByRole('button', { name: /view all/i });
      fireEvent.click(viewAllButton);
      expect(mockNavigate).toHaveBeenCalledWith('/payments');
    });
  });

  it('renders info card action links', async () => {
    renderWithProviders(<DashboardContent />);
    
    await waitFor(() => {
      expect(screen.getByText('View Lease')).toBeInTheDocument();
      expect(screen.getByText('Pay Now')).toBeInTheDocument();
      expect(screen.getByText('New Request')).toBeInTheDocument();
    });
  });

  it('navigates to documents when View Lease is clicked', async () => {
    renderWithProviders(<DashboardContent />);
    
    await waitFor(() => {
      const viewLeaseButton = screen.getByText('View Lease');
      fireEvent.click(viewLeaseButton);
      expect(mockNavigate).toHaveBeenCalledWith('/documents');
    });
  });

  it('renders overview description text', async () => {
    renderWithProviders(<DashboardContent />);
    
    await waitFor(() => {
      expect(screen.getByText(/Here's an overview of your apartment and upcoming payments/)).toBeInTheDocument();
    });
  });
});


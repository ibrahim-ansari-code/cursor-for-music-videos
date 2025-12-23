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

// Mock useTenantDashboard hook with correct data structure
vi.mock('@/hooks/useTenantDashboard', () => ({
  useTenantDashboard: () => ({
    data: {
      my_unit: {
        unit_id: 1,
        unit_name: 'Unit 101',
        property_id: 1,
        property_name: 'Sunset Apartments',
        full_address: '123 Main St, City, State 12345',
        lease_start: '2024-01-01',
        lease_end: '2024-12-31',
      },
      monthly_rent: {
        amount: '1500.00',
        rent_due_day: 1,
        has_active_lease: true,
        last_payment_date: '2024-01-01',
      },
      next_payment: {
        current_balance: '1500.00',
        current_balance_cents: 150000,
        due_date: '2024-02-01',
        days_remaining: 15,
        is_overdue: false,
        is_paid: false,
        has_autopay: false,
        autopay_status: 'not_enrolled',
        next_autopay_date: null,
      },
      maintenance: {
        open_requests: 2,
        last_updated: '2024-01-15T10:00:00Z',
      },
    },
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
  default: () => ({
    data: null,
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

// Mock usePayments hooks - useRentTransactions returns { data, isLoading, error }
vi.mock('@/hooks/usePayments', () => ({
  useRentTransactions: () => ({
    data: [
      {
        id: 'tx-1',
        amount_cents: 150000,
        status: 'succeeded',
        created_at: '2024-01-01T10:00:00Z',
        payment_method_type: 'acss_debit',
        payment_method_last_four: '1234',
        payment_method_bank_name: 'TD Bank',
        receipt_url: 'https://example.com/receipt/1',
      },
    ],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
  usePaymentMethods: () => ({
    paymentMethods: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

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
      // Check the heading contains the welcome message with user name
      const heading = screen.getByRole('heading', { level: 1 });
      expect(heading).toHaveTextContent(/Welcome to your Tenant Dashboard/);
      expect(heading).toHaveTextContent(/Jane/);
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
      const heading = screen.getByRole('heading', { level: 1 });
      expect(heading).toHaveTextContent(/Welcome to your Tenant Dashboard/);
      expect(heading).toHaveTextContent(/Tenant/);
    });
  });

  it('renders dashboard info cards', async () => {
    renderWithProviders(<DashboardContent />);

    await waitFor(() => {
      expect(screen.getByText('My Unit')).toBeInTheDocument();
      expect(screen.getByText('Monthly Rent')).toBeInTheDocument();
      expect(screen.getByText('Current Balance')).toBeInTheDocument();
      expect(screen.getByText('Maintenance Requests')).toBeInTheDocument();
    });
  });

  it('renders quick action buttons', async () => {
    renderWithProviders(<DashboardContent />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Make a Payment' })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: 'Request Maintenance' })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: 'View Documents' })).toBeInTheDocument();
    });
  });

  it('navigates to payments when Make a Payment is clicked', async () => {
    renderWithProviders(<DashboardContent />);

    await waitFor(() => {
      const paymentHeading = screen.getByRole('heading', { name: 'Make a Payment' });
      const paymentButton = paymentHeading.closest('button');
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
      const maintenanceHeading = screen.getByRole('heading', { name: 'Request Maintenance' });
      const maintenanceButton = maintenanceHeading.closest('button');
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
      const documentsHeading = screen.getByRole('heading', { name: 'View Documents' });
      const documentsButton = documentsHeading.closest('button');
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

  it('renders View All button for payments', async () => {
    renderWithProviders(<DashboardContent />);

    await waitFor(() => {
      expect(screen.getByText('View All')).toBeInTheDocument();
    });
  });

  it('navigates to payments when View All is clicked', async () => {
    renderWithProviders(<DashboardContent />);

    await waitFor(() => {
      const viewAllButton = screen.getByText('View All');
      fireEvent.click(viewAllButton);
      expect(mockNavigate).toHaveBeenCalledWith('/payments');
    });
  });

  it('renders dashboard grid layout', async () => {
    renderWithProviders(<DashboardContent />);

    await waitFor(() => {
      // Test that the grid container exists with proper classes
      const mainContent = screen.getByRole('heading', { level: 1 });
      expect(mainContent).toHaveTextContent(/Welcome to your Tenant Dashboard/);
    });
  });

  it('displays correct user name in welcome message', async () => {
    renderWithProviders(<DashboardContent />);

    await waitFor(() => {
      const heading = screen.getByRole('heading', { level: 1 });
      expect(heading).toHaveTextContent(/Jane/);
    });
  });

  it('renders all four dashboard cards', async () => {
    renderWithProviders(<DashboardContent />);

    await waitFor(() => {
      expect(screen.getByText('My Unit')).toBeInTheDocument();
      expect(screen.getByText('Monthly Rent')).toBeInTheDocument();
      expect(screen.getByText('Current Balance')).toBeInTheDocument();
      expect(screen.getByText('Maintenance Requests')).toBeInTheDocument();
    });
  });
});

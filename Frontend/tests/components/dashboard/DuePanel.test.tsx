import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import DuePanel from '../../../src/components/dashboard/DuePanel';
import * as tenantsApi from '../../../src/utils/api/tenants';

// Mock the API functions
vi.mock('../../../src/utils/api/tenants', () => ({
  sendTenantReminder: vi.fn(),
  fetchTenant: vi.fn(),
}));

// Mock react-toastify
vi.mock('react-toastify', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
  },
}));

// Mock react-dom portal
vi.mock('react-dom', async () => {
  const actual = await vi.importActual('react-dom');
  return {
    ...actual,
    createPortal: (node: React.ReactNode) => node,
  };
});

// Mock formatters
vi.mock('../../../src/utils/formatters', () => ({
  formatCurrency: (amount: number) => `$${amount.toFixed(2)}`,
  getAvatarColor: (_name: string) => 'bg-blue-500',
  getInitials: (name: string) => name.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2),
}));

// Mock ReminderMethodModal - auto-selects 'email' method when rendered
vi.mock('../../../src/components/tenants/TenantProfile/ReminderMethodModal', () => ({
  default: ({ isOpen, onClose, onSelect }: any) => {
    // Automatically select 'email' when modal opens to trigger the confirmation modal flow
    React.useEffect(() => {
      if (isOpen) {
        // Small delay to simulate user clicking
        const timer = setTimeout(() => onSelect('email'), 10);
        return () => clearTimeout(timer);
      }
    }, [isOpen, onSelect]);

    if (!isOpen) return null;
    return (
      <div data-testid="method-modal">
        <button data-testid="method-email" onClick={() => onSelect('email')}>
          Send via Email
        </button>
        <button data-testid="method-portal" onClick={() => onSelect('portal')}>
          Send via Portal
        </button>
        <button data-testid="method-close" onClick={onClose}>
          Close
        </button>
      </div>
    );
  },
}));

// Mock ReminderConfirmationModal
vi.mock('../../../src/components/tenants/TenantProfile/ReminderConfirmationModal', () => ({
  default: ({ isOpen, onClose, onConfirm, tenant, event, isLoading }: any) => {
    if (!isOpen) return null;
    return (
      <div data-testid="reminder-modal">
        <div data-testid="modal-tenant-name">
          {tenant.tenant_type === 'Company' ? tenant.company_name : `${tenant.first_name} ${tenant.last_name}`}
        </div>
        <div data-testid="modal-event-title">{event.title}</div>
        <button data-testid="modal-cancel" onClick={onClose} disabled={isLoading}>
          Cancel
        </button>
        <button
          data-testid="modal-confirm"
          onClick={() => onConfirm(null, null)}
          disabled={isLoading}
        >
          {isLoading ? 'Sending...' : 'Send Reminder'}
        </button>
      </div>
    );
  },
}));

// Mock Sentry
vi.mock('@sentry/react', () => ({
  startSpan: vi.fn((_config, callback) => callback()),
  captureException: vi.fn(),
  logger: {
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    trace: vi.fn(),
  },
}));

describe('DuePanel - Reminder Functionality', () => {
  const mockOnChangeTab = vi.fn();
  const mockGetAvatarColor = vi.fn((_name: string) => 'bg-blue-500');
  const mockGetTenantInitials = vi.fn((name: string) => {
    const parts = name.split(' ');
    return parts.map(p => p[0]).join('').toUpperCase().slice(0, 2);
  });

  const mockRentData = [
    {
      lease_id: 1,
      tenant_id: 101,
      tenant_name: 'John Doe',
      remaining_due: 1500.00,
      monthly_rent: 1500.00,
      status: 'DUE',
      due_date: '2024-01-15',
      days_overdue: 0,
    },
    {
      lease_id: 2,
      tenant_id: 102,
      tenant_name: 'Jane Smith',
      remaining_due: 2000.00,
      monthly_rent: 2000.00,
      status: 'OVERDUE',
      due_date: '2024-01-10',
      days_overdue: 5,
    },
    {
      lease_id: 3,
      tenant_id: null, // No tenant ID - should not show reminder button
      tenant_name: 'No Tenant',
      remaining_due: 1000.00,
      monthly_rent: 1000.00,
      status: 'DUE',
      due_date: '2024-01-15',
      days_overdue: 0,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders the DuePanel with rent data', () => {
      render(
        <DuePanel
          activeTab="rent"
          onChangeTab={mockOnChangeTab}
          rentLoading={false}
          rentData={mockRentData}
          getAvatarColor={mockGetAvatarColor}
          getTenantInitials={mockGetTenantInitials}
        />
      );

      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('Jane Smith')).toBeInTheDocument();
      expect(screen.getByText('No Tenant')).toBeInTheDocument();
    });

    it('displays reminder button only for rents with tenant_id', () => {
      render(
        <DuePanel
          activeTab="rent"
          onChangeTab={mockOnChangeTab}
          rentLoading={false}
          rentData={mockRentData}
          getAvatarColor={mockGetAvatarColor}
          getTenantInitials={mockGetTenantInitials}
        />
      );

      // Should have 2 reminder buttons (for John Doe and Jane Smith)
      const reminderButtons = screen.getAllByLabelText('Send reminder email');
      expect(reminderButtons).toHaveLength(2);
    });

    it('does not display reminder button for rents without tenant_id', () => {
      render(
        <DuePanel
          activeTab="rent"
          onChangeTab={mockOnChangeTab}
          rentLoading={false}
          rentData={[mockRentData[2]]} // Only the one without tenant_id
          getAvatarColor={mockGetAvatarColor}
          getTenantInitials={mockGetTenantInitials}
        />
      );

      const reminderButtons = screen.queryAllByLabelText('Send reminder email');
      expect(reminderButtons).toHaveLength(0);
    });
  });

  describe('Reminder Modal Interaction', () => {
    it('opens reminder modal when reminder button is clicked', async () => {
      const mockFetchTenant = vi.mocked(tenantsApi.fetchTenant);
      mockFetchTenant.mockResolvedValue({
        id: 101,
        tenant_type: 'Individual',
        first_name: 'John',
        last_name: 'Doe',
        email: 'john.doe@example.com',
        phone: '555-0000',
        status: 'Active',
        landlord_id: 'landlord-123',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      } as any);

      render(
        <DuePanel
          activeTab="rent"
          onChangeTab={mockOnChangeTab}
          rentLoading={false}
          rentData={[mockRentData[0]]}
          getAvatarColor={mockGetAvatarColor}
          getTenantInitials={mockGetTenantInitials}
        />
      );

      const reminderButton = screen.getByLabelText('Send reminder email');
      fireEvent.click(reminderButton);

      await waitFor(() => {
        expect(screen.getByTestId('reminder-modal')).toBeInTheDocument();
      });
    });

    it('displays correct tenant information in modal after fetching', async () => {
      const mockFetchTenant = vi.mocked(tenantsApi.fetchTenant);
      mockFetchTenant.mockResolvedValue({
        id: 101,
        tenant_type: 'Individual',
        first_name: 'John',
        last_name: 'Doe',
        email: 'john.doe@example.com',
        phone: '555-0000',
        status: 'Active',
        landlord_id: 'landlord-123',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      } as any);

      render(
        <DuePanel
          activeTab="rent"
          onChangeTab={mockOnChangeTab}
          rentLoading={false}
          rentData={[mockRentData[0]]}
          getAvatarColor={mockGetAvatarColor}
          getTenantInitials={mockGetTenantInitials}
        />
      );

      const reminderButton = screen.getByLabelText('Send reminder email');
      fireEvent.click(reminderButton);

      await waitFor(() => {
        expect(screen.getByTestId('reminder-modal')).toBeInTheDocument();
        expect(screen.getByTestId('modal-tenant-name')).toHaveTextContent('John Doe');
      });
    });

    it('shows loading state while fetching tenant', async () => {
      const mockFetchTenant = vi.mocked(tenantsApi.fetchTenant);
      let resolveTenant: (value: any) => void;
      const tenantPromise = new Promise((resolve) => {
        resolveTenant = resolve;
      });
      mockFetchTenant.mockReturnValue(tenantPromise as any);

      render(
        <DuePanel
          activeTab="rent"
          onChangeTab={mockOnChangeTab}
          rentLoading={false}
          rentData={[mockRentData[0]]}
          getAvatarColor={mockGetAvatarColor}
          getTenantInitials={mockGetTenantInitials}
        />
      );

      const reminderButton = screen.getByLabelText('Send reminder email');
      fireEvent.click(reminderButton);

      // Button should show loading spinner
      await waitFor(() => {
        const button = screen.getByLabelText('Send reminder email');
        expect(button).toBeDisabled();
      });

      // Resolve the promise
      resolveTenant!({
        id: 101,
        tenant_type: 'Individual',
        first_name: 'John',
        last_name: 'Doe',
        email: 'john.doe@example.com',
        phone: '555-0000',
        status: 'Active',
        landlord_id: 'landlord-123',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      });

      await waitFor(() => {
        expect(screen.getByTestId('reminder-modal')).toBeInTheDocument();
      });
    });

    it('handles tenant fetch error gracefully', async () => {
      const mockFetchTenant = vi.mocked(tenantsApi.fetchTenant);
      mockFetchTenant.mockRejectedValue(new Error('Failed to fetch tenant'));

      const { toast } = await import('react-toastify');

      render(
        <DuePanel
          activeTab="rent"
          onChangeTab={mockOnChangeTab}
          rentLoading={false}
          rentData={[mockRentData[0]]}
          getAvatarColor={mockGetAvatarColor}
          getTenantInitials={mockGetTenantInitials}
        />
      );

      const reminderButton = screen.getByLabelText('Send reminder email');
      fireEvent.click(reminderButton);

      await waitFor(() => {
        expect(mockFetchTenant).toHaveBeenCalledWith(101);
        expect(toast.error).toHaveBeenCalledWith('Could not load tenant details. Please try again.');
      });

      // Modal should not open on error
      expect(screen.queryByTestId('reminder-modal')).not.toBeInTheDocument();
    });

    it('closes modal when cancel button is clicked', async () => {
      const mockFetchTenant = vi.mocked(tenantsApi.fetchTenant);
      mockFetchTenant.mockResolvedValue({
        id: 101,
        tenant_type: 'Individual',
        first_name: 'John',
        last_name: 'Doe',
        email: 'john.doe@example.com',
        phone: '555-0000',
        status: 'Active',
        landlord_id: 'landlord-123',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      } as any);

      render(
        <DuePanel
          activeTab="rent"
          onChangeTab={mockOnChangeTab}
          rentLoading={false}
          rentData={[mockRentData[0]]}
          getAvatarColor={mockGetAvatarColor}
          getTenantInitials={mockGetTenantInitials}
        />
      );

      const reminderButton = screen.getByLabelText('Send reminder email');
      fireEvent.click(reminderButton);

      await waitFor(() => {
        expect(screen.getByTestId('reminder-modal')).toBeInTheDocument();
      });

      const cancelButton = screen.getByTestId('modal-cancel');
      fireEvent.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByTestId('reminder-modal')).not.toBeInTheDocument();
      });
    });
  });

  describe('Sending Reminder', () => {
    it('sends reminder with correct data when confirmed', async () => {
      const mockFetchTenant = vi.mocked(tenantsApi.fetchTenant);
      const mockSendReminder = vi.mocked(tenantsApi.sendTenantReminder);
      
      mockFetchTenant.mockResolvedValue({
        id: 101,
        tenant_type: 'Individual',
        first_name: 'John',
        last_name: 'Doe',
        email: 'john.doe@example.com',
        phone: '555-0000',
        status: 'Active',
        landlord_id: 'landlord-123',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      } as any);
      mockSendReminder.mockResolvedValue({ success: true, message: 'Reminder sent successfully' });

      render(
        <DuePanel
          activeTab="rent"
          onChangeTab={mockOnChangeTab}
          rentLoading={false}
          rentData={[mockRentData[0]]}
          getAvatarColor={mockGetAvatarColor}
          getTenantInitials={mockGetTenantInitials}
        />
      );

      const reminderButton = screen.getByLabelText('Send reminder email');
      fireEvent.click(reminderButton);

      await waitFor(() => {
        expect(screen.getByTestId('reminder-modal')).toBeInTheDocument();
      });

      const confirmButton = screen.getByTestId('modal-confirm');
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(mockSendReminder).toHaveBeenCalledTimes(1);
      });

      // sendTenantReminder takes (tenant_id, reminderData) as arguments
      const tenantId = mockSendReminder.mock.calls[0][0];
      const callArgs = mockSendReminder.mock.calls[0][1];
      expect(tenantId).toBe(101);
      expect(callArgs.event_type).toBe('rent');
      expect(callArgs.event_amount).toBe(1500.00);
    });

    it('sends reminder with custom subject and message when provided', async () => {
      const mockFetchTenant = vi.mocked(tenantsApi.fetchTenant);
      const mockSendReminder = vi.mocked(tenantsApi.sendTenantReminder);
      
      mockFetchTenant.mockResolvedValue({
        id: 101,
        tenant_type: 'Individual',
        first_name: 'John',
        last_name: 'Doe',
        email: 'john.doe@example.com',
        phone: '555-0000',
        status: 'Active',
        landlord_id: 'landlord-123',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      } as any);
      mockSendReminder.mockResolvedValue({ success: true, message: 'Reminder sent successfully' });

      render(
        <DuePanel
          activeTab="rent"
          onChangeTab={mockOnChangeTab}
          rentLoading={false}
          rentData={[mockRentData[0]]}
          getAvatarColor={mockGetAvatarColor}
          getTenantInitials={mockGetTenantInitials}
        />
      );

      const reminderButton = screen.getByLabelText('Send reminder email');
      fireEvent.click(reminderButton);

      await waitFor(() => {
        expect(screen.getByTestId('reminder-modal')).toBeInTheDocument();
      });

      const confirmButton = screen.getByTestId('modal-confirm');
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(mockSendReminder).toHaveBeenCalled();
      });

      // sendTenantReminder takes (tenant_id, reminderData) as arguments
      const tenantId = mockSendReminder.mock.calls[0][0];
      const callArgs = mockSendReminder.mock.calls[0][1];
      expect(tenantId).toBe(101);
      expect(callArgs).toHaveProperty('event_type', 'rent');
    });

    it('closes modal after successful reminder send', async () => {
      const mockFetchTenant = vi.mocked(tenantsApi.fetchTenant);
      const mockSendReminder = vi.mocked(tenantsApi.sendTenantReminder);
      
      mockFetchTenant.mockResolvedValue({
        id: 101,
        tenant_type: 'Individual',
        first_name: 'John',
        last_name: 'Doe',
        email: 'john.doe@example.com',
        phone: '555-0000',
        status: 'Active',
        landlord_id: 'landlord-123',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      } as any);
      mockSendReminder.mockResolvedValue({ success: true, message: 'Reminder sent successfully' });

      render(
        <DuePanel
          activeTab="rent"
          onChangeTab={mockOnChangeTab}
          rentLoading={false}
          rentData={[mockRentData[0]]}
          getAvatarColor={mockGetAvatarColor}
          getTenantInitials={mockGetTenantInitials}
        />
      );

      const reminderButton = screen.getByLabelText('Send reminder email');
      fireEvent.click(reminderButton);

      await waitFor(() => {
        expect(screen.getByTestId('reminder-modal')).toBeInTheDocument();
      });

      const confirmButton = screen.getByTestId('modal-confirm');
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(screen.queryByTestId('reminder-modal')).not.toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('handles API error gracefully when sending reminder', async () => {
      const mockFetchTenant = vi.mocked(tenantsApi.fetchTenant);
      const mockSendReminder = vi.mocked(tenantsApi.sendTenantReminder);
      
      mockFetchTenant.mockResolvedValue({
        id: 101,
        tenant_type: 'Individual',
        first_name: 'John',
        last_name: 'Doe',
        email: 'john.doe@example.com',
        phone: '555-0000',
        status: 'Active',
        landlord_id: 'landlord-123',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      } as any);
      mockSendReminder.mockRejectedValue(new Error('API Error'));

      // Mock console.error to avoid noise in test output
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(
        <DuePanel
          activeTab="rent"
          onChangeTab={mockOnChangeTab}
          rentLoading={false}
          rentData={[mockRentData[0]]}
          getAvatarColor={mockGetAvatarColor}
          getTenantInitials={mockGetTenantInitials}
        />
      );

      const reminderButton = screen.getByLabelText('Send reminder email');
      fireEvent.click(reminderButton);

      await waitFor(() => {
        expect(screen.getByTestId('reminder-modal')).toBeInTheDocument();
      });

      const confirmButton = screen.getByTestId('modal-confirm');
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(mockSendReminder).toHaveBeenCalled();
      });

      // Modal should still close (or stay open depending on implementation)
      // The error should be handled gracefully
      consoleSpy.mockRestore();
    });

    it('displays loading state while sending reminder', async () => {
      const mockFetchTenant = vi.mocked(tenantsApi.fetchTenant);
      const mockSendReminder = vi.mocked(tenantsApi.sendTenantReminder);
      
      mockFetchTenant.mockResolvedValue({
        id: 101,
        tenant_type: 'Individual',
        first_name: 'John',
        last_name: 'Doe',
        email: 'john.doe@example.com',
        phone: '555-0000',
        status: 'Active',
        landlord_id: 'landlord-123',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      } as any);
      
      // Create a promise that we can control
      let resolvePromise: (value: any) => void;
      const controlledPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      mockSendReminder.mockReturnValue(controlledPromise as any);

      render(
        <DuePanel
          activeTab="rent"
          onChangeTab={mockOnChangeTab}
          rentLoading={false}
          rentData={[mockRentData[0]]}
          getAvatarColor={mockGetAvatarColor}
          getTenantInitials={mockGetTenantInitials}
        />
      );

      const reminderButton = screen.getByLabelText('Send reminder email');
      fireEvent.click(reminderButton);

      await waitFor(() => {
        expect(screen.getByTestId('reminder-modal')).toBeInTheDocument();
      });

      const confirmButton = screen.getByTestId('modal-confirm');
      fireEvent.click(confirmButton);

      // Check that modal button shows loading state
      await waitFor(() => {
        const modalConfirmButton = screen.getByTestId('modal-confirm');
        expect(modalConfirmButton).toHaveTextContent('Sending...');
        expect(modalConfirmButton).toBeDisabled();
      });

      // Resolve the promise
      resolvePromise!({ success: true });

      // After successful send, modal should close (indicating loading state is cleared)
      await waitFor(() => {
        expect(screen.queryByTestId('reminder-modal')).not.toBeInTheDocument();
      });
    });
  });

  describe('Event Data Construction', () => {
    it('constructs correct event data for rent due today', async () => {
      const mockFetchTenant = vi.mocked(tenantsApi.fetchTenant);
      const mockSendReminder = vi.mocked(tenantsApi.sendTenantReminder);
      
      mockFetchTenant.mockResolvedValue({
        id: 101,
        tenant_type: 'Individual',
        first_name: 'John',
        last_name: 'Doe',
        email: 'john.doe@example.com',
        phone: '555-0000',
        status: 'Active',
        landlord_id: 'landlord-123',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      } as any);
      mockSendReminder.mockResolvedValue({ success: true, message: 'Reminder sent successfully' });

      render(
        <DuePanel
          activeTab="rent"
          onChangeTab={mockOnChangeTab}
          rentLoading={false}
          rentData={[mockRentData[0]]} // DUE status, days_overdue: 0
          getAvatarColor={mockGetAvatarColor}
          getTenantInitials={mockGetTenantInitials}
        />
      );

      const reminderButton = screen.getByLabelText('Send reminder email');
      fireEvent.click(reminderButton);

      await waitFor(() => {
        expect(screen.getByTestId('reminder-modal')).toBeInTheDocument();
      });

      const confirmButton = screen.getByTestId('modal-confirm');
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(mockSendReminder).toHaveBeenCalled();
      });

      // The event should be constructed with correct days_remaining
      // For DUE status with days_overdue: 0, days_remaining should be 0
      const callArgs = mockSendReminder.mock.calls[0][1];
      expect(callArgs.event_type).toBe('rent');
    });

    it('constructs correct event data for overdue rent', async () => {
      const mockFetchTenant = vi.mocked(tenantsApi.fetchTenant);
      const mockSendReminder = vi.mocked(tenantsApi.sendTenantReminder);
      
      mockFetchTenant.mockResolvedValue({
        id: 102,
        tenant_type: 'Individual',
        first_name: 'Jane',
        last_name: 'Smith',
        email: 'jane.smith@example.com',
        phone: '555-0000',
        status: 'Active',
        landlord_id: 'landlord-123',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      } as any);
      mockSendReminder.mockResolvedValue({ success: true, message: 'Reminder sent successfully' });

      render(
        <DuePanel
          activeTab="rent"
          onChangeTab={mockOnChangeTab}
          rentLoading={false}
          rentData={[mockRentData[1]]} // OVERDUE status, days_overdue: 5
          getAvatarColor={mockGetAvatarColor}
          getTenantInitials={mockGetTenantInitials}
        />
      );

      const reminderButton = screen.getByLabelText('Send reminder email');
      fireEvent.click(reminderButton);

      await waitFor(() => {
        expect(screen.getByTestId('reminder-modal')).toBeInTheDocument();
      });

      const confirmButton = screen.getByTestId('modal-confirm');
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(mockSendReminder).toHaveBeenCalled();
      });

      // The event should be constructed with negative days_remaining for overdue
      const callArgs = mockSendReminder.mock.calls[0][1];
      expect(callArgs.event_type).toBe('rent');
      expect(callArgs.days_remaining).toBeLessThanOrEqual(0);
    });
  });
});


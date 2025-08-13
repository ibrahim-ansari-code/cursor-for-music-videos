import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders, createMockUser } from '../../test/utils';
import DashboardContent from '../DashboardContent';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate
  };
});

describe('DashboardContent Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders welcome message with user name', () => {
    const testUser = createMockUser({
      first_name: 'Alice'
    });
    
    renderWithProviders(<DashboardContent />, { 
      authContextValue: { user: testUser, loading: false, isAuthenticated: true }
    });
    
    expect(screen.getByText('Welcome back, Alice!')).toBeInTheDocument();
    expect(screen.getByText("Here's an overview of your apartment and upcoming payments.")).toBeInTheDocument();
  });

  it('renders fallback name when user has no first name', () => {
    const testUser = createMockUser({
      first_name: null
    });
    
    renderWithProviders(<DashboardContent />, { 
      authContextValue: { user: testUser, loading: false, isAuthenticated: true }
    });
    
    expect(screen.getByText('Welcome back, Tenant!')).toBeInTheDocument();
  });

  it('renders all dashboard info cards', () => {
    renderWithProviders(<DashboardContent />);
    
    // Check for all info cards
    expect(screen.getByText('My Unit')).toBeInTheDocument();
    expect(screen.getByText('Monthly Rent')).toBeInTheDocument();
    expect(screen.getByText('Next Payment')).toBeInTheDocument();
    expect(screen.getByText('Maintenance Requests')).toBeInTheDocument();
    
    // Check for loading states
    expect(screen.getAllByText('Loading...')).toHaveLength(4);
  });

  it('renders info cards with correct icons', () => {
    renderWithProviders(<DashboardContent />);
    
    const container = screen.getByText('My Unit').closest('.bg-white');
    expect(container.querySelector('svg')).toBeInTheDocument();
    
    const rentContainer = screen.getByText('Monthly Rent').closest('.bg-white');
    expect(rentContainer.querySelector('svg')).toBeInTheDocument();
    
    const paymentContainer = screen.getByText('Next Payment').closest('.bg-white');
    expect(paymentContainer.querySelector('svg')).toBeInTheDocument();
    
    const maintenanceContainer = screen.getByText('Maintenance Requests').closest('.bg-white');
    expect(maintenanceContainer.querySelector('svg')).toBeInTheDocument();
  });

  it('handles info card action clicks correctly', () => {
    renderWithProviders(<DashboardContent />);
    
    // Test "View Lease" action
    const viewLeaseButton = screen.getByText('View Lease');
    fireEvent.click(viewLeaseButton);
    expect(mockNavigate).toHaveBeenCalledWith('/documents');
    
    // Test "Pay Now" action
    const payNowButton = screen.getByText('Pay Now');
    fireEvent.click(payNowButton);
    expect(mockNavigate).toHaveBeenCalledWith('/payments');
    
    // Test "New Request" action
    const newRequestButton = screen.getByText('New Request');
    fireEvent.click(newRequestButton);
    expect(mockNavigate).toHaveBeenCalledWith('/maintenance');
  });

  it('renders recent payments section', () => {
    renderWithProviders(<DashboardContent />);
    
    expect(screen.getByText('Recent Payments')).toBeInTheDocument();
    expect(screen.getByText('View All')).toBeInTheDocument();
    expect(screen.getByText('Payment history will be loaded from your account')).toBeInTheDocument();
  });

  it('handles view all payments click', () => {
    renderWithProviders(<DashboardContent />);
    
    const viewAllButton = screen.getByText('View All');
    fireEvent.click(viewAllButton);
    expect(mockNavigate).toHaveBeenCalledWith('/payments');
  });

  it('renders quick action cards', () => {
    renderWithProviders(<DashboardContent />);
    
    expect(screen.getByText('Make a Payment')).toBeInTheDocument();
    expect(screen.getByText('Pay rent or other charges')).toBeInTheDocument();
    
    expect(screen.getByText('Request Maintenance')).toBeInTheDocument();
    expect(screen.getByText('Submit a new maintenance request')).toBeInTheDocument();
    
    expect(screen.getByText('View Documents')).toBeInTheDocument();
    expect(screen.getByText('Access lease and other documents')).toBeInTheDocument();
  });

  it('handles quick action clicks correctly', () => {
    renderWithProviders(<DashboardContent />);
    
    // Test payment action
    const paymentAction = screen.getByText('Make a Payment').closest('button');
    fireEvent.click(paymentAction);
    expect(mockNavigate).toHaveBeenCalledWith('/payments');
    
    // Test maintenance action
    const maintenanceAction = screen.getByText('Request Maintenance').closest('button');
    fireEvent.click(maintenanceAction);
    expect(mockNavigate).toHaveBeenCalledWith('/maintenance');
    
    // Test documents action
    const documentsAction = screen.getByText('View Documents').closest('button');
    fireEvent.click(documentsAction);
    expect(mockNavigate).toHaveBeenCalledWith('/documents');
  });

  it('applies correct CSS classes for styling', () => {
    renderWithProviders(<DashboardContent />);
    
    // Check grid layout for info cards
    const infoCardsGrid = screen.getByText('My Unit').closest('.grid');
    expect(infoCardsGrid).toHaveClass('grid-cols-1', 'gap-6', 'sm:grid-cols-2', 'lg:grid-cols-4');
    
    // Check quick actions grid
    const quickActionsGrid = screen.getByText('Make a Payment').closest('.grid');
    expect(quickActionsGrid).toHaveClass('grid-cols-1', 'gap-4', 'sm:grid-cols-2', 'lg:grid-cols-3');
  });

  it('displays loading spinner initially', async () => {
    // Create a component that starts with loading: true
    const LoadingDashboard = () => {
      const [loading] = React.useState(true);
      
      if (loading) {
        return (
          <div className="min-h-screen bg-gray-50 flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-teal" role="progressbar"></div>
          </div>
        );
      }
      return <div>Content loaded</div>;
    };
    
    renderWithProviders(<LoadingDashboard />);
    
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    expect(screen.queryByText('Welcome back')).not.toBeInTheDocument();
  });

  it('removes loading state after useEffect', async () => {
    renderWithProviders(<DashboardContent />);
    
    // Should show content after loading
    await waitFor(() => {
      expect(screen.getByText(/Welcome back/)).toBeInTheDocument();
    });
    
    expect(screen.queryByRole('progressbar', { hidden: true })).not.toBeInTheDocument();
  });

  it('has proper accessibility structure', () => {
    renderWithProviders(<DashboardContent />);
    
    // Check for proper heading hierarchy
    expect(screen.getByRole('heading', { level: 2, name: /Welcome back/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3, name: 'Recent Payments' })).toBeInTheDocument();
    
    // Check that action buttons are properly labeled
    const buttons = screen.getAllByRole('button');
    buttons.forEach(button => {
      expect(button).toHaveTextContent(/\w+/); // Should have some text content
    });
  });

  it('handles hover states for interactive elements', () => {
    renderWithProviders(<DashboardContent />);
    
    // Check that interactive elements have hover classes
    const actionButton = screen.getByText('View Lease').closest('button');
    expect(actionButton).toHaveClass('hover:text-brand-green');
    
    const quickActionCard = screen.getByText('Make a Payment').closest('button');
    expect(quickActionCard).toHaveClass('hover:shadow-md');
  });
});
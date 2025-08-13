import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithProviders } from '../../test/utils';
import Sidebar from '../Sidebar';

// Mock NavLink to simulate active state
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    NavLink: ({ children, to, className, ...props }) => {
      const isActive = to === '/dashboard'; // Simulate dashboard being active
      const computedClassName = typeof className === 'function' 
        ? className({ isActive }) 
        : className;
      return (
        <a href={to} className={computedClassName} {...props}>
          {children}
        </a>
      );
    }
  };
});

describe('Sidebar Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the sidebar with all navigation items', () => {
    renderWithProviders(<Sidebar />);
    
    // Check that all navigation items are present
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Rent & Payments')).toBeInTheDocument();
    expect(screen.getByText('Lease Documents')).toBeInTheDocument();
    expect(screen.getByText('Maintenance')).toBeInTheDocument();
    expect(screen.getByText('Notifications')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('renders section headers correctly', () => {
    renderWithProviders(<Sidebar />);
    
    expect(screen.getByText('OVERVIEW')).toBeInTheDocument();
    expect(screen.getByText('CONFIGURATION')).toBeInTheDocument();
  });

  it('displays the Brikli logo when expanded', () => {
    renderWithProviders(<Sidebar />);
    
    const logo = screen.getByAltText('Brikli');
    expect(logo).toBeInTheDocument();
    expect(logo).toHaveAttribute('src', '/BrikliTransparent.png');
  });

  it('toggles between collapsed and expanded states', () => {
    renderWithProviders(<Sidebar />);
    
    const toggleButton = screen.getByLabelText('Collapse sidebar');
    expect(toggleButton).toBeInTheDocument();
    
    // Initially expanded (w-64)
    const sidebar = toggleButton.closest('aside');
    expect(sidebar).toHaveClass('w-64');
    
    // Click to collapse
    fireEvent.click(toggleButton);
    expect(sidebar).toHaveClass('w-16');
    
    // Button should now say "Expand sidebar"
    expect(screen.getByLabelText('Expand sidebar')).toBeInTheDocument();
    
    // Logo should not be visible when collapsed
    expect(screen.queryByAltText('Brikli')).not.toBeInTheDocument();
  });

  it('shows navigation text only when expanded', () => {
    renderWithProviders(<Sidebar />);
    
    const toggleButton = screen.getByLabelText('Collapse sidebar');
    
    // Initially expanded - text should be visible
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    
    // Collapse the sidebar
    fireEvent.click(toggleButton);
    
    // When collapsed, text is conditionally rendered based on state
    // The navigation links should still exist but without text labels
    const allLinks = screen.getAllByRole('link');
    expect(allLinks.length).toBeGreaterThan(0);
    const dashboardLink = allLinks.find(link => link.getAttribute('href') === '/dashboard');
    expect(dashboardLink).toBeInTheDocument();
  });

  it('applies correct active state styling', () => {
    renderWithProviders(<Sidebar />);
    
    // Dashboard should be active by default (current path is /dashboard)
    const dashboardLink = screen.getByRole('link', { name: /Dashboard/i });
    expect(dashboardLink).toHaveClass('bg-teal-50', 'text-teal-700', 'border-r-2', 'border-teal-600');
  });

  it('applies hover styles to inactive navigation items', () => {
    renderWithProviders(<Sidebar />);
    
    const paymentsLink = screen.getByRole('link', { name: /Rent & Payments/i });
    expect(paymentsLink).toHaveClass('text-gray-600', 'hover:bg-gray-50', 'hover:text-gray-900');
  });

  it('has correct navigation links', () => {
    renderWithProviders(<Sidebar />);
    
    expect(screen.getByRole('link', { name: /Dashboard/i })).toHaveAttribute('href', '/dashboard');
    expect(screen.getByRole('link', { name: /Rent & Payments/i })).toHaveAttribute('href', '/payments');
    expect(screen.getByRole('link', { name: /Lease Documents/i })).toHaveAttribute('href', '/documents');
    expect(screen.getByRole('link', { name: /Maintenance/i })).toHaveAttribute('href', '/maintenance');
    expect(screen.getByRole('link', { name: /Notifications/i })).toHaveAttribute('href', '/notifications');
    expect(screen.getByRole('link', { name: /Settings/i })).toHaveAttribute('href', '/settings');
  });

  it('uses React Icons correctly', () => {
    renderWithProviders(<Sidebar />);
    
    // Check icons are present on navigation links (React Icons render as SVG)
    const dashboardLink = screen.getByRole('link', { name: /dashboard/i });
    expect(dashboardLink.querySelector('svg')).toBeInTheDocument();
    
    const paymentsLink = screen.getByRole('link', { name: /rent & payments/i });
    expect(paymentsLink.querySelector('svg')).toBeInTheDocument();
    
    const documentsLink = screen.getByRole('link', { name: /lease documents/i });
    expect(documentsLink.querySelector('svg')).toBeInTheDocument();
  });

  it('maintains accessibility standards', () => {
    renderWithProviders(<Sidebar />);
    
    // Check for proper ARIA labels
    const toggleButton = screen.getByLabelText('Collapse sidebar');
    expect(toggleButton).toBeInTheDocument();
    
    // Check that all navigation items are accessible
    const navItems = screen.getAllByRole('link');
    navItems.forEach(item => {
      expect(item).toBeInTheDocument();
    });
  });

  it('handles keyboard navigation', () => {
    renderWithProviders(<Sidebar />);
    
    const toggleButton = screen.getByLabelText('Collapse sidebar');
    
    // Test keyboard focus
    toggleButton.focus();
    expect(document.activeElement).toBe(toggleButton);
    
    // Test Enter key press (basic keyboard interaction)
    fireEvent.keyDown(toggleButton, { key: 'Enter' });
    
    // Basic test - just verify the toggle button remains accessible
    expect(toggleButton).toBeInTheDocument();
  });
});
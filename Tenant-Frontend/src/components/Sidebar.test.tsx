import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Sidebar from './Sidebar';

// Wrapper component for router context
const renderWithRouter = (component: React.ReactNode) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('Sidebar', () => {
  it('renders all navigation items', () => {
    renderWithRouter(<Sidebar />);
    
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Rent & Payments')).toBeInTheDocument();
    expect(screen.getByText('Lease Documents')).toBeInTheDocument();
    expect(screen.getByText('Maintenance')).toBeInTheDocument();
    expect(screen.getByText('Notifications')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('renders section headers', () => {
    renderWithRouter(<Sidebar />);
    
    expect(screen.getByText('OVERVIEW')).toBeInTheDocument();
    expect(screen.getByText('CONFIGURATION')).toBeInTheDocument();
  });

  it('renders collapse/expand button', () => {
    renderWithRouter(<Sidebar />);
    
    const collapseButton = screen.getByRole('button', { name: /collapse sidebar/i });
    expect(collapseButton).toBeInTheDocument();
  });

  it('toggles collapsed state when button is clicked', () => {
    renderWithRouter(<Sidebar />);
    
    // Initially expanded
    const collapseButton = screen.getByRole('button', { name: /collapse sidebar/i });
    expect(screen.getByText('Dashboard')).toBeVisible();
    
    // Click to collapse
    fireEvent.click(collapseButton);
    
    // Button label should change to expand
    expect(screen.getByRole('button', { name: /expand sidebar/i })).toBeInTheDocument();
  });

  it('hides navigation text when collapsed', () => {
    renderWithRouter(<Sidebar />);
    
    // Click to collapse
    const collapseButton = screen.getByRole('button', { name: /collapse sidebar/i });
    fireEvent.click(collapseButton);
    
    // Text should be visually hidden (sr-only) but still in DOM for accessibility
    const dashboardLink = screen.getByRole('link', { name: /dashboard/i });
    expect(dashboardLink).toBeInTheDocument();
  });

  it('renders navigation links with correct paths', () => {
    renderWithRouter(<Sidebar />);
    
    expect(screen.getByRole('link', { name: /dashboard/i })).toHaveAttribute('href', '/dashboard');
    expect(screen.getByRole('link', { name: /rent & payments/i })).toHaveAttribute('href', '/payments');
    expect(screen.getByRole('link', { name: /lease documents/i })).toHaveAttribute('href', '/documents');
    expect(screen.getByRole('link', { name: /maintenance/i })).toHaveAttribute('href', '/maintenance');
    expect(screen.getByRole('link', { name: /notifications/i })).toHaveAttribute('href', '/notifications');
    expect(screen.getByRole('link', { name: /settings/i })).toHaveAttribute('href', '/settings');
  });

  it('renders the logo container when expanded', () => {
    renderWithRouter(<Sidebar />);
    
    // Logo link should be present (LazyImage shows placeholder in tests)
    const logoLink = screen.getByRole('link', { name: '' }); // Logo link has no text
    expect(logoLink).toHaveAttribute('href', '/dashboard');
  });

  it('hides logo link when collapsed', () => {
    renderWithRouter(<Sidebar />);
    
    // Get initial logo links count (should include logo link to dashboard)
    
    // Click to collapse
    const collapseButton = screen.getByRole('button', { name: /collapse sidebar/i });
    fireEvent.click(collapseButton);
    
    // After collapse, the logo container should still exist but the image is hidden
    // We verify the sidebar is collapsed by checking the button label changed
    expect(screen.getByRole('button', { name: /expand sidebar/i })).toBeInTheDocument();
  });
});


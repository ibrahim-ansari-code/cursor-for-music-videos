import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import ProductionErrorBoundary from '../../src/components/ProductionErrorBoundary';

// Mock the error reporting utility
vi.mock('../../src/utils/error-reporting', () => ({
  reportFatalError: vi.fn(),
  reportError: vi.fn(),
}));

import { reportFatalError } from '../../src/utils/error-reporting';

// Mock component that throws an error
const ThrowError: React.FC<{ shouldThrow: boolean }> = ({ shouldThrow }) => {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>Test component</div>;
};

// Mock Sentry (for legacy test compatibility)

describe('ProductionErrorBoundary', () => {
  const originalConsoleError = console.error;
  const originalLocation = window.location;

  beforeEach(() => {
    // Suppress console.error for tests
    console.error = vi.fn();
    
    // Mock window.location.reload
    delete (window as any).location;
    (window as any).location = { ...originalLocation, reload: vi.fn() };
  });

  afterEach(() => {
    console.error = originalConsoleError;
    (window as any).location = originalLocation;
    vi.clearAllMocks();
    // Clear mocks for error reporting utility
    vi.mocked(reportFatalError).mockClear();
  });

  it('renders children when there is no error', () => {
    render(
      <ProductionErrorBoundary>
        <div>Test content</div>
      </ProductionErrorBoundary>
    );
    
    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('displays error UI when an error is thrown', () => {
    render(
      <ProductionErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ProductionErrorBoundary>
    );
    
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText(/We encountered an unexpected error/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Refresh Page/i })).toBeInTheDocument();
  });


  it('calls window.location.reload when refresh button is clicked', () => {
    render(
      <ProductionErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ProductionErrorBoundary>
    );
    
    const refreshButton = screen.getByRole('button', { name: /Refresh Page/i });
    fireEvent.click(refreshButton);
    
    expect(window.location.reload).toHaveBeenCalledTimes(1);
  });

  it('reports error to centralized error reporting utility', () => {
    render(
      <ProductionErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ProductionErrorBoundary>
    );
    
    expect(reportFatalError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        component: 'ProductionErrorBoundary',
        action: 'error_boundary_catch',
        tags: expect.objectContaining({
          level: 'root',
          critical: true,
        }),
        extra: expect.objectContaining({
          react: expect.objectContaining({
            componentStack: expect.any(String)
          }),
          application: expect.objectContaining({
            errorBoundaryLevel: 'root',
          })
        })
      })
    );
  });

  it('handles errors gracefully even when error reporting fails', () => {
    // Mock error reporting to throw an error
    vi.mocked(reportFatalError).mockImplementationOnce(() => {
      throw new Error('Error reporting failed');
    });
    
    expect(() => {
      render(
        <ProductionErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ProductionErrorBoundary>
      );
    }).not.toThrow();
    
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(reportFatalError).toHaveBeenCalledTimes(1);
    
    // Should fall back to console.error when error reporting fails
    expect(console.error).toHaveBeenCalledWith(
      'Error reporting failed in ProductionErrorBoundary:',
      expect.any(Error)
    );
    expect(console.error).toHaveBeenCalledWith(
      'Original error that could not be reported:',
      expect.any(Error)
    );
  });

  it('logs error to console in all environments', () => {
    render(
      <ProductionErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ProductionErrorBoundary>
    );
    
    expect(console.error).toHaveBeenCalledWith(
      'Production Error Boundary caught:',
      expect.any(Error),
      expect.any(Object)
    );
  });

  it('recovers when error is resolved', () => {
    const { rerender } = render(
      <ProductionErrorBoundary key="error">
        <ThrowError shouldThrow={true} />
      </ProductionErrorBoundary>
    );
    
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    
    // Rerender with new key to force ErrorBoundary reset
    rerender(
      <ProductionErrorBoundary key="recovered">
        <ThrowError shouldThrow={false} />
      </ProductionErrorBoundary>
    );
    
    expect(screen.getByText('Test component')).toBeInTheDocument();
  });
});
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import ProductionErrorBoundary from '../../src/components/ProductionErrorBoundary';

// Mock component that throws an error
const ThrowError: React.FC<{ shouldThrow: boolean }> = ({ shouldThrow }) => {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>No error</div>;
};

// Mock Sentry
const mockSentry = {
  captureException: vi.fn(),
};

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

  it('reports error to Sentry when available', () => {
    (window as any).Sentry = mockSentry;
    
    render(
      <ProductionErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ProductionErrorBoundary>
    );
    
    expect(mockSentry.captureException).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        contexts: expect.objectContaining({
          react: expect.objectContaining({
            componentStack: expect.any(String)
          })
        })
      })
    );
    
    delete (window as any).Sentry;
  });

  it('handles errors gracefully when Sentry is not available', () => {
    delete (window as any).Sentry;
    
    expect(() => {
      render(
        <ProductionErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ProductionErrorBoundary>
      );
    }).not.toThrow();
    
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
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
      <ProductionErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ProductionErrorBoundary>
    );
    
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    
    // Click refresh to reload
    fireEvent.click(screen.getByRole('button', { name: /Refresh Page/i }));
    expect(window.location.reload).toHaveBeenCalled();
  });
});
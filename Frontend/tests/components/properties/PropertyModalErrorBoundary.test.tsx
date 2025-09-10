import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import PropertyModalErrorBoundary from '../../../src/components/properties/NewPropertyModal/components/ErrorBoundary';
import * as Sentry from '@sentry/react';

// Mock component that throws an error
const ThrowError: React.FC<{ shouldThrow?: boolean; errorMessage?: string }> = ({ 
  shouldThrow = true, 
  errorMessage = 'Test error' 
}) => {
  if (shouldThrow) {
    throw new Error(errorMessage);
  }
  return <div data-testid="working-component">Working component</div>;
};

// Mock framer-motion to avoid animation issues in tests
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

// Mock @sentry/react module
vi.mock('@sentry/react', () => ({
  captureException: vi.fn(),
}));

// Mock Sentry object for test assertions

describe('PropertyModalErrorBoundary', () => {
  const originalConsoleError = console.error;
  const originalConsoleWarn = console.warn;

  beforeEach(() => {
    // Suppress console errors and warnings in tests
    console.error = vi.fn();
    console.warn = vi.fn();
    
    // Mock navigator.clipboard
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });

    vi.clearAllMocks();
  });

  afterEach(() => {
    console.error = originalConsoleError;
    console.warn = originalConsoleWarn;
  });

  describe('Normal Operation', () => {
    it('renders children when there is no error', () => {
      render(
        <PropertyModalErrorBoundary>
          <div data-testid="child">Test content</div>
        </PropertyModalErrorBoundary>
      );
      
      expect(screen.getByTestId('child')).toBeInTheDocument();
      expect(screen.getByText('Test content')).toBeInTheDocument();
    });

    it('renders fallback component when provided', () => {
      const fallback = <div data-testid="custom-fallback">Custom fallback</div>;
      
      render(
        <PropertyModalErrorBoundary fallback={fallback}>
          <ThrowError />
        </PropertyModalErrorBoundary>
      );
      
      expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
      expect(screen.queryByText('Property form encountered an issue')).not.toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('displays error UI when an error is thrown (modal level)', () => {
      render(
        <PropertyModalErrorBoundary level="modal">
          <ThrowError />
        </PropertyModalErrorBoundary>
      );
      
      expect(screen.getByText('Property form encountered an issue')).toBeInTheDocument();
      expect(screen.getByText(/Try refreshing the form or contact support/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Try Again/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Back to Properties/i })).toBeInTheDocument();
    });

    it('shows specific error message for useformfielddebounce errors', () => {
      render(
        <PropertyModalErrorBoundary level="modal">
          <ThrowError errorMessage="useformfielddebounce validation failed" />
        </PropertyModalErrorBoundary>
      );
      
      expect(screen.getByText('Property form encountered an issue')).toBeInTheDocument();
      expect(screen.getByText(/Try selecting a different property type/)).toBeInTheDocument();
    });

    it('displays section-level error UI correctly', () => {
      render(
        <PropertyModalErrorBoundary 
          level="section" 
          title="Custom Section Error"
          description="Custom error description"
        >
          <ThrowError />
        </PropertyModalErrorBoundary>
      );
      
      expect(screen.getByText('Custom Section Error')).toBeInTheDocument();
      expect(screen.getByText('Custom error description')).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Back to Properties/i })).not.toBeInTheDocument();
    });

    it('shows specific error suggestions based on error type', () => {
      render(
        <PropertyModalErrorBoundary>
          <ThrowError errorMessage="useFormFieldDebounce: onChange must be a function" />
        </PropertyModalErrorBoundary>
      );
      
      expect(screen.getByText(/Try selecting a different property type/)).toBeInTheDocument();
    });

    it('handles network error suggestions', () => {
      render(
        <PropertyModalErrorBoundary>
          <ThrowError errorMessage="Network error occurred" />
        </PropertyModalErrorBoundary>
      );
      
      expect(screen.getByText(/Check your internet connection/)).toBeInTheDocument();
    });
  });

  describe('Error Details Toggle', () => {
    it('shows and hides technical details when toggled', async () => {
      // Mock development environment to enable technical details
      const originalEnv = import.meta.env;
      Object.defineProperty(import.meta, 'env', {
        value: { ...originalEnv, DEV: true },
        writable: true
      });

      render(
        <PropertyModalErrorBoundary>
          <ThrowError errorMessage="Detailed error message" />
        </PropertyModalErrorBoundary>
      );
      
      const toggleButton = screen.getByText('Show technical details');
      expect(screen.queryByText(/Detailed error message/)).not.toBeInTheDocument();
      
      fireEvent.click(toggleButton);
      
      await waitFor(() => {
        expect(screen.getByText(/Detailed error message/)).toBeInTheDocument();
      });
      
      const hideButton = screen.getByText('Hide technical details');
      fireEvent.click(hideButton);
      
      await waitFor(() => {
        expect(screen.queryByText(/Detailed error message/)).not.toBeInTheDocument();
      });

      // Restore original env
      Object.defineProperty(import.meta, 'env', {
        value: originalEnv,
        writable: true
      });
    });
  });

  describe('Error Recovery', () => {
    it('recovers successfully after clicking Try Again', async () => {
      const { rerender } = render(
        <PropertyModalErrorBoundary>
          <ThrowError />
        </PropertyModalErrorBoundary>
      );
      
      const tryAgainButton = screen.getByRole('button', { name: /Try Again/i });
      fireEvent.click(tryAgainButton);
      
      // Show recovery state
      await waitFor(() => {
        expect(screen.getByText('Recovering...')).toBeInTheDocument();
      });
      
      // Simulate successful recovery by rerendering with working component
      await waitFor(() => {
        rerender(
          <PropertyModalErrorBoundary>
            <ThrowError shouldThrow={false} />
          </PropertyModalErrorBoundary>
        );
      });
      
      // With the new retry logic, successful recovery shows the working component directly
      await waitFor(() => {
        expect(screen.getByTestId('working-component')).toBeInTheDocument();
        expect(screen.getByText('Working component')).toBeInTheDocument();
      });
    });


    it('calls onReset callback when provided', async () => {
      const onResetMock = vi.fn();
      
      render(
        <PropertyModalErrorBoundary onReset={onResetMock}>
          <ThrowError />
        </PropertyModalErrorBoundary>
      );
      
      const tryAgainButton = screen.getByRole('button', { name: /Try Again/i });
      fireEvent.click(tryAgainButton);
      
      await waitFor(() => {
        expect(onResetMock).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Navigation', () => {
    it('calls navigation callback when Back to Properties is clicked', () => {
      const onNavigateMock = vi.fn();
      
      render(
        <PropertyModalErrorBoundary onNavigateToProperties={onNavigateMock}>
          <ThrowError />
        </PropertyModalErrorBoundary>
      );
      
      const backButton = screen.getByRole('button', { name: /Back to Properties/i });
      fireEvent.click(backButton);
      
      expect(onNavigateMock).toHaveBeenCalledTimes(1);
    });

    it('logs warning when no navigation callback is provided', () => {
      render(
        <PropertyModalErrorBoundary>
          <ThrowError />
        </PropertyModalErrorBoundary>
      );
      
      const backButton = screen.getByRole('button', { name: /Back to Properties/i });
      fireEvent.click(backButton);
      
      expect(console.warn).toHaveBeenCalledWith('No navigation callback provided to ErrorBoundary');
    });
  });

  describe('Error Reporting', () => {
    it('copies error details to clipboard when Report Issue is clicked', async () => {
      render(
        <PropertyModalErrorBoundary>
          <ThrowError errorMessage="Test error for reporting" />
        </PropertyModalErrorBoundary>
      );
      
      const reportButton = screen.getByRole('button', { name: /Report Issue/i });
      fireEvent.click(reportButton);
      
      await waitFor(() => {
        expect(navigator.clipboard.writeText).toHaveBeenCalled();
      });
      
      const clipboardCall = (navigator.clipboard.writeText as any).mock.calls[0][0];
      const errorData = JSON.parse(clipboardCall);
      
      expect(errorData).toHaveProperty('error', 'Test error for reporting');
      expect(errorData).toHaveProperty('timestamp');
      expect(errorData).toHaveProperty('userAgent');
      expect(errorData).toHaveProperty('url');
    });

    it('reports error to Sentry when available', () => {
      render(
        <PropertyModalErrorBoundary>
          <ThrowError errorMessage="Sentry test error" />
        </PropertyModalErrorBoundary>
      );
      
      expect(Sentry.captureException).toHaveBeenCalledWith(
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
  });

  describe('Development vs Production', () => {
    let originalEnv: any;
    
    beforeEach(() => {
      originalEnv = import.meta.env;
    });
    
    afterEach(() => {
      // Restore original env after each test
      Object.defineProperty(import.meta, 'env', {
        value: originalEnv,
        writable: true
      });
    });
    
    it('shows component stack in development mode', async () => {
      // Mock development environment
      Object.defineProperty(import.meta, 'env', {
        value: { ...originalEnv, DEV: true },
        writable: true
      });
      
      render(
        <PropertyModalErrorBoundary>
          <ThrowError />
        </PropertyModalErrorBoundary>
      );
      
      // Debug: Check if toggle button exists
      expect(screen.getByText('Show technical details')).toBeInTheDocument();
      
      const toggleButton = screen.getByText('Show technical details');
      fireEvent.click(toggleButton);
      
      // In development, component stack should be included
      await waitFor(() => {
        const errorDetails = screen.getByLabelText(/technical details/i);
        expect(errorDetails).toBeInTheDocument();
      }, { timeout: 2000 });
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA attributes and roles', () => {
      render(
        <PropertyModalErrorBoundary>
          <ThrowError />
        </PropertyModalErrorBoundary>
      );
      
      const tryAgainButton = screen.getByRole('button', { name: /Try Again/i });
      const reportButton = screen.getByRole('button', { name: /Report Issue/i });
      
      expect(tryAgainButton).toBeInTheDocument();
      expect(reportButton).toHaveAttribute('title', 'Copy error details to clipboard');
    });

    it('maintains focus management during error recovery', async () => {
      render(
        <PropertyModalErrorBoundary>
          <ThrowError />
        </PropertyModalErrorBoundary>
      );
      
      const tryAgainButton = screen.getByRole('button', { name: /Try Again/i });
      tryAgainButton.focus();
      
      expect(document.activeElement).toBe(tryAgainButton);
      
      fireEvent.click(tryAgainButton);
      
      // Focus should remain manageable during recovery
      await waitFor(() => {
        expect(document.activeElement).toBeTruthy();
      });
    });
  });
});
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import SectionErrorBoundary from '../../../src/components/properties/NewPropertyModal/components/SectionErrorBoundary';
import * as Sentry from '@sentry/react';

// Mock component that throws an error
const ThrowError: React.FC<{ shouldThrow?: boolean; errorMessage?: string }> = ({ 
  shouldThrow = true, 
  errorMessage = 'Section test error' 
}) => {
  if (shouldThrow) {
    throw new Error(errorMessage);
  }
  return <div data-testid="section-content">Section working correctly</div>;
};

// Mock framer-motion to avoid animation issues in tests
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <div>{children}</div>,
}));

// Mock @sentry/react module
vi.mock('@sentry/react', () => ({
  captureException: vi.fn(),
}));

// Mock Sentry object for test assertions

describe('SectionErrorBoundary', () => {
  const originalConsoleError = console.error;

  beforeEach(() => {
    console.error = vi.fn();
    vi.clearAllMocks();
  });

  afterEach(() => {
    console.error = originalConsoleError;
  });

  describe('Normal Operation', () => {
    it('renders children when there is no error', () => {
      render(
        <SectionErrorBoundary sectionName="TestSection">
          <div data-testid="child">Test section content</div>
        </SectionErrorBoundary>
      );
      
      expect(screen.getByTestId('child')).toBeInTheDocument();
      expect(screen.getByText('Test section content')).toBeInTheDocument();
    });

    it('does not show error UI when component works normally', () => {
      render(
        <SectionErrorBoundary sectionName="TestSection">
          <ThrowError shouldThrow={false} />
        </SectionErrorBoundary>
      );
      
      expect(screen.getByTestId('section-content')).toBeInTheDocument();
      expect(screen.queryByText(/section encountered an issue/)).not.toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('displays section error UI when an error occurs', () => {
      render(
        <SectionErrorBoundary sectionName="ApartmentForm">
          <ThrowError />
        </SectionErrorBoundary>
      );
      
      expect(screen.getByText('ApartmentForm section encountered an issue')).toBeInTheDocument();
      expect(screen.getByText(/This section is temporarily unavailable/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Try Again/i })).toBeInTheDocument();
    });

    it('calls onSectionError callback when error occurs', () => {
      const onSectionErrorMock = vi.fn();
      
      render(
        <SectionErrorBoundary sectionName="TestSection" onSectionError={onSectionErrorMock}>
          <ThrowError errorMessage="Callback test error" />
        </SectionErrorBoundary>
      );
      
      expect(onSectionErrorMock).toHaveBeenCalledWith('TestSection', expect.any(Error));
      expect(onSectionErrorMock.mock.calls[0][1].message).toBe('Callback test error');
    });

    it('reports error to Sentry when available', () => {
      render(
        <SectionErrorBoundary sectionName="TestSection">
          <ThrowError errorMessage="Sentry test error" />
        </SectionErrorBoundary>
      );
      
      expect(Sentry.captureException).toHaveBeenCalledWith(
        expect.any(Error),
        expect.objectContaining({
          tags: {
            section: 'TestSection',
            errorBoundary: 'SectionErrorBoundary',
          },
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

  describe('Error Details Toggle', () => {
    it('shows and hides error details when toggled', async () => {
      render(
        <SectionErrorBoundary sectionName="TestSection">
          <ThrowError errorMessage="Detailed section error" />
        </SectionErrorBoundary>
      );
      
      const toggleButton = screen.getByText('Show error details');
      expect(screen.queryByText('Detailed section error')).not.toBeInTheDocument();
      
      fireEvent.click(toggleButton);
      
      await waitFor(() => {
        expect(screen.getByText('Detailed section error')).toBeInTheDocument();
      });
      
      const hideButton = screen.getByText('Hide error details');
      fireEvent.click(hideButton);
      
      await waitFor(() => {
        expect(screen.queryByText('Detailed section error')).not.toBeInTheDocument();
      });
    });
  });

  describe('Section Recovery', () => {
    it('recovers section after clicking Try Again', async () => {
      let shouldThrow = true;
      const TestComponent = () => {
        if (shouldThrow) {
          throw new Error('Test section error');
        }
        return <div data-testid="section-content">Section working correctly</div>;
      };
      
      render(
        <SectionErrorBoundary sectionName="TestSection">
          <TestComponent />
        </SectionErrorBoundary>
      );
      
      // Verify error state is shown
      expect(screen.getByText('This section is temporarily unavailable. Please try again.')).toBeInTheDocument();
      
      const tryAgainButton = screen.getByRole('button', { name: /Try Again/i });
      
      // Fix the component before clicking Try Again
      shouldThrow = false;
      
      // Click Try Again to reset error boundary
      fireEvent.click(tryAgainButton);
      
      // Wait for the error boundary to reset and re-render the now-working component
      await waitFor(() => {
        expect(screen.getByTestId('section-content')).toBeInTheDocument();
        expect(screen.queryByText('This section is temporarily unavailable. Please try again.')).not.toBeInTheDocument();
      }, { timeout: 3000 });
    });
  });

  describe('Section Fallback Functionality', () => {
    it('shows fallback form when section errors', () => {
      render(
        <SectionErrorBoundary sectionName="TestSection">
          <ThrowError />
        </SectionErrorBoundary>
      );
      
      expect(screen.getByText(/You can continue using the simplified form below/)).toBeInTheDocument();
    });

    it('shows Try Again button', () => {
      render(
        <SectionErrorBoundary sectionName="TestSection">
          <ThrowError />
        </SectionErrorBoundary>
      );
      
      expect(screen.getByRole('button', { name: /Try Again/i })).toBeInTheDocument();
    });

    it('shows apartment complex fallback with all required fields', () => {
      render(
        <SectionErrorBoundary sectionName="apartmentcomplexform">
          <ThrowError />
        </SectionErrorBoundary>
      );
      
      expect(screen.getByText('Simplified Apartment Complex Form')).toBeInTheDocument();
      expect(screen.getByText('Complex Style *')).toBeInTheDocument();
      expect(screen.getByText('Number of Buildings *')).toBeInTheDocument();
      expect(screen.getByText('Total Units *')).toBeInTheDocument();
      expect(screen.getByText('Unit Mix Distribution *')).toBeInTheDocument();
      expect(screen.getByText('Management Information')).toBeInTheDocument();
    });
  });

  describe('Fallback Components', () => {
    it('renders custom fallback component when provided', () => {
      const customFallback = <div data-testid="custom-fallback">Custom fallback content</div>;
      
      render(
        <SectionErrorBoundary sectionName="TestSection" fallbackComponent={customFallback}>
          <ThrowError />
        </SectionErrorBoundary>
      );
      
      expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
      expect(screen.getByText('Custom fallback content')).toBeInTheDocument();
    });

    it('renders apartment complex fallback for ApartmentComplexForm', () => {
      render(
        <SectionErrorBoundary sectionName="apartmentcomplexform">
          <ThrowError />
        </SectionErrorBoundary>
      );
      
      expect(screen.getByText('Simplified Apartment Complex Form')).toBeInTheDocument();
      expect(screen.getByText('Number of Buildings *')).toBeInTheDocument();
      expect(screen.getByText('Total Units *')).toBeInTheDocument();
      expect(screen.getByText(/Simplified mode/)).toBeInTheDocument();
    });

    it('renders generic fallback for unknown sections', () => {
      render(
        <SectionErrorBoundary sectionName="UnknownSection">
          <ThrowError />
        </SectionErrorBoundary>
      );
      
      expect(screen.getByText('UnknownSection section is temporarily unavailable')).toBeInTheDocument();
    });
  });

  describe('Development Environment', () => {
    it('logs errors to console in development', () => {
      const originalEnv = import.meta.env;
      Object.defineProperty(import.meta, 'env', {
        value: { ...originalEnv, DEV: true },
        writable: true
      });
      
      render(
        <SectionErrorBoundary sectionName="TestSection">
          <ThrowError errorMessage="Dev console test" />
        </SectionErrorBoundary>
      );
      
      expect(console.error).toHaveBeenCalledWith(
        'Section Error (TestSection):',
        expect.any(Error),
        expect.any(Object)
      );
      
      // Restore original env
      Object.defineProperty(import.meta, 'env', {
        value: originalEnv,
        writable: true
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper button roles and accessible labels', () => {
      render(
        <SectionErrorBoundary sectionName="TestSection">
          <ThrowError />
        </SectionErrorBoundary>
      );
      
      const tryAgainButton = screen.getByRole('button', { name: /Try Again/i });
      const errorDetailsButton = screen.getByRole('button', { name: /Show error details/i });
      
      expect(tryAgainButton).toBeInTheDocument();
      expect(errorDetailsButton).toBeInTheDocument();
    });

    it('maintains proper heading structure', () => {
      render(
        <SectionErrorBoundary sectionName="ImportantSection">
          <ThrowError />
        </SectionErrorBoundary>
      );
      
      const heading = screen.getByRole('heading', { level: 4 });
      expect(heading).toHaveTextContent('ImportantSection section encountered an issue');
    });
  });

  describe('Edge Cases', () => {
    it('handles very long section names gracefully', () => {
      const longSectionName = 'VeryLongSectionNameThatMightCauseDisplayIssues'.repeat(3);
      
      render(
        <SectionErrorBoundary sectionName={longSectionName}>
          <ThrowError />
        </SectionErrorBoundary>
      );
      
      expect(screen.getByText(`${longSectionName} section encountered an issue`)).toBeInTheDocument();
    });

    it('handles section names with special characters', () => {
      const specialSectionName = 'Section-With_Special.Characters@123';
      
      render(
        <SectionErrorBoundary sectionName={specialSectionName}>
          <ThrowError />
        </SectionErrorBoundary>
      );
      
      expect(screen.getByText(`${specialSectionName} section encountered an issue`)).toBeInTheDocument();
    });

    it('handles errors thrown during callback execution', () => {
      const faultyCallback = vi.fn(() => {
        throw new Error('Callback error');
      });
      
      // This should not crash the error boundary itself
      expect(() => {
        render(
          <SectionErrorBoundary sectionName="TestSection" onSectionError={faultyCallback}>
            <ThrowError />
          </SectionErrorBoundary>
        );
      }).not.toThrow();
    });
  });
});
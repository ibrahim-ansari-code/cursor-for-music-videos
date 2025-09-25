import { Component, ErrorInfo, ReactNode } from 'react';
import { reportFatalError } from '../utils/error-reporting';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ProductionErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('Production Error Boundary caught:', error, errorInfo);
    
    // Report critical error with defensive handling - error boundary must never throw
    try {
      reportFatalError(error, {
        component: 'ProductionErrorBoundary',
        action: 'error_boundary_catch',
        tags: {
          level: 'root',
          critical: true,
        },
        extra: {
          react: {
            componentStack: errorInfo.componentStack,
          },
          application: {
            errorBoundaryLevel: 'root',
          }
        },
      });
    } catch (reportingError) {
      // If error reporting fails, log to console as absolute fallback
      console.error('Error reporting failed in ProductionErrorBoundary:', reportingError);
      console.error('Original error that could not be reported:', error);
    }
    
    this.setState({
      error,
      errorInfo
    });
  }

  handleReload = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900 transition-colors duration-300">
          <div className="max-w-md w-full bg-white dark:bg-gray-800 shadow-lg rounded-lg p-6 border border-gray-200 dark:border-gray-600 transition-colors duration-300">
            <div className="flex items-center justify-center w-12 h-12 mx-auto bg-red-100 dark:bg-red-900/30 rounded-full mb-4">
              <svg className="w-6 h-6 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h1 className="text-xl font-semibold text-center text-gray-900 dark:text-gray-100 mb-2 transition-colors duration-300">
              Something went wrong
            </h1>
            <p className="text-gray-600 dark:text-gray-400 text-center mb-6 transition-colors duration-300">
              We encountered an unexpected error. Please try refreshing the page.
            </p>
            <button
              onClick={this.handleReload}
              className="w-full bg-green-600 dark:bg-green-700 text-white py-2 px-4 rounded-md hover:bg-green-700 dark:hover:bg-green-600 transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
            >
              Refresh Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ProductionErrorBoundary;

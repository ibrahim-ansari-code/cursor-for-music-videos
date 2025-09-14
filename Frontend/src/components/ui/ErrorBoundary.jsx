import React from 'react';
import PropTypes from 'prop-types';
import { reportError } from '../../utils/error-reporting';

/**
 * Error Boundary component for graceful error handling
 * Follows React 16+ error boundary pattern
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null,
      errorInfo: null,
      errorCount: 0
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log error to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    // Update state with error details
    this.setState(prevState => ({
      error,
      errorInfo,
      errorCount: prevState.errorCount + 1
    }));

    // Report to centralized error tracking service
    try {
      reportError(error, {
        component: 'ErrorBoundary',
        action: 'error_boundary_catch',
        tags: {
          errorBoundaryType: 'legacy',
        },
        extra: {
          react: {
            componentStack: errorInfo.componentStack,
          },
          errorCount: this.state.errorCount + 1,
        },
      }, 'error');
    } catch (reportingError) {
      // Fallback to console if error reporting fails - error boundary must never throw
      console.error('Error reporting failed in ErrorBoundary:', reportingError);
      console.error('Original error that could not be reported:', error, errorInfo);
    }

    // Call optional error callback
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({ 
      hasError: false, 
      error: null,
      errorInfo: null,
      errorCount: 0  // Reset error count on manual reset
    });

    // Call optional reset callback
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      // Check if we should use custom fallback
      if (this.props.fallback) {
        return this.props.fallback(
          this.state.error,
          this.state.errorInfo,
          this.handleReset
        );
      }

      // Default fallback UI
      return (
        <div className="min-h-[200px] flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full">
            <div className="flex items-center mb-4">
              <div className="flex-shrink-0">
                <svg
                  className="h-6 w-6 text-red-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <h3 className="ml-3 text-lg font-medium text-gray-900">
                {this.props.title || 'Something went wrong'}
              </h3>
            </div>

            <div className="text-sm text-gray-500 mb-4">
              {this.props.message || 'An unexpected error occurred. The issue has been logged and we\'re working on it.'}
            </div>

            {/* Show error details in development */}
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mb-4">
                <summary className="text-sm text-gray-600 cursor-pointer hover:text-gray-800">
                  Error Details
                </summary>
                <pre className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-auto max-h-40">
                  {this.state.error.toString()}
                  {this.state.errorInfo && this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}

            <div className="flex space-x-3">
              <button
                onClick={this.handleReset}
                className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                {this.props.resetText || 'Try Again'}
              </button>
              
              {(this.props.showReload ?? true) && (
                <button
                  onClick={() => window.location.reload()}
                  className="flex-1 bg-gray-200 text-gray-800 px-4 py-2 rounded-md text-sm font-medium hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
                >
                  Reload Page
                </button>
              )}
            </div>

            {/* Show error count if multiple errors */}
            {this.state.errorCount > 1 && (
              <div className="mt-3 text-xs text-gray-500 text-center">
                This error has occurred {this.state.errorCount} times
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

ErrorBoundary.propTypes = {
  children: PropTypes.node.isRequired,
  fallback: PropTypes.func,
  onError: PropTypes.func,
  onReset: PropTypes.func,
  title: PropTypes.string,
  message: PropTypes.string,
  resetText: PropTypes.string,
  showReload: PropTypes.bool
};


export default ErrorBoundary;
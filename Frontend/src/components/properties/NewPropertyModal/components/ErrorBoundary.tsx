import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onReset?: () => void;
  onNavigateToProperties?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class PropertyModalErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Only log in development
    if (import.meta.env.DEV) {
      console.error('Property Modal Error:', error, errorInfo);
    }
    
    this.setState({
      error,
      errorInfo,
    });
    
    // Log to error reporting service (e.g., Sentry)
    if (typeof window !== 'undefined' && (window as any).Sentry) {
      (window as any).Sentry.captureException(error, {
        contexts: {
          react: {
            componentStack: errorInfo.componentStack,
          },
        },
      });
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
    
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return <>{this.props.fallback}</>;
      }

      return (
        <div className="min-h-[400px] flex items-center justify-center p-8">
          <div className="max-w-md w-full">
            <div className="bg-red-50 border border-red-200 rounded-xl p-6">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <AlertTriangle className="h-6 w-6 text-red-600" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-red-900 mb-2">
                    Property form encountered an error
                  </h3>
                  <p className="text-sm text-red-700 mb-4">
                    The property form couldn't load properly. Try reloading the page or going back to the properties list.
                    If this keeps happening, please contact support.
                  </p>
                  
                  {/* Only show error details in development */}
                  {import.meta.env.DEV && this.state.error && (
                    <details className="mb-4">
                      <summary className="text-sm text-red-600 cursor-pointer hover:underline">
                        Show technical details
                      </summary>
                      <pre className="mt-2 text-xs bg-red-100 p-3 rounded overflow-auto max-h-40">
                        {this.state.error.message || this.state.error.toString()}
                      </pre>
                    </details>
                  )}
                  
                  <div className="flex space-x-3">
                    <button
                      onClick={this.handleReset}
                      className="inline-flex items-center px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Try Again
                    </button>
                    
                    <button
                      onClick={() => {
                        if (this.props.onNavigateToProperties) {
                          this.props.onNavigateToProperties();
                        } else {
                          // Fallback: close the modal instead of navigation
                          // Parent should handle navigation with React Router
                          console.warn('No navigation callback provided to ErrorBoundary');
                        }
                      }}
                      className="inline-flex items-center px-4 py-2 bg-white text-red-600 text-sm font-medium rounded-lg border border-red-300 hover:bg-red-50 transition-colors"
                    >
                      <Home className="h-4 w-4 mr-2" />
                      Back to Properties
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default PropertyModalErrorBoundary;
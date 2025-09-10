import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home, CheckCircle, ChevronDown, ChevronRight, Bug, MessageCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import * as Sentry from '@sentry/react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onReset?: () => void;
  onNavigateToProperties?: () => void;
  level?: 'modal' | 'section';
  title?: string;
  description?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
  isRecovering: boolean;
  hasRecovered: boolean;
  reportedErrorId?: string;
}

class PropertyModalErrorBoundary extends Component<Props, State> {
  private retryCount = 0;
  private maxRetries = 3;
  private timeoutId: NodeJS.Timeout | null = null;
  private resetTimeoutId: NodeJS.Timeout | null = null;
  private _isMounted = true;

  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
      isRecovering: false,
      hasRecovered: false,
      reportedErrorId: undefined,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
      errorInfo: null,
      showDetails: false,
      isRecovering: false,
      hasRecovered: false,
      reportedErrorId: undefined,
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
    
    // Report to Sentry with property modal context
    Sentry.captureException(error, {
      tags: {
        errorBoundary: 'PropertyModalErrorBoundary',
        level: this.props.level || 'modal',
        retryCount: this.retryCount,
      },
      contexts: {
        react: {
          componentStack: errorInfo.componentStack,
        },
        property: {
          modalLevel: this.props.level || 'modal',
          retryAttempts: this.retryCount,
        }
      },
    });
  }

  componentDidUpdate(_prevProps: Props, prevState: State) {
    // Reset retry count after successful recovery
    if (prevState.hasError && !this.state.hasError && !this.state.isRecovering) {
      this.retryCount = 0;
    }
  }

  static getDerivedStateFromProps(nextProps: Props, prevState: State): Partial<State> | null {
    // Reset error state when children change (new form data, different step, etc.)
    // This ensures retry count doesn't persist across different error contexts
    if (prevState.hasError && nextProps.children !== undefined) {
      return null; // No state change - let existing error state persist for same context
    }
    return null;
  }

  componentWillUnmount() {
    this._isMounted = false;
    // Reset retry count on unmount to ensure clean state
    this.retryCount = 0;
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }
    if (this.resetTimeoutId) {
      clearTimeout(this.resetTimeoutId);
      this.resetTimeoutId = null;
    }
  }

  handleReset = async () => {
    if (this.retryCount >= this.maxRetries) {
      // Max retries reached, automatically report error and show fallback options
      this.reportError();
      return;
    }

    this.setState({ isRecovering: true });
    this.retryCount += 1;

    try {
      // Add a small delay for better UX with proper cleanup
      await new Promise((resolve) => {
        this.resetTimeoutId = setTimeout(() => {
          if (this._isMounted) {
            resolve(undefined);
          }
        }, 500);
      });

      if (!this._isMounted) return;

      // Immediately attempt to re-render children without success message
      // This ensures a real retry occurs rather than showing a placeholder
      this.setState({
        hasError: false,
        error: null,
        errorInfo: null,
        showDetails: false,
        isRecovering: false,
        hasRecovered: false, // Don't show success message, retry immediately
        reportedErrorId: undefined,
      });
      
      if (this.props.onReset) {
        this.props.onReset();
      }
    } catch (error) {
      if (this._isMounted) {
        this.setState({ isRecovering: false });
      }
    }
  };

  handleForceReset = () => {
    // Emergency escape hatch - resets everything including retry count
    this.retryCount = 0;
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
      isRecovering: false,
      hasRecovered: false,
      reportedErrorId: undefined,
    });
    
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  toggleDetails = () => {
    this.setState(prev => ({ showDetails: !prev.showDetails }));
  };

  getErrorSuggestion = (error: Error): string => {
    const message = error.message.toLowerCase();
    
    if (message.includes('useformfielddebounce')) {
      return 'Try selecting a different property type or refreshing the form.';
    }
    if (message.includes('network')) {
      return 'Check your internet connection and try again.';
    }
    if (message.includes('validation')) {
      return 'Please check your form inputs and try again.';
    }
    if (message.includes('timeout')) {
      return 'The request took too long. Please try again.';
    }
    
    return 'Try refreshing the form or contact support if the issue persists.';
  };

  private sanitizeStackTrace = (stack?: string | null): string => {
    if (!stack) return '';
    
    // Remove sensitive paths, tokens, and user data
    return stack
      .split('\n')
      .map(line => 
        line
          .replace(/\/Users\/[^\/]+/g, '/Users/[user]')
          .replace(/token=[^&\s]+/g, 'token=[REDACTED]')
          .replace(/key=[^&\s]+/g, 'key=[REDACTED]')
          .replace(/password=[^&\s]+/g, 'password=[REDACTED]')
          .replace(/email=[^&\s]+/g, 'email=[REDACTED]')
      )
      .slice(0, 10) // Limit stack trace length
      .join('\n');
  };

  private sanitizeUrl = (url: string): string => {
    try {
      const urlObj = new URL(url);
      // Remove sensitive query parameters
      urlObj.searchParams.delete('token');
      urlObj.searchParams.delete('key');
      urlObj.searchParams.delete('password');
      urlObj.searchParams.delete('email');
      return urlObj.toString();
    } catch {
      return '[INVALID_URL]';
    }
  };

  reportError = () => {
    const errorId = Math.random().toString(36).substring(7).toUpperCase();
    
    const errorData = {
      id: errorId,
      error: this.state.error?.message?.substring(0, 500) || 'Unknown error', // Limit message length
      stack: this.sanitizeStackTrace(this.state.error?.stack),
      componentStack: this.sanitizeStackTrace(this.state.errorInfo?.componentStack),
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent?.substring(0, 200) || 'Unknown', // Limit UA length
      url: this.sanitizeUrl(window.location.href),
      retryCount: this.retryCount,
      level: this.props.level || 'modal',
    };

    // Production-safe error reporting with enhanced clipboard handling
    if (import.meta.env.PROD) {
      // In production, just log a sanitized error ID for support
      console.error(`Error ID: ${errorId} - Please provide this ID to support`);
      
      // Store for user to copy if needed
      this.setState({ reportedErrorId: errorId });
      
      // Send to Sentry with detailed error context
      Sentry.captureException(this.state.error, {
        tags: { 
          errorId,
          errorBoundary: 'PropertyModalErrorBoundary',
          level: this.props.level || 'modal',
          userReported: true,
        },
        extra: errorData,
      });
    } else {
      // Development: Full error details
      console.error('Error details:', errorData);
      
      // Enhanced clipboard functionality with multiple fallbacks
      const copyToClipboard = async (text: string) => {
        // Method 1: Modern Clipboard API (requires HTTPS)
        if (navigator.clipboard && navigator.clipboard.writeText) {
          try {
            await navigator.clipboard.writeText(text);
            console.log('Error details copied to clipboard via Clipboard API');
            return true;
          } catch (error) {
            console.warn('Clipboard API failed:', error);
          }
        }
        
        // Method 2: Legacy execCommand (deprecated but widely supported)
        if (document.execCommand) {
          try {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-9999px';
            textArea.style.top = '-9999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            
            const success = document.execCommand('copy');
            document.body.removeChild(textArea);
            
            if (success) {
              console.log('Error details copied to clipboard via execCommand');
              return true;
            }
          } catch (error) {
            console.warn('execCommand failed:', error);
          }
        }
        
        // Method 3: Fallback - just log to console with clear instructions
        console.log('=== COPY ERROR DETAILS MANUALLY ===');
        console.log(text);
        console.log('=====================================');
        return false;
      };
      
      copyToClipboard(JSON.stringify(errorData, null, 2));
    }
    
    return errorId;
  };

  render() {
    const { level = 'modal', title, description } = this.props;
    const isModal = level === 'modal';

    if (this.state.hasRecovered) {
      return (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0 }}
          className="flex items-center justify-center p-4"
        >
          <div className="bg-white border border-gray-200 rounded-xl p-4 flex items-center space-x-3 shadow-sm">
            <CheckCircle className="h-5 w-5 text-blue-600" />
            <span className="text-sm font-medium text-gray-800">Form recovered successfully!</span>
          </div>
        </motion.div>
      );
    }

    if (this.state.hasError) {
      if (this.props.fallback) {
        return <>{this.props.fallback}</>;
      }

      const containerClass = isModal 
        ? "min-h-[400px] flex items-center justify-center p-8"
        : "p-4 my-2";

      const cardClass = isModal
        ? "max-w-md w-full"
        : "w-full";

      return (
        <motion.div 
          className={containerClass}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <div className={cardClass}>
            <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0">
                  <div className="p-2 bg-amber-50 rounded-full border border-amber-100">
                    <AlertTriangle className="h-5 w-5 text-amber-600" />
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-800 mb-2">
                    {title || (isModal ? 'Property form encountered an issue' : 'Section temporarily unavailable')}
                  </h3>
                  <p className="text-sm text-gray-600 mb-3">
                    {description || (this.state.error ? this.getErrorSuggestion(this.state.error) : 'An unexpected error occurred.')}
                  </p>

                  {this.state.error && import.meta.env.DEV && (
                    <div className="mb-4">
                      <button
                        onClick={this.toggleDetails}
                        className="flex items-center text-xs text-gray-600 hover:text-gray-800 font-medium transition-colors"
                      >
                        {this.state.showDetails ? (
                          <ChevronDown className="h-3 w-3 mr-1" />
                        ) : (
                          <ChevronRight className="h-3 w-3 mr-1" />
                        )}
                        {this.state.showDetails ? 'Hide' : 'Show'} technical details
                      </button>
                      
                      <AnimatePresence>
                        {this.state.showDetails && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="mt-2 overflow-hidden"
                          >
                            <pre 
                              className="text-xs bg-gray-100 p-3 rounded-lg overflow-auto max-h-32 text-gray-700"
                              role="generic"
                              aria-label="technical details"
                            >
                              {this.state.error.message || this.state.error.toString()}
                              {this.state.errorInfo?.componentStack && (
                                '\n\nComponent Stack:' + this.state.errorInfo.componentStack.slice(0, 500)
                              )}
                            </pre>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  )}
                  
                  <div className="flex flex-wrap gap-2">
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={this.handleReset}
                      disabled={this.state.isRecovering || this.retryCount >= this.maxRetries}
                      className={`inline-flex items-center px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                        this.state.isRecovering 
                          ? 'bg-blue-400 text-white cursor-not-allowed'
                          : this.retryCount >= this.maxRetries
                          ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                          : 'bg-blue-600 text-white hover:bg-blue-700'
                      }`}
                    >
                      <RefreshCw className={`h-4 w-4 mr-2 ${this.state.isRecovering ? 'animate-spin' : ''}`} />
                      {this.state.isRecovering 
                        ? 'Recovering...' 
                        : this.retryCount >= this.maxRetries 
                        ? 'Max retries reached' 
                        : `Try Again${this.retryCount > 0 ? ` (${this.retryCount}/${this.maxRetries})` : ''}`}
                    </motion.button>
                    
                    {isModal && (
                      <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => {
                          if (this.props.onNavigateToProperties) {
                            this.props.onNavigateToProperties();
                          } else {
                            console.warn('No navigation callback provided to ErrorBoundary');
                          }
                        }}
                        className="inline-flex items-center px-4 py-2 bg-white text-gray-600 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
                      >
                        <Home className="h-4 w-4 mr-2" />
                        Back to Properties
                      </motion.button>
                    )}

                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={this.reportError}
                      className="inline-flex items-center px-3 py-2 bg-white text-gray-600 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
                      title={import.meta.env.DEV ? "Copy error details to clipboard" : "Generate error ID for support"}
                    >
                      <MessageCircle className="h-4 w-4 mr-1" />
                      Report Issue
                    </motion.button>

                    {this.retryCount >= this.maxRetries && (
                      <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={this.handleForceReset}
                        className="inline-flex items-center px-4 py-2 bg-orange-600 text-white text-sm font-medium rounded-lg hover:bg-orange-700 transition-colors"
                        title="Force reset - clears all error state"
                      >
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Force Reset
                      </motion.button>
                    )}
                  </div>

                  {this.retryCount >= this.maxRetries && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg"
                    >
                      <div className="flex items-start space-x-2">
                        <Bug className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                        <div className="text-sm text-amber-700">
                          <p className="font-medium">Need additional help?</p>
                          <p className="mt-1">
                            {import.meta.env.DEV 
                              ? 'Error details are available via the "Report Issue" button. You can continue using other parts of the form or try a "Force Reset".'
                              : 'Use the "Report Issue" button to get an error ID, then try "Force Reset" or contact support.'
                            }
                          </p>
                          {this.state.reportedErrorId && (
                            <p className="mt-2 p-2 bg-amber-100 border border-amber-300 rounded font-mono text-xs">
                              Error ID: <span className="font-bold">{this.state.reportedErrorId}</span>
                            </p>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      );
    }

    return this.props.children;
  }
}

export default PropertyModalErrorBoundary;
import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { ComplexStyle } from '@/types/apartmentComplex';

interface Props {
  children: ReactNode;
  sectionName: string;
  fallbackComponent?: ReactNode;
  onSectionError?: (sectionName: string, error: Error) => void;
  fallbackFormData?: Record<string, any>;
  onFallbackDataChange?: (key: string, value: any) => void;
  onValidationChange?: (sectionName: string, isValid: boolean, errors: Record<string, string>) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  showDetails: boolean;
  validationErrors: Record<string, string>;
}

/**
 * Section-level error boundary that isolates errors to specific form sections
 * instead of crashing the entire modal. Provides graceful fallbacks and skip options.
 */
class SectionErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      showDetails: false,
      validationErrors: {},
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
      showDetails: false,
      validationErrors: {},
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error details for debugging
    if (import.meta.env.DEV) {
      console.error(`Section Error (${this.props.sectionName}):`, error, errorInfo);
    }

    // Report error to Sentry if available
    if (typeof window !== 'undefined' && (window as any).Sentry) {
      (window as any).Sentry.captureException(error, {
        tags: {
          section: this.props.sectionName,
          errorBoundary: 'SectionErrorBoundary',
        },
        contexts: {
          react: {
            componentStack: errorInfo.componentStack,
          },
        },
      });
    }

    // Notify parent about section error
    if (this.props.onSectionError) {
      try {
        this.props.onSectionError(this.props.sectionName, error);
      } catch (callbackError) {
        // Don't let callback errors crash the error boundary itself
        if (import.meta.env.DEV) {
          console.warn('Error in onSectionError callback:', callbackError);
        }
      }
    }
  }

  toggleDetails = () => {
    this.setState(prev => ({ showDetails: !prev.showDetails }));
  };

  handleReset = () => {
    // Reset the error boundary state to try rendering children again
    this.setState({
      hasError: false,
      error: null,
      showDetails: false,
      validationErrors: {},
    });
  };

  // Basic validation for fallback form
  validateField = (key: string, value: any): string | null => {
    switch (key) {
      case 'complexStyle':
        return !value ? 'Complex style is required' : null;
      case 'numberOfBuildings':
        if (!value || value < 1) return 'Number of buildings must be at least 1';
        if (value > 100) return 'Number of buildings cannot exceed 100';
        return null;
      case 'totalUnits':
        if (!value || value < 1) return 'Total units must be at least 1';
        if (value > 10000) return 'Total units cannot exceed 10,000';
        return null;
      case 'parkingSpaces':
        if (value < 0) return 'Parking spaces cannot be negative';
        return null;
      default:
        return null;
    }
  };

  handleValidatedChange = (key: string, value: any) => {
    const { onFallbackDataChange, onValidationChange, sectionName } = this.props;
    
    // Validate the field
    const error = this.validateField(key, value);
    const newErrors = { ...this.state.validationErrors };
    
    if (error) {
      newErrors[key] = error;
    } else {
      delete newErrors[key];
    }
    
    this.setState({ validationErrors: newErrors });
    
    // Notify parent of validation state
    const isValid = Object.keys(newErrors).length === 0;
    onValidationChange?.(sectionName, isValid, newErrors);
    
    // Update form data
    onFallbackDataChange?.(key, value);
  };

  getSectionFallback = (): ReactNode => {
    const { sectionName, fallbackFormData = {}, onFallbackDataChange } = this.props;
    const { validationErrors } = this.state;
    
    // Provide basic fallbacks for known sections
    switch (sectionName.toLowerCase()) {
      case 'apartmentcomplexform':
        return (
          <div className="space-y-5 p-4 bg-gray-50 border border-gray-200 rounded-lg">
            <div className="flex items-center space-x-2 mb-4">
              <div className="h-2 w-2 bg-amber-500 rounded-full"></div>
              <h4 className="font-medium text-gray-700">Simplified Apartment Complex Form</h4>
            </div>
            
            {/* Complex Style */}
            <div>
              <label className="text-xs font-medium text-gray-600 mb-2 block">
                Complex Style *
              </label>
              <select 
                className={`w-full px-3 py-2 text-sm border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                  validationErrors.complexStyle ? 'border-red-300 bg-red-50' : 'border-gray-300'
                }`}
                value={fallbackFormData.complexStyle || ''}
                onChange={(e) => this.handleValidatedChange('complexStyle', e.target.value)}
              >
                <option value="">Select style...</option>
                {(['garden', 'highrise', 'midrise', 'townhome', 'luxury', 'student'] as ComplexStyle[]).map(style => (
                  <option key={style} value={style}>
                    {style === 'garden' && 'Garden Style'}
                    {style === 'highrise' && 'High-Rise'}
                    {style === 'midrise' && 'Mid-Rise'}
                    {style === 'townhome' && 'Townhome'}
                    {style === 'luxury' && 'Luxury'}
                    {style === 'student' && 'Student Housing'}
                  </option>
                ))}
              </select>
              {validationErrors.complexStyle && (
                <p className="text-xs text-red-600 mt-1">{validationErrors.complexStyle}</p>
              )}
            </div>

            {/* Essential Details */}
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">
                  Number of Buildings *
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  className={`w-full px-3 py-2 text-sm border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    validationErrors.numberOfBuildings ? 'border-red-300 bg-red-50' : 'border-gray-300'
                  }`}
                  placeholder="3"
                  value={fallbackFormData.numberOfBuildings || ''}
                  onChange={(e) => this.handleValidatedChange('numberOfBuildings', parseInt(e.target.value) || 0)}
                />
                {validationErrors.numberOfBuildings && (
                  <p className="text-xs text-red-600 mt-1">{validationErrors.numberOfBuildings}</p>
                )}
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">
                  Total Units *
                </label>
                <input
                  type="number"
                  min="1"
                  max="10000"
                  className={`w-full px-3 py-2 text-sm border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    validationErrors.totalUnits ? 'border-red-300 bg-red-50' : 'border-gray-300'
                  }`}
                  placeholder="120"
                  value={fallbackFormData.totalUnits || ''}
                  onChange={(e) => this.handleValidatedChange('totalUnits', parseInt(e.target.value) || 0)}
                />
                {validationErrors.totalUnits && (
                  <p className="text-xs text-red-600 mt-1">{validationErrors.totalUnits}</p>
                )}
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">
                  Parking Spaces
                </label>
                <input
                  type="number"
                  min="0"
                  className={`w-full px-3 py-2 text-sm border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    validationErrors.parkingSpaces ? 'border-red-300 bg-red-50' : 'border-gray-300'
                  }`}
                  placeholder="180"
                  value={fallbackFormData.parkingSpaces || ''}
                  onChange={(e) => this.handleValidatedChange('parkingSpaces', parseInt(e.target.value) || 0)}
                />
                {validationErrors.parkingSpaces && (
                  <p className="text-xs text-red-600 mt-1">{validationErrors.parkingSpaces}</p>
                )}
              </div>
            </div>

            {/* Unit Mix */}
            <div>
              <label className="text-xs font-medium text-gray-600 mb-2 block">
                Unit Mix Distribution *
              </label>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Studio</label>
                  <input 
                    type="number" 
                    min="0" 
                    className="w-full px-2 py-1.5 text-xs border border-gray-300 rounded focus:ring-2 focus:ring-blue-500" 
                    placeholder="0" 
                    value={fallbackFormData.unitMix?.studio || ''}
                    onChange={(e) => onFallbackDataChange?.('unitMix.studio', parseInt(e.target.value) || 0)}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">1 BR</label>
                  <input 
                    type="number" 
                    min="0" 
                    className="w-full px-2 py-1.5 text-xs border border-gray-300 rounded focus:ring-2 focus:ring-blue-500" 
                    placeholder="0" 
                    value={fallbackFormData.unitMix?.oneBed || ''}
                    onChange={(e) => onFallbackDataChange?.('unitMix.oneBed', parseInt(e.target.value) || 0)}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">2 BR</label>
                  <input 
                    type="number" 
                    min="0" 
                    className="w-full px-2 py-1.5 text-xs border border-gray-300 rounded focus:ring-2 focus:ring-blue-500" 
                    placeholder="0" 
                    value={fallbackFormData.unitMix?.twoBed || ''}
                    onChange={(e) => onFallbackDataChange?.('unitMix.twoBed', parseInt(e.target.value) || 0)}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">3 BR</label>
                  <input 
                    type="number" 
                    min="0" 
                    className="w-full px-2 py-1.5 text-xs border border-gray-300 rounded focus:ring-2 focus:ring-blue-500" 
                    placeholder="0" 
                    value={fallbackFormData.unitMix?.threeBed || ''}
                    onChange={(e) => onFallbackDataChange?.('unitMix.threeBed', parseInt(e.target.value) || 0)}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">4+ BR</label>
                  <input 
                    type="number" 
                    min="0" 
                    className="w-full px-2 py-1.5 text-xs border border-gray-300 rounded focus:ring-2 focus:ring-blue-500" 
                    placeholder="0" 
                    value={fallbackFormData.unitMix?.fourPlusBed || ''}
                    onChange={(e) => onFallbackDataChange?.('unitMix.fourPlusBed', parseInt(e.target.value) || 0)}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Penthouse</label>
                  <input 
                    type="number" 
                    min="0" 
                    className="w-full px-2 py-1.5 text-xs border border-gray-300 rounded focus:ring-2 focus:ring-blue-500" 
                    placeholder="0" 
                    value={fallbackFormData.unitMix?.penthouse || ''}
                    onChange={(e) => onFallbackDataChange?.('unitMix.penthouse', parseInt(e.target.value) || 0)}
                  />
                </div>
              </div>
            </div>

            {/* Floor & Elevator Count */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-gray-600 mb-2 block">
                  Floor Count
                </label>
                <div className="flex gap-1">
                  <button 
                    type="button" 
                    className={`flex-1 py-1.5 px-2 text-xs border border-gray-300 rounded hover:bg-gray-100 ${fallbackFormData.floorCount === 1 ? 'bg-blue-100 border-blue-300' : ''}`}
                    onClick={() => onFallbackDataChange?.('floorCount', 1)}
                  >
                    1
                  </button>
                  <button 
                    type="button" 
                    className={`flex-1 py-1.5 px-2 text-xs border border-gray-300 rounded hover:bg-gray-100 ${fallbackFormData.floorCount === 2 ? 'bg-blue-100 border-blue-300' : ''}`}
                    onClick={() => onFallbackDataChange?.('floorCount', 2)}
                  >
                    2
                  </button>
                  <button 
                    type="button" 
                    className={`flex-1 py-1.5 px-2 text-xs border border-gray-300 rounded hover:bg-gray-100 ${fallbackFormData.floorCount === 3 ? 'bg-blue-100 border-blue-300' : ''}`}
                    onClick={() => onFallbackDataChange?.('floorCount', 3)}
                  >
                    3
                  </button>
                  <input 
                    type="number" 
                    min="4" 
                    max="100" 
                    placeholder="4+" 
                    className="w-12 px-1 py-1.5 text-xs border border-gray-300 rounded text-center" 
                    value={fallbackFormData.floorCount && fallbackFormData.floorCount > 3 ? fallbackFormData.floorCount : ''}
                    onChange={(e) => onFallbackDataChange?.('floorCount', parseInt(e.target.value) || 4)}
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 mb-2 block">
                  Elevator Count
                </label>
                <div className="flex gap-1">
                  <button 
                    type="button" 
                    className={`flex-1 py-1.5 px-2 text-xs border border-gray-300 rounded hover:bg-gray-100 ${fallbackFormData.elevatorCount === 0 ? 'bg-blue-100 border-blue-300' : ''}`}
                    onClick={() => onFallbackDataChange?.('elevatorCount', 0)}
                  >
                    0
                  </button>
                  <button 
                    type="button" 
                    className={`flex-1 py-1.5 px-2 text-xs border border-gray-300 rounded hover:bg-gray-100 ${fallbackFormData.elevatorCount === 1 ? 'bg-blue-100 border-blue-300' : ''}`}
                    onClick={() => onFallbackDataChange?.('elevatorCount', 1)}
                  >
                    1
                  </button>
                  <button 
                    type="button" 
                    className={`flex-1 py-1.5 px-2 text-xs border border-gray-300 rounded hover:bg-gray-100 ${fallbackFormData.elevatorCount === 2 ? 'bg-blue-100 border-blue-300' : ''}`}
                    onClick={() => onFallbackDataChange?.('elevatorCount', 2)}
                  >
                    2
                  </button>
                  <input 
                    type="number" 
                    min="3" 
                    max="20" 
                    placeholder="3+" 
                    className="w-12 px-1 py-1.5 text-xs border border-gray-300 rounded text-center" 
                    value={fallbackFormData.elevatorCount && fallbackFormData.elevatorCount > 2 ? fallbackFormData.elevatorCount : ''}
                    onChange={(e) => onFallbackDataChange?.('elevatorCount', parseInt(e.target.value) || 3)}
                  />
                </div>
              </div>
            </div>

            {/* Management */}
            <div>
              <label className="text-xs font-medium text-gray-600 mb-2 block">
                Management Information
              </label>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <input
                    type="text"
                    className="w-full px-3 py-2 text-xs border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Property Manager Name"
                    value={fallbackFormData.propertyManager || ''}
                    onChange={(e) => onFallbackDataChange?.('propertyManager', e.target.value)}
                  />
                </div>
                <div>
                  <input
                    type="text"
                    className="w-full px-3 py-2 text-xs border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Management Company"
                    value={fallbackFormData.managementCompany || ''}
                    onChange={(e) => onFallbackDataChange?.('managementCompany', e.target.value)}
                  />
                </div>
              </div>
            </div>

            <div className="text-xs text-amber-600 bg-amber-50 p-2 rounded border border-amber-200">
              ⚠️ Simplified mode: Advanced features are unavailable. Basic validation is enabled for critical fields.
            </div>
          </div>
        );
      
      default:
        return (
          <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg text-center">
            <p className="text-sm text-gray-600">
              {sectionName} section is temporarily unavailable
            </p>
          </div>
        );
    }
  };

  render() {
    const { children, sectionName, fallbackComponent } = this.props;

    if (this.state.hasError) {
      return (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="my-4"
        >
          <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0">
                <div className="p-1.5 bg-amber-50 rounded-full border border-amber-100">
                  <AlertTriangle className="h-4 w-4 text-amber-600" />
                </div>
              </div>
              <div className="flex-1">
                <h4 className="text-sm font-semibold text-gray-800 mb-1">
                  {sectionName} section encountered an issue
                </h4>
                <p className="text-xs text-gray-600 mb-3">
                  This section is temporarily unavailable. Please try again.
                </p>

                {this.state.error && import.meta.env.DEV && (
                  <div className="mb-3">
                    <button
                      onClick={this.toggleDetails}
                      className="flex items-center text-xs text-gray-600 hover:text-gray-800 font-medium transition-colors"
                    >
                      {this.state.showDetails ? (
                        <ChevronDown className="h-3 w-3 mr-1" />
                      ) : (
                        <ChevronRight className="h-3 w-3 mr-1" />
                      )}
                      {this.state.showDetails ? 'Hide' : 'Show'} error details
                    </button>
                    
                    <AnimatePresence>
                      {this.state.showDetails && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="mt-2 overflow-hidden"
                        >
                          <pre className="text-xs bg-gray-100 p-2 rounded overflow-auto max-h-24 text-gray-700">
                            {this.state.error.message || this.state.error.toString()}
                          </pre>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}

                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={this.handleReset}
                    className="inline-flex items-center px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded hover:bg-blue-700 transition-colors"
                  >
                    <RefreshCw className="h-3 w-3 mr-1" />
                    Try Again
                  </button>
                </div>
              </div>
            </div>

            {/* Always show fallback component */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4"
            >
              <div className="border-t border-gray-200 pt-3">
                <p className="text-xs font-medium text-gray-600 mb-2">
                  You can continue using the simplified form below:
                </p>
                {fallbackComponent || this.getSectionFallback()}
              </div>
            </motion.div>
          </div>
        </motion.div>
      );
    }

    return children;
  }
}

export default SectionErrorBoundary;
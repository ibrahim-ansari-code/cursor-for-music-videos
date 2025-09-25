import React, { useState, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { toast } from 'react-toastify';
import { fetchProperties } from '../../../utils/api/properties';
import { fetchTenants } from '../../../utils/api/tenants';
import { useInvoiceForm } from '../../../hooks/accounting/useInvoiceForm';
import { useTaxRecommendations } from '../../../hooks/accounting/useTaxRecommendations';
import TaxRecommendationBanner from '../shared/TaxRecommendationBanner';
import InvoiceFormFields from '../shared/InvoiceFormFields';
import FinancialErrorBoundary from '../shared/FinancialErrorBoundary';
import type { TaxDetail } from '../../../types/accounting';

interface Property {
  id: number;
  name: string;
  address?: string;
}

interface Tenant {
  id: number;
  full_name: string;
  email?: string;
  property_units?: Array<{
    property_id: number;
  }>;
}

interface NewInvoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

/**
 * Refactored NewInvoiceModal with extracted business logic and modular components
 * - Business logic moved to useInvoiceForm and useTaxRecommendations hooks
 * - UI components are reusable and focused on presentation
 * - Error boundaries protect financial calculations
 * - Security utilities ensure data safety
 */
const NewInvoiceModal: React.FC<NewInvoiceModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  // Data state
  const [properties, setProperties] = useState<Property[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [isLoadingData, setIsLoadingData] = useState(false);
  
  // Track recently set tax defaults for immediate visual feedback
  const [recentlySetDefaults, setRecentlySetDefaults] = useState<Array<{
    tax_name: string;
    tax_rate: string;
    type: 'user' | 'property';
  }>>([]);

  // Form management hook - handles all form state, validation, and submission
  const {
    formData,
    errors,
    isSubmitting,
    calculatedTotals,
    isUserDefaultTax,
    updateField,
    updateTaxes,
    addTaxLine,
    removeTaxLine,
    updateTaxLine,
    submitForm,
    resetForm,
    clearUserTaxDefaultFromForm,
    setIsUserDefaultTax,
  } = useInvoiceForm({
    mode: 'create',
    onSuccess: () => {
      onSuccess?.();
      onClose();
      resetForm();
    },
  });

  // Tax recommendations hook - handles smart tax logic and defaults
  const {
    smartTaxRecommendation,
    isLoadingSmartTax,
    setUserDefault,
    setPropertyDefault,
    clearRecommendations,
  } = useTaxRecommendations({
    propertyId: formData.property_id,
    category: 'rental', // Could be dynamic based on invoice type
  });

  // Load initial data when modal opens
  useEffect(() => {
    if (isOpen) {
      loadInitialData();
    } else {
      // Cleanup when modal closes
      resetForm();
      clearRecommendations();
    }
  }, [isOpen, resetForm, clearRecommendations]);

  const loadInitialData = async () => {
    setIsLoadingData(true);
    try {
      const [propertiesResponse, tenantsResponse] = await Promise.all([
        fetchProperties(),
        fetchTenants({ limit: 1000 }), // Adjust as needed
      ]);

      setProperties(propertiesResponse || []);
      setTenants(tenantsResponse || []);
    } catch (error) {
      console.error('Error loading initial data:', error);
      toast.error('Failed to load properties and tenants');
    } finally {
      setIsLoadingData(false);
    }
  };

  // Handle tax recommendation application
  const handleApplyTaxRecommendation = (tax: TaxDetail) => {
    // Find empty tax line or add new one
    const emptyTaxIndex = formData.taxes.findIndex(t => !t.tax_name && !t.tax_rate);
    
    if (emptyTaxIndex >= 0) {
      updateTaxLine(emptyTaxIndex, 'tax_name', tax.tax_name);
      updateTaxLine(emptyTaxIndex, 'tax_rate', tax.tax_rate);
    } else {
      // Add new tax line
      const newTaxes = [...formData.taxes, {
        tax_name: tax.tax_name,
        tax_rate: tax.tax_rate,
      }];
      updateTaxes(newTaxes);
    }

    toast.success(`Applied ${tax.tax_name} (${tax.tax_rate}%) to invoice`);
  };

  // Handle setting/clearing tax as default (toggle behavior)
  const handleSetTaxDefault = async (tax: TaxDetail) => {
    if (!tax.tax_name || !tax.tax_rate) {
      toast.error("Please fill in both tax name and rate before setting as default.");
      return;
    }

    const rate = Number.parseFloat(tax.tax_rate);
    if (isNaN(rate) || rate <= 0 || rate > 100) {
      toast.error("Please enter a valid tax rate between 0.01% and 100%.");
      return;
    }

    // Check if this tax is currently the user's default
    const isCurrentlyDefault = isCurrentDefault(tax);
    
    if (isCurrentlyDefault && isUserDefaultTax) {
      // Clear the user default
      await clearUserTaxDefaultFromForm();
    } else {
      // Set as user default
      const taxData = {
        tax_name: tax.tax_name.trim(),
        tax_rate: rate.toString()
      };

      const success = await setUserDefault(taxData);
      
      if (success) {
        toast.success(`⭐ Set "${tax.tax_name}" as your personal default tax!`);
        
        // Update the state to show star as filled
        setIsUserDefaultTax(true);
        
        // Track this recently set default for immediate visual feedback
        setRecentlySetDefaults(prev => [
          ...prev.filter(d => !(d.tax_name === taxData.tax_name && d.tax_rate === taxData.tax_rate)),
          { ...taxData, type: 'user' }
        ]);
      }
    }
  };

  // Check if a tax is currently the default
  const isCurrentDefault = (tax: TaxDetail): boolean => {
    if (!tax.tax_name || !tax.tax_rate) return false;
    
    // Check if this is the user's default tax that was pre-loaded
    if (isUserDefaultTax && formData.taxes.length > 0) {
      const firstTax = formData.taxes[0];
      if (firstTax.tax_name === tax.tax_name && firstTax.tax_rate === tax.tax_rate) {
        return true;
      }
    }
    
    // Check if this was recently set as a default (immediate feedback)
    const recentlySet = recentlySetDefaults.some(d => 
      d.tax_name === tax.tax_name && d.tax_rate === tax.tax_rate
    );
    
    if (recentlySet) return true;
    
    // Check against current smart recommendation
    if (smartTaxRecommendation && 
        smartTaxRecommendation.tax_name === tax.tax_name &&
        parseFloat(smartTaxRecommendation.tax_rate) === parseFloat(tax.tax_rate)) {
      return smartTaxRecommendation.source === 'user_default' || smartTaxRecommendation.source === 'property_default';
    }
    
    return false;
  };

  // Get tooltip text for star button
  const getTooltipText = (tax: TaxDetail): string => {
    if (!tax.tax_name || !tax.tax_rate) return "Set as my default tax";
    
    const recentlySet = recentlySetDefaults.some(d => 
      d.tax_name === tax.tax_name && d.tax_rate === tax.tax_rate
    );
    
    if (recentlySet) {
      return "⭐ This is now your default tax! Click to remove.";
    }
    
    if (isCurrentDefault(tax)) {
      if (isUserDefaultTax) {
        return "⭐ This is your default tax! Click to remove.";
      } else {
        return smartTaxRecommendation?.source === 'property_default' 
          ? "This is the current default tax for this property"
          : "This is your current default tax";
      }
    }
    
    return "Set as my default tax";
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await submitForm();
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/50 dark:bg-black/80 flex items-center justify-center p-4 z-50">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden transition-colors duration-300"
        >
          {/* Header */}
          <div className="bg-gray-50 dark:bg-gray-900 px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Create New Invoice</h2>
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors disabled:opacity-50"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)] bg-white dark:bg-gray-800">
            <FinancialErrorBoundary 
              componentName="New Invoice Modal"
              onError={(error, errorInfo) => {
                // Log error for monitoring
                console.error('Financial calculation error in NewInvoiceModal:', {
                  error: error.message,
                  stack: error.stack,
                  componentStack: errorInfo.componentStack,
                  formData: {
                    amount: formData.amount,
                    taxes: formData.taxes,
                    property_id: formData.property_id
                  }
                });
              }}
            >
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* Loading State */}
                {isLoadingData && (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 dark:border-blue-400 mx-auto mb-4"></div>
                    <p className="text-gray-600 dark:text-gray-400">Loading properties and tenants...</p>
                  </div>
                )}

                {!isLoadingData && (
                  <>
                    {/* Form Fields with Tax Recommendation Banner positioned between Property & Tax sections */}
                    <InvoiceFormFields
                      formData={formData}
                      errors={errors}
                      properties={properties}
                      tenants={tenants}
                      calculatedTotals={calculatedTotals}
                      onUpdateField={updateField}
                      onAddTaxLine={addTaxLine}
                      onRemoveTaxLine={removeTaxLine}
                      onUpdateTaxLine={updateTaxLine}
                      onSetTaxDefault={handleSetTaxDefault}
                      isCurrentDefault={isCurrentDefault}
                      getTooltipText={getTooltipText}
                      mode="create"
                      taxRecommendationBanner={
                        <TaxRecommendationBanner
                          smartTaxRecommendation={smartTaxRecommendation}
                          isLoadingSmartTax={isLoadingSmartTax}
                          onApplyTax={handleApplyTaxRecommendation}
                          onSetUserDefault={setUserDefault}
                          onSetPropertyDefault={setPropertyDefault}
                          propertyId={formData.property_id ? parseInt(formData.property_id.toString()) : undefined}
                          currentTaxes={formData.taxes}
                        />
                      }
                    />
                  </>
                )}
              </form>
            </FinancialErrorBoundary>
          </div>

          {/* Footer */}
          <div className="bg-gray-50 dark:bg-gray-900 px-6 border-t border-gray-200 dark:border-gray-700 h-16 flex items-center justify-between">
            {/* Calculated Total Display */}
            {!isLoadingData && formData.amount ? (
              <div className="flex items-baseline">
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Total: </span>
                <span className="text-lg font-semibold text-blue-600 dark:text-blue-400 ml-1">
                  ${calculatedTotals.grandTotal.toFixed(2)}
                </span>
                {calculatedTotals.totalTax.gt(0) && (
                  <span className="text-sm text-gray-500 dark:text-gray-400 ml-2">
                    (includes ${calculatedTotals.totalTax.toFixed(2)} tax)
                  </span>
                )}
              </div>
            ) : (
              <div></div>
            )}

            {/* Action Buttons */}
            <div className="flex space-x-3">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800 disabled:opacity-50 transition-colors"
              >
                Cancel
              </button>
              
              <button
                type="submit"
                onClick={handleSubmit}
                disabled={isSubmitting || isLoadingData}
                className="px-6 py-2 text-sm font-medium text-white bg-blue-600 dark:bg-blue-700 border border-transparent rounded-md hover:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center transition-colors"
              >
                {isSubmitting ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Creating Invoice...
                  </>
                ) : (
                  'Create Invoice'
                )}
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default NewInvoiceModal;
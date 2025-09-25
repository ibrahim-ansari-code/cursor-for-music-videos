import React, { useState, useEffect } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { AnimatePresence, motion } from 'framer-motion';
import { toast } from 'react-toastify';
import { X, Receipt } from 'lucide-react';
import { fetchProperties } from '../../../utils/api/properties';
import { useExpenseForm } from '../../../hooks/accounting/useExpenseForm';
import { useTaxRecommendations } from '../../../hooks/accounting/useTaxRecommendations';
import TaxRecommendationBanner from '../shared/TaxRecommendationBanner';
import ExpenseFormFields from '../shared/ExpenseFormFields';
import FinancialErrorBoundary from '../shared/FinancialErrorBoundary';
import type { TaxDetail, Expense } from '../../../types/accounting';

interface Property {
  id: number;
  name: string;
  address?: string;
}

interface EditExpenseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  expenseData?: Expense;
}

/**
 * Refactored EditExpenseModal with extracted business logic and modular components
 * - Uses the same hooks and components as NewExpenseModal for consistency
 * - Initializes form data from existing expense
 * - Handles updates instead of creation
 * - Receipt processing removed (only available in NewExpenseModal)
 */
const EditExpenseModal: React.FC<EditExpenseModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  expenseData,
}) => {
  // Data state
  const [properties, setProperties] = useState<Property[]>([]);
  const [isLoadingData, setIsLoadingData] = useState(false);
  
  // Track recently set tax defaults for immediate visual feedback
  const [recentlySetDefaults, setRecentlySetDefaults] = useState<Array<{
    tax_name: string;
    tax_rate: string;
    type: 'user' | 'property';
  }>>([]);

  // Convert expense data to form data format
  const convertExpenseToFormData = (expense: Expense) => {
    // Format date to YYYY-MM-DD for HTML date input
    const formatDate = (dateStr: string) => {
      if (!dateStr) return '';
      try {
        // Handle different date formats - could be ISO string or just date
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return '';
        return date.toISOString().split('T')[0];
      } catch {
        return '';
      }
    };

    return {
      id: expense.id?.toString(),
      property_id: expense.property_id?.toString() || '',
      property_name: expense.property_name || '',
      category: expense.category || '',
      amount: expense.subtotal_amount || '',
      expense_date: formatDate(expense.expense_date),
      description: expense.description || '',
      payment_method: expense.payment_method || '',
      receipt_url: expense.receipt_url || null,
      taxes: expense.taxes && expense.taxes.length > 0 
        ? expense.taxes 
        : [{ tax_name: '', tax_rate: '' }],
    };
  };

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
    setFormData,
    clearUserTaxDefaultFromForm,
    setIsUserDefaultTax,
  } = useExpenseForm({
    initialData: expenseData ? convertExpenseToFormData(expenseData) : undefined,
    mode: 'edit',
    onSuccess: () => {
      onSuccess?.();
      onClose();
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
    category: formData.category,
  });

  // Initialize data when modal opens
  useEffect(() => {
    if (isOpen) {
      loadInitialData();
      
      // Set form data from expense data if available and valid
      if (expenseData?.id) {
        const convertedData = convertExpenseToFormData(expenseData);
        setFormData(convertedData);
      }
    } else {
      // Clean up when modal closes
      clearRecommendations();
    }
  }, [isOpen, expenseData, setFormData, clearRecommendations]);

  const loadInitialData = async () => {
    setIsLoadingData(true);
    try {
      const propertiesResponse = await fetchProperties();
      setProperties(propertiesResponse || []);
    } catch (error) {
      console.error('Error loading initial data:', error);
      toast.error('Failed to load properties');
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

    toast.success(`Applied ${tax.tax_name} (${tax.tax_rate}%) to expense`);
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

  return (
    <Dialog.Root open={isOpen} onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 dark:bg-black/80 backdrop-blur-sm z-50">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0"
          />
        </Dialog.Overlay>

        <Dialog.Content className="fixed left-[50%] top-[50%] translate-x-[-50%] translate-y-[-50%] z-50">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.3, type: 'spring', stiffness: 300, damping: 30 }}
            className="w-[90vw] max-w-5xl bg-white dark:bg-gray-800 rounded-2xl shadow-2xl overflow-hidden relative flex flex-col transition-colors duration-300"
            style={{ maxHeight: '90vh' }}
          >
            {/* Clean Header matching NewExpenseModal */}
            <div className="relative bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-600 px-6 py-4 transition-colors duration-300">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-emerald-50 rounded-lg">
                    <Receipt className="h-5 w-5 text-emerald-600" />
                  </div>
                  <div>
                    <Dialog.Title className="text-lg font-semibold text-gray-900 dark:text-gray-100 transition-colors duration-300">
                      Edit Expense
                    </Dialog.Title>
                    <Dialog.Description className="text-sm text-gray-500 dark:text-gray-400 mt-0.5 transition-colors duration-300">
                      Update your property expense details
                    </Dialog.Description>
                  </div>
                </div>
                <Dialog.Close asChild>
                  <button
                    className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                    disabled={isSubmitting}
                    aria-label="Close"
                  >
                    <X className="h-5 w-5 text-gray-500 dark:text-gray-400 transition-colors duration-300" />
                  </button>
                </Dialog.Close>
              </div>
            </div>

             {/* Content area optimized for single-page */}
             <motion.div 
               className="overflow-y-auto p-4 bg-gray-50/50 dark:bg-gray-900/50 transition-colors duration-300"
               style={{ maxHeight: '70vh' }}
               initial={{ opacity: 0, y: 10 }}
               animate={{ opacity: 1, y: 0 }}
               transition={{ duration: 0.4, delay: 0.1 }}
             >
              <FinancialErrorBoundary 
                componentName="Edit Expense Modal"
                onError={(error, errorInfo) => {
                  // Log error for monitoring
                  console.error('Financial calculation error in EditExpenseModal:', {
                    error: error.message,
                    stack: error.stack,
                    componentStack: errorInfo.componentStack,
                    expenseId: expenseData?.id,
                    formData: {
                      amount: formData.amount,
                      taxes: formData.taxes,
                      property_id: formData.property_id
                    }
                  });
                }}
              >
                <AnimatePresence mode="wait">
                   <motion.form 
                     onSubmit={handleSubmit} 
                     className="space-y-2"
                     initial={{ opacity: 0 }}
                     animate={{ opacity: 1 }}
                     transition={{ duration: 0.3 }}
                   >
                    {/* Compact Loading State */}
                    {isLoadingData && (
                      <motion.div 
                        className="flex flex-col items-center justify-center py-6 bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-900/20 dark:to-emerald-800/20 rounded-lg border border-emerald-200 dark:border-emerald-700 transition-colors duration-300"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.3 }}
                      >
                        <div className="relative">
                          <div className="w-6 h-6 border-2 border-emerald-200 dark:border-emerald-600 rounded-full animate-spin border-t-emerald-600 dark:border-t-emerald-400 transition-colors duration-300"></div>
                        </div>
                        <p className="text-emerald-700 dark:text-emerald-300 font-medium mt-2 text-sm transition-colors duration-300">Loading expense data...</p>
                      </motion.div>
                    )}

                    {!isLoadingData && (
                      <>
                        {/* Form Fields with Tax Recommendation Banner positioned between Property & Tax sections */}
                        <ExpenseFormFields
                          formData={formData}
                          errors={errors}
                          properties={properties}
                          onUpdateField={updateField}
                          onAddTaxLine={addTaxLine}
                          onRemoveTaxLine={removeTaxLine}
                          onUpdateTaxLine={updateTaxLine}
                          onSetTaxDefault={handleSetTaxDefault}
                          isCurrentDefault={isCurrentDefault}
                          getTooltipText={getTooltipText}
                          mode="edit"
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
                  </motion.form>
                </AnimatePresence>
              </FinancialErrorBoundary>
            </motion.div>

            {/* Clean Footer matching NewPropertyModal */}
            <div className="border-t px-6 py-3 flex justify-between items-center bg-white dark:bg-gray-800 flex-shrink-0 border-gray-200 dark:border-gray-600 transition-colors duration-300">
              {/* Simplified Total Display */}
              {!isLoadingData && formData.amount ? (
                <div className="flex items-baseline">
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-400 transition-colors duration-300">Total:</span>
                  <span className="text-lg font-semibold text-emerald-600 dark:text-emerald-400 ml-2 transition-colors duration-300">
                    ${calculatedTotals.grandTotal.toFixed(2)}
                  </span>
                  {calculatedTotals.totalTax.gt(0) && (
                    <span className="text-sm text-gray-500 dark:text-gray-400 ml-2 transition-colors duration-300">
                      (includes ${calculatedTotals.totalTax.toFixed(2)} tax)
                    </span>
                  )}
                </div>
              ) : (
                <div></div>
              )}
              
              <div className="flex items-center space-x-3">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isSubmitting}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50 transition-colors"
                >
                  Cancel
                </button>
                
                <button
                  type="submit"
                  onClick={handleSubmit}
                  disabled={isSubmitting || isLoadingData}
                  className={`px-5 py-2 text-sm font-medium text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 ${
                    isSubmitting || isLoadingData 
                      ? 'bg-gray-400 dark:bg-gray-600' 
                      : 'bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-500 dark:hover:bg-emerald-600'
                  }`}
                >
                  {isSubmitting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>Updating...</span>
                    </>
                  ) : (
                    'Update Expense'
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};

export default EditExpenseModal;
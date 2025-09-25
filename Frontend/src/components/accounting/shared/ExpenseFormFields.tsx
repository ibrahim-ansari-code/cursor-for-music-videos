import React from 'react';
import { DollarSign, FileText, Tag } from 'lucide-react';
import type { ExpenseFormData, TaxDetail } from '../../../types/accounting';

// Helper function to determine if tax recommendation banner should be shown inline
const shouldShowInlineTaxRecommendation = (
  index: number,
  formData: ExpenseFormData,
  tax: TaxDetail,
  taxRecommendationBanner: React.ReactNode
): taxRecommendationBanner is React.ReactElement => {
  return !!(
    index === 0 &&
    formData.property_id && 
    formData.property_id !== '' && 
    (!tax.tax_name || tax.tax_name.trim() === '') && 
    taxRecommendationBanner && 
    React.isValidElement(taxRecommendationBanner)
  );
};

// Strongly typed interfaces
interface Property {
  id: number;
  name: string;
  address?: string;
}

interface ExpenseFormFieldsProps {
  formData: ExpenseFormData;
  errors: Record<string, string>;
  properties: Property[];
  onUpdateField: <K extends keyof ExpenseFormData>(field: K, value: ExpenseFormData[K]) => void;
  onAddTaxLine: () => void;
  onRemoveTaxLine: (index: number) => void;
  onUpdateTaxLine: (index: number, field: keyof TaxDetail, value: string) => void;
  onSetTaxDefault?: (tax: TaxDetail) => void;
  isCurrentDefault?: (tax: TaxDetail) => boolean;
  getTooltipText?: (tax: TaxDetail) => string;
  mode?: 'create' | 'edit';
  taxRecommendationBanner?: React.ReactNode;
}

// Constants with proper typing
const EXPENSE_CATEGORIES = [
  'maintenance',
  'utilities',
  'taxes',
  'insurance',
  'administrative',
  'other'
] as const;

const PAYMENT_METHODS = [
  'Credit Card',
  'Debit Card',
  'Bank Transfer',
  'Wire Transfer',
  'Direct Deposit',
  'Interac e-Transfer',
  'Cash',
  'Check',
  'Bank Draft',
  'PayPal',
  'Internal Transfer',
  'Other'
] as const;

const ExpenseFormFields: React.FC<ExpenseFormFieldsProps> = ({
  formData,
  errors,
  properties,
  onUpdateField,
  onAddTaxLine,
  onRemoveTaxLine,
  onUpdateTaxLine,
  onSetTaxDefault,
  isCurrentDefault,
  getTooltipText,
  mode = 'create',
  taxRecommendationBanner,
}) => {
  // Helper functions
  const getInputClassName = (fieldName: string): string => {
    const baseClasses = "w-full px-3 py-2.5 border-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-100 text-sm bg-white dark:bg-gray-700 dark:text-gray-100 transition-all duration-200";
    return errors[fieldName] 
      ? `${baseClasses} border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500 focus:border-red-500 focus:ring-red-100 dark:focus:ring-red-900/30`
      : `${baseClasses} border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500 focus:border-emerald-500 dark:focus:border-emerald-400`;
  };

  const handlePropertyChange = (event: React.ChangeEvent<HTMLSelectElement>): void => {
    const selectedProperty = properties.find(p => p.id.toString() === event.target.value);
    onUpdateField('property_id', event.target.value);
    onUpdateField('property_name', selectedProperty?.name || '');
  };

  const handleTaxDefault = (tax: TaxDetail): void => {
    if (!onSetTaxDefault) return;
    onSetTaxDefault({ tax_name: tax.tax_name, tax_rate: tax.tax_rate });
  };

  const isDefaultTax = (tax: TaxDetail): boolean => {
    return isCurrentDefault?.({ tax_name: tax.tax_name, tax_rate: tax.tax_rate }) ?? false;
  };

  const getTaxTooltip = (tax: TaxDetail): string => {
    return getTooltipText?.({ tax_name: tax.tax_name, tax_rate: tax.tax_rate }) || "Set as default";
  };

  return (
    <div className="space-y-3">
      {/* Expense Details Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700 mb-4">
        <div className="flex items-center mb-3">
          <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-lg flex items-center justify-center mr-3">
            <DollarSign className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Expense Details</h3>
          </div>
        </div>
        
        {/* Row 1: Description | Property | Amount */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
          {/* Description */}
          <div>
            <label htmlFor="description" className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
              Title/Description
            </label>
            <div className="relative">
              <FileText className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                id="description"
                value={formData.description || ''}
                onChange={(e) => onUpdateField('description', e.target.value)}
                className="w-full pl-10 pr-3 py-2.5 border-2 rounded-lg bg-white dark:bg-gray-700 focus:border-emerald-500 dark:focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 dark:focus:ring-emerald-900/30 focus:outline-none transition-all duration-200 text-gray-900 dark:text-gray-100 text-sm border-gray-300 dark:border-gray-600"
                placeholder="Expense title..."
              />
            </div>
          </div>

          {/* Property */}
          <div>
            <label htmlFor="property" className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
              Property <span className="text-red-500 dark:text-red-400">*</span>
            </label>
            <select
              id="property"
              value={formData.property_id || ''}
              onChange={handlePropertyChange}
              className={getInputClassName('property_id')}
            >
              <option value="">Select property...</option>
              {properties.map((property) => (
                <option key={property.id} value={property.id}>
                  {property.name}
                </option>
              ))}
            </select>
            {errors.property_id && (
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.property_id}</p>
            )}
          </div>

          {/* Amount */}
          <div>
            <label htmlFor="amount" className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
              {mode === 'edit' ? 'Update Amount' : 'Expense Amount'} <span className="text-red-500 dark:text-red-400">*</span>
            </label>
            <div className="relative">
              <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="number"
                step="0.01"
                min="0"
                id="amount"
                value={formData.amount || ''}
                onChange={(e) => onUpdateField('amount', e.target.value)}
                className={`w-full pl-10 pr-3 py-2.5 border-2 rounded-lg bg-white dark:bg-gray-700 focus:border-emerald-500 dark:focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 dark:focus:ring-emerald-900/30 focus:outline-none transition-all duration-200 text-gray-900 dark:text-gray-100 font-medium text-sm ${
                  errors.amount 
                    ? 'border-red-300 dark:border-red-500 focus:border-red-500 focus:ring-red-100 dark:focus:ring-red-900/30' 
                    : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
                }`}
                placeholder="0.00"
              />
            </div>
            {errors.amount && (
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.amount}</p>
            )}
          </div>
        </div>

        {/* Row 2: Category | Payment Method | Date */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
          {/* Category */}
          <div>
            <label htmlFor="category" className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
              Category <span className="text-red-500 dark:text-red-400">*</span>
            </label>
            <div className="relative">
              <Tag className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <select
                id="category"
                value={formData.category || ''}
                onChange={(e) => onUpdateField('category', e.target.value)}
                className={`w-full pl-10 pr-8 py-2.5 border-2 rounded-lg bg-white dark:bg-gray-700 appearance-none focus:border-emerald-500 dark:focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 dark:focus:ring-emerald-900/30 focus:outline-none transition-all duration-200 text-gray-900 dark:text-gray-100 font-medium text-sm ${
                  errors.category 
                    ? 'border-red-300 dark:border-red-500 focus:border-red-500 focus:ring-red-100 dark:focus:ring-red-900/30' 
                    : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
                }`}
              >
                <option value="">Select category...</option>
                {EXPENSE_CATEGORIES.map((category) => (
                  <option key={category} value={category}>
                    {category.charAt(0).toUpperCase() + category.slice(1)}
                  </option>
                ))}
              </select>
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2 pointer-events-none">
                <svg className="w-4 h-4 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
            {errors.category && (
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.category}</p>
            )}
          </div>

          {/* Payment Method */}
          <div>
            <label htmlFor="payment_method" className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
              Payment Method
            </label>
            <select
              id="payment_method"
              value={formData.payment_method || ''}
              onChange={(e) => onUpdateField('payment_method', e.target.value)}
              className={getInputClassName('payment_method')}
            >
              <option value="">Select method...</option>
              {PAYMENT_METHODS.map((method) => (
                <option key={method} value={method}>
                  {method}
                </option>
              ))}
            </select>
            {errors.payment_method && (
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.payment_method}</p>
            )}
          </div>

          {/* Date */}
          <div>
            <label htmlFor="expense_date" className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
              Date <span className="text-red-500 dark:text-red-400">*</span>
            </label>
            <input
              type="date"
              id="expense_date"
              value={formData.expense_date || ''}
              onChange={(e) => onUpdateField('expense_date', e.target.value)}
              className={getInputClassName('expense_date')}
            />
            {errors.expense_date && (
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.expense_date}</p>
            )}
          </div>
        </div>
      </div>

      {/* Tax Details Section */}
      <div className="mt-4">
        
        <div className="space-y-2 mt-2">
          {formData.taxes?.map((tax, index) => (
            <div 
              key={index} 
              className="group relative bg-gradient-to-r from-emerald-50/50 to-emerald-50 dark:from-emerald-900/20 dark:to-emerald-900/10 border border-emerald-100 dark:border-emerald-800 rounded-lg p-3 hover:shadow-sm transition-all duration-200"
            >
              <div className="flex items-center justify-between">
                {/* Left side - all tax fields and controls except Add Tax button */}
                <div className="flex items-center space-x-4">
                  {/* Tax Details Header - Only on first row */}
                  {index === 0 && (
                    <div className="flex items-center space-x-3 mr-4 w-64 flex-shrink-0">
                    <div className="w-6 h-6 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-lg flex items-center justify-center">
                      <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Tax Details</h4>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Applicable taxes (HST, GST, etc.)</p>
                    </div>
                    <div className="h-10 w-px bg-gray-300 dark:bg-gray-600 ml-4"></div>
                  </div>
                )}

                {/* Alignment spacer for additional rows - matches Tax Details header width + space-x-4 gap */}
                {index > 0 && <div style={{ width: '272px' }} className="flex-shrink-0"></div>}

                {/* Tax Name */}
                <div className="w-56 relative overflow-visible" style={{ minHeight: '40px' }}>
                  <input
                    type="text"
                    value={tax.tax_name || ''}
                    onChange={(e) => onUpdateTaxLine(index, 'tax_name', e.target.value)}
                    className={`w-full px-3 py-2 border-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-100 dark:focus:ring-emerald-900/30 bg-white dark:bg-gray-700 text-sm text-gray-900 dark:text-gray-100 ${
                      errors[`tax_name_${index}`] ? 'border-red-300 dark:border-red-500 bg-red-50 dark:bg-red-900/20' : 'border-gray-200 dark:border-gray-600 hover:border-emerald-300 dark:hover:border-emerald-500'
                    }`}
                    placeholder="Tax name (e.g., HST, GST)"
                  />
                  {/* Inline Tax Recommendation - Only for first tax field if empty and property is selected */}
                  {shouldShowInlineTaxRecommendation(index, formData, tax, taxRecommendationBanner) &&
                    React.cloneElement(taxRecommendationBanner, { isInline: true } as any)
                  }
                  {errors[`tax_name_${index}`] && (
                    <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors[`tax_name_${index}`]}</p>
                  )}
                </div>

                {/* Tax Rate */}
                <div className="w-28">
                  <div className="relative">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      max="100"
                      value={tax.tax_rate || ''}
                      onChange={(e) => onUpdateTaxLine(index, 'tax_rate', e.target.value)}
                      className={`w-full px-3 py-2 pr-8 border-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-100 dark:focus:ring-emerald-900/30 bg-white dark:bg-gray-700 text-sm text-gray-900 dark:text-gray-100 ${
                        errors[`tax_rate_${index}`] ? 'border-red-300 dark:border-red-500 bg-red-50 dark:bg-red-900/20' : 'border-gray-200 dark:border-gray-600 hover:border-emerald-300 dark:hover:border-emerald-500'
                      }`}
                      placeholder="13.00"
                    />
                    <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 dark:text-gray-400 text-sm">%</span>
                  </div>
                  {errors[`tax_rate_${index}`] && (
                    <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors[`tax_rate_${index}`]}</p>
                  )}
                </div>

                {/* Save Button */}
                {onSetTaxDefault && (
                  <button
                    type="button"
                    onClick={() => handleTaxDefault(tax)}
                    disabled={!tax.tax_name || !tax.tax_rate}
                    className={`inline-flex items-center px-3 py-2 rounded-lg transition-all duration-200 text-sm font-medium ${
                      isDefaultTax(tax)
                        ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 shadow-sm'
                        : 'bg-white dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 hover:text-yellow-600 dark:hover:text-yellow-400 disabled:opacity-50 border border-gray-200 dark:border-gray-600'
                    }`}
                    title={getTaxTooltip(tax)}
                  >
                    <svg 
                      className="w-4 h-4 mr-1" 
                      fill={isDefaultTax(tax) ? "currentColor" : "none"} 
                      viewBox="0 0 24 24" 
                      stroke="currentColor" 
                      strokeWidth={2}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                    </svg>
                    Save
                  </button>
                )}
                </div>

                {/* Right side - Action buttons */}
                <div className="flex items-center space-x-2">
                  {/* Add Tax Button - Only on first row */}
                  {index === 0 && (
                    <button
                      type="button"
                      onClick={onAddTaxLine}
                      className="inline-flex items-center px-3 py-2 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white text-sm font-medium rounded-lg transition-all duration-200 shadow-sm"
                    >
                      <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                      </svg>
                      Add Tax
                    </button>
                  )}

                  {/* Remove Button */}
                  {formData.taxes && formData.taxes.length > 1 && (
                    <button
                      type="button"
                      onClick={() => onRemoveTaxLine(index)}
                      className="p-2 text-red-500 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all duration-200"
                      title="Remove tax"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            </div>
          )) || []}
        </div>

      </div>
    </div>
  );
};

export default ExpenseFormFields;
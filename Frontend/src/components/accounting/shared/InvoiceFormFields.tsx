import React from 'react';
import Decimal from 'decimal.js';
import type { InvoiceFormData, InvoiceStatus, TaxDetail } from '../../../types/accounting';
import { INVOICE_STATUSES } from '../../../utils/constants';

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

interface InvoiceFormFieldsProps {
  formData: InvoiceFormData;
  errors: Record<string, string>;
  properties: Property[];
  tenants: Tenant[];
  calculatedTotals: {
    subtotal: Decimal;
    totalTax: Decimal;
    grandTotal: Decimal;
  };
  onUpdateField: <K extends keyof InvoiceFormData>(field: K, value: InvoiceFormData[K]) => void;
  onAddTaxLine: () => void;
  onRemoveTaxLine: (index: number) => void;
  onUpdateTaxLine: (index: number, field: keyof TaxDetail, value: string) => void;
  onSetTaxDefault?: (tax: TaxDetail) => Promise<void>;
  isCurrentDefault?: (tax: TaxDetail) => boolean;
  getTooltipText?: (tax: TaxDetail) => string;
  mode?: 'create' | 'edit';
  taxRecommendationBanner?: React.ReactNode;
}

const InvoiceFormFields: React.FC<InvoiceFormFieldsProps> = ({
  formData,
  errors,
  properties,
  tenants,
  calculatedTotals,
  onUpdateField,
  onAddTaxLine,
  onRemoveTaxLine,
  onUpdateTaxLine,
  onSetTaxDefault,
  isCurrentDefault,
  getTooltipText,
  taxRecommendationBanner,
}) => {
  // Filter tenants based on selected property
  const filteredTenants = React.useMemo(() => {
    if (!formData.property_id) return tenants; // Show all tenants when no property selected
    
    // Safely convert to string first, then parse to handle both string and number inputs
    const propertyIdStr = String(formData.property_id).trim();
    if (!propertyIdStr) return tenants; // Handle empty string case
    
    const selectedPropertyId = parseInt(propertyIdStr, 10);
    if (isNaN(selectedPropertyId)) return tenants; // Handle NaN case
    
    return tenants.filter(tenant =>
      tenant.property_units?.some(unit => 
        unit.property_id === selectedPropertyId
      )
    );
  }, [tenants, formData.property_id]);

  return (
    <div className="space-y-6">
      {/* Invoice Details Section */}
      <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Invoice Details</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Invoice Number */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Invoice Number *
            </label>
            <input
              type="text"
              value={formData.invoice_number}
              onChange={(e) => onUpdateField('invoice_number', e.target.value)}
              className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 ${
                errors.invoice_number ? 'border-red-300 dark:border-red-500 bg-red-50 dark:bg-red-900/20' : 'border-gray-300 dark:border-gray-600'
              }`}
              placeholder="e.g., INV-2023-001"
            />
            {errors.invoice_number && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.invoice_number}</p>
            )}
          </div>

          {/* Status */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Status
            </label>
            <select
              value={formData.status}
              onChange={(e) => onUpdateField('status', e.target.value as InvoiceStatus)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              {INVOICE_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </div>

          {/* Issue Date */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Issue Date *
            </label>
            <input
              type="date"
              value={formData.issue_date}
              onChange={(e) => onUpdateField('issue_date', e.target.value)}
              className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 ${
                errors.issue_date ? 'border-red-300 dark:border-red-500 bg-red-50 dark:bg-red-900/20' : 'border-gray-300 dark:border-gray-600'
              }`}
            />
            {errors.issue_date && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.issue_date}</p>
            )}
          </div>

          {/* Due Date */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Due Date *
            </label>
            <input
              type="date"
              value={formData.due_date}
              onChange={(e) => onUpdateField('due_date', e.target.value)}
              className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 ${
                errors.due_date ? 'border-red-300 dark:border-red-500 bg-red-50 dark:bg-red-900/20' : 'border-gray-300 dark:border-gray-600'
              }`}
            />
            {errors.due_date && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.due_date}</p>
            )}
          </div>
        </div>
      </div>

      {/* Amount & Description Section */}
      <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Amount & Description</h3>
        
        <div className="space-y-4">
          {/* Subtotal Amount */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Subtotal Amount (before taxes) *
            </label>
            <div className="relative">
              <span className="absolute left-3 top-2 text-gray-500 dark:text-gray-400">$</span>
              <input
                type="number"
                step="0.01"
                min="0"
                value={formData.amount}
                onChange={(e) => onUpdateField('amount', e.target.value)}
                className={`w-full pl-8 pr-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 ${
                  errors.amount ? 'border-red-300 dark:border-red-500 bg-red-50 dark:bg-red-900/20' : 'border-gray-300 dark:border-gray-600'
                }`}
                placeholder="0.00"
              />
            </div>
            {errors.amount && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.amount}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description *
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => onUpdateField('description', e.target.value)}
              rows={3}
              className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 resize-vertical bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 ${
                errors.description ? 'border-red-300 dark:border-red-500 bg-red-50 dark:bg-red-900/20' : 'border-gray-300 dark:border-gray-600'
              }`}
              placeholder="Invoice description..."
            />
            {errors.description && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.description}</p>
            )}
          </div>
        </div>
      </div>

      {/* Property & Tenant Section */}
      <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Property & Tenant</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Property Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Property (Optional)
            </label>
            <select
              value={formData.property_id}
              onChange={(e) => {
                onUpdateField('property_id', e.target.value);
                onUpdateField('tenant_id', ''); // Reset tenant when property changes
                onUpdateField('tenant_name', '');
                
                // Update property name
                const propertyIdValue = e.target.value.trim();
                const selectedProperty = propertyIdValue 
                  ? properties.find(p => {
                      const parsedId = parseInt(propertyIdValue, 10);
                      return !isNaN(parsedId) && p.id === parsedId;
                    })
                  : undefined;
                onUpdateField('property_name', selectedProperty?.name || '');
              }}
              className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 ${
                errors.property_id ? 'border-red-300 dark:border-red-500 bg-red-50 dark:bg-red-900/20' : 'border-gray-300 dark:border-gray-600'
              }`}
            >
              <option value="">Select a property...</option>
              {properties.map((property) => (
                <option key={property.id} value={property.id}>
                  {property.name}
                  {property.address && ` - ${property.address}`}
                </option>
              ))}
            </select>
            {errors.property_id && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.property_id}</p>
            )}
          </div>

          {/* Tenant Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Tenant (Optional)
            </label>
            <select
              value={formData.tenant_id}
              onChange={(e) => {
                onUpdateField('tenant_id', e.target.value);
                
                // Update tenant name
                const selectedTenant = filteredTenants.find(t => t.id === parseInt(e.target.value, 10));
                onUpdateField('tenant_name', selectedTenant?.full_name || '');
              }}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="">Select a tenant (optional)...</option>
              {filteredTenants.map((tenant) => (
                <option key={tenant.id} value={tenant.id}>
                  {tenant.full_name}
                  {tenant.email && ` (${tenant.email})`}
                </option>
              ))}
            </select>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {formData.property_id 
                ? 'Showing tenants for selected property' 
                : 'Showing all tenants - select a property to filter'}
            </p>
          </div>
        </div>
      </div>

      {/* Tax Recommendation Banner - positioned between Property & Tenant and Tax Details */}
      {taxRecommendationBanner}

      {/* Tax Lines Section */}
      <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">Tax Details</h3>
          <button
            type="button"
            onClick={onAddTaxLine}
            className="bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-800 text-white px-3 py-1 rounded-md text-sm font-medium transition-colors"
          >
            + Add Tax
          </button>
        </div>

        <div className="space-y-3">
          {formData.taxes.map((tax, index) => (
            <div key={index} className="flex items-center space-x-3 bg-white dark:bg-gray-700 p-3 rounded-md border border-gray-200 dark:border-gray-600">
              <div className="flex-grow grid grid-cols-1 md:grid-cols-2 gap-3">
                {/* Tax Name */}
                <div>
                  <input
                    type="text"
                    value={tax.tax_name}
                    onChange={(e) => onUpdateTaxLine(index, 'tax_name', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 ${
                      errors[`tax_name_${index}`] ? 'border-red-300 dark:border-red-500 bg-red-50 dark:bg-red-900/20' : 'border-gray-300 dark:border-gray-600'
                    }`}
                    placeholder="Tax name (e.g., HST, GST)"
                  />
                  {errors[`tax_name_${index}`] && (
                    <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors[`tax_name_${index}`]}</p>
                  )}
                </div>

                {/* Tax Rate */}
                <div>
                  <div className="relative">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      max="100"
                      value={tax.tax_rate}
                      onChange={(e) => onUpdateTaxLine(index, 'tax_rate', e.target.value)}
                      className={`w-full px-3 py-2 pr-8 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 ${
                        errors[`tax_rate_${index}`] ? 'border-red-300 dark:border-red-500 bg-red-50 dark:bg-red-900/20' : 'border-gray-300 dark:border-gray-600'
                      }`}
                      placeholder="0.00"
                    />
                    <span className="absolute right-3 top-2 text-gray-500 dark:text-gray-400">%</span>
                  </div>
                  {errors[`tax_rate_${index}`] && (
                    <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors[`tax_rate_${index}`]}</p>
                  )}
                </div>
              </div>

              {/* Star Button for Setting Default */}
              {onSetTaxDefault && (
                <button
                  type="button"
                  onClick={() => onSetTaxDefault({ tax_name: tax.tax_name, tax_rate: String(tax.tax_rate) })}
                  disabled={!tax.tax_name || !tax.tax_rate}
                  className={`p-2 h-9 w-9 flex items-center justify-center border rounded-lg transition-all ${
                    isCurrentDefault?.({ tax_name: tax.tax_name, tax_rate: String(tax.tax_rate) })
                      ? 'bg-yellow-50 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400 border-yellow-200 dark:border-yellow-700 hover:bg-yellow-100 dark:hover:bg-yellow-900/50'
                      : 'bg-white dark:bg-gray-700 text-gray-400 dark:text-gray-500 border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 hover:text-yellow-500 dark:hover:text-yellow-400 disabled:opacity-50 disabled:cursor-not-allowed'
                  }`}
                  title={getTooltipText?.({ tax_name: tax.tax_name, tax_rate: String(tax.tax_rate) }) || "Set as my default tax"}
                >
                  <svg 
                    className="w-4 h-4" 
                    fill={isCurrentDefault?.({ tax_name: tax.tax_name, tax_rate: String(tax.tax_rate) }) ? "currentColor" : "none"} 
                    viewBox="0 0 24 24" 
                    stroke="currentColor" 
                    strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                  </svg>
                </button>
              )}

              {/* Remove Button */}
              {formData.taxes.length > 1 && (
                <button
                  type="button"
                  onClick={() => onRemoveTaxLine(index)}
                  className="text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 p-2 rounded-md transition-colors"
                  title="Remove tax line"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Totals Summary */}
      <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-3">Invoice Summary</h3>
        
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600 dark:text-gray-400">Subtotal:</span>
            <span className="font-medium text-gray-900 dark:text-gray-100">${calculatedTotals.subtotal.toFixed(2)}</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-600 dark:text-gray-400">Total Tax:</span>
            <span className="font-medium text-gray-900 dark:text-gray-100">${calculatedTotals.totalTax.toFixed(2)}</span>
          </div>
          
          <div className="border-t border-blue-200 dark:border-blue-700 pt-2">
            <div className="flex justify-between text-lg font-semibold">
              <span className="text-gray-900 dark:text-gray-100">Total Amount:</span>
              <span className="text-blue-600 dark:text-blue-400">${calculatedTotals.grandTotal.toFixed(2)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InvoiceFormFields;
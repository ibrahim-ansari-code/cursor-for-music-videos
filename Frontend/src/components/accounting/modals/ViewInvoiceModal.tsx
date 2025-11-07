import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { XIcon, FileTextIcon, CalendarIcon, DollarSignIcon, BuildingIcon } from 'lucide-react';
import type { Invoice } from '../../../types/accounting';

interface ViewInvoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  invoice: Invoice | null;
}

/**
 * ViewInvoiceModal - Read-only modal for displaying invoice details
 *
 * Displays all invoice information in a clean, organized format:
 * - Invoice number, amount, and status
 * - Property and tenant details
 * - Dates (issue and due)
 * - Taxes breakdown
 * - QuickBooks sync status
 */
const ViewInvoiceModal: React.FC<ViewInvoiceModalProps> = ({
  isOpen,
  onClose,
  invoice,
}) => {
  if (!invoice) return null;

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return isNaN(date.getTime()) ? 'N/A' : date.toLocaleDateString();
  };

  const formatCurrency = (amount?: string | number) => {
    const num = typeof amount === 'string' ? parseFloat(amount) : amount;
    if (num === undefined || isNaN(num)) return '$0.00';
    return `$${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const getStatusColor = (status?: string) => {
    switch (status?.toUpperCase()) {
      case 'PAID':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300';
      case 'PENDING':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300';
      case 'OVERDUE':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';
      case 'CANCELLED':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300';
    }
  };

  // Calculate totals
  const subtotal = parseFloat(invoice.amount || '0');
  const taxTotal = invoice.taxes?.reduce((sum, tax) => {
    const rate = parseFloat(tax.tax_rate || '0');
    return sum + (subtotal * rate / 100);
  }, 0) || 0;
  const total = subtotal + taxTotal;

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black bg-opacity-50 dark:bg-opacity-70 backdrop-blur-sm z-[9999] flex items-center justify-center p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 400 }}
            className="relative w-full max-w-2xl bg-white dark:bg-gray-800 rounded-xl shadow-xl max-h-[90vh] overflow-hidden flex flex-col z-[10000]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="relative px-6 py-4 bg-brand-green dark:bg-gray-700 text-white">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-3">
                    <FileTextIcon className="w-6 h-6" />
                    <div>
                      <h2 className="text-xl font-semibold text-white dark:text-gray-100">
                        Invoice #{invoice.invoice_number}
                      </h2>
                      <div className="flex items-center mt-1 space-x-2">
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(invoice.status)}`}>
                          {invoice.status?.toUpperCase() || 'PENDING'}
                        </span>
                        {invoice.quickbooks_id && (
                          <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">
                            Synced to QuickBooks
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="text-white/70 dark:text-gray-300/70 hover:text-white dark:hover:text-gray-100 hover:bg-white/10 dark:hover:bg-gray-700/50 p-1.5 rounded-lg transition-all"
                >
                  <XIcon className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-900 p-6">
              <div className="space-y-4">
                {/* Amount Section */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700">
                  <div className="flex items-center mb-4">
                    <div className="w-9 h-9 bg-green-50 dark:bg-green-900/20 rounded-lg flex items-center justify-center mr-3">
                      <DollarSignIcon className="w-4 h-4 text-green-600 dark:text-green-400" />
                    </div>
                    <h3 className="text-base font-medium text-gray-900 dark:text-gray-100">Amount Details</h3>
                  </div>

                  <div className="space-y-3">
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-700 dark:text-gray-300">Subtotal:</span>
                      <span className="font-medium text-gray-900 dark:text-gray-100">
                        {formatCurrency(subtotal)}
                      </span>
                    </div>

                    {invoice.taxes && invoice.taxes.length > 0 && (
                      <>
                        {invoice.taxes.map((tax, index) => {
                          const taxAmount = subtotal * (parseFloat(tax.tax_rate || '0') / 100);
                          return (
                            <div key={index} className="flex justify-between items-center text-sm">
                              <span className="text-gray-700 dark:text-gray-300">
                                {tax.tax_name} ({tax.tax_rate}%):
                              </span>
                              <span className="font-medium text-gray-900 dark:text-gray-100">
                                {formatCurrency(taxAmount)}
                              </span>
                            </div>
                          );
                        })}
                      </>
                    )}

                    <div className="border-t border-gray-200 dark:border-gray-600 pt-3 flex justify-between items-center">
                      <span className="text-base font-semibold text-gray-900 dark:text-gray-100">Total:</span>
                      <span className="text-xl font-bold text-green-600 dark:text-green-400">
                        {formatCurrency(total)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Dates Section */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700">
                  <div className="flex items-center mb-4">
                    <div className="w-9 h-9 bg-blue-50 dark:bg-blue-900/20 rounded-lg flex items-center justify-center mr-3">
                      <CalendarIcon className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                    </div>
                    <h3 className="text-base font-medium text-gray-900 dark:text-gray-100">Important Dates</h3>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Issue Date
                      </label>
                      <p className="text-sm text-gray-900 dark:text-gray-100">
                        {formatDate(invoice.issue_date)}
                      </p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Due Date
                      </label>
                      <p className="text-sm text-gray-900 dark:text-gray-100">
                        {formatDate(invoice.due_date)}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Property & Tenant Section */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700">
                  <div className="flex items-center mb-4">
                    <div className="w-9 h-9 bg-purple-50 dark:bg-purple-900/20 rounded-lg flex items-center justify-center mr-3">
                      <BuildingIcon className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                    </div>
                    <h3 className="text-base font-medium text-gray-900 dark:text-gray-100">Property & Tenant</h3>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Property
                      </label>
                      <p className="text-sm text-gray-900 dark:text-gray-100">
                        {invoice.property?.name || 'N/A'}
                      </p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Tenant
                      </label>
                      <p className="text-sm text-gray-900 dark:text-gray-100">
                        {invoice.tenant?.full_name ||
                         (invoice.tenant?.first_name && invoice.tenant?.last_name
                          ? `${invoice.tenant.first_name} ${invoice.tenant.last_name}`
                          : invoice.tenant?.company_name || 'N/A')}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Description Section */}
                {invoice.description && (
                  <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Description
                    </label>
                    <p className="text-sm text-gray-900 dark:text-gray-100 whitespace-pre-wrap">
                      {invoice.description}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-end">
                <button
                  onClick={onClose}
                  className="px-5 py-2.5 bg-gray-600 text-white rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 transition-all text-sm font-medium shadow-sm"
                >
                  Close
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default ViewInvoiceModal;

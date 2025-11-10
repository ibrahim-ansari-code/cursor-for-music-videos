import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { XIcon, FileTextIcon, CalendarIcon, DollarSignIcon, BuildingIcon, UserIcon, HomeIcon } from 'lucide-react';
import type { Lease } from '../../../types/lease';
import { formatDateForDisplay } from '../../../utils/dateHelpers';

interface ViewLeaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  lease: Lease | null;
}

/**
 * ViewLeaseModal - Read-only modal for displaying lease details
 *
 * Displays all lease information in a clean, organized format:
 * - Lease status and dates
 * - Property and unit details
 * - Tenant information
 * - Financial terms (rent, security deposit, late fees)
 * - Special terms and conditions
 */
const ViewLeaseModal: React.FC<ViewLeaseModalProps> = ({
  isOpen,
  onClose,
  lease,
}) => {
  if (!lease) return null;

  const formatCurrency = (amount?: string | number | null) => {
    const num = typeof amount === 'string' ? parseFloat(amount) : amount;
    if (num == null || isNaN(num as number)) return '$0.00';
    return `$${(num as number).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const getStatusColor = (status?: string) => {
    switch (status?.toUpperCase()) {
      case 'ACTIVE':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300';
      case 'PENDING':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300';
      case 'EXPIRED':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';
      case 'TERMINATED':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300';
      case 'RENEWED':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300';
      case 'DRAFT':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300';
    }
  };

  // Calculate lease duration
  const calculateLeaseDuration = () => {
    if (!lease.start_date || !lease.end_date) return 'N/A';
    const start = new Date(lease.start_date);
    const end = new Date(lease.end_date);
    const months = Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24 * 30));
    return `${months} month${months !== 1 ? 's' : ''}`;
  };

  // Get tenant display name
  const getTenantName = () => {
    if (!lease.tenant) return 'N/A';
    return lease.tenant.full_name ||
           (lease.tenant.first_name && lease.tenant.last_name
            ? `${lease.tenant.first_name} ${lease.tenant.last_name}`
            : 'N/A');
  };

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
            className="relative w-full max-w-3xl bg-white dark:bg-gray-800 rounded-xl shadow-xl max-h-[90vh] overflow-hidden flex flex-col z-[10000]"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="view-lease-modal-title"
            aria-describedby="view-lease-modal-description"
          >
            {/* Header */}
            <div className="relative px-6 py-4 bg-brand-green dark:bg-gray-700 text-white">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-3">
                    <FileTextIcon className="w-6 h-6" />
                    <div>
                      <h2 id="view-lease-modal-title" className="text-xl font-semibold text-white dark:text-gray-100">
                        Lease Agreement
                      </h2>
                      <p id="view-lease-modal-description" className="text-sm text-white/80 dark:text-gray-300 mt-0.5">
                        Lease #{lease.id}
                      </p>
                      <div className="flex items-center mt-1 space-x-2">
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(lease.status)}`}>
                          {lease.status?.toUpperCase() || 'DRAFT'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="text-white/70 dark:text-gray-300/70 hover:text-white dark:hover:text-gray-100 hover:bg-white/10 dark:hover:bg-gray-700/50 p-1.5 rounded-lg transition-all"
                  aria-label="Close"
                >
                  <XIcon className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-900 p-6">
              <div className="space-y-4">
                {/* Property & Unit Section */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700">
                  <div className="flex items-center mb-4">
                    <div className="w-9 h-9 bg-purple-50 dark:bg-purple-900/20 rounded-lg flex items-center justify-center mr-3">
                      <BuildingIcon className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                    </div>
                    <h3 className="text-base font-medium text-gray-900 dark:text-gray-100">Property Details</h3>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Property
                      </label>
                      <p className="text-sm text-gray-900 dark:text-gray-100">
                        {lease.property?.name || 'N/A'}
                      </p>
                      {lease.property?.address && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                          {lease.property.address}
                          {lease.property.city && `, ${lease.property.city}`}
                          {lease.property.province && `, ${lease.property.province}`}
                        </p>
                      )}
                    </div>
                    {lease.unit && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Unit
                        </label>
                        <div className="flex items-center space-x-2">
                          <HomeIcon className="w-4 h-4 text-gray-400" />
                          <p className="text-sm text-gray-900 dark:text-gray-100">
                            {lease.unit.name}
                          </p>
                        </div>
                        {(lease.unit.bedrooms || lease.unit.bathrooms) && (
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                            {lease.unit.bedrooms && `${lease.unit.bedrooms} bed`}
                            {lease.unit.bedrooms && lease.unit.bathrooms && ' • '}
                            {lease.unit.bathrooms && `${lease.unit.bathrooms} bath`}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Tenant Section */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700">
                  <div className="flex items-center mb-4">
                    <div className="w-9 h-9 bg-blue-50 dark:bg-blue-900/20 rounded-lg flex items-center justify-center mr-3">
                      <UserIcon className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                    </div>
                    <h3 className="text-base font-medium text-gray-900 dark:text-gray-100">Tenant Information</h3>
                  </div>

                  <div className="space-y-2">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Name
                      </label>
                      <p className="text-sm text-gray-900 dark:text-gray-100">
                        {getTenantName()}
                      </p>
                    </div>
                    {lease.tenant?.email && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Email
                        </label>
                        <p className="text-sm text-gray-900 dark:text-gray-100">
                          {lease.tenant.email}
                        </p>
                      </div>
                    )}
                    {lease.tenant?.phone && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Phone
                        </label>
                        <p className="text-sm text-gray-900 dark:text-gray-100">
                          {lease.tenant.phone}
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Lease Period Section */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700">
                  <div className="flex items-center mb-4">
                    <div className="w-9 h-9 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg flex items-center justify-center mr-3">
                      <CalendarIcon className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                    </div>
                    <h3 className="text-base font-medium text-gray-900 dark:text-gray-100">Lease Period</h3>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Start Date
                      </label>
                      <p className="text-sm text-gray-900 dark:text-gray-100">
                        {formatDateForDisplay(lease.start_date)}
                      </p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        End Date
                      </label>
                      <p className="text-sm text-gray-900 dark:text-gray-100">
                        {formatDateForDisplay(lease.end_date)}
                      </p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Duration
                      </label>
                      <p className="text-sm text-gray-900 dark:text-gray-100">
                        {calculateLeaseDuration()}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Financial Terms Section */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700">
                  <div className="flex items-center mb-4">
                    <div className="w-9 h-9 bg-green-50 dark:bg-green-900/20 rounded-lg flex items-center justify-center mr-3">
                      <DollarSignIcon className="w-4 h-4 text-green-600 dark:text-green-400" />
                    </div>
                    <h3 className="text-base font-medium text-gray-900 dark:text-gray-100">Financial Terms</h3>
                  </div>

                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Monthly Rent
                        </label>
                        <p className="text-lg font-semibold text-green-600 dark:text-green-400">
                          {formatCurrency(lease.monthly_rent)}
                        </p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Security Deposit
                        </label>
                        <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                          {formatCurrency(lease.security_deposit)}
                        </p>
                      </div>
                    </div>

                    {lease.rent_due_day && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Rent Due Day
                        </label>
                        <p className="text-sm text-gray-900 dark:text-gray-100">
                          Day {lease.rent_due_day} of each month
                        </p>
                      </div>
                    )}

                    {(lease.late_fee_amount || lease.late_fee_after_days) && (
                      <div className="pt-3 border-t border-gray-200 dark:border-gray-600">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Late Fee Policy
                        </label>
                        <div className="flex items-start space-x-2 text-sm text-gray-700 dark:text-gray-300">
                          <span className="text-amber-600 dark:text-amber-400 font-medium">
                            {formatCurrency(lease.late_fee_amount)}
                          </span>
                          {lease.late_fee_after_days && (
                            <span>
                              after {lease.late_fee_after_days} day{lease.late_fee_after_days !== 1 ? 's' : ''}
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Additional Terms Section */}
                {(lease.is_renewable !== undefined || lease.auto_renew !== undefined || lease.special_terms) && (
                  <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                      Additional Terms
                    </label>

                    <div className="space-y-2">
                      {lease.is_renewable !== undefined && (
                        <div className="flex items-center text-sm">
                          <span className="w-32 text-gray-700 dark:text-gray-300">Renewable:</span>
                          <span className={`font-medium ${lease.is_renewable ? 'text-green-600 dark:text-green-400' : 'text-gray-900 dark:text-gray-100'}`}>
                            {lease.is_renewable ? 'Yes' : 'No'}
                          </span>
                        </div>
                      )}
                      {lease.auto_renew !== undefined && (
                        <div className="flex items-center text-sm">
                          <span className="w-32 text-gray-700 dark:text-gray-300">Auto-Renew:</span>
                          <span className={`font-medium ${lease.auto_renew ? 'text-green-600 dark:text-green-400' : 'text-gray-900 dark:text-gray-100'}`}>
                            {lease.auto_renew ? 'Yes' : 'No'}
                          </span>
                        </div>
                      )}
                      {lease.special_terms && (
                        <div className="pt-2 border-t border-gray-200 dark:border-gray-600">
                          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                            Special Terms & Conditions
                          </label>
                          <p className="text-sm text-gray-900 dark:text-gray-100 whitespace-pre-wrap">
                            {lease.special_terms}
                          </p>
                        </div>
                      )}
                    </div>
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

export default ViewLeaseModal;

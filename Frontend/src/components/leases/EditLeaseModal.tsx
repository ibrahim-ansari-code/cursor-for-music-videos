import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-toastify';
import * as Sentry from '@sentry/react';
import { useUpdateLease } from '../../hooks/useLeasesQueries';
import {
  Label,
  Input,
  TextArea,
  Button,
  ErrorMessage,
} from '../ui/SharedModalComponents';
import { getTenantDisplayName } from '../../utils/tenantUtils';
import type { Lease, LeaseUpdate } from '../../types/lease';

const MIN_RENT_DUE_DAY = 1;
const MAX_RENT_DUE_DAY = 28;

interface EditLeaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  lease: Lease | null;
  onLeaseUpdated: (lease: Lease) => void;
}

interface FormData {
  start_date: string;
  end_date: string;
  monthly_rent: string;
  security_deposit: string;
  rent_due_day: string;
  late_fee_amount: string;
  late_fee_after_days: string;
  special_terms: string;
}

const EditLeaseModal: React.FC<EditLeaseModalProps> = ({
  isOpen,
  onClose,
  lease,
  onLeaseUpdated,
}) => {
  const updateLeaseMutation = useUpdateLease();

  const [formData, setFormData] = useState<FormData>({
    start_date: '',
    end_date: '',
    monthly_rent: '',
    security_deposit: '',
    rent_due_day: '',
    late_fee_amount: '',
    late_fee_after_days: '',
    special_terms: '',
  });
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Initialize form data when lease changes
  useEffect(() => {
    if (lease && isOpen) {
      setFormData({
        start_date: lease.start_date
          ? new Date(lease.start_date).toISOString().split('T')[0]
          : '',
        end_date: lease.end_date
          ? new Date(lease.end_date).toISOString().split('T')[0]
          : '',
        monthly_rent: lease.monthly_rent?.toString() || '',
        security_deposit: lease.security_deposit?.toString() || '',
        rent_due_day: lease.rent_due_day?.toString() || '',
        late_fee_amount: lease.late_fee_amount?.toString() || '',
        late_fee_after_days: lease.late_fee_after_days?.toString() || '',
        special_terms: lease.special_terms || '',
      });
      setError(null);
    }
  }, [lease, isOpen]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lease) return;

    setIsLoading(true);
    setError(null);

    // Validate rent_due_day
    const rentDueDay = parseInt(formData.rent_due_day, 10);
    if (
      formData.rent_due_day &&
      (isNaN(rentDueDay) ||
        rentDueDay < MIN_RENT_DUE_DAY ||
        rentDueDay > MAX_RENT_DUE_DAY)
    ) {
      setError(
        `Rent due day must be between ${MIN_RENT_DUE_DAY} and ${MAX_RENT_DUE_DAY}.`
      );
      setIsLoading(false);
      return;
    }

    const parseFloatOrNull = (value: string): number | null => {
      const parsed = parseFloat(value);
      return isNaN(parsed) ? null : parsed;
    };


    const parseIntOrNull = (value: string): number | null => {
      const parsed = parseInt(value, 10);
      return isNaN(parsed) ? null : parsed;
    };

    const updateData: LeaseUpdate = {
      start_date: formData.start_date || undefined,
      end_date: formData.end_date || undefined,
      monthly_rent: parseFloatOrNull(formData.monthly_rent) ?? undefined,
      security_deposit: parseFloatOrNull(formData.security_deposit) ?? undefined,
      rent_due_day: rentDueDay || undefined,
      late_fee_amount: parseFloatOrNull(formData.late_fee_amount),
      late_fee_after_days: parseIntOrNull(formData.late_fee_after_days),
      special_terms: formData.special_terms || null,
    };

    try {
      Sentry.logger.info('Updating lease', {
        leaseId: lease.id,
        changedFields: Object.keys(updateData),
      });

      const updatedLease = await updateLeaseMutation.mutateAsync({
        leaseId: lease.id,
        leaseData: updateData,
      });

      Sentry.logger.info('Lease updated successfully', {
        leaseId: lease.id,
      });

      toast.success('Lease updated successfully!');
      onClose();

      try {
        onLeaseUpdated(updatedLease);
      } catch (callbackError) {
        Sentry.logger.error('Error in onLeaseUpdated callback', {
          error:
            callbackError instanceof Error
              ? callbackError.message
              : 'Unknown error',
          leaseId: lease.id,
        });
      }
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to update lease';

      Sentry.logger.error('Failed to update lease', {
        error: errorMessage,
        leaseId: lease.id,
      });

      Sentry.captureException(err, {
        tags: {
          component: 'EditLeaseModal',
          action: 'update_lease',
          feature: 'leases',
        },
        contexts: {
          lease: {
            leaseId: lease.id,
            propertyId: lease.property_id,
            tenantId: lease.tenant_id,
          },
        },
      });

      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen || !lease) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm z-[9999] flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="relative w-full max-w-3xl bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-h-[90vh] overflow-hidden flex flex-col z-[10000]"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Edit Lease
            </h2>
            <button
              onClick={onClose}
              type="button"
              aria-label="Close"
              className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 rounded-full p-1"
            >
              <svg
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                role="img"
              >
                <title>Close modal</title>
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* Form Area */}
          <form onSubmit={handleSubmit} className="flex flex-col flex-1 overflow-hidden">
            <div className="flex-1 overflow-y-auto p-6 bg-white dark:bg-gray-800">
              {error && <ErrorMessage message={error} />}

              {/* Property & Tenant Info (Read-only) */}
              <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">
                  Property & Tenant (Read-only)
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <Label>Property</Label>
                    <Input
                      value={lease.property?.name || 'N/A'}
                      disabled
                      className="bg-gray-100 dark:bg-gray-800"
                    />
                  </div>
                  <div>
                    <Label>Unit</Label>
                    <Input
                      value={lease.unit?.name || 'N/A'}
                      disabled
                      className="bg-gray-100 dark:bg-gray-800"
                    />
                  </div>
                  <div>
                    <Label>Tenant</Label>
                    <Input
                      value={getTenantDisplayName(lease.tenant, 'N/A')}
                      disabled
                      className="bg-gray-100 dark:bg-gray-800"
                    />
                  </div>
                </div>
              </div>

              {/* Lease Terms */}
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Lease Terms
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="start_date" required>
                      Start Date
                    </Label>
                    <Input
                      name="start_date"
                      id="start_date"
                      type="date"
                      value={formData.start_date}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="end_date" required>
                      End Date
                    </Label>
                    <Input
                      name="end_date"
                      id="end_date"
                      type="date"
                      value={formData.end_date}
                      onChange={handleChange}
                      required
                    />
                  </div>
                </div>
              </div>

              {/* Financial Terms */}
              <div className="space-y-4 mt-6">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Financial Terms
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="monthly_rent" required>
                      Monthly Rent ($)
                    </Label>
                    <Input
                      name="monthly_rent"
                      id="monthly_rent"
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="e.g., 1500.00"
                      value={formData.monthly_rent}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="security_deposit">Security Deposit ($)</Label>
                    <Input
                      name="security_deposit"
                      id="security_deposit"
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="e.g., 1500.00"
                      value={formData.security_deposit}
                      onChange={handleChange}
                    />
                  </div>
                </div>
              </div>

              {/* Rent Collection & Fees */}
              <div className="space-y-4 mt-6">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Rent Collection & Late Fees
                </h3>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label htmlFor="rent_due_day">Rent Due Day (1-28)</Label>
                    <Input
                      name="rent_due_day"
                      id="rent_due_day"
                      type="number"
                      min={MIN_RENT_DUE_DAY}
                      max={MAX_RENT_DUE_DAY}
                      placeholder="e.g., 1"
                      value={formData.rent_due_day}
                      onChange={handleChange}
                    />
                  </div>
                  <div>
                    <Label htmlFor="late_fee_amount">Late Fee ($)</Label>
                    <Input
                      name="late_fee_amount"
                      id="late_fee_amount"
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="e.g., 50.00"
                      value={formData.late_fee_amount}
                      onChange={handleChange}
                    />
                  </div>
                  <div>
                    <Label htmlFor="late_fee_after_days">Late After (Days)</Label>
                    <Input
                      name="late_fee_after_days"
                      id="late_fee_after_days"
                      type="number"
                      min="1"
                      placeholder="e.g., 5"
                      value={formData.late_fee_after_days}
                      onChange={handleChange}
                    />
                  </div>
                </div>
              </div>

              {/* Special Terms */}
              <div className="space-y-4 mt-6">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Additional Information
                </h3>
                <div>
                  <Label htmlFor="special_terms">Special Terms / Notes</Label>
                  <TextArea
                    name="special_terms"
                    id="special_terms"
                    rows={3}
                    placeholder="Enter any special terms or notes for this lease..."
                    value={formData.special_terms}
                    onChange={handleChange}
                  />
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700 border-t border-gray-200 dark:border-gray-600 flex justify-end space-x-3">
              <Button
                type="button"
                variant="secondary"
                onClick={onClose}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                disabled={isLoading}
                isLoading={isLoading}
              >
                Save Changes
              </Button>
            </div>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default EditLeaseModal;

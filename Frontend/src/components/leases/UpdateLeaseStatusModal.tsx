import React, { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { motion } from 'framer-motion';
import { toast } from 'react-toastify';
import * as Sentry from '@sentry/react';
import { X, RefreshCw, CheckCircle2 } from 'lucide-react';
import { useUpdateLeaseStatus } from '../../hooks/useLeasesQueries';
import type { Lease } from '../../types/lease';
import { LeaseStatus } from '../../types/lease';

interface UpdateLeaseStatusModalProps {
  isOpen: boolean;
  onClose: () => void;
  lease: Lease;
  onUpdate?: () => void;
}

const STATUS_OPTIONS: { value: LeaseStatus; label: string; color: string }[] = [
  { value: LeaseStatus.DRAFT, label: 'Draft', color: 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 border-gray-300 dark:border-gray-600' },
  { value: LeaseStatus.PENDING, label: 'Pending', color: 'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-200 border-yellow-300 dark:border-yellow-700' },
  { value: LeaseStatus.ACTIVE, label: 'Active', color: 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-200 border-green-300 dark:border-green-700' },
  { value: LeaseStatus.EXPIRED, label: 'Expired', color: 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200 border-red-300 dark:border-red-700' },
  { value: LeaseStatus.TERMINATED, label: 'Terminated', color: 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200 border-red-300 dark:border-red-700' },
  { value: LeaseStatus.RENEWED, label: 'Renewed', color: 'bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200 border-blue-300 dark:border-blue-700' },
];

const UpdateLeaseStatusModal: React.FC<UpdateLeaseStatusModalProps> = ({
  isOpen,
  onClose,
  lease,
  onUpdate,
}) => {
  const [selectedStatus, setSelectedStatus] = useState<LeaseStatus | null>(null);
  const updateStatusMutation = useUpdateLeaseStatus();

  const handleClose = () => {
    setSelectedStatus(null);
    onClose();
  };

  const handleStatusChange = async (newStatus: LeaseStatus) => {
    if (!lease || lease.status.toUpperCase() === newStatus) return;

    setSelectedStatus(newStatus);

    try {
      await updateStatusMutation.mutateAsync({
        leaseId: lease.id,
        status: newStatus,
      });

      toast.success(`Lease status updated to ${newStatus.toLowerCase()}`);
      
      if (onUpdate) {
        onUpdate();
      }
      
      handleClose();
    } catch (err: any) {
      console.error('Error updating lease status:', err);
      
      const errorMessage =
        err?.data?.detail ||
        err?.message ||
        'Failed to update lease status. Please try again.';
      
      toast.error(errorMessage);
      
      Sentry.captureException(err, {
        tags: {
          component: 'UpdateLeaseStatusModal',
          action: 'update_lease_status',
          feature: 'leases',
        },
        contexts: {
          lease: {
            id: lease.id,
            current_status: lease.status,
            new_status: newStatus,
          },
        },
      });
    } finally {
      setSelectedStatus(null);
    }
  };

  const getCurrentStatusConfig = () => {
    const foundOption = STATUS_OPTIONS.find(
      (option) => option.value === lease.status.toUpperCase()
    );

    if (foundOption) {
      return foundOption;
    }

    // Fallback for unknown status - return generic configuration
    return {
      value: lease.status as LeaseStatus,
      label: lease.status.charAt(0).toUpperCase() + lease.status.slice(1).toLowerCase(),
      color: 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 border-gray-300 dark:border-gray-600',
    };
  };

  const currentStatus = getCurrentStatusConfig();

  return (
    <Dialog.Root open={isOpen} onOpenChange={handleClose}>
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
            className="w-[90vw] max-w-md bg-white dark:bg-gray-800 rounded-2xl shadow-2xl overflow-hidden"
          >
            {/* Clean Header matching NewExpenseModal */}
            <div className="relative bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                    <RefreshCw className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <Dialog.Title className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                      Update Lease Status
                    </Dialog.Title>
                    <Dialog.Description className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                      Change the status of this lease
                    </Dialog.Description>
                  </div>
                </div>
                <Dialog.Close asChild>
                  <button
                    className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                    disabled={updateStatusMutation.isPending}
                    aria-label="Close"
                  >
                    <X className="h-5 w-5 text-gray-500 dark:text-gray-400" />
                  </button>
                </Dialog.Close>
              </div>
            </div>

            {/* Content area */}
            <motion.div
              className="p-6 bg-gray-50/50 dark:bg-gray-800/50 space-y-5"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 }}
            >
              {/* Current Status Display */}
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <CheckCircle2 className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Current Status:
                    </span>
                  </div>
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${currentStatus.color}`}>
                    {currentStatus.label}
                  </span>
                </div>
              </div>

              {/* Status Options */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Change status to:
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {STATUS_OPTIONS.map((option) => {
                    const isCurrent = lease.status.toUpperCase() === option.value;
                    const isSelected = selectedStatus === option.value;
                    const isDisabled = updateStatusMutation.isPending || isCurrent;

                    return (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => handleStatusChange(option.value)}
                        disabled={isDisabled}
                        className={`relative px-4 py-3 text-sm font-medium rounded-lg transition-all border-2 ${
                          isCurrent
                            ? 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                            : isSelected
                            ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-500 dark:border-blue-400 text-blue-700 dark:text-blue-300'
                            : 'bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20'
                        }`}
                      >
                        {option.label}
                        {isCurrent && (
                          <span className="absolute top-1 right-1">
                            <CheckCircle2 className="h-4 w-4 text-gray-400 dark:text-gray-500" />
                          </span>
                        )}
                        {isSelected && updateStatusMutation.isPending && (
                          <div className="absolute inset-0 flex items-center justify-center bg-blue-50/80 dark:bg-blue-900/40 rounded-lg">
                            <div className="w-4 h-4 border-2 border-blue-600 dark:border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            </motion.div>

            {/* Clean Footer */}
            <div className="border-t border-gray-200 dark:border-gray-700 px-6 py-3 flex justify-end items-center bg-white dark:bg-gray-800">
              <button
                type="button"
                onClick={handleClose}
                disabled={updateStatusMutation.isPending}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800 disabled:opacity-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};

export default UpdateLeaseStatusModal;


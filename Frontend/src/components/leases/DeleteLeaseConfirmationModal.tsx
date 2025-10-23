import React, { useState, useEffect } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { motion } from 'framer-motion';
import * as Sentry from '@sentry/react';
import { X, AlertTriangle, Trash2 } from 'lucide-react';
import type { LeaseWithDocuments } from '../../types/lease';

interface DeleteLeaseConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  lease: LeaseWithDocuments;
  onConfirm: () => Promise<void>;
}

const DeleteLeaseConfirmationModal: React.FC<DeleteLeaseConfirmationModalProps> = ({
  isOpen,
  onClose,
  lease,
  onConfirm,
}) => {
  const [confirmText, setConfirmText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [countdown, setCountdown] = useState(3);

  // Security: Countdown timer before delete button is enabled (prevents accidental clicks)
  useEffect(() => {
    if (!isOpen) {
      setCountdown(3);
      return;
    }

    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [isOpen, countdown]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setConfirmText('');
      setIsDeleting(false);
      setCountdown(3);
    }
  }, [isOpen]);

  const handleClose = () => {
    if (isDeleting) return; // Prevent closing during deletion
    Sentry.logger.debug('User cancelled lease deletion via modal close', { 
      leaseId: lease.id 
    });
    onClose();
  };

  const handleConfirm = async () => {
    if (isDeleting) return; // Prevent double-click

    Sentry.startSpan(
      {
        op: 'lease.delete.confirm',
        name: 'Delete Lease Confirmation',
      },
      async (span) => {
        span.setAttribute('leaseId', lease.id);
        span.setAttribute('confirmationMethod', 'typed_confirmation');

        setIsDeleting(true);

        try {
          await onConfirm();
          onClose();
        } catch (error) {
          Sentry.logger.error('Deletion failed in confirmation modal', {
            error: error instanceof Error ? error.message : String(error),
            leaseId: lease.id,
          });
        } finally {
          setIsDeleting(false);
        }
      }
    );
  };

  const getTenantName = () => {
    const { tenant } = lease;
    if (!tenant) return 'No tenant assigned';
    if (tenant.full_name) return tenant.full_name;
    if (tenant.first_name || tenant.last_name) {
      return `${tenant.first_name || ''} ${tenant.last_name || ''}`.trim();
    }
    return `Tenant #${tenant.id}`;
  };

  const expectedConfirmText = `delete-${lease.id}`;
  const isConfirmValid = confirmText.trim().toLowerCase() === expectedConfirmText.toLowerCase();
  const canDelete = isConfirmValid && countdown === 0;

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
            {/* Header with warning styling */}
            <div className="relative bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-700 px-6 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
                    <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
                  </div>
                  <div>
                    <Dialog.Title className="text-lg font-semibold text-red-900 dark:text-red-100">
                      Delete Lease
                    </Dialog.Title>
                    <Dialog.Description className="text-sm text-red-700 dark:text-red-300 mt-0.5">
                      This action cannot be undone
                    </Dialog.Description>
                  </div>
                </div>
                <Dialog.Close asChild>
                  <button
                    className="p-1.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors disabled:opacity-50"
                    disabled={isDeleting}
                    aria-label="Close"
                  >
                    <X className="h-5 w-5 text-red-600 dark:text-red-400" />
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
              {/* Warning Message */}
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <Trash2 className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-red-900 dark:text-red-100 mb-2">
                      You are about to permanently delete this lease:
                    </p>
                    <div className="space-y-1 text-sm text-red-800 dark:text-red-200">
                      <p><strong>Tenant:</strong> {getTenantName()}</p>
                      <p><strong>Property:</strong> {lease.property?.name || `Property #${lease.property_id}`}</p>
                      {lease.unit && <p><strong>Unit:</strong> {lease.unit.name}</p>}
                      <p><strong>Monthly Rent:</strong> ${Number(lease.monthly_rent).toFixed(2)}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Consequences */}
              <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg p-4">
                <p className="text-sm font-medium text-yellow-900 dark:text-yellow-100 mb-2">
                  ⚠️ Consequences:
                </p>
                <ul className="text-sm text-yellow-800 dark:text-yellow-200 space-y-1 list-disc list-inside">
                  <li>Associated payment records will be kept but unlinked</li>
                  <li>Lease documents will be permanently removed</li>
                  <li>This action cannot be reversed</li>
                </ul>
              </div>

              {/* Confirmation Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Type <code className="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-red-600 dark:text-red-400 font-mono text-xs">
                    {expectedConfirmText}
                  </code> to confirm:
                </label>
                <input
                  type="text"
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  placeholder={expectedConfirmText}
                  disabled={isDeleting}
                  className="block w-full px-4 py-2.5 text-sm bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-red-500 focus:border-red-500 dark:focus:ring-red-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-mono"
                  autoComplete="off"
                  autoFocus
                />
                {confirmText && !isConfirmValid && (
                  <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                    Text doesn't match. Please type exactly: {expectedConfirmText}
                  </p>
                )}
              </div>
            </motion.div>

            {/* Footer with countdown protection */}
            <div className="border-t border-gray-200 dark:border-gray-700 px-6 py-3 flex justify-between items-center bg-white dark:bg-gray-800">
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {countdown > 0 && (
                  <span>Delete enabled in {countdown}s...</span>
                )}
              </div>
              <div className="flex items-center space-x-3">
                <button
                  type="button"
                  onClick={handleClose}
                  disabled={isDeleting}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 dark:focus:ring-offset-gray-800 disabled:opacity-50 transition-colors"
                >
                  Cancel
                </button>

                <button
                  type="button"
                  onClick={handleConfirm}
                  disabled={!canDelete || isDeleting}
                  className={`px-5 py-2 text-sm font-medium text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 dark:focus:ring-offset-gray-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 ${
                    isDeleting || !canDelete
                      ? 'bg-gray-400 dark:bg-gray-600'
                      : 'bg-red-600 dark:bg-red-700 hover:bg-red-700 dark:hover:bg-red-600'
                  }`}
                  title={!canDelete ? 'Type confirmation text and wait for countdown' : 'Delete lease'}
                >
                  {isDeleting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>Deleting...</span>
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4" />
                      <span>Delete Lease</span>
                    </>
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

export default DeleteLeaseConfirmationModal;


/**
 * SetupAutopayModal Component
 * Modal for tenants to enroll in automatic rent payments
 */

import React, { useState, useEffect, useRef } from 'react';
import { FaInfoCircle } from 'react-icons/fa';
import { motion, AnimatePresence } from 'framer-motion';
import { useEnrollAutopay, useAutopayStatus, useCancelAutopay } from '@/hooks/usePayments';
import type { SavedPaymentMethod } from '@/types/payments';

interface SetupAutopayModalProps {
  isOpen: boolean;
  onClose: () => void;
  savedPaymentMethods: SavedPaymentMethod[];
  leaseId: number | undefined;
}

const SetupAutopayModal: React.FC<SetupAutopayModalProps> = ({
  isOpen,
  onClose,
  savedPaymentMethods,
  leaseId,
}) => {
  const { data: autopayStatus } = useAutopayStatus(leaseId);
  const enrollAutopay = useEnrollAutopay();
  const cancelAutopay = useCancelAutopay();
  
  const [selectedPaymentMethodId, setSelectedPaymentMethodId] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState(false);

  const isEnrolled = autopayStatus?.is_enrolled && autopayStatus?.is_active;

  const handleEnroll = async () => {
    if (!selectedPaymentMethodId || !leaseId) {
      return;
    }

    setIsProcessing(true);
    enrollAutopay.mutate(
      {
        leaseId: leaseId,
        paymentMethodId: selectedPaymentMethodId,
      },
      {
        onSuccess: () => {
          setIsProcessing(false);
          onClose();
        },
        onError: () => {
          setIsProcessing(false);
        },
      }
    );
  };

  const handleCancel = async () => {
    if (!leaseId) return;
    
    setIsProcessing(true);
    cancelAutopay.mutate(leaseId, {
      onSuccess: () => {
        setIsProcessing(false);
        onClose();
      },
      onError: () => {
        setIsProcessing(false);
      },
    });
  };

  // Pre-select default payment method or first available
  React.useEffect(() => {
    if (savedPaymentMethods.length > 0 && !selectedPaymentMethodId) {
      const defaultMethod = savedPaymentMethods.find((m) => m.is_default);
      setSelectedPaymentMethodId(
        defaultMethod?.id || savedPaymentMethods[0].id
      );
    }
  }, [savedPaymentMethods, selectedPaymentMethodId]);

  const modalRef = useRef<HTMLDivElement>(null);

  // Handle Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
    }
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm overflow-y-auto h-full w-full z-9999 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          ref={modalRef}
          className="relative w-full max-w-lg bg-white rounded-xl shadow-2xl flex flex-col overflow-hidden max-h-[calc(100vh-4rem)] z-10000"
        >
          {/* Header */}
          <div className="sticky top-0 z-10 px-6 py-4 bg-white border-b border-gray-200 flex justify-between items-center shrink-0">
            <div>
              <h2 id="modal-title" className="text-xl font-semibold text-gray-900">
                {isEnrolled ? 'Manage Autopay' : 'Set Up Autopay'}
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                {isEnrolled
                  ? 'Update or cancel your automatic rent payments'
                  : 'Never miss a payment with automatic rent payments'}
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-teal focus:ring-offset-2 rounded-full p-1 transition-colors duration-200"
              aria-label="Close modal"
            >
              <svg
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* Body */}
          <div className="p-6 grow overflow-y-auto space-y-6">
          {/* Current Autopay Status */}
          {isEnrolled && autopayStatus?.payment_method && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start">
                <FaInfoCircle className="text-green-600 mt-0.5 mr-2 shrink-0" />
                <div className="text-sm text-green-800">
                  <p className="font-medium mb-1">Autopay is active</p>
                  <p>
                    Your rent will be automatically paid on day of each month using{' '}
                    <strong>
                      {autopayStatus.payment_method.payment_method_type === 'acss_debit' 
                        ? 'Bank Account' 
                        : 'Card'}{' '}
                      ending in {autopayStatus.payment_method.last_four || 'N/A'}
                    </strong>
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* No Payment Methods */}
          {savedPaymentMethods.length === 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-start">
                <FaInfoCircle className="text-yellow-600 mt-0.5 mr-2 shrink-0" />
                <div className="text-sm text-yellow-800">
                  <p className="font-medium mb-1">No payment methods available</p>
                  <p>Please add a payment method before setting up autopay.</p>
                </div>
              </div>
            </div>
          )}

          {/* Autopay Setup Form */}
          {!isEnrolled && savedPaymentMethods.length > 0 && (
            <>
              {/* Info Banner */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start">
                  <FaInfoCircle className="text-blue-600 mt-0.5 mr-2 shrink-0" />
                  <div className="text-sm text-blue-800">
                    <p className="font-medium mb-1">How Autopay Works</p>
                    <ul className="list-disc list-inside space-y-1">
                      <li>Your rent will be automatically charged each month</li>
                      <li>You'll receive a notification after each payment</li>
                      <li>You can cancel anytime</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Payment Method Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Payment Method
                </label>
                <select
                  value={selectedPaymentMethodId}
                  onChange={(e) => setSelectedPaymentMethodId(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-teal focus:border-brand-teal"
                >
                  {savedPaymentMethods.map((method) => (
                    <option key={method.id} value={method.id}>
                      {method.payment_method_type === 'acss_debit'
                        ? `Bank Account (${method.bank_name || 'Bank'}) •••• ${method.last_four}`
                        : `${method.brand || 'Card'} •••• ${method.last_four}`}
                      {method.is_default ? ' (Default)' : ''}
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}

          {/* Action Buttons */}
          <div className="flex space-x-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isProcessing}
              className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
            >
              {isEnrolled ? 'Close' : 'Cancel'}
            </button>

            {isEnrolled ? (
              <button
                type="button"
                onClick={handleCancel}
                disabled={isProcessing}
                className="flex-1 px-4 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors flex items-center justify-center"
              >
                {isProcessing ? (
                  <>
                    <svg
                      className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Cancelling...
                  </>
                ) : (
                  'Cancel Autopay'
                )}
              </button>
            ) : (
              <button
                type="button"
                onClick={handleEnroll}
                disabled={isProcessing || savedPaymentMethods.length === 0 || !selectedPaymentMethodId}
                className="flex-1 px-4 py-3 bg-brand-teal text-white rounded-lg hover:bg-brand-green disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors flex items-center justify-center"
              >
                {isProcessing ? (
                  <>
                    <svg
                      className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Enrolling...
                  </>
                ) : (
                  'Enable Autopay'
                )}
              </button>
            )}
          </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default SetupAutopayModal;


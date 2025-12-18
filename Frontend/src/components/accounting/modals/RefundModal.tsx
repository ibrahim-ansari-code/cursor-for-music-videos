/**
 * RefundModal Component
 * 
 * Modal for issuing full or partial refunds for Stripe rent payments.
 * Supports custom amounts, refund reasons, and platform fee refunding.
 */

import React, { useState, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { toast } from 'react-toastify';
import * as Sentry from '@sentry/react';
import { useCreateRefund } from '../../../hooks/useAccountingQueries';
import type { Payment, RefundReason } from '../../../types/rentPayments';

interface RefundModalProps {
  isOpen: boolean;
  onClose: () => void;
  payment: Payment | null;
  onSuccess?: () => void;
}

type RefundStep = 'amount' | 'details' | 'confirm';

const REFUND_REASONS: Array<{ value: RefundReason; label: string; description: string }> = [
  { value: 'duplicate', label: 'Duplicate Payment', description: 'Payment was processed twice' },
  { value: 'fraudulent', label: 'Fraudulent', description: 'Suspected fraud or unauthorized charge' },
  { value: 'requested_by_customer', label: 'Tenant Requested', description: 'Tenant requested a refund' },
  { value: 'rent_adjustment', label: 'Rent Adjustment', description: 'Rent amount was incorrect' },
  { value: 'lease_cancellation', label: 'Lease Cancellation', description: 'Lease was terminated early' },
  { value: 'overpayment', label: 'Overpayment', description: 'Tenant paid more than required' },
  { value: 'other', label: 'Other', description: 'Other reason' },
];

const RefundModal: React.FC<RefundModalProps> = ({ isOpen, onClose, payment, onSuccess }) => {
  const [step, setStep] = useState<RefundStep>('amount');
  const [refundType, setRefundType] = useState<'full' | 'partial'>('full');
  const [customAmount, setCustomAmount] = useState<string>('');
  const [reason, setReason] = useState<RefundReason>('requested_by_customer');
  const [notes, setNotes] = useState<string>('');
  
  const createRefundMutation = useCreateRefund();

  // Reset form when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setStep('amount');
      setRefundType('full');
      setCustomAmount('');
      setReason('requested_by_customer');
      setNotes('');
    }
  }, [isOpen]);

  if (!payment) return null;

  const paymentAmount = typeof payment.amount === 'number' ? payment.amount : parseFloat(payment.amount as string) || 0;
  const refundAmountDollars = refundType === 'full' 
    ? paymentAmount 
    : parseFloat(customAmount) || 0;
  const refundAmountCents = Math.round(refundAmountDollars * 100);

  // Validation
  const isValidAmount = refundType === 'full' || (
    refundAmountDollars > 0 && 
    refundAmountDollars <= paymentAmount
  );

  const handleNext = () => {
    if (step === 'amount') {
      if (!isValidAmount) {
        toast.error('Please enter a valid refund amount');
        return;
      }
      setStep('details');
    } else if (step === 'details') {
      setStep('confirm');
    }
  };

  const handleBack = () => {
    if (step === 'details') {
      setStep('amount');
    } else if (step === 'confirm') {
      setStep('details');
    }
  };

  const handleSubmit = async () => {
    if (!payment.stripe_payment_intent_id) {
      toast.error('Cannot refund: Missing Stripe payment information');
      return;
    }

    try {
      await createRefundMutation.mutateAsync({
        transaction_id: payment.stripe_payment_intent_id,
        amount_cents: refundAmountCents,
        reason,
        notes: notes || undefined,
        refund_application_fee: false, // Platform fee is non-refundable
      });

      toast.success(
        `Refund of $${refundAmountDollars.toFixed(2)} initiated successfully. Status will update momentarily.`,
        { autoClose: 5000 }
      );
      onSuccess?.();
      onClose();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to process refund';
      toast.error(errorMessage);
      Sentry.captureException(error, {
        tags: {
          component: 'RefundModal',
          action: 'submit_refund',
          payment_id: payment.id,
        },
      });
    }
  };

  const renderAmountStep = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Refund Amount</h3>
        <p className="text-sm text-gray-600">
          Original payment: <span className="font-semibold">${paymentAmount.toFixed(2)}</span>
        </p>
      </div>

      {/* Refund Type Selection */}
      <div className="space-y-3">
        <label className="flex items-center p-4 border-2 rounded-lg cursor-pointer transition-colors hover:border-brand-teal"
          style={{
            borderColor: refundType === 'full' ? '#004225' : '#e5e7eb',
            backgroundColor: refundType === 'full' ? '#f0fdf4' : 'white',
          }}>
          <input
            type="radio"
            name="refundType"
            value="full"
            checked={refundType === 'full'}
            onChange={() => setRefundType('full')}
            className="w-4 h-4 text-brand-teal focus:ring-brand-teal"
          />
          <div className="ml-3 flex-1">
            <div className="font-medium text-gray-900">Full Refund</div>
            <div className="text-sm text-gray-600">Refund the entire payment amount</div>
          </div>
          <div className="text-lg font-semibold text-gray-900">
            ${paymentAmount.toFixed(2)}
          </div>
        </label>

        <label className="flex items-center p-4 border-2 rounded-lg cursor-pointer transition-colors hover:border-brand-teal"
          style={{
            borderColor: refundType === 'partial' ? '#004225' : '#e5e7eb',
            backgroundColor: refundType === 'partial' ? '#f0fdf4' : 'white',
          }}>
          <input
            type="radio"
            name="refundType"
            value="partial"
            checked={refundType === 'partial'}
            onChange={() => setRefundType('partial')}
            className="w-4 h-4 text-brand-teal focus:ring-brand-teal"
          />
          <div className="ml-3 flex-1">
            <div className="font-medium text-gray-900">Partial Refund</div>
            <div className="text-sm text-gray-600">Refund a custom amount</div>
          </div>
        </label>
      </div>

      {/* Custom Amount Input */}
      {refundType === 'partial' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Refund Amount
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">$</span>
            <input
              type="number"
              step="0.01"
              min="0.01"
              max={paymentAmount}
              value={customAmount}
              onChange={(e) => setCustomAmount(e.target.value)}
              placeholder="0.00"
              className="w-full pl-8 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-teal focus:border-transparent"
              style={{
                borderColor: customAmount && (!isValidAmount) ? '#ef4444' : undefined,
              }}
            />
          </div>
          {customAmount && !isValidAmount && (
            <p className="mt-1 text-sm text-red-600">
              Amount must be between $0.01 and ${paymentAmount.toFixed(2)}
            </p>
          )}
        </div>
      )}
    </div>
  );

  const renderDetailsStep = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Refund Details</h3>
        <p className="text-sm text-gray-600">
          Refunding: <span className="font-semibold">${refundAmountDollars.toFixed(2)}</span>
        </p>
      </div>

      {/* Reason Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Reason for Refund <span className="text-red-500">*</span>
        </label>
        <select
          value={reason}
          onChange={(e) => setReason(e.target.value as RefundReason)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-teal focus:border-transparent"
        >
          {REFUND_REASONS.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
        <p className="mt-1 text-sm text-gray-500">
          {REFUND_REASONS.find(r => r.value === reason)?.description}
        </p>
      </div>

      {/* Notes */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Additional Notes (Optional)
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          placeholder="Add any additional context about this refund..."
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-teal focus:border-transparent resize-none"
        />
      </div>

      {/* Platform Fee Notice - Not Refundable */}
      <div className="bg-blue-50 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800">Platform Fee Policy</h3>
            <div className="mt-2 text-sm text-blue-700">
              The Brikli platform fee ($3-$8 depending on payment method) is non-refundable as it covers the cost of payment processing services already rendered.
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderConfirmStep = () => (
    <div className="space-y-6">
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-800">Confirm Refund</h3>
            <div className="mt-2 text-sm text-yellow-700">
              This action cannot be undone. The refund will be processed immediately.
            </div>
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="bg-gray-50 rounded-lg p-4 space-y-3">
        <div className="flex justify-between">
          <span className="text-gray-600">Tenant:</span>
          <span className="font-medium text-gray-900">{payment.tenant_name || 'Unknown'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Original Payment:</span>
          <span className="font-medium text-gray-900">${paymentAmount.toFixed(2)}</span>
        </div>
        <div className="flex justify-between text-lg">
          <span className="font-semibold text-gray-900">Refund Amount:</span>
          <span className="font-semibold text-brand-teal">${refundAmountDollars.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Reason:</span>
          <span className="font-medium text-gray-900">
            {REFUND_REASONS.find(r => r.value === reason)?.label}
          </span>
        </div>
        {notes && (
          <div className="pt-2 border-t border-gray-200">
            <span className="text-gray-600 block mb-1">Notes:</span>
            <span className="text-sm text-gray-700">{notes}</span>
          </div>
        )}
        <div className="pt-2 border-t border-gray-200">
          <span className="text-sm text-gray-600">
            Note: Platform fee is non-refundable (covers payment processing costs)
          </span>
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          The tenant will receive an email notification and the refund will appear in their account within 5-10 business days.
        </p>
      </div>
    </div>
  );

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden"
          >
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-gray-900">Issue Refund</h2>
                <button
                  onClick={onClose}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Progress Steps */}
              <div className="flex items-center justify-between mt-4">
                {(['amount', 'details', 'confirm'] as RefundStep[]).map((s, index) => (
                  <React.Fragment key={s}>
                    <div className="flex items-center">
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                          step === s
                            ? 'bg-brand-teal text-white'
                            : index < ['amount', 'details', 'confirm'].indexOf(step)
                            ? 'bg-green-500 text-white'
                            : 'bg-gray-200 text-gray-600'
                        }`}
                      >
                        {index + 1}
                      </div>
                      <span className="ml-2 text-sm font-medium text-gray-700 capitalize">
                        {s}
                      </span>
                    </div>
                    {index < 2 && (
                      <div className="flex-1 h-1 mx-4 bg-gray-200 rounded">
                        <div
                          className="h-full bg-brand-teal rounded transition-all"
                          style={{
                            width: index < ['amount', 'details', 'confirm'].indexOf(step) ? '100%' : '0%',
                          }}
                        />
                      </div>
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>

            {/* Content */}
            <div className="px-6 py-6 overflow-y-auto max-h-[calc(90vh-200px)]">
              {step === 'amount' && renderAmountStep()}
              {step === 'details' && renderDetailsStep()}
              {step === 'confirm' && renderConfirmStep()}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
              <button
                onClick={step === 'amount' ? onClose : handleBack}
                className="px-4 py-2 text-gray-700 hover:text-gray-900 font-medium transition-colors"
              >
                {step === 'amount' ? 'Cancel' : 'Back'}
              </button>
              <button
                onClick={step === 'confirm' ? handleSubmit : handleNext}
                disabled={!isValidAmount || createRefundMutation.isPending}
                className="px-6 py-2 bg-brand-teal text-white rounded-lg hover:bg-brand-teal-hover font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {createRefundMutation.isPending
                  ? 'Processing...'
                  : step === 'confirm'
                  ? 'Issue Refund'
                  : 'Continue'}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default RefundModal;


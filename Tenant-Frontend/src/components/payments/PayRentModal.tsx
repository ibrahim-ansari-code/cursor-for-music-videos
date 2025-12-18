/**
 * PayRentModal Component
 * Modal for tenants to pay rent using Stripe Elements
 */

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { loadStripe, StripeElementsOptions, Stripe } from '@stripe/stripe-js';
import {
  Elements,
  PaymentElement,
  useStripe,
  useElements,
} from '@stripe/react-stripe-js';
import { FaLock } from 'react-icons/fa';
import { toast } from 'react-toastify';
import { motion, AnimatePresence } from 'framer-motion';
import * as Sentry from '@sentry/react';
import {
  useCreateRentPaymentIntent,
  paymentsKeys,
} from '@/hooks/usePayments';
import { useQueryClient } from '@tanstack/react-query';
import type { SavedPaymentMethod } from '@/types/payments';

interface PayRentModalProps {
  isOpen: boolean;
  onClose: () => void;
  leaseId: number;
  amountDue: number; // Amount in dollars (not cents)
  landlordName: string;
  propertyAddress: string;
  savedPaymentMethods?: SavedPaymentMethod[];
}

/**
 * Payment Form Component (inside Stripe Elements)
 * @param amountToPayCents - Amount to pay in cents
 */
const PaymentForm: React.FC<{
  amountToPayCents: number;
  onSuccess: () => void;
  onCancel: () => void;
}> = ({ amountToPayCents, onSuccess, onCancel }) => {
  const stripe = useStripe();
  const elements = useElements();
  const queryClient = useQueryClient();
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!stripe || !elements) {
      setErrorMessage('Payment system not ready. Please try again.');
      return;
    }

    setIsProcessing(true);
    setErrorMessage(null);

    return Sentry.startSpan(
      {
        op: 'payment.submit',
        name: 'Submit Rent Payment',
      },
      async () => {
        try {
          const { error } = await stripe.confirmPayment({
            elements,
            confirmParams: {
              return_url: `${window.location.origin}/payments?payment_status=success`,
            },
            redirect: 'if_required',
          });

          if (error) {
            Sentry.captureException(error, {
              tags: {
                component: 'PayRentModal',
                action: 'confirm_payment',
              },
            });
            setErrorMessage(error.message || 'Payment failed. Please try again.');
            setIsProcessing(false);
          } else {
            // Payment succeeded
            setIsSuccess(true);
            toast.success('Payment successful!');
            
            // Invalidate relevant queries
            await queryClient.invalidateQueries({ queryKey: paymentsKeys.balance() });
            await queryClient.invalidateQueries({ queryKey: paymentsKeys.transactions() });
            
            // Close modal after showing success state
            setTimeout(() => {
              onSuccess();
            }, 2000);
          }
        } catch (err) {
          Sentry.captureException(err, {
            tags: {
              component: 'PayRentModal',
              action: 'payment_error',
            },
          });
          setErrorMessage('An unexpected error occurred. Please try again.');
          setIsProcessing(false);
        }
      }
    );
  };

  const formatCurrency = (cents: number) => {
    return new Intl.NumberFormat('en-CA', {
      style: 'currency',
      currency: 'CAD',
    }).format(cents / 100);
  };

  // Show success state
  if (isSuccess) {
    return (
      <div className="text-center py-8 space-y-4">
        <div className="flex justify-center">
          <div className="rounded-full bg-green-100 p-3">
            <svg
              className="h-12 w-12 text-green-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
        </div>
        <div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Payment Successful!
          </h3>
          <p className="text-gray-600">
            Your payment of <span className="font-semibold">{formatCurrency(amountToPayCents)}</span> has been processed.
          </p>
          <p className="text-sm text-gray-500 mt-2">
            This window will close automatically...
          </p>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Payment Amount */}
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="flex justify-between items-center">
          <span className="text-gray-600">Amount to Pay</span>
          <span className="font-bold text-gray-900 text-2xl">{formatCurrency(amountToPayCents)}</span>
        </div>
      </div>

      {/* Stripe Payment Element */}
      <div>
        <PaymentElement />
      </div>

      {/* Error Message */}
      {errorMessage && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {errorMessage}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex space-x-3">
        <button
          type="button"
          onClick={onCancel}
          disabled={isProcessing}
          className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors cursor-pointer"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isProcessing || !stripe || !elements}
          className="flex-1 px-4 py-3 bg-brand-teal text-white rounded-lg hover:bg-brand-green disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors flex items-center justify-center cursor-pointer"
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
              Processing...
            </>
          ) : (
            <>
              <FaLock className="mr-2" />
              Pay {formatCurrency(amountToPayCents)}
            </>
          )}
        </button>
      </div>

      {/* Security Notice */}
      <div className="text-xs text-gray-500 text-center">
        <FaLock className="inline mr-1" />
        Secured by Stripe • Your payment information is encrypted
      </div>
    </form>
  );
};

/**
 * Main Modal Component
 */
const PayRentModal: React.FC<PayRentModalProps> = ({
  isOpen,
  onClose,
  leaseId,
  amountDue,
  landlordName: _landlordName,
  propertyAddress,
}) => {
  const [step, setStep] = useState<'amount' | 'payment'>('amount');
  const [amountToPayCents, setAmountToPayCents] = useState<number>(0);
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [stripeAccountId, setStripeAccountId] = useState<string | null>(null);
  const [initError, setInitError] = useState<string | null>(null);
  const [isCreatingIntent, setIsCreatingIntent] = useState(false);
  const { mutate: createPaymentIntentMutate } = useCreateRentPaymentIntent();

  // Convert amountDue (dollars) to cents reliably
  // toFixed(2) ensures we work with exactly 2 decimal places before conversion
  const amountDueCents = Math.round(parseFloat(amountDue.toFixed(2)) * 100);
  const amountToPayDollars = amountToPayCents / 100;
  
  // Validation
  const isAmountValid = amountToPayCents >= 100 && amountToPayCents <= amountDueCents;
  
  const getValidationError = (): string | null => {
    if (amountToPayCents <= 0) return 'Amount must be greater than $0.00';
    if (amountToPayCents < 100) return 'Minimum payment is $1.00';
    if (amountToPayCents > amountDueCents) {
      return `Amount cannot exceed ${new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD' }).format(amountDue)}`;
    }
    return null;
  };

  // Reset state when modal opens (from closed state only)
  // Don't reset if balance updates mid-flow (amountDueCents change while open)
  const previousIsOpenRef = useRef(isOpen);
  useEffect(() => {
    const wasClosedNowOpen = !previousIsOpenRef.current && isOpen;
    previousIsOpenRef.current = isOpen;
    
    if (wasClosedNowOpen) {
      // Only reset when transitioning from closed to open
      setStep('amount');
      setAmountToPayCents(amountDueCents); // Default to full balance in cents
      setClientSecret(null);
      setStripeAccountId(null);
      setInitError(null);
      setIsCreatingIntent(false);
    }
  }, [isOpen, amountDueCents]);

  // Create Stripe instance with connected account
  const stripePromise = useMemo<Promise<Stripe | null>>(() => {
    if (!stripeAccountId) {
      return Promise.resolve(null);
    }
    return loadStripe(
      import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || '',
      { stripeAccount: stripeAccountId }
    );
  }, [stripeAccountId]);

  const handleAmountSubmit = () => {
    if (!isAmountValid) {
      const error = getValidationError();
      if (error) toast.error(error);
      return;
    }

    setIsCreatingIntent(true);
    createPaymentIntentMutate(
      {
        leaseId,
        amountCents: amountToPayCents,
        paymentMethodId: null,
      },
      {
        onSuccess: (data) => {
          setClientSecret(data.client_secret);
          setStripeAccountId(data.stripe_account_id);
          setInitError(null);
          setStep('payment');
          setIsCreatingIntent(false);
        },
        onError: (error: Error) => {
          const errorMessage = error?.message || 'Failed to initialize payment';
          
          if (errorMessage.includes('not set up online payments')) {
            setInitError('Your landlord has not enabled online rent payments yet. Please contact your landlord or pay rent using an alternative method.');
          } else {
            setInitError(errorMessage);
          }
          
          Sentry.captureException(error, {
            tags: {
              component: 'PayRentModal',
              action: 'create_payment_intent',
            },
          });
          setIsCreatingIntent(false);
        },
      }
    );
  };

  const handleSuccess = () => {
    setClientSecret(null); // Reset for next payment
    setStripeAccountId(null); // Reset account
    setInitError(null); // Reset error
    onClose();
  };

  const handleCancel = useCallback(() => {
    setClientSecret(null); // Reset
    setStripeAccountId(null); // Reset account
    setInitError(null); // Reset error
    onClose();
  }, [onClose]);

  const modalRef = useRef<HTMLDivElement>(null);

  // Handle Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        handleCancel();
      }
    };
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
    }
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, handleCancel]);

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
        handleCancel();
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, handleCancel]);

  if (!isOpen) return null;

  const stripeOptions: StripeElementsOptions = {
    clientSecret: clientSecret || undefined,
    appearance: {
      theme: 'stripe',
      variables: {
        colorPrimary: '#1BC5AE', // brand-teal
        colorBackground: '#ffffff',
        colorText: '#1f2937',
        colorDanger: '#ef4444',
        fontFamily: 'system-ui, sans-serif',
        borderRadius: '8px',
      },
    },
  };

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
              <h2 id="modal-title" className="text-xl font-semibold text-gray-900">Pay Rent</h2>
              <p className="text-sm text-gray-600 mt-1">{propertyAddress}</p>
            </div>
            <button
              type="button"
              onClick={handleCancel}
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
          <div className="p-6 grow overflow-y-auto">
            {initError ? (
              /* Error State */
              <div className="space-y-4">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-start">
                    <svg
                      className="h-6 w-6 text-red-600 mt-0.5 mr-3 shrink-0"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                      />
                    </svg>
                    <div>
                      <h3 className="text-sm font-semibold text-red-800 mb-1">
                        Payment Not Available
                      </h3>
                      <p className="text-sm text-red-700">{initError}</p>
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleCancel}
                  className="w-full px-4 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 font-medium transition-colors cursor-pointer"
                >
                  Close
                </button>
              </div>
            ) : step === 'amount' ? (
              /* Amount Selection Step */
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Payment Amount
                  </label>
                  <div className="space-y-3">
                    {/* Full Balance Option */}
                    <button
                      type="button"
                      onClick={() => setAmountToPayCents(amountDueCents)}
                      className={`w-full p-4 border-2 rounded-lg text-left transition-all cursor-pointer ${
                        amountToPayCents === amountDueCents
                          ? 'border-brand-teal bg-brand-teal/5'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex justify-between items-center">
                        <div>
                          <p className="font-medium text-gray-900">Pay Full Balance</p>
                          <p className="text-sm text-gray-500 mt-1">Recommended</p>
                        </div>
                        <p className="text-lg font-semibold text-gray-900">
                          {new Intl.NumberFormat('en-CA', {
                            style: 'currency',
                            currency: 'CAD',
                          }).format(amountDue)}
                        </p>
                      </div>
                    </button>

                    {/* Custom Amount Option */}
                    <div className="p-4 border-2 border-gray-200 rounded-lg">
                      <p className="font-medium text-gray-900 mb-3">Custom Amount</p>
                      <div className="flex items-center space-x-2">
                        <span className="text-gray-500 text-lg">$</span>
                        <input
                          type="number"
                          min="1"
                          max={amountDue}
                          step="0.01"
                          value={amountToPayCents === amountDueCents ? '' : amountToPayDollars}
                          onChange={(e) => {
                            const value = e.target.value;
                            if (value === '') {
                              setAmountToPayCents(0);
                            } else {
                              const numValue = parseFloat(value);
                              if (!isNaN(numValue)) {
                                setAmountToPayCents(Math.round(numValue * 100));
                              }
                            }
                          }}
                          onFocus={(e) => {
                            // Clear field when focused if it's set to full balance
                            if (amountToPayCents === amountDueCents) {
                              setAmountToPayCents(0);
                            }
                            e.target.select();
                          }}
                          placeholder={amountDue.toFixed(2)}
                          className={`flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:border-transparent transition-colors ${
                            amountToPayCents !== amountDueCents && !isAmountValid
                              ? 'border-red-300 focus:ring-red-500 bg-red-50'
                              : 'border-gray-300 focus:ring-brand-teal'
                          }`}
                        />
                      </div>
                      {amountToPayCents !== amountDueCents && !isAmountValid ? (
                        <p className="text-xs text-red-600 mt-2 font-medium">
                          {getValidationError()}
                        </p>
                      ) : (
                        <p className="text-xs text-gray-500 mt-2">
                          Enter any amount from $1.00 to ${amountDue.toFixed(2)}
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Continue Button */}
                <button
                  type="button"
                  onClick={handleAmountSubmit}
                  disabled={isCreatingIntent || !isAmountValid}
                  className="w-full px-4 py-3 bg-brand-teal text-white rounded-lg hover:bg-brand-green font-medium transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center cursor-pointer"
                >
                  {isCreatingIntent ? (
                    <>
                      <svg
                        className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
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
                      Loading...
                    </>
                  ) : (
                    'Continue to Payment'
                  )}
                </button>
              </div>
            ) : clientSecret && stripeAccountId ? (
              /* Payment Form */
              <Elements stripe={stripePromise} options={stripeOptions}>
                <PaymentForm
                  amountToPayCents={amountToPayCents}
                  onSuccess={handleSuccess}
                  onCancel={handleCancel}
                />
              </Elements>
            ) : (
              /* Loading State */
              <div className="flex items-center justify-center py-12">
                <svg
                  className="animate-spin h-8 w-8 text-brand-teal"
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
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default PayRentModal;


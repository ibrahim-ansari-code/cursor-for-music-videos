/**
 * AddPaymentMethodModal Component
 * Modal for tenants to add and save payment methods
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { loadStripe, StripeElementsOptions } from '@stripe/stripe-js';
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
  useCreateSetupIntent,
  useSavePaymentMethod,
} from '@/hooks/usePayments';

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || '');

interface AddPaymentMethodModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

/**
 * Payment Method Form Component (inside Stripe Elements)
 */
const PaymentMethodForm: React.FC<{
  onSuccess: () => void;
  onCancel: () => void;
}> = ({ onSuccess, onCancel }) => {
  const stripe = useStripe();
  const elements = useElements();
  const savePaymentMethod = useSavePaymentMethod();
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!stripe || !elements) {
      return;
    }

    setIsProcessing(true);
    setErrorMessage(null);

    return Sentry.startSpan(
      {
        op: 'payment_method.add',
        name: 'Add Payment Method',
      },
      async () => {
        try {
          // Confirm the setup intent
          const { error, setupIntent } = await stripe.confirmSetup({
            elements,
            redirect: 'if_required',
            confirmParams: {
              return_url: `${window.location.origin}/payments?setup_status=success`,
            },
          });

          if (error) {
            Sentry.captureException(error, {
              tags: {
                component: 'AddPaymentMethodModal',
                action: 'confirm_setup',
              },
            });
            setErrorMessage(error.message || 'Failed to add payment method. Please try again.');
            setIsProcessing(false);
          } else if (setupIntent && setupIntent.status === 'succeeded') {
            // Extract payment method ID
            const paymentMethod = setupIntent.payment_method;
            let paymentMethodId: string;

            if (typeof paymentMethod === 'string') {
              // Already a payment method ID
              paymentMethodId = paymentMethod;
            } else if (typeof paymentMethod === 'object' && paymentMethod !== null) {
              // Payment method object - extract ID
              paymentMethodId = paymentMethod.id;
            } else {
              setErrorMessage('Failed to extract payment method. Please try again.');
              setIsProcessing(false);
              return;
            }

            // Save to our backend
            savePaymentMethod.mutate(
              {
                stripePaymentMethodId: paymentMethodId,
                setAsDefault: false,
              },
              {
                onSuccess: () => {
                  onSuccess();
                },
                onError: () => {
                  setErrorMessage('Payment method verified but failed to save. Please try again.');
                  setIsProcessing(false);
                },
              }
            );
          }
        } catch (err) {
          Sentry.captureException(err, {
            tags: {
              component: 'AddPaymentMethodModal',
              action: 'setup_error',
            },
          });
          setErrorMessage('An unexpected error occurred. Please try again.');
          setIsProcessing(false);
        }
      }
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">

      {/* Stripe Payment Element */}
      <div>
        <PaymentElement
          options={{
            terms: {
              card: 'never',
              // ACSS Debit (Canadian PAD) mandate is handled by Stripe automatically
              auBecsDebit: 'never',
              bancontact: 'never',
              ideal: 'never',
              sepaDebit: 'never',
              sofort: 'never',
              usBankAccount: 'never',
            },
          }}
        />
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
          className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isProcessing || !stripe || !elements}
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
              Saving...
            </>
          ) : (
            <>
              <FaLock className="mr-2" />
              Add Payment Method
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
const AddPaymentMethodModal: React.FC<AddPaymentMethodModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [setupIntentId, setSetupIntentId] = useState<string | null>(null);
  const { mutate: createSetupIntentMutate } = useCreateSetupIntent();

  // Create SetupIntent when modal opens
  useEffect(() => {
    if (isOpen && !clientSecret) {
      createSetupIntentMutate(undefined, {
        onSuccess: (data) => {
          setClientSecret(data.client_secret);
          setSetupIntentId(data.setup_intent_id);
        },
        onError: () => {
          toast.error('Failed to initialize payment method setup. Please try again.');
          onClose();
        },
      });
    }
  }, [isOpen, clientSecret, createSetupIntentMutate, onClose]);

  const handleSuccess = () => {
    setClientSecret(null); // Reset for next use
    setSetupIntentId(null);
    onSuccess?.();
    onClose();
  };

  const handleCancel = useCallback(() => {
    setClientSecret(null); // Reset
    setSetupIntentId(null);
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
    locale: 'en-CA', // Canadian locale for PAD
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
              <h2 id="modal-title" className="text-xl font-semibold text-gray-900">Add Payment Method</h2>
              <p className="text-sm text-gray-600 mt-1">Save a payment method for future use</p>
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
            {clientSecret && setupIntentId ? (
              <Elements stripe={stripePromise} options={stripeOptions}>
                <PaymentMethodForm
                  onSuccess={handleSuccess}
                  onCancel={handleCancel}
                />
              </Elements>
            ) : (
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

export default AddPaymentMethodModal;


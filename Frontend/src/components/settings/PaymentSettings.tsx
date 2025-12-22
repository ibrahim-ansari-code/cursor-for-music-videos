/**
 * Payment Settings Component
 *
 * Allows landlords to manage their Stripe Connect account and
 * configure which payment methods they accept from tenants.
 */

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as Sentry from '@sentry/react';
import { CreditCard, Building2, AlertCircle, CheckCircle2, Loader2, ExternalLink } from 'lucide-react';
import { toast } from 'react-toastify';
import {
  getConnectStatus,
  updatePaymentPreferences,
  getStripeDashboardLink,
  startConnectOnboarding,
} from '../../utils/api/connect';
import type { ConnectStatusResponse, PaymentMethodType } from '../../types/rentPayments';

// Payment method display configuration
const PAYMENT_METHODS: {
  type: PaymentMethodType;
  label: string;
  description: string;
  fee: string;
  icon: React.ReactNode;
}[] = [
  {
    type: 'card',
    label: 'Credit/Debit Cards',
    description: 'Accept Visa, Mastercard, American Express',
    fee: '$8.00',
    icon: <CreditCard className="w-5 h-5" />,
  },
  {
    type: 'acss_debit',
    label: 'PAD Bank Transfer',
    description: 'Pre-Authorized Debit from Canadian bank accounts',
    fee: '$3.00',
    icon: <Building2 className="w-5 h-5" />,
  },
];

const PaymentSettings: React.FC = () => {
  const queryClient = useQueryClient();
  const [pendingMethods, setPendingMethods] = useState<PaymentMethodType[] | null>(null);

  // Fetch Connect status
  const {
    data: connectStatus,
    isLoading,
    error,
  } = useQuery<ConnectStatusResponse>({
    queryKey: ['connect', 'status'],
    queryFn: getConnectStatus,
    staleTime: 30000, // 30 seconds
  });

  // Update payment preferences mutation
  const updatePreferencesMutation = useMutation({
    mutationFn: updatePaymentPreferences,
    onSuccess: (data) => {
      queryClient.setQueryData<ConnectStatusResponse>(['connect', 'status'], (old) =>
        old ? { ...old, accepted_payment_methods: data.accepted_payment_methods } : old
      );
      setPendingMethods(null);
      toast.success('Payment preferences updated successfully');

      Sentry.logger.info('Payment preferences updated', {
        methods: data.accepted_payment_methods,
      });
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Failed to update payment preferences');

      Sentry.captureException(err, {
        tags: {
          component: 'PaymentSettings',
          action: 'update_payment_preferences',
        },
      });
    },
  });

  // Get Stripe Dashboard link
  const dashboardLinkMutation = useMutation({
    mutationFn: getStripeDashboardLink,
    onSuccess: (data) => {
      window.open(data.dashboard_url, '_blank', 'noopener,noreferrer');
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Failed to open Stripe dashboard');
    },
  });

  // Start onboarding
  const onboardingMutation = useMutation({
    mutationFn: startConnectOnboarding,
    onSuccess: (data) => {
      window.location.href = data.onboarding_url;
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Failed to start onboarding');
    },
  });

  // Get current accepted methods (from pending state or server)
  // Handle empty arrays by falling back to defaults (empty array is falsy-like for our purposes)
  const getSafeAcceptedMethods = (methods: PaymentMethodType[] | undefined | null) =>
    methods && methods.length > 0 ? methods : ['card', 'acss_debit'] as PaymentMethodType[];

  const currentMethods = pendingMethods
    ? getSafeAcceptedMethods(pendingMethods)
    : getSafeAcceptedMethods(connectStatus?.accepted_payment_methods);

  // Toggle a payment method
  const toggleMethod = (method: PaymentMethodType) => {
    const newMethods = currentMethods.includes(method)
      ? currentMethods.filter((m) => m !== method)
      : [...currentMethods, method];

    // Must have at least one method
    if (newMethods.length === 0) {
      toast.error('At least one payment method must be enabled');
      return;
    }

    setPendingMethods(newMethods);
  };

  // Save preferences
  const savePreferences = () => {
    if (pendingMethods) {
      updatePreferencesMutation.mutate(pendingMethods);
    }
  };

  // Cancel changes
  const cancelChanges = () => {
    setPendingMethods(null);
  };

  // Check if there are unsaved changes
  const hasUnsavedChanges = pendingMethods !== null;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
          <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded mb-4"></div>
          <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-6">
        <div className="flex items-center gap-3">
          <AlertCircle className="w-6 h-6 text-red-500" />
          <div>
            <h3 className="text-lg font-medium text-red-800 dark:text-red-300">
              Failed to load payment settings
            </h3>
            <p className="text-sm text-red-600 dark:text-red-400 mt-1">
              Please try refreshing the page.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Not connected - show onboarding prompt
  if (!connectStatus?.is_connected) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Payment Settings
          </h2>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Set up your payment account to receive rent payments from tenants
          </p>
        </div>

        <div className="dark-panel dark-shadow rounded-lg p-8 text-center">
          <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
            <CreditCard className="w-8 h-8 text-blue-600 dark:text-blue-400" />
          </div>
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Set Up Online Payments
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md mx-auto">
            Connect your Stripe account to start accepting rent payments directly from tenants.
            Funds are deposited directly to your bank account.
          </p>
          <button
            onClick={() => onboardingMutation.mutate()}
            disabled={onboardingMutation.isPending}
            className="px-8 py-3 bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 rounded-full font-medium transition-all duration-200 shadow-sm hover:shadow-md flex items-center gap-2 mx-auto disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {onboardingMutation.isPending ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Setting up...
              </>
            ) : (
              <>
                <CreditCard className="w-5 h-5" />
                Set Up Stripe Connect
              </>
            )}
          </button>
        </div>
      </div>
    );
  }

  // Connected but not fully onboarded
  if (!connectStatus.charges_enabled) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Payment Settings
          </h2>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Complete your Stripe account setup to start accepting payments
          </p>
        </div>

        <div className="dark-panel dark-shadow rounded-lg p-6">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-yellow-100 dark:bg-yellow-900/30 rounded-full flex items-center justify-center flex-shrink-0">
              <AlertCircle className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
                Account Setup Incomplete
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                Your Stripe account needs additional information before you can accept payments.
                {connectStatus.requirements_currently_due.length > 0 && (
                  <span className="block mt-2 text-sm">
                    Required: {connectStatus.requirements_currently_due.join(', ')}
                  </span>
                )}
              </p>
              <button
                onClick={() => onboardingMutation.mutate()}
                disabled={onboardingMutation.isPending}
                className="px-6 py-2.5 bg-yellow-600 text-white hover:bg-yellow-700 rounded-full font-medium transition-all duration-200 shadow-sm hover:shadow-md flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {onboardingMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    Continue Setup
                    <ExternalLink className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Fully connected - show settings
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Payment Settings
        </h2>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Configure how you receive rent payments from tenants
        </p>
      </div>

      {/* Account Status */}
      <div className="dark-panel dark-shadow rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Stripe Connect Account
          </h3>
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            Active
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Account ID</p>
            <p className="text-sm font-mono text-gray-900 dark:text-white">
              {connectStatus.account_id}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Currency</p>
            <p className="text-sm font-medium text-gray-900 dark:text-white uppercase">
              {connectStatus.default_currency || 'CAD'}
            </p>
          </div>
        </div>

        <button
          onClick={() => dashboardLinkMutation.mutate()}
          disabled={dashboardLinkMutation.isPending}
          className="px-6 py-2.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-full font-medium transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {dashboardLinkMutation.isPending ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Opening...
            </>
          ) : (
            <>
              <ExternalLink className="w-4 h-4" />
              Open Stripe Dashboard
            </>
          )}
        </button>
      </div>

      {/* Payment Method Preferences */}
      <div className="dark-panel dark-shadow rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Accepted Payment Methods
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Choose which payment methods tenants can use to pay rent
            </p>
          </div>
          {hasUnsavedChanges && (
            <span className="text-xs text-yellow-600 dark:text-yellow-400 font-medium">
              Unsaved changes
            </span>
          )}
        </div>

        <div className="space-y-3 mb-6">
          {PAYMENT_METHODS.map((method) => {
            const isEnabled = currentMethods.includes(method.type);
            const isOnlyMethod = isEnabled && currentMethods.length === 1;

            return (
              <div
                key={method.type}
                onClick={() => !isOnlyMethod && toggleMethod(method.type)}
                className={`border rounded-xl p-5 transition-all duration-200 cursor-pointer ${
                  isEnabled
                    ? 'border-blue-500 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 dark:border-blue-500 shadow-sm'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800/50'
                } ${isOnlyMethod ? 'cursor-not-allowed' : ''}`}
              >
                <div className="flex items-center gap-4">
                  {/* Icon */}
                  <div className={`p-3 rounded-xl transition-colors ${
                    isEnabled
                      ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400'
                      : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400'
                  }`}>
                    {method.icon}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-900 dark:text-white">
                        {method.label}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        isEnabled
                          ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/60 dark:text-blue-300'
                          : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                      }`}>
                        {method.fee}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                      {method.description}
                    </p>
                    {isOnlyMethod && (
                      <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
                        At least one payment method must be enabled
                      </p>
                    )}
                  </div>

                  {/* Toggle Switch */}
                  <button
                    type="button"
                    role="switch"
                    aria-checked={isEnabled}
                    disabled={isOnlyMethod}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (!isOnlyMethod) toggleMethod(method.type);
                    }}
                    className={`relative inline-flex h-7 w-12 flex-shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 ${
                      isEnabled
                        ? 'bg-blue-600 dark:bg-blue-500'
                        : 'bg-gray-200 dark:bg-gray-700'
                    } ${isOnlyMethod ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                  >
                    <span
                      className={`pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                        isEnabled ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Save/Cancel buttons */}
        {hasUnsavedChanges && (
          <div className="flex items-center gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={savePreferences}
              disabled={updatePreferencesMutation.isPending}
              className="px-6 py-2.5 bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 rounded-full font-medium transition-all duration-200 shadow-sm hover:shadow-md flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {updatePreferencesMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Changes'
              )}
            </button>
            <button
              onClick={cancelChanges}
              disabled={updatePreferencesMutation.isPending}
              className="px-6 py-2.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-full font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
          </div>
        )}

        {/* Fee Info */}
        <div className="mt-4 rounded-md bg-blue-50 dark:bg-blue-900/20 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800 dark:text-blue-300">
              <p className="font-medium mb-1">About payment fees</p>
              <p>
                Fees are charged per transaction and cover payment processing costs.
                PAD bank transfers have lower fees but take 3-5 business days to process.
                Card payments are instant but have higher fees.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PaymentSettings;

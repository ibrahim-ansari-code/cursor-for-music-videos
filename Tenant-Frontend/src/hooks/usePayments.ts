/**
 * usePayments Hook
 * TanStack Query hooks for rent payment management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import * as Sentry from '@sentry/react';
import {
  getTenantBalance,
  getPlatformFees,
  createSetupIntent,
  savePaymentMethod,
  getPaymentMethods,
  deletePaymentMethod,
  setDefaultPaymentMethod,
  createRentPaymentIntent,
  getRentTransactions,
  getRentTransaction,
  enrollAutopay,
  getAutopayStatus,
  cancelAutopay,
} from '@/utils/api/payments';

// ============================================================================
// Query Keys
// ============================================================================

export const paymentsKeys = {
  all: ['payments'] as const,
  balance: () => [...paymentsKeys.all, 'balance'] as const,
  fees: () => [...paymentsKeys.all, 'fees'] as const,
  methods: () => [...paymentsKeys.all, 'methods'] as const,
  transactions: () => [...paymentsKeys.all, 'transactions'] as const,
  transaction: (id: string) => [...paymentsKeys.transactions(), id] as const,
  autopay: () => [...paymentsKeys.all, 'autopay'] as const,
};

// ============================================================================
// Balance & Fees
// ============================================================================

export const useTenantBalance = () => {
  return useQuery({
    queryKey: paymentsKeys.balance(),
    queryFn: getTenantBalance,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};

export const usePlatformFees = () => {
  return useQuery({
    queryKey: paymentsKeys.fees(),
    queryFn: getPlatformFees,
    staleTime: 1000 * 60 * 60, // 1 hour (fees don't change often)
  });
};

// ============================================================================
// Payment Methods
// ============================================================================

export const usePaymentMethods = () => {
  return useQuery({
    queryKey: paymentsKeys.methods(),
    queryFn: getPaymentMethods,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};

export const useCreateSetupIntent = () => {
  return useMutation({
    mutationFn: createSetupIntent,
    onError: (error: Error) => {
      Sentry.captureException(error, {
        tags: {
          component: 'usePayments',
          action: 'create_setup_intent',
        },
      });
      toast.error('Failed to initialize payment method setup');
    },
  });
};

export const useSavePaymentMethod = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      stripePaymentMethodId,
      setAsDefault,
    }: {
      stripePaymentMethodId: string;
      setAsDefault?: boolean;
    }) => savePaymentMethod(stripePaymentMethodId, setAsDefault),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: paymentsKeys.methods() });
      toast.success('Payment method added successfully');
    },
    onError: (error: Error) => {
      Sentry.captureException(error, {
        tags: {
          component: 'usePayments',
          action: 'save_payment_method',
        },
      });
      toast.error('Failed to save payment method');
    },
  });
};

export const useDeletePaymentMethod = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (paymentMethodId: string) => deletePaymentMethod(paymentMethodId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: paymentsKeys.methods() });
      queryClient.invalidateQueries({ queryKey: paymentsKeys.autopay() });
      toast.success('Payment method removed successfully');
    },
    onError: (error: Error) => {
      Sentry.captureException(error, {
        tags: {
          component: 'usePayments',
          action: 'delete_payment_method',
        },
      });
      toast.error('Failed to remove payment method');
    },
  });
};

export const useSetDefaultPaymentMethod = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (paymentMethodId: string) => setDefaultPaymentMethod(paymentMethodId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: paymentsKeys.methods() });
      toast.success('Default payment method updated');
    },
    onError: (error: Error) => {
      Sentry.captureException(error, {
        tags: {
          component: 'usePayments',
          action: 'set_default_payment_method',
        },
      });
      toast.error('Failed to update default payment method');
    },
  });
};

// ============================================================================
// Rent Payments
// ============================================================================

export const useCreateRentPaymentIntent = () => {
  return useMutation({
    mutationFn: ({ leaseId, amountCents, paymentMethodId }: { leaseId: number; amountCents: number; paymentMethodId: string | null }) =>
      createRentPaymentIntent(leaseId, amountCents, paymentMethodId),
    // Error handling moved to modal component for better UX
  });
};

export const useRentTransactions = () => {
  return useQuery({
    queryKey: paymentsKeys.transactions(),
    queryFn: getRentTransactions,
    staleTime: 1000 * 60 * 2, // 2 minutes
  });
};

export const useRentTransaction = (transactionId: string | null) => {
  return useQuery({
    queryKey: paymentsKeys.transaction(transactionId || ''),
    queryFn: () => (transactionId ? getRentTransaction(transactionId) : null),
    enabled: !!transactionId,
  });
};

// ============================================================================
// Autopay
// ============================================================================

export const useAutopayStatus = (leaseId: number | undefined) => {
  return useQuery({
    queryKey: paymentsKeys.autopay(),
    queryFn: () => getAutopayStatus(leaseId!),
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: !!leaseId,
  });
};

export const useEnrollAutopay = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ leaseId, paymentMethodId }: { leaseId: number; paymentMethodId: string }) =>
      enrollAutopay(leaseId, paymentMethodId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: paymentsKeys.autopay() });
      toast.success('Autopay enrolled successfully');
    },
    onError: (error: Error) => {
      Sentry.captureException(error, {
        tags: {
          component: 'usePayments',
          action: 'enroll_autopay',
        },
      });
      toast.error('Failed to enroll in autopay');
    },
  });
};

export const useCancelAutopay = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (leaseId: number) => cancelAutopay(leaseId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: paymentsKeys.autopay() });
      toast.success('Autopay cancelled successfully');
    },
    onError: (error: Error) => {
      Sentry.captureException(error, {
        tags: {
          component: 'usePayments',
          action: 'cancel_autopay',
        },
      });
      toast.error('Failed to cancel autopay');
    },
  });
};


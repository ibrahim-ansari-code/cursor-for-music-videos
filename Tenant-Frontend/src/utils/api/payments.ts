/**
 * Tenant Payment API
 * API calls for rent payment functionality
 */

import { apiRequest } from './core';
import type {
  TenantBalance,
  SavedPaymentMethod,
  SetupIntentResponse,
  PaymentIntentResponse,
  RentTransaction,
  AutopayStatus,
  FeeListResponse,
} from '@/types/payments';

// ============================================================================
// Balance & Fees
// ============================================================================

/**
 * Get tenant's current rent balance
 */
export const getTenantBalance = async (): Promise<TenantBalance> => {
  const result = await apiRequest<TenantBalance>('/rent-payments/balance');
  if (!result) {
    throw new Error('No balance data returned');
  }
  return result;
};

/**
 * Get platform fees for different payment methods
 */
export const getPlatformFees = async (): Promise<FeeListResponse> => {
  const result = await apiRequest<FeeListResponse>('/rent-payments/fees');
  if (!result) {
    throw new Error('No fee data returned');
  }
  return result;
};

// ============================================================================
// Payment Methods
// ============================================================================

/**
 * Create a SetupIntent for adding a new payment method
 */
export const createSetupIntent = async (): Promise<SetupIntentResponse> => {
  const result = await apiRequest<SetupIntentResponse>('/rent-payments/payment-methods/setup-intent', {
    method: 'POST',
  });
  if (!result) {
    throw new Error('No setup intent returned');
  }
  return result;
};

/**
 * Save a payment method after Stripe confirmation
 */
export const savePaymentMethod = async (
  stripePaymentMethodId: string,
  setAsDefault: boolean = false
): Promise<SavedPaymentMethod> => {
  const result = await apiRequest<SavedPaymentMethod>('/rent-payments/payment-methods', {
    method: 'POST',
    body: JSON.stringify({
      stripe_payment_method_id: stripePaymentMethodId,
      set_as_default: setAsDefault,
    }),
  });
  if (!result) {
    throw new Error('No payment method returned');
  }
  return result;
};

/**
 * Get all saved payment methods
 */
export const getPaymentMethods = async (): Promise<SavedPaymentMethod[]> => {
  try {
    const result = await apiRequest<{ items: SavedPaymentMethod[]; default_id: string | null }>(
      '/rent-payments/payment-methods'
    );
    if (!result) {
      return [];
    }
    return result.items || [];
  } catch (error) {
    console.error('Error fetching payment methods:', error);
    return [];
  }
};

/**
 * Delete a saved payment method
 */
export const deletePaymentMethod = async (paymentMethodId: string): Promise<void> => {
  await apiRequest(`/rent-payments/payment-methods/${paymentMethodId}`, {
    method: 'DELETE',
  });
};

/**
 * Set a payment method as default
 */
export const setDefaultPaymentMethod = async (paymentMethodId: string): Promise<SavedPaymentMethod> => {
  const result = await apiRequest<SavedPaymentMethod>(
    `/rent-payments/payment-methods/${paymentMethodId}/default`,
    {
      method: 'POST',
    }
  );
  if (!result) {
    throw new Error('No payment method returned');
  }
  return result;
};

// ============================================================================
// Rent Payments
// ============================================================================

/**
 * Create a PaymentIntent for rent payment
 */
export const createRentPaymentIntent = async (
  leaseId: number,
  amountCents: number,
  paymentMethodId: string | null
): Promise<PaymentIntentResponse> => {
  const result = await apiRequest<PaymentIntentResponse>('/rent-payments/payments', {
    method: 'POST',
    body: JSON.stringify({
      lease_id: leaseId,
      amount_cents: amountCents,
      payment_method_id: paymentMethodId,
    }),
  });
  if (!result) {
    throw new Error('No payment intent returned');
  }
  return result;
};

/**
 * Get rent payment transaction history
 */
export const getRentTransactions = async (): Promise<RentTransaction[]> => {
  try {
    const result = await apiRequest<{ items: RentTransaction[]; total: number; has_more: boolean }>('/rent-payments/transactions');
    if (!result) {
      return [];
    }
    return result.items || [];
  } catch (error) {
    console.error('Error fetching rent transactions:', error);
    return [];
  }
};

/**
 * Get a specific rent payment transaction
 */
export const getRentTransaction = async (transactionId: string): Promise<RentTransaction> => {
  const result = await apiRequest<RentTransaction>(`/rent-payments/transactions/${transactionId}`);
  if (!result) {
    throw new Error('No transaction returned');
  }
  return result;
};

// ============================================================================
// Autopay
// ============================================================================

/**
 * Enroll in autopay
 */
export const enrollAutopay = async (
  leaseId: number,
  paymentMethodId: string
): Promise<AutopayStatus> => {
  const result = await apiRequest<AutopayStatus>('/rent-payments/autopay/enroll', {
    method: 'POST',
    body: JSON.stringify({
      lease_id: leaseId,
      payment_method_id: paymentMethodId,
    }),
  });
  if (!result) {
    throw new Error('No autopay status returned');
  }
  return result;
};

/**
 * Get autopay enrollment status
 */
export const getAutopayStatus = async (leaseId: number): Promise<AutopayStatus> => {
  const result = await apiRequest<AutopayStatus>(`/rent-payments/autopay/${leaseId}`);
  if (!result) {
    throw new Error('No autopay status returned');
  }
  return result;
};

/**
 * Cancel autopay enrollment
 */
export const cancelAutopay = async (leaseId: number): Promise<void> => {
  await apiRequest(`/rent-payments/autopay/${leaseId}`, {
    method: 'DELETE',
  });
};


/**
 * Billing API Client
 * Handles all subscription and payment-related API calls
 */

import { apiRequest } from './core';
import type {
  SubscriptionStatus,
  SubscriptionPlan,
  CheckoutSessionRequest,
  CheckoutSessionResponse,
  CustomerPortalResponse,
} from '../../types/billing';

/**
 * Get current user's subscription status
 * @returns Subscription status details
 */
export async function getSubscriptionStatus(): Promise<SubscriptionStatus> {
  return apiRequest('/billing/status', {
    method: 'GET',
    cache: false, // Always fetch fresh subscription status
  });
}

/**
 * Get available subscription plans
 * @returns List of active subscription plans
 */
export async function getSubscriptionPlans(): Promise<SubscriptionPlan[]> {
  return apiRequest('/billing/plans', {
    method: 'GET',
    cacheMaxAge: 3600, // Cache plans for 1 hour
  });
}

/**
 * Create a Stripe Checkout session for subscription purchase
 * @param request Checkout session configuration
 * @returns Checkout session URL and ID
 */
export async function createCheckoutSession(
  request: CheckoutSessionRequest
): Promise<CheckoutSessionResponse> {
  return apiRequest('/billing/checkout-session', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Create a Stripe Customer Portal session for subscription management
 * Allows users to update payment methods, view invoices, and cancel subscriptions
 * @returns Customer portal URL
 */
export async function createCustomerPortalSession(): Promise<CustomerPortalResponse> {
  return apiRequest('/billing/customer-portal', {
    method: 'POST',
    body: JSON.stringify({}), // Send empty body to satisfy Pydantic model requirement
  });
}

/**
 * Cancel subscription at end of current billing period
 * User retains access until period end
 * @returns Updated subscription status
 */
export async function cancelSubscription(): Promise<SubscriptionStatus> {
  return apiRequest('/billing/cancel', {
    method: 'POST',
  });
}

/**
 * Resume a canceled subscription (if still within current period)
 * @returns Updated subscription status
 */
export async function resumeSubscription(): Promise<SubscriptionStatus> {
  return apiRequest('/billing/resume', {
    method: 'POST',
  });
}

/**
 * Check if error is a 402 Payment Required error
 * @param error Error object from API
 * @returns True if subscription is required
 */
export function isPaymentRequiredError(error: unknown): boolean {
  if (typeof error === 'object' && error !== null) {
    const err = error as { 
      status?: number; 
      data?: { code?: string }; 
      subscriptionRequired?: boolean;
    };
    return (
      err.status === 402 || 
      err.data?.code === 'SUBSCRIPTION_REQUIRED' ||
      err.subscriptionRequired === true
    );
  }
  return false;
}

/**
 * Redirect to billing settings page
 * Used when subscription is required
 */
export function redirectToBilling(): void {
  window.location.href = '/settings?tab=billing';
}


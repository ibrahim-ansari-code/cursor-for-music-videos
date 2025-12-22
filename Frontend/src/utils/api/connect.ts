/**
 * Stripe Connect API Utilities
 * 
 * API calls for landlord Stripe Connect onboarding and management.
 */

import { apiRequest } from './core';
import type {
  ConnectStatusResponse,
  ConnectOnboardingResponse,
  ConnectDashboardLinkResponse,
  FeeScheduleResponse,
  UpdatePaymentPreferencesRequest,
  UpdatePaymentPreferencesResponse,
} from '../../types/rentPayments';

const BASE_PATH = '/rent-payments';

// =============================================================================
// Connect Account Status
// =============================================================================

/**
 * Get the current Connect account status for the landlord.
 */
export async function getConnectStatus(): Promise<ConnectStatusResponse> {
  return apiRequest<ConnectStatusResponse>(`${BASE_PATH}/connect/status`, {
    method: 'GET',
  });
}

/**
 * Start the Stripe Connect onboarding process.
 * Returns a URL to redirect the landlord to Stripe.
 */
export async function startConnectOnboarding(): Promise<ConnectOnboardingResponse> {
  return apiRequest<ConnectOnboardingResponse>(`${BASE_PATH}/connect/onboard`, {
    method: 'POST',
  });
}

/**
 * Get a new onboarding link if the previous one expired.
 */
export async function refreshConnectLink(): Promise<ConnectOnboardingResponse> {
  return apiRequest<ConnectOnboardingResponse>(`${BASE_PATH}/connect/refresh-link`, {
    method: 'POST',
  });
}

/**
 * Get a link to the Stripe Express Dashboard.
 * Allows landlords to manage their payout settings.
 */
export async function getStripeDashboardLink(): Promise<ConnectDashboardLinkResponse> {
  return apiRequest<ConnectDashboardLinkResponse>(`${BASE_PATH}/connect/dashboard-link`, {
    method: 'POST',
  });
}

// =============================================================================
// Fee Schedule
// =============================================================================

/**
 * Get the platform fee schedule by payment method.
 */
export async function getFeeSchedule(): Promise<FeeScheduleResponse> {
  return apiRequest<FeeScheduleResponse>(`${BASE_PATH}/fees`, {
    method: 'GET',
  });
}

// =============================================================================
// Payment Preferences
// =============================================================================

/**
 * Update which payment methods the landlord accepts from tenants.
 *
 * @param acceptedPaymentMethods - Array of payment methods: 'card' ($8 fee), 'acss_debit' ($3 fee)
 */
export async function updatePaymentPreferences(
  acceptedPaymentMethods: UpdatePaymentPreferencesRequest['accepted_payment_methods']
): Promise<UpdatePaymentPreferencesResponse> {
  return apiRequest<UpdatePaymentPreferencesResponse>(`${BASE_PATH}/connect/payment-preferences`, {
    method: 'PATCH',
    body: JSON.stringify({ accepted_payment_methods: acceptedPaymentMethods }),
  });
}


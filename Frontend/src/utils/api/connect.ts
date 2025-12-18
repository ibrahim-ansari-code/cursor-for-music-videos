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


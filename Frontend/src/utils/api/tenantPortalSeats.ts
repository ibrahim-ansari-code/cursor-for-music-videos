/**
 * Tenant Portal Seats API Client
 * Handles seat-based licensing for tenant portal access
 */

import { apiRequest } from './core';

/**
 * Seat availability response
 */
export interface SeatAvailability {
  limit: number;
  used: number;
  available: number;
  free_seats: number;
  purchased_seats: number;
}

/**
 * Request to subscribe to seats
 */
export interface SubscribeToSeatsRequest {
  quantity: number;
  success_url: string;
  cancel_url: string;
}

/**
 * Checkout session response
 */
export interface CheckoutSessionResponse {
  checkout_url: string;
  session_id: string;
}

/**
 * Request to update subscription quantity
 */
export interface UpdateSubscriptionQuantityRequest {
  new_quantity: number;
}

/**
 * Get current seat availability for the authenticated landlord
 * @returns Real-time seat usage (GitHub-style)
 */
export async function getSeatAvailability(): Promise<SeatAvailability> {
  return apiRequest('/tenant-portal-seats/availability', {
    method: 'GET',
    cache: false, // Always fetch fresh seat availability
  });
}

/**
 * Create Stripe Checkout session to subscribe to seats
 * @param request Subscription request with quantity and URLs
 * @returns Checkout session URL and ID
 */
export async function subscribeToSeats(
  request: SubscribeToSeatsRequest
): Promise<CheckoutSessionResponse> {
  return apiRequest('/tenant-portal-seats/subscribe', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Update existing seat subscription quantity
 * @param request New quantity
 */
export async function updateSubscriptionQuantity(
  request: UpdateSubscriptionQuantityRequest
): Promise<{ message: string }> {
  return apiRequest('/tenant-portal-seats/subscription/quantity', {
    method: 'PATCH',
    body: JSON.stringify(request),
  });
}

/**
 * Cancel seat subscription
 * @param immediately If true, cancel now. If false, cancel at period end.
 */
export async function cancelSubscription(
  immediately: boolean = false
): Promise<{ message: string }> {
  return apiRequest(`/tenant-portal-seats/subscription?immediately=${immediately}`, {
    method: 'DELETE',
  });
}

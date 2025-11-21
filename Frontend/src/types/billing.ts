/**
 * Billing and Subscription Type Definitions
 * Matches backend schemas from Backend/api/billing/schemas.py
 */

export interface SubscriptionPlan {
  id: string;
  name: string;
  description?: string;
  stripe_product_id: string;
  stripe_price_id: string;
  amount: number;
  currency: string;
  interval: 'day' | 'week' | 'month' | 'year';
  interval_count: number;
  trial_period_days: number;
  is_active: boolean;
  features: string[];
  created_at: string;
  updated_at: string;
}

export interface SubscriptionStatus {
  has_active_subscription: boolean;
  subscription_status: 'none' | 'active' | 'canceled' | 'past_due' | 'trialing' | 'incomplete' | 'incomplete_expired' | 'unpaid';
  subscription_tier: string;
  trial_active: boolean;
  trial_days_remaining?: number;
  trial_ends_at?: string;
  current_period_end?: string;
  cancel_at_period_end: boolean;
  subscription_details?: SubscriptionPlan;  // Full plan details, matching backend SubscriptionPlanResponse
}

export interface CheckoutSessionRequest {
  price_id: string;
  success_url?: string;
  cancel_url?: string;
}

export interface CheckoutSessionResponse {
  checkout_session_id: string;
  checkout_url: string;
  expires_at: string;
}

export interface CustomerPortalResponse {
  portal_url: string;
}

export interface BillingError {
  code: string;
  message: string;
  type?: string;
  request_id?: string;
  param?: string;
}

/**
 * HTTP 402 Payment Required error details
 * Returned when user lacks active subscription
 */
export interface PaymentRequiredError {
  code: 'SUBSCRIPTION_REQUIRED';
  message: string;
  subscription_status: string;
  trial_ended: boolean;
  upgrade_url: string;
}


/**
 * Tenant Rent Payment Types
 * Types for Stripe Connect rent payment system
 */

export interface TenantBalance {
  lease_id: number;
  property_name: string;
  unit_name: string | null;
  current_balance_cents: number;
  current_balance: number;
  currency: string;
  due_date: string | null;
  rent_due_day: number;
  monthly_rent_cents: number;
  monthly_rent: number;
  is_past_due: boolean;
  days_overdue: number;
  landlord_name: string;
  landlord_accepts_online_payments: boolean;
}

export interface SavedPaymentMethod {
  id: string;
  payment_method_type: 'acss_debit' | 'card';
  last_four: string;
  brand?: string | null; // For cards
  bank_name?: string | null; // For bank accounts
  exp_month?: number | null; // Card expiry month
  exp_year?: number | null; // Card expiry year
  is_default: boolean;
  is_verified: boolean; // For PAD verification status
  created_at: string;
}

export interface SetupIntentResponse {
  client_secret: string;
  setup_intent_id: string;
}

export interface PaymentIntentResponse {
  client_secret: string;
  payment_intent_id: string;
  stripe_account_id: string;
  amount_cents: number;
  application_fee_cents: number;
  landlord_receives_cents: number;
}

export interface RentTransaction {
  id: string;
  lease_id: string;
  amount_cents: number;
  application_fee_cents: number;
  payment_method_type: 'acss_debit' | 'card' | null;
  payment_method_last_four?: string | null;
  payment_method_bank_name?: string | null;
  stripe_payment_intent_id: string | null;
  stripe_charge_id?: string | null;
  receipt_url?: string | null;
  status: 'pending' | 'processing' | 'succeeded' | 'failed' | 'refunded';
  created_at: string;
  updated_at: string;
  succeeded_at?: string | null;
  failed_at?: string | null;
  failure_code?: string | null;
  failure_message?: string | null;
}

export interface AutopayStatus {
  lease_id: number;
  is_enrolled: boolean;
  is_active: boolean;
  status: 'not_enrolled' | 'active' | 'paused' | 'canceled';
  amount_cents?: number | null;
  amount?: number | null;
  payment_method?: SavedPaymentMethod | null;
  next_scheduled_at?: string | null;
  last_success_at?: string | null;
  last_failure_reason?: string | null;
  enrolled_at?: string | null;
}

export interface FeeDetails {
  payment_method_type: 'acss_debit' | 'card';
  fee_cents: number;
  fee_display: string;
}

export interface FeeListResponse {
  fees: FeeDetails[];
}


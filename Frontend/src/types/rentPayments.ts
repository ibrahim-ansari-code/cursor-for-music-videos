/**
 * Rent Payments Types
 * 
 * TypeScript interfaces for rent payment system (Stripe Connect).
 */

// =============================================================================
// Connect Account Types (Landlord)
// =============================================================================

export type OnboardingStatus = 
  | 'not_started' 
  | 'incomplete' 
  | 'pending_verification' 
  | 'active';

export interface ConnectStatusResponse {
  is_connected: boolean;
  account_id: string | null;
  charges_enabled: boolean;
  payouts_enabled: boolean;
  details_submitted: boolean;
  onboarding_status: OnboardingStatus;
  needs_action: boolean;
  disabled_reason: string | null;
  requirements_currently_due: string[];
  requirements_past_due: string[];
  requirements_eventually_due: string[];
  business_type: string | null;
  country: string | null;
  default_currency: string | null;
}

export interface ConnectOnboardingResponse {
  account_id: string;
  onboarding_url: string;
  expires_at: string;
}

export interface ConnectDashboardLinkResponse {
  dashboard_url: string;
  expires_at: string;
}

// =============================================================================
// Fee Types
// =============================================================================

export interface FeeScheduleItem {
  payment_method_type: string;
  display_name: string;
  fee_cents: number;
  fee_display: string;
}

export interface FeeScheduleResponse {
  fees: FeeScheduleItem[];
  currency: string;
}

// =============================================================================
// Payment Types
// =============================================================================

export type PaymentSource = 'manual' | 'quickbooks' | 'online_bank' | 'online_card';

export interface Payment {
  id: number;
  user_id: string;
  tenant_id: number;
  lease_id: number;
  amount: number;
  payment_date: string;
  payment_method: string;
  status: string;
  transaction_reference: string | null;
  description: string | null;
  receipt_url: string | null;
  reduction_amount: number | null;
  reduction_reason: string | null;
  quickbooks_id: string | null;
  created_at: string;
  updated_at: string;
  // Derived fields
  tenant_name?: string;
  property_name?: string;
  tenant?: {
    first_name?: string;
    last_name?: string;
    email?: string;
  };
  // Online payment metadata
  stripe_payment_intent_id?: string;
  source?: PaymentSource;
}

export interface PaginatedPaymentsResponse {
  items: Payment[];
  total: number;
  has_more: boolean;
}

// =============================================================================
// Payment Filters
// =============================================================================

export interface PaymentFilters {
  status: string;
  dateRange: string;
  search: string;
}

export interface PaymentQueryParams {
  payment_status?: string;
  search?: string;
  limit: number;
  offset: number;
  start_date?: string;
  end_date?: string;
}

// =============================================================================
// CSV Types
// =============================================================================

export interface CSVHeader {
  label: string;
  key: string;
}

export interface CSVImportHeader {
  key: string;
  label: string;
  required: boolean;
  type?: 'string' | 'number' | 'date';
  aliases?: string[];
}

export interface CSVImportConfig {
  title: string;
  description: string;
  apiFunction: (data: unknown[]) => Promise<unknown>;
  expectedHeaders: CSVImportHeader[];
  sampleData: Record<string, unknown>[];
  validationTips: string[];
}

// =============================================================================
// Table Column Types
// =============================================================================

export interface TableColumn {
  key: string;
  label: string;
  align: 'left' | 'center' | 'right';
}

// =============================================================================
// Pagination Types
// =============================================================================

export interface PaginationState {
  currentPage: number;
  limit: number;
  hasMore: boolean;
}

// =============================================================================
// Refund Types
// =============================================================================

export type RefundStatus = 'pending' | 'processing' | 'succeeded' | 'failed' | 'canceled';

export type RefundReason = 
  | 'duplicate' 
  | 'fraudulent' 
  | 'requested_by_customer' 
  | 'rent_adjustment' 
  | 'lease_cancellation' 
  | 'overpayment' 
  | 'other';

export interface RefundCreateRequest {
  transaction_id: string;
  amount_cents: number;
  reason: RefundReason;
  notes?: string;
  refund_application_fee: boolean;
}

export interface RefundResponse {
  id: string;
  transaction_id: string;
  stripe_refund_id: string;
  stripe_charge_id: string;
  amount_cents: number;
  amount: number;
  currency: string;
  application_fee_refunded_cents: number | null;
  application_fee_refunded: number | null;
  status: RefundStatus;
  reason: RefundReason;
  notes: string | null;
  failure_reason: string | null;
  initiated_by_user_id: string;
  initiated_by_name: string | null;
  created_at: string;
  succeeded_at: string | null;
  failed_at: string | null;
}

export interface RefundListResponse {
  items: RefundResponse[];
  total: number;
  has_more: boolean;
}

// =============================================================================
// Dispute Types
// =============================================================================

export type DisputeStatus = 
  | 'warning_needs_response' 
  | 'needs_response' 
  | 'under_review' 
  | 'charge_refunded' 
  | 'won' 
  | 'lost';

export interface DisputeResponse {
  id: string;
  transaction_id: string;
  stripe_dispute_id: string;
  stripe_charge_id: string;
  amount_cents: number;
  amount: number;
  currency: string;
  status: DisputeStatus;
  reason: string;
  evidence_due_by: string | null;
  evidence_submitted: boolean;
  evidence_submitted_at: string | null;
  is_charge_refundable: boolean;
  created_at: string;
  closed_at: string | null;
  landlord_notified: boolean;
  landlord_notified_at: string | null;
  needs_attention: boolean;
  days_until_due: number | null;
}

export interface DisputeListResponse {
  items: DisputeResponse[];
  total: number;
  has_more: boolean;
  active_disputes: number;
}


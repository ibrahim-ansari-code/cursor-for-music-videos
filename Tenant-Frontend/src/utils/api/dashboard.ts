// Tenant Portal Dashboard API Functions
import { apiRequest } from './core';

// ============================================================================
// Types
// ============================================================================

export interface TenantMyUnitSection {
  unit_id: number;
  unit_name: string;
  property_id: number;
  property_name: string;
  full_address: string;
  lease_start: string;
  lease_end: string;
}

export interface TenantMonthlyRentSection {
  amount: string;
  rent_due_day: number;
  has_active_lease: boolean;
  last_payment_date: string;
}

export interface TenantNextPaymentSection {
  // Balance info (actual outstanding balance)
  current_balance: string;
  current_balance_cents: number;

  // Due date info
  due_date: string;
  days_remaining: number;

  // Status flags
  is_overdue: boolean;
  is_paid: boolean;

  // Autopay info
  has_autopay: boolean;
  autopay_status: 'not_enrolled' | 'active' | 'paused' | 'canceled';
  next_autopay_date: string | null;
}

export interface TenantMaintenanceSection {
  open_requests: number;
  last_updated: string;
}

export interface TenantDashboardResponse {
  my_unit: TenantMyUnitSection;
  monthly_rent: TenantMonthlyRentSection;
  next_payment: TenantNextPaymentSection;
  maintenance: TenantMaintenanceSection;
}

// ============================================================================
// API Functions
// ============================================================================

export const fetchTenantDashboard = async (): Promise<TenantDashboardResponse> => {
  const result = await apiRequest<TenantDashboardResponse>('/dashboard/tenant');
  if (!result) {
    throw new Error('No dashboard data returned');
  }
  return result;
};

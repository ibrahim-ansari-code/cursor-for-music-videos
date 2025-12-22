/**
 * Dashboard component types
 * Shared types for tenant dashboard components
 */

import type { TenantDashboardResponse } from '@/utils/api/dashboard';

// Re-export API types for convenience
export type { TenantDashboardResponse } from '@/utils/api/dashboard';

/**
 * Props for dashboard card components
 */
export interface MyUnitCardProps {
  data: TenantDashboardResponse['my_unit'];
}

export interface MonthlyRentCardProps {
  data: TenantDashboardResponse['monthly_rent'];
}

export interface NextPaymentCardProps {
  data: TenantDashboardResponse['next_payment'];
}

export interface MaintenanceCardProps {
  data: TenantDashboardResponse['maintenance'];
}

/**
 * Props for dashboard header
 */
export interface DashboardHeaderProps {
  firstName: string;
}

/**
 * Date formatting helpers
 */
export const formatDate = (dateStr: string): string => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return '';
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
};

export const formatShortDate = (dateStr: string): string => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return '';
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
};

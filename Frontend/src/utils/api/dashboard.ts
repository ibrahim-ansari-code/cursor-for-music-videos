// Dashboard API Functions
import { apiRequest, formatQueryString } from './core';

export interface DashboardParams {
  property_id?: number | string;
  time_period?: string;
  start_date?: string;
  end_date?: string;
}

export interface DashboardSummary {
  total_properties: number;
  total_units: number;
  occupied_units: number;
  vacancy_rate: number | string;
  monthly_revenue: number | string;
  monthly_expenses: number | string;
  outstanding_rent: number | string;
  maintenance_expenses: number | string;
}

export interface OccupancyData {
  total_units: number;
  occupied_units: number;
  vacant_units: number;
  occupancy_rate: number | string;
}

export interface RevenueData {
  months: string[];
  revenue: (number | string)[];
  expenses: (number | string)[];
  net_income: (number | string)[];
}

export interface PaymentDue {
  id: number;
  tenant_id: number;
  tenant_name: string;
  amount: number | string;
  due_date: string;
  days_overdue: number | null;
  status: string;
  has_portal_access: boolean;
  tenant_email: string | null;
}

export interface DashboardResponse {
  summary: DashboardSummary;
  occupancy: OccupancyData;
  revenue: RevenueData;
  payments_due: PaymentDue[];
}

export const fetchDashboardData = async (params: DashboardParams = {}): Promise<DashboardResponse> => {
  const queryParams = new URLSearchParams();

  if (params.property_id) queryParams.append("property_id", String(params.property_id));
  if (params.time_period) queryParams.append("time_period", params.time_period);
  if (params.start_date) queryParams.append("start_date", params.start_date);
  if (params.end_date) queryParams.append("end_date", params.end_date);

  const queryString = queryParams.toString();
  return apiRequest(`/dashboard/${formatQueryString(queryString)}`);
};


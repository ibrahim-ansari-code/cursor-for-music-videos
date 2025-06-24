// Dashboard API Functions
import { apiRequest, formatQueryString } from './core';

export const fetchDashboardData = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.property_id) queryParams.append("property_id", params.property_id);
  if (params.time_period) queryParams.append("time_period", params.time_period);

  const queryString = queryParams.toString();
  return apiRequest(`/dashboard${formatQueryString(queryString)}`);
}; 
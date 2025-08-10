// Dashboard API Functions
import { apiRequest, formatQueryString } from './core';

export const fetchDashboardData = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.property_id) queryParams.append("property_id", params.property_id);
  if (params.time_period) queryParams.append("time_period", params.time_period);
  if (params.start_date) queryParams.append("start_date", params.start_date);
  if (params.end_date) queryParams.append("end_date", params.end_date);

  const queryString = queryParams.toString();
  return apiRequest(`/dashboard/${formatQueryString(queryString)}`);
}; 
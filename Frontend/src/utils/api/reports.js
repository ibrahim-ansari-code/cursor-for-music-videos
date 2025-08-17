// Reports API Functions
import { apiRequest, formatQueryString } from './core';

/**
 * Fetches a report summary with optional filtering parameters.
 * @param {Object} [params={}] - Query parameters for generating the report
 * @param {string} [params.report_type] - The type of report to generate
 * @param {string} [params.date_range] - The date range for the report (e.g., "Current Month", "Last Quarter")
 * @param {Array<number|string>} [params.property_ids] - Array of property IDs to include in the report
 * @returns {Promise<Object>} A promise that resolves to the report summary object
 */
export const fetchReportSummary = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.report_type) queryParams.append("report_type", params.report_type);
  if (params.date_range) queryParams.append("date_range", params.date_range);
  if (params.property_ids && params.property_ids.length > 0) {
    params.property_ids.forEach((id) => queryParams.append("property_ids", id));
  }

  const queryString = queryParams.toString();
  return apiRequest(`/reports/summary${formatQueryString(queryString)}`);
}; 
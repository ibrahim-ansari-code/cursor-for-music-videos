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

/**
 * Fetches rent tracker data for a specific month and year.
 * @param {Object} [params={}] - Query parameters for filtering rent tracker data
 * @param {number} [params.month] - The month to fetch data for (1-12)
 * @param {number} [params.year] - The year to fetch data for
 * @param {number} [params.property_id] - The property ID to filter by
 * @returns {Promise<Array<Object>>} A promise that resolves to an array of rent tracking objects
 */
export const fetchRentTracker = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.month) queryParams.append("month", params.month);
  if (params.year) queryParams.append("year", params.year);
  if (params.property_id) queryParams.append("property_id", params.property_id);

  const queryString = queryParams.toString();
  return apiRequest(`/rent-tracker${formatQueryString(queryString)}`);
}; 
/**
 * Rent Tracker API Functions
 * Handles all API calls related to rent tracking and collection management
 */
import { apiRequest, formatQueryString } from './core';

/**
 * Fetches rent tracker data for a specific period.
 * @param {Object} [params={}] - Query parameters for filtering rent tracker data
 * @param {number} [params.month] - The month to fetch data for (1-12)
 * @param {number} [params.year] - The year to fetch data for
 * @param {number} [params.property_id] - The property ID to filter by
 * @param {string} [params.rent_status] - Filter by status (PAID, PARTIAL, DUE, OVERDUE)
 * @param {boolean} [params.include_vacant] - Include vacant units in results
 * @returns {Promise<Array<Object>>} A promise that resolves to an array of rent tracking entries
 */
export const fetchRentTracker = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.month !== undefined && params.month !== null) queryParams.append("month", params.month);
  if (params.year !== undefined && params.year !== null) queryParams.append("year", params.year);
  if (params.property_id !== undefined && params.property_id !== null) queryParams.append("property_id", params.property_id);
  if (params.rent_status !== undefined && params.rent_status !== null) queryParams.append("status", params.rent_status);
  if (params.include_vacant !== undefined) {
    queryParams.append("include_vacant", params.include_vacant);
  }

  const queryString = queryParams.toString();
  return apiRequest(`/accounting/rent-tracker${formatQueryString(queryString)}`);
};

/**
 * Fetches rent tracker summary statistics.
 * @param {Object} [params={}] - Query parameters for filtering
 * @param {number} [params.month] - The month to fetch data for (1-12)
 * @param {number} [params.year] - The year to fetch data for
 * @param {number} [params.property_id] - The property ID to filter by
 * @returns {Promise<Object>} A promise that resolves to summary statistics including:
 * - total_units: Total number of units being tracked
 * - total_expected: Total expected rent for the period
 * - total_collected: Total amount collected for the period
 * - total_outstanding: Total amount outstanding
 * - units_paid: Number of units fully paid
 * - units_partial: Number of units with partial payment
 * - units_due: Number of units with rent due
 * - units_overdue: Number of units with overdue rent
 * - collection_rate: Percentage of rent collected
 */
export const fetchRentTrackerSummary = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.month) queryParams.append("month", params.month);
  if (params.year) queryParams.append("year", params.year);
  if (params.property_id) queryParams.append("property_id", params.property_id);

  const queryString = queryParams.toString();
  return apiRequest(`/accounting/rent-tracker/summary${formatQueryString(queryString)}`);
};

/**
 * Exports rent tracker data to a specified format.
 * @param {Object} params - Export parameters
 * @param {string} params.format - Export format ('csv' or 'pdf')
 * @param {number} [params.month] - The month to export data for
 * @param {number} [params.year] - The year to export data for
 * @param {number} [params.property_id] - The property ID to filter by
 * @returns {Promise<Blob>} A promise that resolves to the exported file as a Blob
 */
export const exportRentTracker = async (params) => {
  if (!params || !params.format) {
    throw new Error('Export format is required');
  }
  
  const queryParams = new URLSearchParams();
  
  queryParams.append("format", params.format);
  if (params.month !== undefined && params.month !== null) queryParams.append("month", params.month);
  if (params.year !== undefined && params.year !== null) queryParams.append("year", params.year);
  if (params.property_id !== undefined && params.property_id !== null) queryParams.append("property_id", params.property_id);

  const queryString = queryParams.toString();
  
  // Note: This endpoint would need to be implemented in the backend
  return apiRequest(`/accounting/rent-tracker/export${formatQueryString(queryString)}`, {
    method: 'GET',
    responseType: 'blob'
  });
};

/**
 * Helper function to format currency values from rent tracker data
 * @param {number|string} value - The value to format
 * @returns {string} Formatted currency string
 */
export const formatCurrency = (value) => {
  const num = parseFloat(value) || 0;
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(num);
};

/**
 * Helper function to get status color classes
 * @param {string} status - The rent status
 * @returns {Object} Object with background and text color classes
 */
export const getStatusColors = (status) => {
  switch (status) {
    case 'PAID':
      return { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-200' };
    case 'PARTIAL':
      return { bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-200' };
    case 'DUE':
      return { bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-200' };
    case 'OVERDUE':
      return { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-200' };
    default:
      return { bg: 'bg-gray-100', text: 'text-gray-800', border: 'border-gray-200' };
  }
};

/**
 * Helper function to calculate summary metrics from rent data
 * @param {Array<Object>} rentData - Array of rent tracking entries
 * @returns {Object} Summary metrics
 */
export const calculateRentMetrics = (rentData) => {
  if (!Array.isArray(rentData) || rentData.length === 0) {
    return {
      totalExpected: 0,
      totalCollected: 0,
      totalOutstanding: 0,
      collectionRate: 0,
      unitCounts: {
        paid: 0,
        partial: 0,
        due: 0,
        overdue: 0
      }
    };
  }

  const totalExpected = rentData.reduce((sum, entry) => 
    sum + (parseFloat(entry.monthly_rent) || 0), 0
  );
  
  const totalCollected = rentData.reduce((sum, entry) => 
    sum + (parseFloat(entry.amount_paid) || 0), 0
  );
  
  const totalOutstanding = rentData.reduce((sum, entry) => 
    sum + (parseFloat(entry.remaining_due) || 0), 0
  );
  
  const collectionRate = totalExpected > 0
    ? Math.round((totalCollected / totalExpected) * 100 * 100) / 100
    : 0;

  const unitCounts = {
    paid: rentData.filter(r => r.status === 'PAID').length,
    partial: rentData.filter(r => r.status === 'PARTIAL').length,
    due: rentData.filter(r => r.status === 'DUE').length,
    overdue: rentData.filter(r => r.status === 'OVERDUE').length
  };

  return {
    totalExpected,
    totalCollected,
    totalOutstanding,
    collectionRate,
    unitCounts
  };
};
// Vendors API Functions
import { apiRequest, formatQueryString, uploadFile } from './core';

/**
 * Fetches a list of vendors with optional filtering parameters.
 * @param {Object} [params={}] - Query parameters for filtering vendors
 * @param {string} [params.status] - Filter vendors by status
 * @param {string} [params.business_type] - Filter vendors by business type
 * @returns {Promise<Array<Object>>} A promise that resolves to an array of vendor objects
 */
export const fetchVendors = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.status) queryParams.append("status", params.status);
  if (params.business_type)
    queryParams.append("business_type", params.business_type);

  const queryString = queryParams.toString();
  return apiRequest(`/vendors${formatQueryString(queryString)}`);
};

/**
 * Fetches a specific vendor by ID.
 * @param {number|string} vendorId - The ID of the vendor to fetch
 * @returns {Promise<Object>} A promise that resolves to the vendor object
 */
export const fetchVendor = async (vendorId) => {
  return apiRequest(`/vendors/${vendorId}/`);
};

/**
 * Creates a new vendor.
 * @param {Object} vendorData - The vendor data to create
 * @param {string} vendorData.name - The vendor's name
 * @param {string} [vendorData.business_type] - The vendor's business type
 * @param {string} [vendorData.status] - The vendor's status
 * @returns {Promise<Object>} A promise that resolves to the created vendor object
 */
export const createVendor = async (vendorData) => {
  return apiRequest("/vendors/", {
    method: "POST",
    body: JSON.stringify(vendorData),
  });
};

/**
 * Updates an existing vendor.
 * @param {number|string} vendorId - The ID of the vendor to update
 * @param {Object} vendorData - The updated vendor data
 * @returns {Promise<Object>} A promise that resolves to the updated vendor object
 */
export const updateVendor = async (vendorId, vendorData) => {
  return apiRequest(`/vendors/${vendorId}/`, {
    method: "PUT",
    body: JSON.stringify(vendorData),
  });
};

/**
 * Updates a vendor's status.
 * @param {number|string} vendorId - The ID of the vendor to update
 * @param {string} status - The new status for the vendor
 * @returns {Promise<Object>} A promise that resolves to the updated vendor object
 */
export const updateVendorStatus = async (vendorId, status) => {
  return apiRequest(`/vendors/${vendorId}/status/`, {
    method: "POST",
    body: JSON.stringify({ status }),
  });
};

/**
 * Uploads a document for a specific vendor.
 * @param {number|string} vendorId - The ID of the vendor to upload document for
 * @param {FormData} formData - The form data containing the file to upload
 * @returns {Promise<Object>} A promise that resolves to the upload result
 */
export const uploadVendorDocument = async (vendorId, formData) => {
  return uploadFile(`/vendors/${vendorId}/upload/`, formData, {
    errorMsg: "Failed to upload vendor document.",
  });
};

/**
 * Fetches all documents for a specific vendor.
 * @param {number|string} vendorId - The ID of the vendor to fetch documents for
 * @returns {Promise<Array<Object>>} A promise that resolves to an array of document objects
 */
export const fetchVendorDocuments = async (vendorId) => {
  return apiRequest(`/vendors/${vendorId}/documents/`);
};

/**
 * Assigns a vendor to a property.
 * @param {number|string} vendorId - The ID of the vendor to assign
 * @param {Object} assignmentData - The assignment data
 * @param {number|string} assignmentData.property_id - The ID of the property to assign to
 * @returns {Promise<Object>} A promise that resolves to the assignment result
 */
export const assignVendorToProperty = async (vendorId, assignmentData) => {
  return apiRequest(`/vendors/${vendorId}/properties/`, {
    method: "POST",
    body: JSON.stringify(assignmentData),
  });
};

/**
 * Gets AI-powered onboarding help for vendors.
 * @param {string} query - The help query or question
 * @returns {Promise<Object>} A promise that resolves to the AI response
 */
export const getVendorOnboardingHelp = async (query) => {
  return apiRequest("/vendors/ai/onboarding-help/", {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}; 
// Maintenance API Functions
import { apiRequest, formatQueryString, uploadFile } from './core';

/**
 * Fetches a summary of maintenance data.
 * @returns {Promise<Object>} A promise that resolves to the maintenance summary object
 */
export const getMaintenanceSummary = async () => {
  return apiRequest("/maintenance/summary/");
};

/**
 * Fetches maintenance requests with optional filtering parameters.
 * @param {Object} [params={}] - Query parameters for filtering maintenance requests
 * @param {string} [params.status] - Filter by request status
 * @param {string} [params.priority] - Filter by request priority
 * @param {string} [params.property_id] - Filter by property ID
 * @param {string} [params.category] - Filter by maintenance category
 * @returns {Promise<Array<Object>>} A promise that resolves to an array of maintenance request objects
 */
export const fetchMaintenanceRequests = async (params = {}) => {
  const queryParams = new URLSearchParams();

  Object.keys(params).forEach((key) => {
    const value = params[key];
    if (value === null || value === undefined || value === "") return;

    if (Array.isArray(value)) {
      value.forEach((v) => queryParams.append(key, v));
    } else {
      queryParams.append(key, value);
    }
  });

  const queryString = queryParams.toString();
  return apiRequest(`/maintenance/requests/${formatQueryString(queryString)}`);
};

/**
 * Creates a new maintenance request.
 * @param {Object} requestData - The maintenance request data to create
 * @param {string} requestData.title - The title of the maintenance request
 * @param {string} requestData.description - The description of the issue
 * @param {string} [requestData.priority] - The priority level of the request
 * @param {string} [requestData.category] - The category of the maintenance request
 * @param {number} [requestData.property_id] - The ID of the associated property
 * @returns {Promise<Object>} A promise that resolves to the created maintenance request object
 */
export const createMaintenanceRequest = async (requestData) => {
  return apiRequest("/maintenance/requests/", {
    method: "POST",
    body: JSON.stringify(requestData),
  });
};

/**
 * Fetches a specific maintenance request by ID.
 * @param {number|string} requestId - The ID of the maintenance request to fetch
 * @returns {Promise<Object>} A promise that resolves to the maintenance request object
 */
export const getMaintenanceRequest = async (requestId) => {
  return apiRequest(`/maintenance/requests/${requestId}/`);
};

/**
 * Updates an existing maintenance request.
 * @param {number|string} requestId - The ID of the maintenance request to update
 * @param {Object} requestData - The updated maintenance request data
 * @returns {Promise<Object>} A promise that resolves to the updated maintenance request object
 */
export const updateMaintenanceRequest = async (requestId, requestData) => {
  return apiRequest(`/maintenance/requests/${requestId}/`, {
    method: "PUT",
    body: JSON.stringify(requestData),
  });
};

/**
 * Deletes a maintenance request.
 * @param {number|string} requestId - The ID of the maintenance request to delete
 * @returns {Promise<void>} A promise that resolves when the request is deleted
 */
export const deleteMaintenanceRequest = async (requestId) => {
  return apiRequest(`/maintenance/requests/${requestId}/`, {
    method: "DELETE",
  });
};

/**
 * Uploads a photo for a maintenance request.
 * @param {File} file - The image file to upload
 * @returns {Promise<string>} A promise that resolves to the uploaded photo URL
 */
export const uploadMaintenancePhoto = async (file) => {
  const data = await uploadFile("/maintenance/upload-photo/", file, {
    formKey: "upload_file",
    errorMsg: "Failed to upload maintenance photo.",
  });
  return data.photo_url;
}; 
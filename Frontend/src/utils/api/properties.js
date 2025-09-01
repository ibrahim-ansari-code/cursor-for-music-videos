// Property Management API Functions
import { apiRequest } from './core';

/**
 * @typedef {import('../../types/property').PropertyCreatePayload} PropertyCreatePayload
 * @typedef {import('../../types/property').PropertyUpdatePayload} PropertyUpdatePayload
 */

/**
 * Fetches properties from the API.
 * @param {object} params - Query parameters for filtering properties.
 * @param {object} [options={}] - Optional request options, e.g., for AbortController.
 * @param {object} [options.headers] - Custom headers for the request.
 * @param {AbortSignal} [options.signal] - An AbortSignal to allow aborting the request.
 * @returns {Promise<Array<object>>} A promise that resolves to an array of property objects.
 */
export const fetchProperties = async (params = {}, options = {}) => {
  const queryParams = new URLSearchParams();

  if (params.owner_id) queryParams.append("owner_id", params.owner_id);
  if (params.property_type)
    queryParams.append("property_type", params.property_type);

  const queryString = queryParams.toString();
  return apiRequest(`/properties/${queryString ? '?' + queryString : ''}`, options);
};

export const fetchPropertyById = async (propertyId) => {
  return apiRequest(`/properties/${propertyId}`);
};

/**
 * @param {PropertyCreatePayload} propertyData
 */
export const createProperty = async (propertyData) => {
  return apiRequest("/properties/", {
    method: "POST",
    body: JSON.stringify(propertyData),
  });
};

/**
 * @param {number} propertyId
 * @param {PropertyUpdatePayload} propertyData
 */
export const updateProperty = async (propertyId, propertyData) => {
  return apiRequest(`/properties/${propertyId}`, {
    method: "PUT",
    body: JSON.stringify(propertyData),
  });
};

export const deleteProperty = async (propertyId) => {
  return apiRequest(`/properties/${propertyId}`, {
    method: "DELETE",
  });
};

 
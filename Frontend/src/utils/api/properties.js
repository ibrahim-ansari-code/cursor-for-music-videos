// Property Management API Functions
import { apiRequest } from './core';

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

export const createProperty = async (propertyData) => {
  return apiRequest("/properties/", {
    method: "POST",
    body: JSON.stringify(propertyData),
  });
};

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

export const fetchPropertyUnits = async (propertyId) => {
  return apiRequest(`/properties/${propertyId}/units`);
};

export const createUnit = async (propertyId, unitData) => {
  return apiRequest(`/properties/${propertyId}/units`, {
    method: "POST",
    body: JSON.stringify(unitData),
  });
};

export const updateUnit = async (unitId, unitData) => {
  // Ensure numeric values are properly formatted
  const formattedData = {
    ...unitData,
    monthly_rent: unitData.monthly_rent
      ? parseFloat(unitData.monthly_rent)
      : null,
    size: unitData.size ? parseFloat(unitData.size) : null,
    bedrooms: unitData.bedrooms ? parseInt(unitData.bedrooms, 10) : null,
    bathrooms: unitData.bathrooms ? parseFloat(unitData.bathrooms) : null,
    floor: unitData.floor ? parseInt(unitData.floor, 10) : null,
    tenant_id: unitData.tenant_id || null,
  };

  return apiRequest(`/units/${unitId}`, {
    method: "PUT",
    body: JSON.stringify(formattedData),
  });
};

export const deleteUnit = async (unitId) => {
  // The response will be null for 204 status, which is OK
  return apiRequest(`/units/${unitId}`, {
    method: "DELETE",
  });
};

export const fetchUnitById = async (unitId) => {
  if (!unitId) {
    throw new Error("Unit ID is required to fetch unit details.");
  }
  return apiRequest(`/units/${unitId}`);
}; 
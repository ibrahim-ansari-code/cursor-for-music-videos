// Unit Management API Functions
import { apiRequest } from './core';

/**
 * Fetches all units for a specific property
 * @param {number} propertyId - The ID of the property
 * @returns {Promise<Array<object>>} A promise that resolves to an array of unit objects
 */
export const fetchPropertyUnits = async (propertyId) => {
  return apiRequest(`/properties/${propertyId}/units`);
};

/**
 * Fetches a single unit by ID
 * @param {number} unitId - The ID of the unit
 * @returns {Promise<object>} A promise that resolves to a unit object
 */
export const fetchUnitById = async (unitId) => {
  if (!unitId) {
    throw new Error("Unit ID is required to fetch unit details.");
  }
  return apiRequest(`/units/${unitId}`);
};

/**
 * Creates a new unit for a property
 * @param {number} propertyId - The ID of the property
 * @param {object} unitData - The unit data
 * @returns {Promise<object>} A promise that resolves to the created unit
 */
export const createUnit = async (propertyId, unitData) => {
  return apiRequest(`/properties/${propertyId}/units`, {
    method: "POST",
    body: JSON.stringify(unitData),
  });
};

/**
 * Updates an existing unit
 * @param {number} unitId - The ID of the unit to update
 * @param {object} unitData - The updated unit data
 * @returns {Promise<object>} A promise that resolves to the updated unit
 */
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

/**
 * Deletes a unit
 * @param {number} unitId - The ID of the unit to delete
 * @returns {Promise<void>} A promise that resolves when the unit is deleted
 */
export const deleteUnit = async (unitId) => {
  // The response will be null for 204 status, which is OK
  return apiRequest(`/units/${unitId}`, {
    method: "DELETE",
  });
};

/**
 * Fetches the active lease for a unit
 * @param {number} unitId - The ID of the unit
 * @returns {Promise<object>} A promise that resolves to the lease object
 */
export const fetchUnitLease = async (unitId) => {
  if (!unitId) {
    throw new Error("Unit ID is required to fetch unit lease.");
  }
  return apiRequest(`/units/${unitId}/lease`);
};

/**
 * Search units with filters
 * @param {object} filters - Search filters (min_rent, max_rent, bedrooms, etc.)
 * @param {object} options - Additional options like pagination
 * @returns {Promise<Array<object>>} A promise that resolves to an array of units
 */
export const searchUnits = async (filters = {}, options = {}) => {
  const { skip = 0, limit = 100 } = options;
  const params = new URLSearchParams();

  // Add pagination
  params.append('skip', skip);
  params.append('limit', limit);

  // Append query parameters to the URL
  const url = `/units/search?${params.toString()}`;

  return apiRequest(url, {
    method: 'POST',
    body: JSON.stringify(filters),
    headers: {
      'Content-Type': 'application/json',
    },
  });
};

/**
 * Bulk create units for a property
 * @param {number} propertyId - The ID of the property
 * @param {object} bulkData - Object containing array of units to create
 * @returns {Promise<object>} A promise that resolves to creation results
 */
export const createUnitsBulk = async (propertyId, bulkData) => {
  return apiRequest(`/properties/${propertyId}/units/bulk`, {
    method: "POST",
    body: JSON.stringify(bulkData),
  });
};

/**
 * Bulk assign tenants to units via CSV data
 * @param {number} propertyId - The ID of the property
 * @param {object} csvData - Object containing array of assignments from CSV
 * @returns {Promise<object>} A promise that resolves to assignment results
 */
export const bulkAssignFromCSV = async (propertyId, csvData) => {
  return apiRequest(`/properties/${propertyId}/units/bulk-assign-csv`, {
    method: "POST",
    body: JSON.stringify(csvData),
  });
};

/**
 * Bulk assign a single tenant to multiple units
 * @param {object} bulkData - Object containing unit IDs and tenant assignment data
 * @returns {Promise<object>} A promise that resolves to assignment results
 */
export const bulkAssignTenant = async (bulkData) => {
  return apiRequest(`/units/bulk-assign`, {
    method: "POST",
    body: JSON.stringify(bulkData),
  });
};
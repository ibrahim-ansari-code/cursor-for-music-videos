// Tenant Management API Functions
import { apiRequest, formatQueryString } from './core';

export const fetchTenants = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.property_id) queryParams.append("property_id", params.property_id);
  if (params.status) queryParams.append("status", params.status);
  if (params.search) queryParams.append("search", params.search);
  if (params.unassigned_only) queryParams.append("unassigned_only", "true");

  const queryString = queryParams.toString();
  return apiRequest(`/tenants/${formatQueryString(queryString)}`);
};

export const fetchTenant = async (tenantId) => {
  return apiRequest(`/tenants/${tenantId}/`);
};

export const createTenant = async (tenantData) => {
  // Backend now handles all normalization and validation.
  // Use the standardized apiRequest helper for consistency
  return apiRequest("/tenants/", {
    method: "POST",
    body: JSON.stringify(tenantData),
  });
};

export const updateTenant = async (tenantId, tenantData) => {
  // Backend now handles all validation and normalization via Pydantic validators
  // No need for frontend data manipulation that could introduce bugs
  return apiRequest(`/tenants/${tenantId}/`, {
    method: "PATCH",
    body: JSON.stringify(tenantData),
  });
};

export const deleteTenant = async (tenantId) => {
  return apiRequest(`/tenants/${tenantId}/`, {
    method: "DELETE",
  });
};

export const fetchTenantsByProperty = async (propertyId) => {
  if (!propertyId) {
    console.error("fetchTenantsByProperty called without propertyId");
    return []; // Return empty array instead of throwing
  }

  try {
    // Use fetchTenants with property_id parameter to avoid duplicate logic
    return await fetchTenants({ property_id: propertyId });
  } catch (error) {
    console.error("Error in fetchTenantsByProperty:", error);
    return []; // Return empty array on error to avoid breaking the UI
  }
}; 
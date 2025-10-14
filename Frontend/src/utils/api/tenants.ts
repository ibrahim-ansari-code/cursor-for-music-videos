// Tenant Management API Functions
import { apiRequest, formatQueryString } from './core';
import { EnrichedTenant, Tenant, TenantStatus, EmergencyContact } from '../../types/tenant';

export interface FetchTenantsParams {
  property_id?: number;
  status?: TenantStatus;
  search?: string;
  unassigned_only?: boolean;
}

export const fetchTenants = async (params: FetchTenantsParams = {}): Promise<EnrichedTenant[]> => {
  const queryParams = new URLSearchParams();

  if (params.property_id) queryParams.append("property_id", params.property_id.toString());
  if (params.status) queryParams.append("status", params.status);
  if (params.search) queryParams.append("search", params.search);
  if (params.unassigned_only) queryParams.append("unassigned_only", "true");

  const queryString = queryParams.toString();
  return apiRequest(`/tenants/${formatQueryString(queryString)}`);
};

export const fetchTenant = async (tenantId: number): Promise<EnrichedTenant> => {
  return apiRequest(`/tenants/${tenantId}`);
};

export const createTenant = async (tenantData: Partial<Tenant>): Promise<Tenant> => {
  // Backend now handles all normalization and validation.
  // Use the standardized apiRequest helper for consistency
  return apiRequest("/tenants/", {
    method: "POST",
    body: JSON.stringify(tenantData),
  });
};

export const updateTenant = async (tenantId: number, tenantData: Partial<Tenant>): Promise<Tenant> => {
  // Backend now handles all validation and normalization via Pydantic validators
  // No need for frontend data manipulation that could introduce bugs
  return apiRequest(`/tenants/${tenantId}`, {
    method: "PATCH",
    body: JSON.stringify(tenantData),
  });
};

export const deleteTenant = async (tenantId: number): Promise<void> => {
  return apiRequest(`/tenants/${tenantId}`, {
    method: "DELETE",
  });
};

export const fetchTenantsByProperty = async (propertyId: number): Promise<EnrichedTenant[]> => {
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

// === Emergency Contact Atomic Operations ===

/**
 * Atomically adds a new emergency contact to a tenant.
 * Backend handles primary contact logic automatically.
 */
export const addEmergencyContact = async (
  tenantId: number,
  contactData: Omit<EmergencyContact, 'id'>
): Promise<EmergencyContact> => {
  return apiRequest(`/tenants/${tenantId}/emergency-contacts`, {
    method: "POST",
    body: JSON.stringify(contactData),
  });
};

/**
 * Atomically updates an existing emergency contact.
 * Supports partial updates. Backend handles primary contact logic.
 */
export const updateEmergencyContact = async (
  tenantId: number,
  contactId: string,
  contactData: Partial<EmergencyContact>
): Promise<EmergencyContact> => {
  return apiRequest(`/tenants/${tenantId}/emergency-contacts/${contactId}`, {
    method: "PUT",
    body: JSON.stringify(contactData),
  });
};

/**
 * Atomically deletes an emergency contact from a tenant.
 */
export const deleteEmergencyContact = async (
  tenantId: number,
  contactId: string
): Promise<void> => {
  return apiRequest(`/tenants/${tenantId}/emergency-contacts/${contactId}`, {
    method: "DELETE",
  });
}; 
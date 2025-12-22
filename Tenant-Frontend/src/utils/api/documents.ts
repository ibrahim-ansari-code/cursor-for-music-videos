/**
 * Tenant Portal Documents API Functions
 *
 * Provides API access for tenants to view their lease documents
 * and additional documents uploaded by their landlord.
 */
import { apiRequest } from './core';

// ============================================================================
// Types
// ============================================================================

export interface TenantLeaseInfo {
  // IDs needed for document API calls
  lease_id: number;
  tenant_id: number;
  unit_id: number;
  property_id: number;

  // Lease details
  lease_start: string;
  lease_end: string;
  monthly_rent: string;
  rent_due_day: number;
  security_deposit: string;
  security_deposit_paid_date: string | null;

  // Property info
  property_name: string;
  property_address: string;
  unit_name: string;

  // Landlord info
  landlord_name: string;
  landlord_email: string | null;

  // Tenant info
  tenant_name: string;
  tenant_email: string;
}

export interface LeaseDocument {
  id: number;
  name: string;
  file_path: string;
  document_type: string;
  upload_date: string;
  uploaded_by_id: string | null;
}

export interface TenantDocument {
  id: string;
  tenant_id: number;
  uploaded_by: string;
  file_name: string;
  file_path: string;
  file_size: number;
  file_type: string;
  document_category: string;
  document_type: string;
  tags: string[];
  notes: string | null;
  expiry_date: string | null;
  status: 'pending' | 'verified' | 'rejected' | 'expired';
  uploaded_at: string;
  created_at: string;
  updated_at: string;
  // Computed fields
  is_expired?: boolean;
  days_until_expiry?: number | null;
}

export interface TenantDocumentListResponse {
  documents: TenantDocument[];
  total: number;
  limit: number;
  offset: number;
}

export interface SecureUrlResponse {
  secure_url: string;
  expires_at: string;
  expires_in_seconds: number;
}

// ============================================================================
// Lease Info API
// ============================================================================

/**
 * Fetch detailed lease information for the current tenant.
 * Includes IDs needed for document API calls and lease summary.
 */
export const fetchTenantLeaseInfo = async (): Promise<TenantLeaseInfo> => {
  const result = await apiRequest<TenantLeaseInfo>('/dashboard/tenant/lease-info');
  if (!result) {
    throw new Error('No lease info returned');
  }
  return result;
};

// ============================================================================
// Lease Documents API
// ============================================================================

/**
 * Fetch all documents associated with a lease (the main lease agreement).
 */
export const fetchLeaseDocuments = async (leaseId: number): Promise<LeaseDocument[]> => {
  const result = await apiRequest<LeaseDocument[]>(`/leases/${leaseId}/documents`);
  return result || [];
};

/**
 * Get a secure (time-limited SAS token) URL for viewing/downloading a lease document.
 */
export const getLeaseDocumentSecureUrl = async (
  leaseId: number,
  documentId: number
): Promise<SecureUrlResponse> => {
  const result = await apiRequest<SecureUrlResponse>(
    `/leases/${leaseId}/documents/${documentId}/secure-url`
  );
  if (!result) {
    throw new Error('Failed to get secure document URL');
  }
  return result;
};

// ============================================================================
// Tenant Documents API (Additional documents from landlord)
// ============================================================================

/**
 * Fetch documents uploaded by landlord for the tenant.
 * These are "additional documents" like insurance certificates, building rules, etc.
 */
export const fetchTenantDocuments = async (
  tenantId: number,
  options?: {
    category?: string;
    document_type?: string;
    status?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }
): Promise<TenantDocumentListResponse> => {
  const params = new URLSearchParams();

  if (options?.category) params.append('category', options.category);
  if (options?.document_type) params.append('document_type', options.document_type);
  if (options?.status) params.append('status', options.status);
  if (options?.search) params.append('search', options.search);
  if (options?.limit) params.append('limit', options.limit.toString());
  if (options?.offset) params.append('offset', options.offset.toString());

  const queryString = params.toString();
  const endpoint = `/tenants/${tenantId}/documents${queryString ? `?${queryString}` : ''}`;

  const result = await apiRequest<TenantDocumentListResponse>(endpoint);
  if (!result) {
    return { documents: [], total: 0, limit: 20, offset: 0 };
  }
  return result;
};

/**
 * Get a secure (time-limited SAS token) URL for viewing/downloading a tenant document.
 */
export const getTenantDocumentSecureUrl = async (
  tenantId: number,
  documentId: string
): Promise<SecureUrlResponse> => {
  const result = await apiRequest<SecureUrlResponse>(
    `/tenants/${tenantId}/documents/${documentId}/secure-url`
  );
  if (!result) {
    throw new Error('Failed to get secure document URL');
  }
  return result;
};

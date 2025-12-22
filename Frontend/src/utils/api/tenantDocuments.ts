/**
 * Tenant Documents API Client
 * 
 * API functions for tenant document management.
 * Follows patterns from tenants.ts and leases.js for consistency.
 */

import { apiRequest, formatQueryString } from './core';
import {
  TenantDocument,
  DocumentListResponse,
  DocumentFilters,
  DocumentTaxonomy,
  SecureUrlResponse,
  DocumentUpdateData,
  DocumentCategory,
} from '../../types/tenantDocument';

// ============================================================================
// LIST DOCUMENTS
// ============================================================================

/**
 * Fetch list of documents for a tenant with optional filtering
 * 
 * @param tenantId - Tenant UUID
 * @param filters - Optional filter parameters
 * @returns Paginated list of documents
 */
export const fetchTenantDocuments = async (
  tenantId: string,
  filters: DocumentFilters = {}
): Promise<DocumentListResponse> => {
  const queryParams = new URLSearchParams();
  
  if (filters.search) queryParams.append('search', filters.search);
  if (filters.category) queryParams.append('category', filters.category);
  if (filters.type) queryParams.append('document_type', filters.type);
  if (filters.status) queryParams.append('status', filters.status);
  if (filters.date_from) queryParams.append('date_from', filters.date_from);
  if (filters.date_to) queryParams.append('date_to', filters.date_to);
  
  // Default pagination
  const limit = 20;
  const offset = 0;
  queryParams.append('limit', limit.toString());
  queryParams.append('offset', offset.toString());
  
  const queryString = queryParams.toString();
  return apiRequest(`/tenants/${tenantId}/documents${formatQueryString(queryString)}`);
};

// ============================================================================
// UPLOAD DOCUMENT
// ============================================================================

/**
 * Upload a new document for a tenant
 * 
 * @param tenantId - Tenant UUID
 * @param formData - FormData with file and metadata
 * @returns Created document details
 */
export const uploadTenantDocument = async (
  tenantId: string,
  formData: FormData
): Promise<TenantDocument> => {
  return apiRequest(`/tenants/${tenantId}/documents`, {
    method: 'POST',
    body: formData,
  });
};

// ============================================================================
// GET DOCUMENT DETAILS
// ============================================================================

/**
 * Get details of a specific document
 * 
 * @param tenantId - Tenant UUID
 * @param documentId - Document UUID
 * @returns Document details
 */
export const fetchTenantDocument = async (
  tenantId: string,
  documentId: string
): Promise<TenantDocument> => {
  return apiRequest(`/tenants/${tenantId}/documents/${documentId}`);
};

// ============================================================================
// GET SECURE URL
// ============================================================================

/**
 * Generate time-limited secure URL for document access
 * 
 * Follows same pattern as lease documents secure URL generation.
 * Returns SAS token URL that expires in 1 hour.
 * 
 * @param tenantId - Tenant UUID
 * @param documentId - Document UUID
 * @returns Secure URL with expiration info
 */
export const getSecureTenantDocumentUrl = async (
  tenantId: string,
  documentId: string
): Promise<SecureUrlResponse> => {
  return apiRequest(`/tenants/${tenantId}/documents/${documentId}/secure-url`);
};

// ============================================================================
// UPDATE DOCUMENT
// ============================================================================

/**
 * Update document metadata (tags, notes, status, expiry)
 * 
 * Note: File itself cannot be updated. Upload new document instead.
 * 
 * @param tenantId - Tenant UUID
 * @param documentId - Document UUID
 * @param data - Fields to update
 * @returns Updated document details
 */
export const updateTenantDocument = async (
  tenantId: string,
  documentId: string,
  data: DocumentUpdateData
): Promise<TenantDocument> => {
  return apiRequest(`/tenants/${tenantId}/documents/${documentId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
};

// ============================================================================
// DELETE DOCUMENT
// ============================================================================

/**
 * Delete a document (file and database record)
 * 
 * Warning: This action cannot be undone.
 * 
 * @param tenantId - Tenant UUID
 * @param documentId - Document UUID
 * @returns void (204 No Content)
 */
export const deleteTenantDocument = async (
  tenantId: string,
  documentId: string
): Promise<void> => {
  return apiRequest(`/tenants/${tenantId}/documents/${documentId}`, {
    method: 'DELETE',
  });
};

// ============================================================================
// GET TAXONOMY
// ============================================================================

/**
 * Fetch complete document taxonomy (categories and types)
 * 
 * This is static reference data that should be cached long-term.
 * No authentication required.
 * 
 * @returns Complete category/type hierarchy
 */
export const fetchDocumentTaxonomy = async (): Promise<DocumentTaxonomy> => {
  return apiRequest('/document-types/taxonomy');
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Build FormData for document upload
 *
 * Helper function to construct FormData object from upload data.
 *
 * @param file - File to upload
 * @param metadata - Document metadata
 * @returns FormData ready for upload
 */
export function buildDocumentFormData(
  file: File,
  metadata: {
    document_name?: string;
    document_category: DocumentCategory;
    document_type: string;
    tags?: string[];
    notes?: string;
    expiry_date?: string | null;
  }
): FormData {
  const formData = new FormData();

  // Add file
  formData.append('file', file);

  // Add metadata fields
  formData.append('document_category', metadata.document_category);
  formData.append('document_type', metadata.document_type);

  // Optional fields
  if (metadata.document_name) {
    formData.append('document_name', metadata.document_name);
  }

  if (metadata.tags && metadata.tags.length > 0) {
    formData.append('tags', metadata.tags.join(','));
  }

  if (metadata.notes) {
    formData.append('notes', metadata.notes);
  }

  if (metadata.expiry_date) {
    formData.append('expiry_date', metadata.expiry_date);
  }

  return formData;
}



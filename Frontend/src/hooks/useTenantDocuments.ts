/**
 * Tenant Documents React Query Hooks
 * 
 * Custom hooks for tenant document management using TanStack Query.
 * Provides queries for fetching documents and mutations for CRUD operations.
 * 
 * Hooks:
 * - useTenantDocuments: Fetch documents with filters
 * - useDocumentTaxonomy: Fetch category/type taxonomy (cached long-term)
 * - useUploadTenantDocument: Mutation for uploading
 * - useUpdateTenantDocument: Mutation for updating metadata
 * - useDeleteTenantDocument: Mutation for deleting
 */

import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from '@tanstack/react-query';
import { QUERY_KEYS } from './queryKeys';
import {
  fetchTenantDocuments,
  fetchTenantDocument,
  uploadTenantDocument,
  updateTenantDocument,
  deleteTenantDocument,
  fetchDocumentTaxonomy,
  buildDocumentFormData,
} from '../utils/api/tenantDocuments';
import {
  TenantDocument,
  DocumentListResponse,
  DocumentFilters,
  DocumentTaxonomy,
  DocumentUpdateData,
  DocumentCategory,
} from '../types/tenantDocument';

// ============================================================================
// QUERY HOOKS
// ============================================================================

/**
 * Fetch documents for a tenant with optional filtering
 * 
 * @param tenantId - Tenant UUID (use string from tenant.id)
 * @param filters - Optional filter parameters
 * @returns Query result with paginated documents
 */
export const useTenantDocuments = (
  tenantId: string | undefined,
  filters: DocumentFilters = {}
): UseQueryResult<DocumentListResponse, Error> => {
  return useQuery({
    queryKey: QUERY_KEYS.tenantDocuments.list(tenantId, filters),
    queryFn: () => fetchTenantDocuments(tenantId!, filters),
    enabled: !!tenantId,
    staleTime: 1 * 60 * 1000, // 1 minute - documents don't change frequently
  });
};

/**
 * Fetch single document details
 * 
 * @param tenantId - Tenant UUID
 * @param documentId - Document UUID
 * @returns Query result with document details
 */
export const useTenantDocument = (
  tenantId: string | undefined,
  documentId: string | undefined
): UseQueryResult<TenantDocument, Error> => {
  return useQuery({
    queryKey: QUERY_KEYS.tenantDocuments.detail(tenantId, documentId),
    queryFn: () => fetchTenantDocument(tenantId!, documentId!),
    enabled: !!tenantId && !!documentId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

/**
 * Fetch document taxonomy (categories and types)
 * 
 * This is static reference data cached for the entire session.
 * 
 * @returns Query result with complete taxonomy
 */
export const useDocumentTaxonomy = (): UseQueryResult<DocumentTaxonomy, Error> => {
  return useQuery({
    queryKey: QUERY_KEYS.tenantDocuments.taxonomy(),
    queryFn: fetchDocumentTaxonomy,
    staleTime: 60 * 60 * 1000, // 1 hour - taxonomy rarely changes
    gcTime: 60 * 60 * 1000, // Keep in cache for 1 hour
  });
};

// ============================================================================
// MUTATION HOOKS
// ============================================================================

interface UploadDocumentParams {
  tenantId: string;
  file: File;
  document_category: DocumentCategory;
  document_type: string;
  tags?: string[];
  notes?: string;
  expiry_date?: string | null;
}

/**
 * Upload a new document for a tenant
 * 
 * @returns Mutation hook for uploading documents
 */
export const useUploadTenantDocument = (): UseMutationResult<
  TenantDocument,
  Error,
  UploadDocumentParams
> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: UploadDocumentParams) => {
      const formData = buildDocumentFormData(params.file, {
        document_category: params.document_category,
        document_type: params.document_type,
        tags: params.tags,
        notes: params.notes,
        expiry_date: params.expiry_date,
      });
      
      return uploadTenantDocument(params.tenantId, formData);
    },
    onSuccess: (_data, variables) => {
      // Invalidate document list for this tenant
      queryClient.invalidateQueries({ 
        queryKey: QUERY_KEYS.tenantDocuments.lists() 
      });
      
      // Also invalidate tenant detail query (may include document counts)
      queryClient.invalidateQueries({ 
        queryKey: QUERY_KEYS.tenants.detail(Number(variables.tenantId)) 
      });
    },
  });
};

interface UpdateDocumentParams {
  tenantId: string;
  documentId: string;
  data: DocumentUpdateData;
}

/**
 * Update document metadata
 * 
 * @returns Mutation hook for updating documents
 */
export const useUpdateTenantDocument = (): UseMutationResult<
  TenantDocument,
  Error,
  UpdateDocumentParams
> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: UpdateDocumentParams) => {
      return updateTenantDocument(params.tenantId, params.documentId, params.data);
    },
    onSuccess: (_data, variables) => {
      // Invalidate document list for this tenant
      queryClient.invalidateQueries({ 
        queryKey: QUERY_KEYS.tenantDocuments.lists() 
      });
      
      // Invalidate specific document detail
      queryClient.invalidateQueries({ 
        queryKey: QUERY_KEYS.tenantDocuments.detail(variables.tenantId, variables.documentId) 
      });
    },
  });
};

interface DeleteDocumentParams {
  tenantId: string;
  documentId: string;
}

/**
 * Delete a document
 * 
 * @returns Mutation hook for deleting documents
 */
export const useDeleteTenantDocument = (): UseMutationResult<
  void,
  Error,
  DeleteDocumentParams
> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: DeleteDocumentParams) => {
      return deleteTenantDocument(params.tenantId, params.documentId);
    },
    onSuccess: (_data, variables) => {
      // Invalidate document list for this tenant
      queryClient.invalidateQueries({ 
        queryKey: QUERY_KEYS.tenantDocuments.lists() 
      });
      
      // Remove specific document from cache
      queryClient.removeQueries({ 
        queryKey: QUERY_KEYS.tenantDocuments.detail(variables.tenantId, variables.documentId) 
      });
      
      // Also invalidate tenant detail query
      queryClient.invalidateQueries({ 
        queryKey: QUERY_KEYS.tenants.detail(Number(variables.tenantId)) 
      });
    },
  });
};

// ============================================================================
// EXPORTS
// ============================================================================

export default {
  useTenantDocuments,
  useTenantDocument,
  useDocumentTaxonomy,
  useUploadTenantDocument,
  useUpdateTenantDocument,
  useDeleteTenantDocument,
};



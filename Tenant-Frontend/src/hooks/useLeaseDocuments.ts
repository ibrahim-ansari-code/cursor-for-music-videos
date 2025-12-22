import { useQuery } from '@tanstack/react-query';
import {
  fetchTenantLeaseInfo,
  fetchLeaseDocuments,
  fetchTenantDocuments,
  type TenantLeaseInfo,
  type LeaseDocument,
  type TenantDocument,
} from '@/utils/api/documents';

// Query keys for cache management
export const leaseDocumentsKeys = {
  all: ['tenant', 'lease-documents'] as const,
  leaseInfo: () => [...leaseDocumentsKeys.all, 'info'] as const,
  leaseDocuments: (leaseId: number) => [...leaseDocumentsKeys.all, 'lease', leaseId] as const,
  tenantDocuments: (tenantId: number) => [...leaseDocumentsKeys.all, 'tenant', tenantId] as const,
};

interface UseLeaseDocumentsResult {
  // Lease info with IDs
  leaseInfo: TenantLeaseInfo | undefined;
  leaseInfoLoading: boolean;
  leaseInfoError: Error | null;

  // Lease documents (main lease agreement)
  leaseDocuments: LeaseDocument[];
  leaseDocumentsLoading: boolean;
  leaseDocumentsError: Error | null;

  // Additional documents from landlord
  additionalDocuments: TenantDocument[];
  additionalDocumentsLoading: boolean;
  additionalDocumentsError: Error | null;

  // Combined loading/error state
  isLoading: boolean;
  error: Error | null;

  // Refetch functions
  refetchAll: () => void;
}

/**
 * Hook to fetch all lease document data for the Lease Documents page.
 * Fetches lease info first, then uses the IDs to fetch documents.
 */
export const useLeaseDocuments = (): UseLeaseDocumentsResult => {
  // First, fetch lease info to get lease_id and tenant_id
  const leaseInfoQuery = useQuery({
    queryKey: leaseDocumentsKeys.leaseInfo(),
    queryFn: fetchTenantLeaseInfo,
    staleTime: 10 * 60 * 1000, // Cache for 10 minutes (lease info rarely changes)
    retry: 2,
  });

  const leaseId = leaseInfoQuery.data?.lease_id;
  const tenantId = leaseInfoQuery.data?.tenant_id;

  // Fetch lease documents (depends on lease_id)
  const leaseDocsQuery = useQuery({
    queryKey: leaseDocumentsKeys.leaseDocuments(leaseId || 0),
    queryFn: () => fetchLeaseDocuments(leaseId!),
    enabled: !!leaseId, // Only run when leaseId is available
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });

  // Fetch additional tenant documents (depends on tenant_id)
  const tenantDocsQuery = useQuery({
    queryKey: leaseDocumentsKeys.tenantDocuments(tenantId || 0),
    queryFn: () => fetchTenantDocuments(tenantId!),
    enabled: !!tenantId, // Only run when tenantId is available
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });

  const isLoading =
    leaseInfoQuery.isLoading ||
    (!!leaseId && leaseDocsQuery.isLoading) ||
    (!!tenantId && tenantDocsQuery.isLoading);

  const error = leaseInfoQuery.error || leaseDocsQuery.error || tenantDocsQuery.error;

  const refetchAll = () => {
    leaseInfoQuery.refetch();
    if (leaseId) leaseDocsQuery.refetch();
    if (tenantId) tenantDocsQuery.refetch();
  };

  return {
    leaseInfo: leaseInfoQuery.data,
    leaseInfoLoading: leaseInfoQuery.isLoading,
    leaseInfoError: leaseInfoQuery.error,

    leaseDocuments: leaseDocsQuery.data || [],
    leaseDocumentsLoading: leaseDocsQuery.isLoading,
    leaseDocumentsError: leaseDocsQuery.error,

    additionalDocuments: tenantDocsQuery.data?.documents || [],
    additionalDocumentsLoading: tenantDocsQuery.isLoading,
    additionalDocumentsError: tenantDocsQuery.error,

    isLoading,
    error,
    refetchAll,
  };
};

export default useLeaseDocuments;

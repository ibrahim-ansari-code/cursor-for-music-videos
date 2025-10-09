import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from "@tanstack/react-query";
import { 
  fetchLeases, 
  createLease, 
  updateLease, 
  deleteLease,
  fetchLeaseDocuments,
  uploadLeaseDocument,
} from "../utils/api/leases";
import { QUERY_KEYS } from "./queryKeys";
import type {
  Lease,
  LeaseCreate,
  LeaseUpdate,
  LeaseDocument,
  LeasesQueryParams,
} from "../types/lease";

// Error type for API errors
interface ApiError {
  status?: number;
  statusText?: string;
  data?: {
    detail?: string;
  };
  message?: string;
}

// Main leases hook for Leases page
export const useLeases = (params: LeasesQueryParams = {}): UseQueryResult<Lease[], ApiError> => {
  return useQuery({
    queryKey: QUERY_KEYS.leases.all(params),
    queryFn: () => fetchLeases(params),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

// Lease documents hook
export const useLeaseDocuments = (leaseId: number | null): UseQueryResult<LeaseDocument[], ApiError> => {
  return useQuery({
    queryKey: QUERY_KEYS.leases.documents(leaseId),
    queryFn: () => {
      if (leaseId === null) {
        throw new Error('Lease ID is required');
      }
      return fetchLeaseDocuments(leaseId);
    },
    enabled: !!leaseId,
    staleTime: 5 * 60 * 1000, // 5 minutes for documents
  });
};

// Enhanced leases hook that includes documents
interface LeaseWithDocuments extends Lease {
  documents: LeaseDocument[];
  file_url: string | null;
}

export const useLeasesWithDocuments = (
  params: LeasesQueryParams = {}
): UseQueryResult<LeaseWithDocuments[], ApiError> => {
  const { data: leases = [], isLoading: leasesLoading, error: leasesError } = useLeases(params);
  
  const result = useQuery({
    queryKey: QUERY_KEYS.leases.withDocuments(params),
    queryFn: async (): Promise<LeaseWithDocuments[]> => {
      if (!leases.length) return [];
      
      const leasesWithDocs = await Promise.allSettled(
        leases.map(async (lease): Promise<LeaseWithDocuments> => {
          try {
            const documents = await fetchLeaseDocuments(lease.id);
            const contractDoc = documents.find(
              (doc) =>
                doc.document_type === "contract" ||
                doc.document_type === "lease" ||
                doc.document_type === "agreement"
            ) || documents[0];

            return {
              ...lease,
              documents: documents,
              file_url: contractDoc ? contractDoc.file_path : null,
            };
          } catch (err) {
            console.error(`Failed to fetch documents for lease ${lease.id}:`, err);
            return { ...lease, documents: [], file_url: null };
          }
        })
      );

      // Filter out rejected promises and only return fulfilled lease objects
      return leasesWithDocs
        .filter(result => result.status === 'fulfilled')
        .map(result => (result as PromiseFulfilledResult<LeaseWithDocuments>).value);
    },
    enabled: !!leases.length,
    staleTime: 3 * 60 * 1000, // 3 minutes
  });

  return {
    ...result,
    data: result.data || [],
    isLoading: leasesLoading || result.isLoading,
    error: (leasesError || result.error) as ApiError,
  } as UseQueryResult<LeaseWithDocuments[], ApiError>;
};

// Mutation hooks for lease operations
export const useCreateLease = (): UseMutationResult<Lease, ApiError, LeaseCreate> => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: createLease,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.leases.all() });
    },
  });
};

interface UpdateLeaseVariables {
  leaseId: number;
  leaseData: LeaseUpdate;
}

export const useUpdateLease = (): UseMutationResult<Lease, ApiError, UpdateLeaseVariables> => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ leaseId, leaseData }: UpdateLeaseVariables) => updateLease(leaseId, leaseData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.leases.all() });
    },
  });
};

export const useDeleteLease = (): UseMutationResult<void, ApiError, number> => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: deleteLease,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.leases.all() });
    },
  });
};

interface UploadLeaseDocumentVariables {
  leaseId: number;
  formData: FormData;
}

export const useUploadLeaseDocument = (): UseMutationResult<
  LeaseDocument,
  ApiError,
  UploadLeaseDocumentVariables
> => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ leaseId, formData }: UploadLeaseDocumentVariables) => 
      uploadLeaseDocument(leaseId, formData),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.leases.all() });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.leases.documents(variables.leaseId) });
    },
  });
};

export default useLeases;


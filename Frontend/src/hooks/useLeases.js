import { useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { 
  fetchLeases, 
  createLease, 
  updateLease, 
  deleteLease,
  fetchLeaseDocuments,
  uploadLeaseDocument,
} from "../utils/api/leases";
import { QUERY_KEYS } from "./queryKeys";

// Main leases hook for Leases page
export const useLeases = (params = {}) => {
  return useQuery({
    queryKey: QUERY_KEYS.leases.all(params),
    queryFn: () => fetchLeases(params),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

// Lease documents hook
export const useLeaseDocuments = (leaseId) => {
  return useQuery({
    queryKey: QUERY_KEYS.leases.documents(leaseId),
    queryFn: () => fetchLeaseDocuments(leaseId),
    enabled: !!leaseId,
    staleTime: 5 * 60 * 1000, // 5 minutes for documents
  });
};

// Enhanced leases hook that includes documents
export const useLeasesWithDocuments = (params = {}) => {
  const { data: leases = [], isLoading: leasesLoading, error: leasesError } = useLeases(params);
  
  const { data: leasesWithDocuments, isLoading: documentsLoading, error: documentsError } = useQuery({
    queryKey: QUERY_KEYS.leases.withDocuments(params),
    queryFn: async () => {
      if (!leases.length) return [];
      
      const leasesWithDocs = await Promise.allSettled(
        leases.map(async (lease) => {
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
        .map(result => result.value);
    },
    enabled: !!leases.length,
    staleTime: 3 * 60 * 1000, // 3 minutes
  });

  return {
    data: leasesWithDocuments || [],
    isLoading: leasesLoading || documentsLoading,
    error: leasesError || documentsError,
  };
};

// Mutation hooks for lease operations
export const useCreateLease = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: createLease,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.leases.all() });
    },
  });
};

export const useUpdateLease = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ leaseId, leaseData }) => updateLease(leaseId, leaseData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.leases.all() });
    },
  });
};

export const useDeleteLease = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: deleteLease,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.leases.all() });
    },
  });
};

export const useUploadLeaseDocument = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ leaseId, formData }) => uploadLeaseDocument(leaseId, formData),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.leases.all() });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.leases.documents(variables.leaseId) });
    },
  });
};

export default useLeases;

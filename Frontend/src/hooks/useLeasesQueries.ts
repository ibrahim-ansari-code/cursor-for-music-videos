import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from '@tanstack/react-query';
import * as Sentry from '@sentry/react';
import {
  fetchLeases,
  createLease,
  updateLease,
  deleteLease,
  fetchLeaseDocuments,
  uploadLeaseDocument,
  updateLeaseStatus,
  bulkDeleteLeases,
} from '../utils/api/leases';
import { QUERY_KEYS } from './queryKeys';
import type {
  Lease,
  LeaseCreate,
  LeaseUpdate,
  LeaseDocument,
  LeasesQueryParams,
  LeaseWithDocuments,
  ApiError,
} from '../types/lease';

/**
 * Hook to fetch leases with optional filtering
 * 
 * @param params - Query parameters for filtering
 * @returns Query result with leases array
 * 
 * @example
 * ```tsx
 * const { data: leases, isLoading } = useLeases({ status: 'ACTIVE' });
 * ```
 */
export const useLeases = (params: LeasesQueryParams = {}): UseQueryResult<Lease[], ApiError> => {
  return useQuery({
    queryKey: QUERY_KEYS.leases.all(params),
    queryFn: () => fetchLeases(params),
    staleTime: 5 * 60 * 1000, // 5 minutes - trust optimistic updates, don't auto-refetch
    gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes
  });
};

/**
 * Hook to fetch lease documents
 * 
 * @param leaseId - Lease ID to fetch documents for
 * @returns Query result with documents array
 */
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
    staleTime: 5 * 60 * 1000, // Trust optimistic updates
    gcTime: 10 * 60 * 1000,
  });
};

/**
 * Enhanced leases hook that includes documents for each lease
 * This is the main hook for the Leases page
 * 
 * @param params - Query parameters for filtering
 * @returns Query result with leases and their documents
 * 
 * @example
 * ```tsx
 * const { data: leases, isLoading } = useLeasesWithDocuments({ status: 'ACTIVE' });
 * ```
 */
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
            return {
              ...lease,
              documents: documents || [],
            };
          } catch (err) {
            console.error(`Failed to fetch documents for lease ${lease.id}:`, err);
            return { ...lease, documents: [] };
          }
        })
      );

      // Filter out rejected promises and only return fulfilled lease objects
      return leasesWithDocs
        .filter((result) => result.status === 'fulfilled')
        .map((result) => (result as PromiseFulfilledResult<LeaseWithDocuments>).value);
    },
    enabled: !leasesLoading && leases.length > 0,
    staleTime: 5 * 60 * 1000, // Trust optimistic updates, don't auto-refetch
    gcTime: 10 * 60 * 1000,
  });

  return {
    ...result,
    data: result.data || [],
    isLoading: leasesLoading || result.isLoading,
    error: (leasesError || result.error) as ApiError,
  } as UseQueryResult<LeaseWithDocuments[], ApiError>;
};

/**
 * Mutation hook to create a new lease
 * 
 * Automatically adds to cache optimistically and refetches in background
 * 
 * @returns Mutation result with mutate/mutateAsync functions
 * 
 * @example
 * ```tsx
 * const createMutation = useCreateLease();
 * 
 * const handleSubmit = async (data) => {
 *   await createMutation.mutateAsync(data);
 *   toast.success('Lease created!');
 * };
 * ```
 */
export const useCreateLease = (): UseMutationResult<Lease, ApiError, LeaseCreate> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createLease,
    // True optimistic update: Add to UI BEFORE API call completes
    onMutate: async (newLeaseData) => {
      await queryClient.cancelQueries({ queryKey: ['leases'] });

      const previousData = queryClient.getQueriesData({ queryKey: ['leases'] });

      // Create optimistic lease with temporary ID
      const optimisticLease: Lease = {
        id: Date.now(), // Temporary ID - will be replaced by real ID from server
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        ...newLeaseData,
        status: newLeaseData.status || 'ACTIVE',
      };

      // Filter-aware optimistic update for withDocuments queries
      const withDocsQueries = queryClient.getQueryCache().findAll({ 
        queryKey: ['leases', 'withDocuments'] 
      });
      
      withDocsQueries.forEach((query) => {
        const filters = query.queryKey[2] as LeasesQueryParams | undefined;
        
        const matchesFilter = !filters?.status || 
                             filters.status === 'all' || 
                             filters.status === optimisticLease.status ||
                             filters.status.toUpperCase() === optimisticLease.status.toUpperCase();
        
        if (matchesFilter) {
          queryClient.setQueryData<LeaseWithDocuments[]>(query.queryKey, (old) => {
            if (!old) return [{ ...optimisticLease, documents: [] }];
            return [{ ...optimisticLease, documents: [] }, ...old];
          });
        }
      });

      // Filter-aware optimistic update for base leases queries
      const baseQueries = queryClient.getQueryCache().findAll({ 
        queryKey: ['leases', 'list'] 
      });
      
      baseQueries.forEach((query) => {
        const filters = query.queryKey[2] as LeasesQueryParams | undefined;
        const matchesFilter = !filters?.status || 
                             filters.status === 'all' || 
                             filters.status === optimisticLease.status ||
                             filters.status.toUpperCase() === optimisticLease.status.toUpperCase();
        
        if (matchesFilter) {
          queryClient.setQueryData<Lease[]>(query.queryKey, (old) => {
            if (!old) return [optimisticLease];
            return [optimisticLease, ...old];
          });
        }
      });

      return { previousData, optimisticLeaseId: optimisticLease.id };
    },
    onError: (_err, _newLease, context) => {
      // Rollback on error - restore all previous data
      if (context?.previousData) {
        context.previousData.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
    },
    onSuccess: (realLease, _variables, context) => {
      // Replace optimistic lease with real one from server (with real ID)
      const withDocsQueries = queryClient.getQueryCache().findAll({ 
        queryKey: ['leases', 'withDocuments'] 
      });
      
      withDocsQueries.forEach((query) => {
        queryClient.setQueryData<LeaseWithDocuments[]>(query.queryKey, (old) => {
          if (!old) return old;
          return old.map((lease) => 
            lease.id === context?.optimisticLeaseId 
              ? { ...realLease, documents: [] } 
              : lease
          );
        });
      });

      const baseQueries = queryClient.getQueryCache().findAll({ 
        queryKey: ['leases', 'list'] 
      });
      
      baseQueries.forEach((query) => {
        queryClient.setQueryData<Lease[]>(query.queryKey, (old) => {
          if (!old) return old;
          return old.map((lease) => 
            lease.id === context?.optimisticLeaseId ? realLease : lease
          );
        });
      });

      // Log for monitoring
      Sentry.logger.info('Lease created - optimistic ID replaced with real ID', {
        optimisticId: context?.optimisticLeaseId,
        realId: realLease.id,
        status: realLease.status,
      });

      // Only invalidate related data that might have changed
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
};

/**
 * Mutation hook to update an existing lease
 * 
 * Uses optimistic updates for instant UI feedback with rollback on error
 * 
 * @returns Mutation result with mutate/mutateAsync functions
 * 
 * @example
 * ```tsx
 * const updateMutation = useUpdateLease();
 * 
 * const handleUpdate = async (leaseId, data) => {
 *   await updateMutation.mutateAsync({ leaseId, leaseData: data });
 *   toast.success('Lease updated!');
 * };
 * ```
 */
export const useUpdateLease = (): UseMutationResult<
  Lease,
  ApiError,
  { leaseId: number; leaseData: LeaseUpdate }
> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ leaseId, leaseData }) => updateLease(leaseId, leaseData),
    // Optimistic update: Update UI immediately before API call
    onMutate: async ({ leaseId, leaseData }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['leases'] });

      // Snapshot for rollback
      const previousData = queryClient.getQueriesData({ queryKey: ['leases'] });

      // Update queries - updates affect all filters since we're modifying existing items
      queryClient.setQueriesData<LeaseWithDocuments[]>(
        { queryKey: ['leases', 'withDocuments'], exact: false },
        (old) => {
          if (!old) return old;
          return old.map((lease) => {
            if (lease.id === leaseId) {
              return { ...lease, ...leaseData };
            }
            return lease;
          });
        }
      );

      // Also update base leases queries
      queryClient.setQueriesData<Lease[]>(
        { queryKey: ['leases', 'list'], exact: false },
        (old) => {
          if (!old) return old;
          return old.map((lease) => {
            if (lease.id === leaseId) {
              return { ...lease, ...leaseData };
            }
            return lease;
          });
        }
      );

      return { previousData };
    },
    onError: (_err, _variables, context) => {
      // Rollback on error
      if (context?.previousData) {
        context.previousData.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
    },
    onSuccess: () => {
      // Only invalidate related data - trust the optimistic update for leases
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
    },
  });
};

/**
 * Mutation hook to delete a lease
 * 
 * Uses optimistic updates to remove from UI immediately
 * 
 * @returns Mutation result with mutate/mutateAsync functions
 * 
 * @example
 * ```tsx
 * const deleteMutation = useDeleteLease();
 * 
 * const handleDelete = async (leaseId) => {
 *   if (window.confirm('Delete this lease?')) {
 *     await deleteMutation.mutateAsync(leaseId);
 *     toast.success('Lease deleted!');
 *   }
 * };
 * ```
 */
export const useDeleteLease = (): UseMutationResult<void, ApiError, number> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteLease,
    // Optimistic update: Remove from UI immediately for instant UX
    onMutate: async (leaseId) => {
      // Cancel any outgoing refetches to avoid overwriting optimistic update
      await queryClient.cancelQueries({ queryKey: ['leases'] });

      // Snapshot current data for rollback
      const previousData = queryClient.getQueriesData({ queryKey: ['leases'] });

      // Remove from all queries - deletes affect all filters
      queryClient.setQueriesData<LeaseWithDocuments[]>(
        { queryKey: ['leases', 'withDocuments'], exact: false },
        (old) => {
          if (!old) return old;
          return old.filter((lease) => lease.id !== leaseId);
        }
      );

      // Also remove from all base leases queries
      queryClient.setQueriesData<Lease[]>(
        { queryKey: ['leases', 'list'], exact: false },
        (old) => {
          if (!old) return old;
          return old.filter((lease) => lease.id !== leaseId);
        }
      );

      return { previousData };
    },
    onError: (_err, _leaseId, context) => {
      // Rollback on error - restore all previous data
      if (context?.previousData) {
        context.previousData.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
    },
    onSuccess: () => {
      // ONLY invalidate related data - NEVER refetch or invalidate lease data
      // The optimistic update IS the source of truth after successful deletion
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
};


/**
 * Mutation hook to bulk delete multiple leases
 * 
 * Uses optimistic updates to remove leases from UI immediately
 * 
 * @returns Mutation result with mutate/mutateAsync functions
 * 
 * @example
 * ```tsx
 * const bulkDeleteMutation = useBulkDeleteLeases();
 * 
 * const handleBulkDelete = async (leaseIds) => {
 *   await bulkDeleteMutation.mutateAsync(leaseIds);
 *   toast.success('Leases deleted!');
 * };
 * ```
 */
export const useBulkDeleteLeases = (): UseMutationResult<void, ApiError, number[]> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: bulkDeleteLeases,
    // Optimistic update: Remove from UI immediately for instant UX
    onMutate: async (leaseIds) => {
      // Cancel any outgoing refetches to avoid overwriting optimistic update
      await queryClient.cancelQueries({ queryKey: ['leases'] });

      // Snapshot current data for rollback
      const previousData = queryClient.getQueriesData({ queryKey: ['leases'] });

      // Remove from all queries - deletes affect all filters
      queryClient.setQueriesData<LeaseWithDocuments[]>(
        { queryKey: ['leases', 'withDocuments'], exact: false },
        (old) => {
          if (!old) return old;
          return old.filter((lease) => !leaseIds.includes(lease.id));
        }
      );

      // Also remove from all base leases queries
      queryClient.setQueriesData<Lease[]>(
        { queryKey: ['leases', 'list'], exact: false },
        (old) => {
          if (!old) return old;
          return old.filter((lease) => !leaseIds.includes(lease.id));
        }
      );

      return { previousData };
    },
    onError: (_err, _leaseIds, context) => {
      // Rollback on error - restore all previous data
      if (context?.previousData) {
        context.previousData.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
    },
    onSuccess: () => {
      // ONLY invalidate related data - NEVER refetch or invalidate lease data
      // The optimistic update IS the source of truth after successful deletion
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
};

/**
 * Mutation hook to update lease status
 * 
 * Uses optimistic updates for instant UI feedback
 * 
 * @returns Mutation result with mutate/mutateAsync functions
 * 
 * @example
 * ```tsx
 * const updateStatusMutation = useUpdateLeaseStatus();
 * 
 * const handleStatusChange = async (leaseId, status) => {
 *   await updateStatusMutation.mutateAsync({ leaseId, status });
 *   toast.success('Status updated!');
 * };
 * ```
 */
export const useUpdateLeaseStatus = (): UseMutationResult<
  Lease,
  ApiError,
  { leaseId: number; status: string }
> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ leaseId, status }) => updateLeaseStatus(leaseId, status),
    // Optimistic update
    onMutate: async ({ leaseId, status }) => {
      await queryClient.cancelQueries({ queryKey: ['leases'] });
      const previousData = queryClient.getQueriesData({ queryKey: ['leases'] });

      // Granular update: Handle status changes that affect filtering
      const withDocsQueries = queryClient.getQueryCache().findAll({ 
        queryKey: ['leases', 'withDocuments'] 
      });
      
      withDocsQueries.forEach((query) => {
        const filters = query.queryKey[2] as LeasesQueryParams | undefined;
        const oldData = query.state.data as LeaseWithDocuments[] | undefined;
        
        if (!oldData) return;
        
        // Find the lease in this query
        const existingLease = oldData.find((l) => l.id === leaseId);
        
        if (!existingLease) return;
        
        // Check if lease should remain in this filtered view after status change
        const shouldBeInView = !filters?.status || 
                              filters.status === 'all' || 
                              filters.status === status ||
                              filters.status.toUpperCase() === status.toUpperCase();
        
        if (shouldBeInView) {
          // Update the lease in place
          queryClient.setQueryData<LeaseWithDocuments[]>(query.queryKey, (old) => {
            if (!old) return old;
            return old.map((lease) => lease.id === leaseId ? { ...lease, status } : lease);
          });
        } else {
          // Remove from this filtered view (status no longer matches)
          queryClient.setQueryData<LeaseWithDocuments[]>(query.queryKey, (old) => {
            if (!old) return old;
            return old.filter((lease) => lease.id !== leaseId);
          });
        }
      });

      // Same for base leases queries
      const baseQueries = queryClient.getQueryCache().findAll({ 
        queryKey: ['leases', 'list'] 
      });
      
      baseQueries.forEach((query) => {
        const filters = query.queryKey[2] as LeasesQueryParams | undefined;
        const oldData = query.state.data as Lease[] | undefined;
        
        if (!oldData) return;
        
        const existingLease = oldData.find((l) => l.id === leaseId);
        if (!existingLease) return;
        
        const shouldBeInView = !filters?.status || 
                              filters.status === 'all' || 
                              filters.status === status ||
                              filters.status.toUpperCase() === status.toUpperCase();
        
        if (shouldBeInView) {
          queryClient.setQueryData<Lease[]>(query.queryKey, (old) => {
            if (!old) return old;
            return old.map((lease) => lease.id === leaseId ? { ...lease, status } : lease);
          });
        } else {
          queryClient.setQueryData<Lease[]>(query.queryKey, (old) => {
            if (!old) return old;
            return old.filter((lease) => lease.id !== leaseId);
          });
        }
      });

      return { previousData };
    },
    onError: (_err, _variables, context) => {
      if (context?.previousData) {
        context.previousData.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
    },
    onSuccess: () => {
      // Only invalidate related data - trust the optimistic update
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
};

/**
 * Mutation hook to upload a document to a lease
 * 
 * KEY FEATURE: Optimistically adds document to lease.documents array
 * This makes the upload icon switch to preview icon INSTANTLY
 * 
 * @returns Mutation result with mutate/mutateAsync functions
 * 
 * @example
 * ```tsx
 * const uploadMutation = useUploadLeaseDocument();
 * 
 * const handleUpload = async (leaseId, formData) => {
 *   await uploadMutation.mutateAsync({ leaseId, formData });
 *   toast.success('Document uploaded!');
 * };
 * ```
 */
export const useUploadLeaseDocument = (): UseMutationResult<
  LeaseDocument,
  ApiError,
  { leaseId: number; formData: FormData }
> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ leaseId, formData }) => uploadLeaseDocument(leaseId, formData),
    // Optimistic update: Add document immediately to show preview icon
    onMutate: async ({ leaseId, formData }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['leases'] });

      // Snapshot for rollback
      const previousData = queryClient.getQueriesData({ queryKey: ['leases'] });

      // Create optimistic document
      const file = formData.get('file') as File;
      const documentType = (formData.get('document_type') as string) || 'contract';
      
      const optimisticDocument: LeaseDocument = {
        id: Date.now(), // Temporary ID
        name: file?.name || 'Uploading...',
        file_path: '', // Will be populated on success
        document_type: documentType,
        upload_date: new Date().toISOString(),
        lease_id: leaseId,
      };

      // Add document to all queries (documents don't affect filtering)
      queryClient.setQueriesData<LeaseWithDocuments[]>(
        { queryKey: ['leases', 'withDocuments'], exact: false },
        (old) => {
          if (!old) return old;
          return old.map((lease) => {
            if (lease.id === leaseId) {
              return {
                ...lease,
                documents: [...(lease.documents || []), optimisticDocument],
              };
            }
            return lease;
          });
        }
      );

      return { previousData, optimisticDocumentId: optimisticDocument.id };
    },
    onError: (_err, _variables, context) => {
      // Rollback on error
      if (context?.previousData) {
        context.previousData.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
    },
    onSuccess: (newDocument, { leaseId }, context) => {
      // Replace optimistic document with real one (documents don't affect filtering)
      queryClient.setQueriesData<LeaseWithDocuments[]>(
        { queryKey: ['leases', 'withDocuments'], exact: false },
        (old) => {
          if (!old) return old;
          return old.map((lease) => {
            if (lease.id === leaseId) {
              // Remove optimistic document and add real one
              const documentsWithoutOptimistic = (lease.documents || []).filter(
                (doc) => doc.id !== context?.optimisticDocumentId
              );
              return {
                ...lease,
                documents: [...documentsWithoutOptimistic, newDocument],
              };
            }
            return lease;
          });
        }
      );

      // No need to invalidate - the cache update IS the source of truth
    },
  });
};


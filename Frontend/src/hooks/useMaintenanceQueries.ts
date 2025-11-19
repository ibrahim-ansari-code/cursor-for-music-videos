import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from '@tanstack/react-query';
import {
  getMaintenanceSummary,
  fetchMaintenanceRequests,
  createMaintenanceRequest,
  updateMaintenanceRequest,
  deleteMaintenanceRequest,
  bulkDeleteMaintenanceRequests,
} from '../utils/api/maintenance';
import { QUERY_KEYS } from './queryKeys';
import type { MaintenanceRequest, MaintenanceSummary, MaintenanceStatus, MaintenancePriority } from '../types/tenant';

// Query parameter types
export interface MaintenanceQueryParams {
  status?: MaintenanceStatus;
  priority?: MaintenancePriority;
  property_id?: number;
  tenant_id?: number;
  category?: string;
  limit?: number;
  offset?: number;
  req_status?: string; // Alternative status field name for backend compatibility
  [key: string]: any; // Allow additional params
}

// API response types
export interface MaintenanceRequestsResponse {
  results?: MaintenanceRequest[];
  total?: number;
  // Allow for direct array response (backward compatibility)
  [key: number]: MaintenanceRequest;
  length?: number;
}

/**
 * Hook to fetch maintenance summary statistics
 *
 * @param params - Optional query parameters for filtering
 * @returns Query result with summary data
 *
 * @example
 * ```tsx
 * const { data: summary, isLoading } = useMaintenanceSummary();
 * console.log(summary?.total_requests); // Total maintenance requests
 * ```
 */
export const useMaintenanceSummary = (
  params: MaintenanceQueryParams = {}
): UseQueryResult<MaintenanceSummary, Error> => {
  return useQuery({
    queryKey: QUERY_KEYS.maintenance.summary(params),
    queryFn: () => getMaintenanceSummary(params),
    staleTime: 0, // Always consider data stale - refetch immediately on invalidation
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes for back navigation
  });
};

/**
 * Hook to fetch maintenance requests with optional filtering
 *
 * @param params - Query parameters for filtering and pagination
 * @returns Query result with maintenance requests array
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useMaintenanceRequests({
 *   status: 'pending',
 *   limit: 20,
 *   offset: 0
 * });
 * ```
 */
export const useMaintenanceRequests = (
  params: MaintenanceQueryParams = {}
): UseQueryResult<MaintenanceRequestsResponse, Error> => {
  return useQuery({
    queryKey: QUERY_KEYS.maintenance.requests(params),
    queryFn: () => fetchMaintenanceRequests(params),
    staleTime: 0, // Optimistic updates + refetchQueries will keep data fresh
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes for back navigation
  });
};

/**
 * Mutation hook to create a new maintenance request
 *
 * Automatically invalidates maintenance queries on success
 *
 * @returns Mutation result with mutate/mutateAsync functions
 *
 * @example
 * ```tsx
 * const createMutation = useCreateMaintenanceRequest();
 *
 * const handleSubmit = async (data) => {
 *   await createMutation.mutateAsync(data);
 *   toast.success('Request created!');
 * };
 * ```
 */
export const useCreateMaintenanceRequest = (): UseMutationResult<
  MaintenanceRequest,
  Error,
  Partial<MaintenanceRequest>
> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createMaintenanceRequest,
    onSuccess: (newRequest) => {
      // Optimistically add to cache immediately
      queryClient.setQueriesData<MaintenanceRequestsResponse | MaintenanceRequest[]>(
        { queryKey: QUERY_KEYS.maintenance.requests() },
        (old: any) => {
          if (!old) return [newRequest];

          // Handle both array and object response formats
          if (Array.isArray(old)) {
            return [newRequest, ...old]; // Add to beginning
          }
          if (old.results) {
            return {
              ...old,
              results: [newRequest, ...old.results],
              total: (old.total || 0) + 1,
            };
          }
          return old;
        }
      );

      // Refetch in background to sync with server and update summary stats
      queryClient.refetchQueries({ queryKey: ['maintenance'], type: 'active' });
      queryClient.refetchQueries({ queryKey: ['tenants'], type: 'active' });
    },
  });
};

/**
 * Mutation hook to update an existing maintenance request
 *
 * Automatically invalidates maintenance queries on success
 *
 * @returns Mutation result with mutate/mutateAsync functions
 *
 * @example
 * ```tsx
 * const updateMutation = useUpdateMaintenanceRequest();
 *
 * const handleUpdate = async (requestId, data) => {
 *   await updateMutation.mutateAsync({ requestId, requestData: data });
 *   toast.success('Request updated!');
 * };
 * ```
 */
export const useUpdateMaintenanceRequest = (): UseMutationResult<
  MaintenanceRequest,
  Error,
  { requestId: number; requestData: Partial<MaintenanceRequest> }
> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ requestId, requestData }) => updateMaintenanceRequest(requestId, requestData),
    // Optimistic update: Update UI immediately before API call
    onMutate: async ({ requestId, requestData }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: QUERY_KEYS.maintenance.requests() });

      // Snapshot for rollback
      const previousData = queryClient.getQueriesData({ queryKey: QUERY_KEYS.maintenance.requests() });

      // Optimistically update all maintenance queries (use partial match)
      queryClient.setQueriesData<MaintenanceRequestsResponse | MaintenanceRequest[]>(
        { queryKey: ['maintenance', 'requests'] }, // Partial key - matches ALL maintenance request queries
        (old: any) => {
          if (!old) return old;

          const updateRequest = (req: MaintenanceRequest) => {
            if (req.id === requestId) {
              return { ...req, ...requestData };
            }
            return req;
          };

          // Handle both array and object response formats
          if (Array.isArray(old)) {
            return old.map(updateRequest);
          }
          if (old.results) {
            return {
              ...old,
              results: old.results.map(updateRequest),
            };
          }
          return old;
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
      // Refetch in background to sync with server truth
      queryClient.refetchQueries({ queryKey: ['maintenance'], type: 'active' });
      queryClient.refetchQueries({ queryKey: ['tenants'], type: 'active' });
    },
  });
};

/**
 * Mutation hook to delete a maintenance request
 *
 * Automatically invalidates maintenance queries on success
 *
 * @returns Mutation result with mutate/mutateAsync functions
 *
 * @example
 * ```tsx
 * const deleteMutation = useDeleteMaintenanceRequest();
 *
 * const handleDelete = async (requestId) => {
 *   if (window.confirm('Delete this request?')) {
 *     await deleteMutation.mutateAsync(requestId);
 *     toast.success('Request deleted!');
 *   }
 * };
 * ```
 */
export const useDeleteMaintenanceRequest = (): UseMutationResult<
  void,
  Error,
  number
> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteMaintenanceRequest,
    // Optimistic update: Remove from UI immediately for instant UX
    onMutate: async (requestId) => {
      // Cancel any outgoing refetches to avoid overwriting optimistic update
      await queryClient.cancelQueries({ queryKey: QUERY_KEYS.maintenance.requests() });

      // Snapshot current data for rollback
      const previousData = queryClient.getQueriesData({ queryKey: QUERY_KEYS.maintenance.requests() });

      // Optimistically update all maintenance queries (use partial match)
      queryClient.setQueriesData<MaintenanceRequestsResponse | MaintenanceRequest[]>(
        { queryKey: ['maintenance', 'requests'] }, // Partial key - matches ALL maintenance request queries
        (old: any) => {
          if (!old) return old;
          
          // Handle both array and object response formats
          if (Array.isArray(old)) {
            return old.filter((req: MaintenanceRequest) => req.id !== requestId);
          }
          if (old.results) {
            return {
              ...old,
              results: old.results.filter((req: MaintenanceRequest) => req.id !== requestId),
              total: (old.total || 0) - 1,
            };
          }
          return old;
        }
      );

      return { previousData };
    },
    onError: (_err, _requestId, context) => {
      // Rollback on error
      if (context?.previousData) {
        context.previousData.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
    },
    onSuccess: () => {
      // Refetch in background to sync with server and update summary stats
      queryClient.refetchQueries({ queryKey: ['maintenance'], type: 'active' });
      queryClient.refetchQueries({ queryKey: ['tenants'], type: 'active' });
    },
  });
};

/**
 * Mutation hook to bulk delete maintenance requests
 *
 * @returns Mutation result for bulk deleting requests
 */
export const useBulkDeleteMaintenanceRequests = (): UseMutationResult<
  void,
  Error,
  number[]
> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: bulkDeleteMaintenanceRequests,
    onMutate: async (requestIds) => {
      await queryClient.cancelQueries({ queryKey: QUERY_KEYS.maintenance.requests() });

      const previousData = queryClient.getQueriesData({ queryKey: QUERY_KEYS.maintenance.requests() });

      queryClient.setQueriesData<MaintenanceRequestsResponse | MaintenanceRequest[]>(
        { queryKey: ['maintenance', 'requests'] },
        (old: any) => {
          if (!old) return old;

          const idSet = new Set(requestIds);

          if (Array.isArray(old)) {
            return old.filter((req: MaintenanceRequest) => !idSet.has(req.id));
          }
          if (old.results) {
            const filteredResults = old.results.filter((req: MaintenanceRequest) => !idSet.has(req.id));
            const removedCount = old.results.length - filteredResults.length;
            return {
              ...old,
              results: filteredResults,
              total:
                typeof old.total === 'number'
                  ? Math.max(0, old.total - removedCount)
                  : old.total,
            };
          }
          return old;
        }
      );

      return { previousData };
    },
    onError: (_err, _requestIds, context) => {
      if (context?.previousData) {
        context.previousData.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
    },
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ['maintenance'], type: 'active' });
      queryClient.refetchQueries({ queryKey: ['tenants'], type: 'active' });
    },
  });
};
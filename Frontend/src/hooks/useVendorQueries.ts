/**
 * Vendor Contact React Query Hooks
 *
 * Custom hooks for vendor contact data fetching and mutations
 * Uses TanStack Query for caching, background refetching, and optimistic updates
 */

import { useQuery, useMutation, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import type {
  VendorContact,
  VendorContactCreate,
  VendorContactUpdate,
  VendorContactListResponse,
} from "../types/vendor";
import * as vendorApi from "../utils/api/vendors";

// Query keys for caching and invalidation
export const vendorKeys = {
  all: ["vendors"] as const,
  lists: () => [...vendorKeys.all, "list"] as const,
  list: (filters?: Record<string, any>) => [...vendorKeys.lists(), filters] as const,
  details: () => [...vendorKeys.all, "detail"] as const,
  detail: (id: number) => [...vendorKeys.details(), id] as const,
  tradeCategories: () => [...vendorKeys.all, "trade-categories"] as const,
};

/**
 * Hook to fetch list of vendors with optional filters
 */
export function useVendors(params?: {
  trade_category?: string;
  is_active?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}): UseQueryResult<VendorContactListResponse, Error> {
  return useQuery({
    queryKey: vendorKeys.list(params),
    queryFn: () => vendorApi.listVendors(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: params !== undefined, // Only fetch when params are provided
  });
}

/**
 * Hook to fetch a single vendor by ID
 */
export function useVendor(vendorId: number | null): UseQueryResult<VendorContact, Error> {
  return useQuery({
    queryKey: vendorKeys.detail(vendorId!),
    queryFn: () => vendorApi.getVendor(vendorId!),
    enabled: vendorId !== null,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch trade categories
 */
export function useTradeCategories(): UseQueryResult<string[], Error> {
  return useQuery({
    queryKey: vendorKeys.tradeCategories(),
    queryFn: vendorApi.getTradeCategories,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to create a new vendor
 */
export function useCreateVendor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: VendorContactCreate) => vendorApi.createVendor(data),
    onSuccess: () => {
      // Invalidate all vendor lists to refetch with new data
      queryClient.invalidateQueries({ queryKey: vendorKeys.lists() });
      queryClient.invalidateQueries({ queryKey: vendorKeys.tradeCategories() });
    },
  });
}

/**
 * Hook to update an existing vendor
 */
export function useUpdateVendor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ vendorId, data }: { vendorId: number; data: VendorContactUpdate }) =>
      vendorApi.updateVendor(vendorId, data),
    onSuccess: (updatedVendor) => {
      // Invalidate all vendor lists
      queryClient.invalidateQueries({ queryKey: vendorKeys.lists() });
      // Update the specific vendor detail cache
      queryClient.setQueryData(vendorKeys.detail(updatedVendor.id), updatedVendor);
      // Invalidate trade categories in case the category changed
      queryClient.invalidateQueries({ queryKey: vendorKeys.tradeCategories() });
    },
  });
}

/**
 * Hook to toggle vendor favorite status with optimistic updates
 * Provides instant UI feedback before server confirmation
 */
export function useToggleVendorFavorite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ vendorId, isFavorite }: { vendorId: number; isFavorite: boolean }) =>
      vendorApi.updateVendor(vendorId, { is_favorite: isFavorite }),
    
    // Optimistic update: Update UI immediately before API call
    onMutate: async ({ vendorId, isFavorite }) => {
      // Cancel outgoing refetches to avoid overwriting optimistic update
      await queryClient.cancelQueries({ queryKey: vendorKeys.lists() });
      
      // Snapshot previous state for rollback
      const previousVendorLists = queryClient.getQueriesData({ queryKey: vendorKeys.lists() });
      
      // Optimistically update all vendor list caches
      queryClient.setQueriesData<VendorContactListResponse>(
        { queryKey: vendorKeys.lists() },
        (old) => {
          if (!old) return old;
          
          return {
            ...old,
            vendors: old.vendors.map((vendor) =>
              vendor.id === vendorId
                ? { ...vendor, is_favorite: isFavorite }
                : vendor
            ),
          };
        }
      );
      
      // Return context with snapshot for rollback
      return { previousVendorLists };
    },
    
    // Rollback on error
    onError: (_err, _variables, context) => {
      // Restore all cached vendor lists to previous state
      if (context?.previousVendorLists) {
        context.previousVendorLists.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
    },
    
    // Always refetch after error or success to ensure consistency
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: vendorKeys.lists() });
    },
  });
}

/**
 * Hook to delete a vendor
 */
export function useDeleteVendor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vendorId: number) => vendorApi.deleteVendor(vendorId),
    onSuccess: (_, vendorId) => {
      // Invalidate all vendor lists
      queryClient.invalidateQueries({ queryKey: vendorKeys.lists() });
      // Remove the specific vendor from cache
      queryClient.removeQueries({ queryKey: vendorKeys.detail(vendorId) });
      // Invalidate trade categories
      queryClient.invalidateQueries({ queryKey: vendorKeys.tradeCategories() });
    },
  });
}

/**
 * Hook to bulk delete vendors
 */
export function useBulkDeleteVendors() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vendorIds: number[]) => vendorApi.bulkDeleteVendors(vendorIds),
    onSuccess: (_, vendorIds) => {
      // Invalidate all vendor lists
      queryClient.invalidateQueries({ queryKey: vendorKeys.lists() });
      // Remove deleted vendors from cache
      vendorIds.forEach((id) => {
        queryClient.removeQueries({ queryKey: vendorKeys.detail(id) });
      });
      // Invalidate trade categories
      queryClient.invalidateQueries({ queryKey: vendorKeys.tradeCategories() });
    },
  });
}


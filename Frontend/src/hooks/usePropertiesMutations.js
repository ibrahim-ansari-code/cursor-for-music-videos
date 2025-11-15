import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { 
  createProperty, 
  updateProperty, 
  deleteProperty, 
  fetchPropertyById,
  bulkDeleteProperties
} from "../utils/api/properties";
import { QUERY_KEYS } from "./queryKeys";

// Property mutation hooks for CRUD operations
export const useCreateProperty = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: createProperty,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.properties.all() });
    },
  });
};

export const useUpdateProperty = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ propertyId, propertyData }) => updateProperty(propertyId, propertyData),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.properties.all() });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.properties.detail(variables.propertyId) });
    },
  });
};

export const useDeleteProperty = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: deleteProperty,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.properties.all() });
    },
  });
};

/**
 * Mutation hook to bulk delete multiple properties
 * Uses optimistic updates to remove properties from UI immediately
 * @returns Mutation result with mutate/mutateAsync functions
 */
export const useBulkDeleteProperties = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: bulkDeleteProperties,
    // Optimistic update: Remove from UI immediately for instant UX
    onMutate: async (propertyIds) => {
      // Cancel any outgoing refetches to avoid overwriting optimistic update
      await queryClient.cancelQueries({ queryKey: QUERY_KEYS.properties.all() });
      
      // Snapshot current data for rollback
      const previousData = queryClient.getQueriesData({ queryKey: QUERY_KEYS.properties.all() });
      
      // Remove from all queries - deletes affect all filters
      queryClient.setQueriesData(
        { queryKey: QUERY_KEYS.properties.all(), exact: false },
        (old) => {
          if (!old) return old;
          return old.filter((property) => !propertyIds.includes(property.id));
        }
      );
      
      return { previousData };
    },
    onError: (_err, _propertyIds, context) => {
      // Rollback on error - restore all previous data
      if (context?.previousData) {
        context.previousData.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
    },
    onSuccess: () => {
      // Invalidate related data after successful deletion
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.properties.all() });
    },
  });
};

export const usePropertyById = (propertyId) => {
  return useQuery({
    queryKey: QUERY_KEYS.properties.detail(propertyId),
    queryFn: () => fetchPropertyById(propertyId),
    enabled: !!propertyId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

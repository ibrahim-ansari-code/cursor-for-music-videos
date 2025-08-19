import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { 
  createProperty, 
  updateProperty, 
  deleteProperty, 
  fetchPropertyById 
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

export const usePropertyById = (propertyId) => {
  return useQuery({
    queryKey: QUERY_KEYS.properties.detail(propertyId),
    queryFn: () => fetchPropertyById(propertyId),
    enabled: !!propertyId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

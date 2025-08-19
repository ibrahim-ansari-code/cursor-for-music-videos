import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchTenants, createTenant, updateTenant, deleteTenant } from "../utils/api/tenants";
import { fetchTenantsByProperty } from "../utils/api/tenants";
import { QUERY_KEYS } from "./queryKeys";

// Main tenants hook for Tenants page
export const useTenants = (params = {}) => {
  return useQuery({
    queryKey: QUERY_KEYS.tenants.all(params),
    queryFn: () => fetchTenants(params),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

// Tenants by property hook
export const useTenantsByProperty = (propertyId) => {
  return useQuery({
    queryKey: QUERY_KEYS.tenants.byProperty(propertyId),
    queryFn: () => fetchTenantsByProperty(propertyId),
    enabled: !!propertyId && propertyId !== "all",
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

// Mutation hooks for tenant operations
export const useCreateTenant = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: createTenant,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.tenants.all() });
    },
  });
};

export const useUpdateTenant = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ tenantId, tenantData }) => updateTenant(tenantId, tenantData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.tenants.all() });
    },
  });
};

export const useDeleteTenant = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: deleteTenant,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.tenants.all() });
    },
  });
};

export default useTenants;

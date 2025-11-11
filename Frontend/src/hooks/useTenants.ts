import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from "@tanstack/react-query";
import { fetchTenants, createTenant, updateTenant, deleteTenant, fetchTenant, bulkDeleteTenants } from "../utils/api/tenants";
import { fetchTenantsByProperty } from "../utils/api/tenants";
import { QUERY_KEYS } from "./queryKeys";
import { EnrichedTenant, Tenant, TenantStatus } from "../types/tenant";

interface UseTenantsParams {
  property_id?: number;
  status?: TenantStatus;
  search?: string;
  unassigned_only?: boolean;
}

interface UpdateTenantParams {
  tenantId: number;
  tenantData: Partial<Tenant>;
}

// Main tenants hook for Tenants page
export const useTenants = (params: UseTenantsParams = {}): UseQueryResult<EnrichedTenant[], Error> => {
  return useQuery({
    queryKey: QUERY_KEYS.tenants.all(params),
    queryFn: () => fetchTenants(params),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

// Tenants by property hook
export const useTenantsByProperty = (propertyId: number): UseQueryResult<EnrichedTenant[], Error> => {
  return useQuery({
    queryKey: QUERY_KEYS.tenants.byProperty(propertyId),
    queryFn: () => fetchTenantsByProperty(propertyId),
    enabled: !!propertyId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

// Hook for fetching a single tenant by ID
export const useTenantById = (tenantId: number): UseQueryResult<EnrichedTenant, Error> => {
  return useQuery({
    queryKey: QUERY_KEYS.tenants.detail(tenantId),
    queryFn: () => fetchTenant(tenantId),
    enabled: !!tenantId,
    staleTime: 1 * 60 * 1000, // 1 minute
  });
};

// Mutation hooks for tenant operations
export const useCreateTenant = (): UseMutationResult<Tenant, Error, Partial<Tenant>> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createTenant,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.tenants.all() });
    },
  });
};

export const useUpdateTenant = (): UseMutationResult<Tenant, Error, UpdateTenantParams> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ tenantId, tenantData }: UpdateTenantParams) => updateTenant(tenantId, tenantData),
    onSuccess: (_data, { tenantId }) => {
      // Invalidate both the list and the specific detail query to prevent stale data
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.tenants.all() });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.tenants.detail(tenantId) });
    },
  });
};

export const useDeleteTenant = (): UseMutationResult<void, Error, number> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteTenant,
    onSuccess: (_data, tenantId) => {
      // Invalidate the list query to remove the deleted tenant from lists
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.tenants.all() });
      // Remove the deleted tenant's detail query from cache
      // to ensure data consistency and prevent errors if someone navigates to that tenant
      queryClient.removeQueries({ queryKey: QUERY_KEYS.tenants.detail(tenantId) });
    },
  });
};

export const useBulkDeleteTenants = (): UseMutationResult<void, Error, number[]> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: bulkDeleteTenants,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.tenants.all() });
    },
  });
};


export default useTenants;

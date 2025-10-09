import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchTenants, fetchTenantsByProperty } from "../utils/api";
import { QUERY_KEYS } from "./queryKeys";

export default function useTenantsCount(selectedProperty, fallbackOccupiedUnits = 0) {
  // Use TanStack Query internally
  const { data: tenants, isLoading: loading, error } = useQuery({
    queryKey: QUERY_KEYS.tenants.count(selectedProperty),
    queryFn: () => {
      if (selectedProperty === "all") {
        return fetchTenants();
      } else {
        return fetchTenantsByProperty(selectedProperty);
      }
    },
    staleTime: 3 * 60 * 1000, // 3 minutes for tenant counts
  });

  // Calculate count with fallback
  const count = useMemo(() => {
    if (error) return fallbackOccupiedUnits || 0;
    return Array.isArray(tenants) ? tenants.length : 0;
  }, [tenants, error, fallbackOccupiedUnits]);

  return { count, loading };
}

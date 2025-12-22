import { useQuery } from '@tanstack/react-query';
import { fetchTenantDashboard, type TenantDashboardResponse } from '@/utils/api/dashboard';

interface UseTenantDashboardResult {
  data: TenantDashboardResponse | undefined;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * Hook to fetch tenant dashboard data using TanStack Query
 * Provides caching, automatic refetch, and retry logic
 */
export const useTenantDashboard = (): UseTenantDashboardResult => {
  const query = useQuery({
    queryKey: ['tenant', 'dashboard'],
    queryFn: fetchTenantDashboard,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    retry: 2,
  });

  return {
    data: query.data,
    loading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
};

export default useTenantDashboard;

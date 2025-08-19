import { useMemo } from 'react';
import { useQuery } from "@tanstack/react-query";
import { fetchUnitLease } from '../utils/api';
import { QUERY_KEYS } from './queryKeys';

/**
 * Custom hook to fetch and manage unit lease status
 * @param {string} unitId - The ID of the unit (UUID)
 * @returns {object} An object containing lease data, loading state, and error state
 */
export const useUnitStatus = (unitId) => {
  // Use TanStack Query internally
  const { data: lease, isLoading: loading, error, refetch } = useQuery({
    queryKey: QUERY_KEYS.leases.unitStatus(unitId),
    queryFn: () => fetchUnitLease(unitId),
    enabled: !!unitId,
    staleTime: 3 * 60 * 1000, // 3 minutes for unit lease status
    retry: (failureCount, error) => {
      // Don't retry on 404 - unit just doesn't have an active lease
      if (error?.status === 404) return false;
      return failureCount < 1;
    },
    throwOnError: (error) => {
      // Don't throw on 404 - treat as "no lease"
      return error?.status !== 404;
    },
  });

  const hasActiveLease = useMemo(() => !!lease, [lease]);

  return {
    lease: lease || null,
    loading,
    error: error?.status === 404 ? null : error, // Don't show error for 404
    refetch,
    hasActiveLease,
  };
};

export default useUnitStatus;
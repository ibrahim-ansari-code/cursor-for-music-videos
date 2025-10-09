import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchDashboardData } from "../utils/api";
import { QUERY_KEYS } from "./queryKeys";

export default function useDashboardData({ propertyId, timePeriod, startDate, endDate }) {
  // Build query parameters
  const queryParams = useMemo(() => {
    const params = {
      property_id: propertyId || undefined,
      time_period: timePeriod,
    };
    if (startDate && endDate) {
      params.start_date = startDate;
      params.end_date = endDate;
    }
    return params;
  }, [propertyId, timePeriod, startDate, endDate]);

  // Use TanStack Query internally
  const { data, isLoading: loading, error } = useQuery({
    queryKey: QUERY_KEYS.dashboard.data(queryParams),
    queryFn: () => fetchDashboardData(queryParams),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  return { data, loading, error };
}

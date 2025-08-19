import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchRentTracker } from "../utils/api/rentTracker";
import { QUERY_KEYS } from "./queryKeys";

export default function useRentTracker({ month, year, propertyId }) {
  // Build query parameters
  const queryParams = useMemo(() => ({
    month, 
    year, 
    property_id: propertyId
  }), [month, year, propertyId]);

  // Use TanStack Query internally - use dashboard context for dashboard usage
  const { data: rentTrackerResponse, isLoading: loading, error } = useQuery({
    queryKey: QUERY_KEYS.dashboard.rentTracker(queryParams),
    queryFn: () => fetchRentTracker(queryParams),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  // Process data to filter unpaid entries
  const data = useMemo(() => {
    if (!Array.isArray(rentTrackerResponse)) return [];
    
    return rentTrackerResponse.filter((r) => 
      r.status === "DUE" || r.status === "PARTIAL" || r.status === "OVERDUE"
    );
  }, [rentTrackerResponse]);

  return { data, loading, error };
}

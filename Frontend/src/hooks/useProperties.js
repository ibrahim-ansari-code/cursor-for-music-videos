import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchProperties as fetchPropertiesApi } from "../utils/api/properties";
import { QUERY_KEYS } from "./queryKeys";

export default function useProperties() {
  // Use TanStack Query internally
  const { data: properties = [], isLoading: loading, error } = useQuery({
    queryKey: QUERY_KEYS.properties.all(),
    queryFn: () => fetchPropertiesApi({}),
    staleTime: 5 * 60 * 1000, // 5 minutes - properties don't change often
  });

  const options = useMemo(() => [
    { id: "all", name: "All Properties" }, 
    ...properties
  ], [properties]);

  return { properties, loading, error, options };
}

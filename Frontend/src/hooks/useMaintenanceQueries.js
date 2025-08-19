import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getMaintenanceSummary,
  fetchMaintenanceRequests,
  createMaintenanceRequest,
  updateMaintenanceRequest,
  deleteMaintenanceRequest,
} from "../utils/api/maintenance";
import { QUERY_KEYS } from "./queryKeys";

// ===== MAINTENANCE QUERIES =====
export const useMaintenanceSummary = (params = {}) => {
  return useQuery({
    queryKey: QUERY_KEYS.maintenance.summary(params),
    queryFn: () => getMaintenanceSummary(params),
    staleTime: 3 * 60 * 1000, // 3 minutes for summary data
  });
};

export const useMaintenanceRequests = (params = {}) => {
  return useQuery({
    queryKey: QUERY_KEYS.maintenance.requests(params),
    queryFn: () => fetchMaintenanceRequests(params),
    staleTime: 2 * 60 * 1000, // 2 minutes for maintenance requests
  });
};

// ===== MAINTENANCE MUTATIONS =====
export const useCreateMaintenanceRequest = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: createMaintenanceRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.maintenance.requests() });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.maintenance.summary() });
    },
  });
};

export const useUpdateMaintenanceRequest = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ requestId, requestData }) => updateMaintenanceRequest(requestId, requestData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.maintenance.requests() });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.maintenance.summary() });
    },
  });
};

export const useDeleteMaintenanceRequest = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: deleteMaintenanceRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.maintenance.requests() });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.maintenance.summary() });
    },
  });
};

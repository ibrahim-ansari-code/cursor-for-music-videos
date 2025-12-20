/**
 * useMaintenance Hook
 * TanStack Query hooks for maintenance request management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import * as Sentry from '@sentry/react';
import {
  fetchMaintenanceRequests,
  createMaintenanceRequest,
  getMaintenanceRequest,
  updateMaintenanceRequest,
  deleteMaintenanceRequest,
  getMaintenanceSummary,
  uploadMaintenancePhoto,
} from '@/utils/api/maintenance';
import type {
  MaintenanceRequestCreate,
  MaintenanceRequestUpdate,
  MaintenanceFilters,
} from '@/utils/api/maintenance/types';

// ============================================================================
// Query Keys
// ============================================================================

export const maintenanceKeys = {
  all: ['maintenance'] as const,
  requests: (filters?: MaintenanceFilters) => 
    filters ? [...maintenanceKeys.all, 'requests', filters] as const 
    : [...maintenanceKeys.all, 'requests'] as const,
  request: (id: number) => [...maintenanceKeys.all, 'request', id] as const,
  summary: () => [...maintenanceKeys.all, 'summary'] as const,
};

// ============================================================================
// Maintenance Requests
// ============================================================================

export const useMaintenanceRequests = (filters?: MaintenanceFilters) => {
  return useQuery({
    queryKey: maintenanceKeys.requests(filters),
    queryFn: () => fetchMaintenanceRequests(filters),
    staleTime: 1000 * 60 * 2, // 2 minutes
    placeholderData: (previousData) => previousData, // Keep previous data while fetching
  });
};

export const useMaintenanceRequest = (requestId: number | null) => {
  return useQuery({
    queryKey: maintenanceKeys.request(requestId || 0),
    queryFn: () => (requestId ? getMaintenanceRequest(requestId) : null),
    enabled: !!requestId,
  });
};

export const useMaintenanceSummary = () => {
  return useQuery({
    queryKey: maintenanceKeys.summary(),
    queryFn: getMaintenanceSummary,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};

// ============================================================================
// Mutations
// ============================================================================

export const useCreateMaintenanceRequest = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: MaintenanceRequestCreate) => createMaintenanceRequest(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: maintenanceKeys.all });
      toast.success('Maintenance request submitted successfully');
    },
    onError: (error: Error) => {
      Sentry.captureException(error, {
        tags: {
          component: 'useMaintenance',
          action: 'create_request',
        },
      });
      toast.error('Failed to create maintenance request');
    },
  });
};

export const useUpdateMaintenanceRequest = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ requestId, data }: { requestId: number; data: MaintenanceRequestUpdate }) =>
      updateMaintenanceRequest(requestId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: maintenanceKeys.all });
      queryClient.invalidateQueries({ queryKey: maintenanceKeys.request(variables.requestId) });
      toast.success('Maintenance request updated successfully');
    },
    onError: (error: Error) => {
      Sentry.captureException(error, {
        tags: {
          component: 'useMaintenance',
          action: 'update_request',
        },
      });
      toast.error('Failed to update maintenance request');
    },
  });
};

export const useDeleteMaintenanceRequest = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (requestId: number) => deleteMaintenanceRequest(requestId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: maintenanceKeys.all });
      toast.success('Maintenance request deleted successfully');
    },
    onError: (error: Error) => {
      Sentry.captureException(error, {
        tags: {
          component: 'useMaintenance',
          action: 'delete_request',
        },
      });
      toast.error('Failed to delete maintenance request');
    },
  });
};

export const useUploadMaintenancePhoto = () => {
  return useMutation({
    mutationFn: (file: File) => uploadMaintenancePhoto(file),
    onError: (error: Error) => {
      Sentry.captureException(error, {
        tags: {
          component: 'useMaintenance',
          action: 'upload_photo',
        },
      });
      toast.error('Failed to upload photo');
    },
  });
};


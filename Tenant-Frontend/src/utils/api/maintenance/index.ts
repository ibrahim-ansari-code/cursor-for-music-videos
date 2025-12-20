// Maintenance API functions for Tenant-Frontend
import { apiRequest } from '../core';
import type {
  MaintenanceRequest,
  MaintenanceRequestCreate,
  MaintenanceRequestUpdate,
  MaintenanceSummary,
  MaintenancePhotoUploadResponse,
  MaintenanceFilters
} from './types';

/**
 * Fetches a summary of maintenance data for the current tenant.
 * @returns {Promise<MaintenanceSummary>} A promise that resolves to the maintenance summary object
 */
export const getMaintenanceSummary = async (): Promise<MaintenanceSummary> => {
  const response = await apiRequest<MaintenanceSummary>("/maintenance/summary");
  if (!response) {
    throw new Error("Failed to fetch maintenance summary");
  }
  return response;
};

/**
 * Fetches maintenance requests with optional filtering parameters.
 * @param {MaintenanceFilters} [filters={}] - Query parameters for filtering maintenance requests
 * @returns {Promise<MaintenanceRequest[]>} A promise that resolves to an array of maintenance request objects
 */
export const fetchMaintenanceRequests = async (filters: MaintenanceFilters = {}): Promise<MaintenanceRequest[]> => {
  const queryParams = new URLSearchParams();

  Object.keys(filters).forEach((key) => {
    const value = filters[key as keyof MaintenanceFilters];
    if (value === null || value === undefined || value === "") return;

    if (Array.isArray(value)) {
      value.forEach((v) => queryParams.append(key, v.toString()));
    } else {
      queryParams.append(key, value.toString());
    }
  });

  const queryString = queryParams.toString();
  const response = await apiRequest<MaintenanceRequest[]>(`/maintenance/requests${queryString ? `?${queryString}` : ''}`);
  if (!response) {
    throw new Error("Failed to fetch maintenance requests");
  }
  return response;
};

/**
 * Creates a new maintenance request.
 * @param {MaintenanceRequestCreate} requestData - The maintenance request data to create
 * @returns {Promise<MaintenanceRequest>} A promise that resolves to the created maintenance request object
 */
export const createMaintenanceRequest = async (requestData: MaintenanceRequestCreate): Promise<MaintenanceRequest> => {
  const response = await apiRequest<MaintenanceRequest>("/maintenance/requests", {
    method: "POST",
    body: JSON.stringify(requestData),
  });
  if (!response) {
    throw new Error("Failed to create maintenance request");
  }
  return response;
};

/**
 * Fetches a specific maintenance request by ID.
 * @param {number} requestId - The ID of the maintenance request to fetch
 * @returns {Promise<MaintenanceRequest>} A promise that resolves to the maintenance request object
 */
export const getMaintenanceRequest = async (requestId: number): Promise<MaintenanceRequest> => {
  const response = await apiRequest<MaintenanceRequest>(`/maintenance/requests/${requestId}`);
  if (!response) {
    throw new Error("Failed to fetch maintenance request");
  }
  return response;
};

/**
 * Updates an existing maintenance request.
 * @param {number} requestId - The ID of the maintenance request to update
 * @param {MaintenanceRequestUpdate} requestData - The updated maintenance request data
 * @returns {Promise<MaintenanceRequest>} A promise that resolves to the updated maintenance request object
 */
export const updateMaintenanceRequest = async (
  requestId: number, 
  requestData: MaintenanceRequestUpdate
): Promise<MaintenanceRequest> => {
  const response = await apiRequest<MaintenanceRequest>(`/maintenance/requests/${requestId}`, {
    method: "PUT",
    body: JSON.stringify(requestData),
  });
  if (!response) {
    throw new Error("Failed to update maintenance request");
  }
  return response;
};

/**
 * Deletes a maintenance request.
 * @param {number} requestId - The ID of the maintenance request to delete
 * @returns {Promise<void>} A promise that resolves when the request is deleted
 */
export const deleteMaintenanceRequest = async (requestId: number): Promise<void> => {
  await apiRequest<void>(`/maintenance/requests/${requestId}`, {
    method: "DELETE",
  });
};

/**
 * Uploads a photo for a maintenance request.
 * @param {File} file - The image file to upload
 * @returns {Promise<string>} A promise that resolves to the uploaded photo URL
 */
export const uploadMaintenancePhoto = async (file: File): Promise<string> => {
  const formData = new FormData();
  formData.append('upload_file', file);

  const response = await apiRequest<MaintenancePhotoUploadResponse>("/maintenance/upload-photo", {
    method: "POST",
    body: formData,
  });

  if (!response) {
    throw new Error("Failed to upload maintenance photo");
  }

  return response.photo_url;
};

/**
 * Generates a secure, time-limited URL for viewing a maintenance photo.
 * @param {string} photoUrl - The original Azure Blob URL of the photo
 * @returns {Promise<{secure_url: string, expires_at: string, expires_in_seconds: number}>}
 */
export const getSecurePhotoUrl = async (photoUrl: string): Promise<{
  secure_url: string;
  expires_at: string;
  expires_in_seconds: number;
}> => {
  const response = await apiRequest<{
    secure_url: string;
    expires_at: string;
    expires_in_seconds: number;
  }>(`/maintenance/photos/secure-url?photo_url=${encodeURIComponent(photoUrl)}`, {
    method: "POST",
  });
  
  if (!response) {
    throw new Error("Failed to generate secure photo URL");
  }
  
  return response;
};
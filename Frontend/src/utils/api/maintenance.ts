// Maintenance API Functions
import { apiRequest, formatQueryString, uploadFile } from './core';
import { MaintenanceRequest, MaintenanceStatus, MaintenancePriority } from '../../types/tenant';
import { validateImageFile } from '../fileValidation';
import * as Sentry from '@sentry/react';

interface MaintenanceSummary {
  total_requests: number;
  pending: number;
  in_progress: number;
  completed: number;
  cancelled: number;
}

/**
 * Fetches a summary of maintenance data.
 * @param {FetchMaintenanceParams} [params={}] - Query parameters for filtering the summary
 * @returns {Promise<MaintenanceSummary>} A promise that resolves to the maintenance summary object
 */
export const getMaintenanceSummary = async (params: FetchMaintenanceParams = {}): Promise<MaintenanceSummary> => {
  const queryParams = new URLSearchParams();

  (Object.keys(params) as (keyof FetchMaintenanceParams)[]).forEach((key) => {
    const value = params[key];
    if (value === null || value === undefined || value === "") return;

    if (Array.isArray(value)) {
      value.forEach((v) => queryParams.append(key, String(v)));
    } else {
      queryParams.append(key, String(value));
    }
  });

  const queryString = queryParams.toString();
  return apiRequest(`/maintenance/summary${formatQueryString(queryString)}`);
};

interface FetchMaintenanceParams {
  status?: MaintenanceStatus;
  priority?: MaintenancePriority;
  property_id?: number;
  tenant_id?: number;
  category?: string;
}

/**
 * Fetches maintenance requests with optional filtering parameters.
 * @param {FetchMaintenanceParams} [params={}] - Query parameters for filtering maintenance requests
 * @returns {Promise<MaintenanceRequest[]>} A promise that resolves to an array of maintenance request objects
 */
export const fetchMaintenanceRequests = async (params: FetchMaintenanceParams = {}): Promise<MaintenanceRequest[]> => {
  const queryParams = new URLSearchParams();

  (Object.keys(params) as (keyof FetchMaintenanceParams)[]).forEach((key) => {
    const value = params[key];
    if (value === null || value === undefined || value === "") return;

    if (Array.isArray(value)) {
      value.forEach((v) => queryParams.append(key, String(v)));
    } else {
      queryParams.append(key, String(value));
    }
  });

  const queryString = queryParams.toString();
  return apiRequest(`/maintenance/requests${formatQueryString(queryString)}`);
};

/**
 * Creates a new maintenance request.
 * @param {Partial<MaintenanceRequest>} requestData - The maintenance request data to create
 * @returns {Promise<MaintenanceRequest>} A promise that resolves to the created maintenance request object
 */
export const createMaintenanceRequest = async (requestData: Partial<MaintenanceRequest>): Promise<MaintenanceRequest> => {
  return apiRequest("/maintenance/requests", {
    method: "POST",
    body: JSON.stringify(requestData),
  });
};

/**
 * Fetches a specific maintenance request by ID.
 * @param {number} requestId - The ID of the maintenance request to fetch
 * @returns {Promise<MaintenanceRequest>} A promise that resolves to the maintenance request object
 */
export const getMaintenanceRequest = async (requestId: number): Promise<MaintenanceRequest> => {
  return apiRequest(`/maintenance/requests/${requestId}`);
};

/**
 * Updates an existing maintenance request.
 * @param {number} requestId - The ID of the maintenance request to update
 * @param {Partial<MaintenanceRequest>} requestData - The updated maintenance request data
 * @returns {Promise<MaintenanceRequest>} A promise that resolves to the updated maintenance request object
 */
export const updateMaintenanceRequest = async (requestId: number, requestData: Partial<MaintenanceRequest>): Promise<MaintenanceRequest> => {
  return apiRequest(`/maintenance/requests/${requestId}`, {
    method: "PUT",
    body: JSON.stringify(requestData),
  });
};

/**
 * Deletes a maintenance request.
 * @param {number} requestId - The ID of the maintenance request to delete
 * @returns {Promise<void>} A promise that resolves when the request is deleted
 */
export const deleteMaintenanceRequest = async (requestId: number): Promise<void> => {
  return apiRequest(`/maintenance/requests/${requestId}`, {
    method: "DELETE",
  });
};

/**
 * Deletes multiple maintenance requests in bulk.
 * @param {number[]} requestIds - An array of maintenance request IDs to delete.
 * @returns {Promise<void>} A promise that resolves when the requests are deleted.
 */
export const bulkDeleteMaintenanceRequests = async (requestIds: number[]): Promise<void> => {
  return apiRequest("/maintenance/requests/bulk", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request_ids: requestIds }),
  });
};

/**
 * Uploads a photo for a maintenance request.
 *
 * Security: This function performs client-side validation before upload to prevent:
 * - Invalid file types (only images allowed: jpg, jpeg, png, gif, webp)
 * - Excessively large files (max 10MB)
 * - Poor UX from delayed server-side validation failures
 *
 * Note: Server-side validation is still required as client-side checks can be bypassed.
 * This is a defensive measure to catch issues early and improve user experience.
 *
 * @param {File} file - The image file to upload
 * @returns {Promise<string>} A promise that resolves to the uploaded photo URL
 * @throws {Error} Throws an error if validation fails or upload fails
 *
 * @example
 * ```typescript
 * try {
 *   const photoUrl = await uploadMaintenancePhoto(file);
 *   console.log('Photo uploaded:', photoUrl);
 * } catch (error) {
 *   // Handle validation or upload error
 *   toast.error(error.message);
 * }
 * ```
 */
export const uploadMaintenancePhoto = async (file: File): Promise<string> => {
  // Perform client-side validation before upload
  const validationResult = validateImageFile(file);

  if (!validationResult.isValid) {
    // Validation failed - throw error with user-friendly message
    const errorMessage = validationResult.message || 'Invalid file';

    // Track validation failure in Sentry with additional context
    Sentry.captureException(new Error(`Maintenance photo upload validation failed: ${validationResult.error}`), {
      tags: {
        component: 'maintenance',
        action: 'photo_upload',
        validation_error: validationResult.error,
        upload_type: 'maintenance_photo',
      },
      contexts: {
        file: {
          name: file.name,
          type: file.type,
          size: file.size,
        },
        validation: {
          error_code: validationResult.error,
          error_message: errorMessage,
        },
      },
      level: 'warning',
    });

    // Throw error to be caught by caller
    throw new Error(errorMessage);
  }

  // Validation passed - proceed with upload
  try {
    const data = await uploadFile("/maintenance/upload-photo", file, {
      formKey: "upload_file",
    });
    return data.photo_url;
  } catch (error: any) {
    // Track upload failure in Sentry
    Sentry.captureException(error, {
      tags: {
        component: 'maintenance',
        action: 'photo_upload',
        upload_type: 'maintenance_photo',
        error_type: 'upload_failed',
      },
      contexts: {
        file: {
          name: file.name,
          type: file.type,
          size: file.size,
        },
      },
    });

    // Re-throw to allow caller to handle
    throw error;
  }
};

/**
 * Generate a secure, time-limited URL for a maintenance photo.
 * 
 * For private Azure containers, photos require SAS tokens to be accessed.
 * This endpoint generates a 1-hour expiring SAS token for secure photo access.
 * 
 * @param {string} photoUrl - The original Azure Blob URL of the photo
 * @returns {Promise<{secure_url: string, expires_at: string, expires_in_seconds: number}>}
 * 
 * @example
 * ```typescript
 * const { secure_url } = await getSecurePhotoUrl(
 *   'https://storage.blob.core.windows.net/maintenance-photos/photo.jpg'
 * );
 * // Use secure_url to display image (valid for 1 hour)
 * ```
 */
export const getSecurePhotoUrl = async (photoUrl: string): Promise<{
  secure_url: string;
  expires_at: string;
  expires_in_seconds: number;
}> => {
  // Encode photo URL as query parameter
  const encodedUrl = encodeURIComponent(photoUrl);
  return apiRequest(`/maintenance/photos/secure-url?photo_url=${encodedUrl}`, {
    method: "POST",
  });
}; 
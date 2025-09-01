import { apiRequest } from './core';

// Simplified interfaces - no more SAS token complexity

interface PropertyImageResponse {
  id: number;
  property_id: number;
  image_url: string;
  is_primary: boolean;
  display_order: number;
  created_at: string;
  updated_at: string;
}

interface ImageReorderRequest {
  image_id: number;
  display_order: number;
}

interface UploadOptions {
  is_primary?: boolean;
  display_order?: number;
}

interface UploadResult {
  success?: PropertyImageResponse;
  error?: string;
  filename?: string;
}

/**
 * Property Images API Service  
 * Simplified direct upload approach (matches expense receipts)
 */
export const propertyImagesApi = {
  /**
   * Upload a single property image directly (simplified approach)
   */
  async uploadImage(
    propertyId: number,
    file: File,
    options: UploadOptions = {}
  ): Promise<PropertyImageResponse> {
    const { is_primary = false, display_order } = options;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('is_primary', String(is_primary));
    if (display_order !== undefined) {
      formData.append('display_order', String(display_order));
    }

    return apiRequest(`/properties/${propertyId}/images/upload`, {
      method: 'POST',
      body: formData,
      // Don't set Content-Type header - let the browser set it with boundary for FormData
      headers: {}
    });
  },

  /**
   * Upload multiple images (simplified - uploads one by one)
   */
  async uploadMultipleImages(
    propertyId: number,
    files: File[]
  ): Promise<UploadResult[]> {
    const results: UploadResult[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const isPrimary = i === 0; // First image is primary by default

      try {
        const imageRecord = await this.uploadImage(propertyId, file, {
          is_primary: isPrimary,
          display_order: i
        });

        results.push({ success: imageRecord });
      } catch (error) {
        console.error(`Failed to upload file ${file.name}:`, error);
        results.push({
          error: error instanceof Error ? error.message : 'Upload failed',
          filename: file.name
        });
      }
    }

    return results;
  },

  /**
   * Get all images for a property
   */
  async getPropertyImages(propertyId: number): Promise<PropertyImageResponse[]> {
    return apiRequest(`/properties/${propertyId}/images`);
  },

  /**
   * Delete a property image
   */
  async deleteImage(
    propertyId: number,
    imageId: number
  ): Promise<{ message: string }> {
    return apiRequest(`/properties/${propertyId}/images/${imageId}`, {
      method: 'DELETE'
    });
  },

  /**
   * Reorder property images
   */
  async reorderImages(
    propertyId: number,
    imageOrders: ImageReorderRequest[]
  ): Promise<PropertyImageResponse[]> {
    return apiRequest(`/properties/${propertyId}/images/reorder`, {
      method: 'PUT',
      body: JSON.stringify(imageOrders)
    });
  },

  /**
   * Set an image as the primary image
   */
  async setPrimaryImage(
    propertyId: number,
    imageId: number
  ): Promise<PropertyImageResponse> {
    return apiRequest(`/properties/${propertyId}/images/${imageId}/primary`, {
      method: 'PUT'
    });
  }
};

// Export types for use in components
export type {
  PropertyImageResponse,
  ImageReorderRequest,
  UploadOptions,
  UploadResult
};
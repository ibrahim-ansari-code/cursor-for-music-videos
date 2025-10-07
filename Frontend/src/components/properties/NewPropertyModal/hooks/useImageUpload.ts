import { useState, useCallback } from 'react';
import { toast } from 'react-toastify';
import { 
  propertyImagesApi, 
  PropertyImageResponse, 
  UploadResult 
} from '../../../../utils/api/propertyImages';

interface UploadProgress {
  [key: string]: number;
}

interface UseImageUploadOptions {
  onUploadComplete?: (images: PropertyImageResponse[]) => void;
  onUploadError?: (error: Error) => void;
}

export const useImageUpload = (options: UseImageUploadOptions = {}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress>({});
  const [uploadedImages, setUploadedImages] = useState<PropertyImageResponse[]>([]);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);

  /**
   * Upload a single image
   */
  const uploadSingleImage = useCallback(async (
    propertyId: number,
    file: File,
    isPrimary: boolean = false,
    displayOrder: number = 0
  ): Promise<PropertyImageResponse | null> => {
    const fileId = `${file.name}-${Date.now()}`;
    
    try {
      setUploadProgress(prev => ({ ...prev, [fileId]: 0 }));
      
      const result = await propertyImagesApi.uploadImage(propertyId, file, {
        is_primary: isPrimary,
        display_order: displayOrder
      });

      setUploadProgress(prev => {
        const { [fileId]: _, ...rest } = prev;
        return rest;
      });

      return result;
    } catch (error) {
      console.error(`Failed to upload ${file.name}:`, error);
      setUploadProgress(prev => {
        const { [fileId]: _, ...rest } = prev;
        return rest;
      });
      
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      setUploadErrors(prev => [...prev, `${file.name}: ${errorMessage}`]);
      
      if (options.onUploadError) {
        options.onUploadError(error as Error);
      }
      
      return null;
    }
  }, [options]);

  /**
   * Upload multiple images
   */
  const uploadMultipleImages = useCallback(async (
    propertyId: number,
    files: File[]
  ): Promise<PropertyImageResponse[]> => {
    if (!propertyId || files.length === 0) {
      return [];
    }

    setIsUploading(true);
    setUploadErrors([]);
    const successfulUploads: PropertyImageResponse[] = [];

    try {
      const results = await propertyImagesApi.uploadMultipleImages(
        propertyId,
        files
      );

      // Process results and collect errors
      const failedUploads: string[] = [];
      results.forEach((result: UploadResult) => {
        if (result.success) {
          successfulUploads.push(result.success);
        } else if (result.error) {
          const errorMessage = `${result.filename}: ${result.error}`;
          failedUploads.push(errorMessage);
          setUploadErrors(prev => [...prev, errorMessage]);
        }
      });

      // Update uploaded images state
      setUploadedImages(prev => [...prev, ...successfulUploads]);

      // Show success/error toasts
      if (successfulUploads.length > 0) {
        toast.success(
          `Successfully uploaded ${successfulUploads.length} of ${files.length} images`,
          { position: 'top-right', autoClose: 3000 }
        );
      }

      if (failedUploads.length > 0) {
        toast.error(
          `Failed to upload ${failedUploads.length} images`,
          { position: 'top-right', autoClose: 5000 }
        );
      }

      // Call success callback
      if (options.onUploadComplete && successfulUploads.length > 0) {
        options.onUploadComplete(successfulUploads);
      }

      return successfulUploads;
    } catch (error) {
      console.error('Batch upload failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      toast.error(`Upload failed: ${errorMessage}`, {
        position: 'top-right',
        autoClose: 5000
      });
      
      if (options.onUploadError) {
        options.onUploadError(error as Error);
      }
      
      return [];
    } finally {
      setIsUploading(false);
      setUploadProgress({});
    }
  }, [options]);

  /**
   * Delete an image
   */
  const deleteImage = useCallback(async (
    propertyId: number,
    imageId: number
  ): Promise<boolean> => {
    try {
      await propertyImagesApi.deleteImage(propertyId, imageId);
      
      setUploadedImages(prev => prev.filter(img => img.id !== imageId));
      
      toast.success('Image deleted successfully', {
        position: 'top-right',
        autoClose: 3000
      });
      
      return true;
    } catch (error) {
      console.error('Failed to delete image:', error);
      const errorMessage = error instanceof Error ? error.message : 'Delete failed';
      toast.error(`Failed to delete image: ${errorMessage}`, {
        position: 'top-right',
        autoClose: 5000
      });
      
      return false;
    }
  }, []);

  /**
   * Set an image as primary
   */
  const setPrimaryImage = useCallback(async (
    propertyId: number,
    imageId: number
  ): Promise<boolean> => {
    try {
      await propertyImagesApi.setPrimaryImage(propertyId, imageId);

      
      // Update local state
      setUploadedImages(prev => prev.map(img => ({
        ...img,
        is_primary: img.id === imageId
      })));
      
      toast.success('Primary image updated', {
        position: 'top-right',
        autoClose: 3000
      });
      
      return true;
    } catch (error) {
      console.error('Failed to set primary image:', error);
      const errorMessage = error instanceof Error ? error.message : 'Update failed';
      toast.error(`Failed to set primary image: ${errorMessage}`, {
        position: 'top-right',
        autoClose: 5000
      });
      
      return false;
    }
  }, []);

  /**
   * Reorder images
   */
  const reorderImages = useCallback(async (
    propertyId: number,
    newOrder: { image_id: number; display_order: number }[]
  ): Promise<boolean> => {
    try {
      const reorderedImages = await propertyImagesApi.reorderImages(propertyId, newOrder);
      
      setUploadedImages(reorderedImages);
      
      return true;
    } catch (error) {
      console.error('Failed to reorder images:', error);
      const errorMessage = error instanceof Error ? error.message : 'Reorder failed';
      toast.error(`Failed to reorder images: ${errorMessage}`, {
        position: 'top-right',
        autoClose: 5000
      });
      
      return false;
    }
  }, []);

  /**
   * Clear all upload state
   */
  const clearUploadState = useCallback(() => {
    setUploadProgress({});
    setUploadedImages([]);
    setUploadErrors([]);
    setIsUploading(false);
  }, []);

  return {
    // State
    isUploading,
    uploadProgress,
    uploadedImages,
    uploadErrors,
    
    // Actions
    uploadSingleImage,
    uploadMultipleImages,
    deleteImage,
    setPrimaryImage,
    reorderImages,
    clearUploadState
  };
};

export type { UseImageUploadOptions, UploadProgress };
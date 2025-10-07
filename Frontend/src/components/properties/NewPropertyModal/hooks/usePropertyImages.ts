import { useState, useCallback, useRef, useEffect } from 'react';
import { toast } from 'react-toastify';
import { 
  propertyImagesApi, 
  PropertyImageResponse, 
  UploadResult 
} from '../../../../utils/api/propertyImages';

// Unified image state with discriminated union for type safety
export interface PropertyImageState {
  id: string | number;
  file?: File;
  preview?: string;
  imageUrl?: string;
  isPrimary: boolean;
  displayOrder: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  progress: number;
  errorMessage?: string;
  // Backend fields for completed images
  propertyId?: number;
  createdAt?: string;
  updatedAt?: string;
}

// Type guards for better type safety
export const isPendingImage = (image: PropertyImageState): image is PropertyImageState & { file: File; preview: string } => {
  return image.status === 'pending' && !!image.file && !!image.preview;
};

export const isUploadedImage = (image: PropertyImageState): image is PropertyImageState & { imageUrl: string; propertyId: number } => {
  return image.status === 'completed' && !!image.imageUrl && !!image.propertyId;
};

export interface ImageUploadError {
  type: 'NETWORK' | 'AUTHENTICATION' | 'FILE_TYPE' | 'FILE_SIZE' | 'STORAGE' | 'PERMISSION' | 'QUOTA_EXCEEDED' | 'DUPLICATE';
  message: string;
  filename: string;
  retryable: boolean;
  code?: string;
}

interface UsePropertyImagesOptions {
  propertyId?: number;
  onUploadComplete?: (images: PropertyImageResponse[]) => void;
  onUploadError?: (error: ImageUploadError) => void;
  maxFiles?: number;
  maxFileSize?: number; // bytes
  allowedTypes?: string[];
}

interface UsePropertyImagesReturn {
  // State
  images: PropertyImageState[];
  isUploading: boolean;
  operationLoading: Record<string, boolean>;
  uploadProgress: Record<string, number>;
  
  // Actions
  addPendingImages: (files: File[]) => Promise<string[]>; // Returns image IDs
  uploadImages: (imageIds?: string[]) => Promise<PropertyImageResponse[]>;
  deleteImage: (imageId: string | number) => Promise<boolean>;
  setPrimaryImage: (imageId: string | number) => Promise<boolean>;
  reorderImages: (newOrder: PropertyImageState[]) => Promise<boolean>;
  retryUpload: (imageId: string) => Promise<boolean>;
  clearPendingImages: () => void;
  
  // Utilities
  getPendingImages: () => PropertyImageState[];
  getUploadedImages: () => PropertyImageState[];
  getImageById: (id: string | number) => PropertyImageState | undefined;
  validateFiles: (files: File[]) => { valid: File[], errors: ImageUploadError[] };
}

export const usePropertyImages = (options: UsePropertyImagesOptions = {}): UsePropertyImagesReturn => {
  const {
    propertyId,
    onUploadComplete,
    onUploadError,
    maxFiles = 20,
    maxFileSize = 10 * 1024 * 1024, // 10MB
    allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif']
  } = options;

  // Single source of truth for all images
  const [images, setImages] = useState<PropertyImageState[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [operationLoading, setOperationLoading] = useState<Record<string, boolean>>({});
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  
  // Resource management
  const previewRefs = useRef<Set<string>>(new Set());
  
  // Race condition protection
  const primaryOperationRef = useRef<{ propertyId: number; targetId: string | number } | null>(null);

  // File validation with comprehensive error types
  const validateFiles = useCallback((files: File[]): { valid: File[], errors: ImageUploadError[] } => {
    const errors: ImageUploadError[] = [];
    const valid: File[] = [];
    
    const currentImageCount = images.length;
    
    if (files.length + currentImageCount > maxFiles) {
      errors.push({
        type: 'QUOTA_EXCEEDED',
        message: `Maximum ${maxFiles} images allowed. Currently have ${currentImageCount}, trying to add ${files.length}.`,
        filename: 'multiple files',
        retryable: false
      });
      return { valid: [], errors };
    }
    
    files.forEach(file => {
      // File type validation
      if (!allowedTypes.includes(file.type)) {
        errors.push({
          type: 'FILE_TYPE',
          message: `Invalid file type. Supported formats: ${allowedTypes.join(', ')}`,
          filename: file.name,
          retryable: false
        });
        return;
      }
      
      // File size validation
      if (file.size > maxFileSize) {
        const maxSizeMB = (maxFileSize / (1024 * 1024)).toFixed(1);
        errors.push({
          type: 'FILE_SIZE',
          message: `File too large. Maximum size: ${maxSizeMB}MB`,
          filename: file.name,
          retryable: false
        });
        return;
      }
      
      // Check for duplicate files (by name and size)
      const isDuplicate = images.some(img => 
        isPendingImage(img) && 
        img.file.name === file.name && 
        img.file.size === file.size
      );
      
      if (isDuplicate) {
        errors.push({
          type: 'DUPLICATE',
          message: 'File already added',
          filename: file.name,
          retryable: false
        });
        return;
      }
      
      valid.push(file);
    });
    
    return { valid, errors };
  }, [images, maxFiles, maxFileSize, allowedTypes]);

  // Add pending images with proper resource management
  const addPendingImages = useCallback(async (files: File[]): Promise<string[]> => {
    const { valid: validFiles, errors } = validateFiles(files);
    
    // Display validation errors
    errors.forEach(error => {
      toast.error(`${error.filename}: ${error.message}`, {
        position: 'top-right',
        autoClose: 5000
      });
      onUploadError?.(error);
    });
    
    if (validFiles.length === 0) return [];
    
    const newImageIds: string[] = [];
    const newImages = validFiles.map((file, index) => {
      const preview = URL.createObjectURL(file);
      previewRefs.current.add(preview);
      
      const imageId = `pending-${Date.now()}-${index}`;
      newImageIds.push(imageId);
      
      const shouldBePrimary = images.length === 0 && index === 0; // First image of first batch is primary
      
      return {
        id: imageId,
        file,
        preview,
        isPrimary: shouldBePrimary,
        displayOrder: images.length + index,
        status: 'pending' as const,
        progress: 0
      };
    });

    setImages(prev => [...prev, ...newImages]);
    return newImageIds;
  }, [images, validateFiles, onUploadError]);

  // Upload images with comprehensive error handling
  const uploadImages = useCallback(async (imageIds?: string[]): Promise<PropertyImageResponse[]> => {
    if (!propertyId) {
      throw new Error('Property ID is required for upload');
    }

    const imagesToUpload = imageIds 
      ? images.filter(img => imageIds.includes(img.id as string) && isPendingImage(img))
      : images.filter(isPendingImage);

    if (imagesToUpload.length === 0) return [];

    setIsUploading(true);
    const successfulUploads: PropertyImageResponse[] = [];

    // Mark images as uploading
    setImages(prev => prev.map(img => 
      imagesToUpload.some(uploadImg => uploadImg.id === img.id)
        ? { ...img, status: 'uploading' as const, progress: 0 }
        : img
    ));

    try {
      const filesToUpload = imagesToUpload.map(img => img.file!);
      
      const results = await propertyImagesApi.uploadMultipleImages(
        propertyId,
        filesToUpload
      );

      // Process results and update state using functional setState to avoid stale closures
      setImages(currentImages => {
        const updatedImages = [...currentImages];
        results.forEach((result: UploadResult, index) => {
          const imageId = imagesToUpload[index]?.id;
          const imageIndex = updatedImages.findIndex(img => img.id === imageId);
          
          if (imageIndex === -1) return;
          
          if (result.success) {
            // Transform to completed image
            const completedImage: PropertyImageState = {
              id: result.success.id,
              propertyId: result.success.property_id,
              imageUrl: result.success.image_url,
              isPrimary: result.success.is_primary,
              displayOrder: result.success.display_order,
              status: 'completed',
              progress: 100,
              createdAt: result.success.created_at,
              updatedAt: result.success.updated_at
            };
            
            // Clean up preview URL
            const originalImage = updatedImages[imageIndex];
            if (originalImage.preview) {
              URL.revokeObjectURL(originalImage.preview);
              previewRefs.current.delete(originalImage.preview);
            }
            
            updatedImages[imageIndex] = completedImage;
            successfulUploads.push(result.success);
          } else if (result.error) {
            // Set error state
            updatedImages[imageIndex] = {
              ...updatedImages[imageIndex],
              status: 'error',
              errorMessage: result.error,
              progress: 0
            };
            
            const error: ImageUploadError = {
              type: 'STORAGE',
              message: result.error,
              filename: result.filename || 'unknown',
              retryable: true
            };
            onUploadError?.(error);
          }
        });
        
        return updatedImages;
      });

      // Show success toast
      if (successfulUploads.length > 0) {
        toast.success(
          `Successfully uploaded ${successfulUploads.length} of ${imagesToUpload.length} images`,
          { position: 'top-right', autoClose: 3000 }
        );
        onUploadComplete?.(successfulUploads);
      }

      // Show error toast for failures
      const failedCount = imagesToUpload.length - successfulUploads.length;
      if (failedCount > 0) {
        toast.error(
          `${failedCount} images failed to upload. Click retry to try again.`,
          { position: 'top-right', autoClose: 5000 }
        );
      }

      return successfulUploads;
    } catch (error) {
      console.error('Batch upload failed:', error);
      
      const uploadError: ImageUploadError = {
        type: 'NETWORK',
        message: error instanceof Error ? error.message : 'Upload failed',
        filename: 'batch upload',
        retryable: true
      };
      
      toast.error(`Upload failed: ${uploadError.message}`, {
        position: 'top-right',
        autoClose: 5000
      });
      
      onUploadError?.(uploadError);
      
      // Mark all as error
      setImages(prev => prev.map(img => 
        imagesToUpload.some(uploadImg => uploadImg.id === img.id)
          ? { ...img, status: 'error' as const, errorMessage: uploadError.message, progress: 0 }
          : img
      ));
      
      return [];
    } finally {
      setIsUploading(false);
      setUploadProgress({});
    }
  }, [propertyId, images, onUploadComplete, onUploadError]);

  // Delete image with proper cleanup
  const deleteImage = useCallback(async (imageId: string | number): Promise<boolean> => {
    const image = images.find(img => img.id === imageId);
    if (!image) return false;

    const loadingKey = `delete-${imageId}`;
    setOperationLoading(prev => ({ ...prev, [loadingKey]: true }));

    try {
      if (isUploadedImage(image) && propertyId) {
        // Delete from backend
        await propertyImagesApi.deleteImage(propertyId, image.id as number);
      }

      // Clean up preview URL if it exists
      if (image.preview) {
        URL.revokeObjectURL(image.preview);
        previewRefs.current.delete(image.preview);
      }

      // Remove from state
      setImages(prev => {
        const filtered = prev.filter(img => img.id !== imageId);
        
        // If we removed the primary image, make the first one primary
        if (image.isPrimary && filtered.length > 0 && !filtered.some(img => img.isPrimary)) {
          const firstImage = filtered[0];
          filtered[0] = { ...firstImage, isPrimary: true };
          
          // Set primary in backend if it's an uploaded image
          if (isUploadedImage(firstImage) && propertyId) {
            propertyImagesApi.setPrimaryImage(propertyId, firstImage.id as number)
              .catch(error => {
                console.error('Failed to set new primary image:', error);
                // Revert the UI state to maintain consistency
                setImages(prev => prev.map(img => 
                  img.id === firstImage.id ? { ...img, isPrimary: false } : img
                ));
                // Notify user of the failure
                const { toast } = require('react-toastify');
                toast.error('Failed to update primary image. Please try again.', {
                  position: 'top-right',
                  autoClose: 4000
                });
              });
          }
        }
        
        return filtered;
      });

      toast.success('Image deleted successfully', {
        position: 'top-right',
        autoClose: 3000
      });

      return true;
    } catch (error) {
      console.error('Failed to delete image:', error);
      
      const deleteError: ImageUploadError = {
        type: 'NETWORK',
        message: error instanceof Error ? error.message : 'Delete failed',
        filename: `Image ${imageId}`,
        retryable: true
      };
      
      toast.error(`Failed to delete image: ${deleteError.message}`, {
        position: 'top-right',
        autoClose: 5000
      });
      
      return false;
    } finally {
      setOperationLoading(prev => {
        const { [loadingKey]: _, ...rest } = prev;
        return rest;
      });
    }
  }, [images, propertyId]);

  // Set primary image with race condition protection
  const setPrimaryImage = useCallback(async (imageId: string | number): Promise<boolean> => {
    const image = images.find(img => img.id === imageId);
    if (!image || image.isPrimary) return true;

    const loadingKey = `primary-${imageId}`;

    if (isUploadedImage(image) && propertyId) {
      // Race condition protection for uploaded images
      if (primaryOperationRef.current && 
          primaryOperationRef.current.propertyId === propertyId && 
          primaryOperationRef.current.targetId !== imageId) {
        console.warn('Primary image operation already in progress, ignoring new request');
        return false;
      }

      primaryOperationRef.current = { propertyId, targetId: imageId };
      setOperationLoading(prev => ({ ...prev, [loadingKey]: true }));

      try {
        await propertyImagesApi.setPrimaryImage(propertyId, image.id as number);
        
        // Only update state if this is still the current operation
        if (primaryOperationRef.current?.propertyId === propertyId && 
            primaryOperationRef.current?.targetId === imageId) {
          
          setImages(prev => prev.map(img => ({
            ...img,
            isPrimary: img.id === imageId
          })));

          toast.success('Primary image updated', {
            position: 'top-right',
            autoClose: 3000
          });
        }

        return true;
      } catch (error) {
        console.error('Failed to set primary image:', error);
        
        toast.error('Failed to set primary image', {
          position: 'top-right',
          autoClose: 5000
        });
        
        return false;
      } finally {
        if (primaryOperationRef.current?.propertyId === propertyId && 
            primaryOperationRef.current?.targetId === imageId) {
          primaryOperationRef.current = null;
        }
        
        setOperationLoading(prev => {
          const { [loadingKey]: _, ...rest } = prev;
          return rest;
        });
      }
    } else {
      // Update pending images locally
      setImages(prev => prev.map(img => ({
        ...img,
        isPrimary: img.id === imageId
      })));
      
      return true;
    }
  }, [images, propertyId]);

  // Reorder images
  const reorderImages = useCallback(async (newOrder: PropertyImageState[]): Promise<boolean> => {
    if (!propertyId) {
      // For pending images, just update local state
      setImages(newOrder.map((img, index) => ({ ...img, displayOrder: index })));
      return true;
    }

    const uploadedImages = newOrder.filter(isUploadedImage);
    if (uploadedImages.length === 0) {
      setImages(newOrder);
      return true;
    }

    const loadingKey = 'reorder-uploaded';
    setOperationLoading(prev => ({ ...prev, [loadingKey]: true }));

    try {
      const reorderData = uploadedImages.map((img, index) => ({
        image_id: img.id as number,
        display_order: index
      }));

      await propertyImagesApi.reorderImages(propertyId, reorderData);
      
      setImages(newOrder.map((img, index) => ({ ...img, displayOrder: index })));
      
      return true;
    } catch (error) {
      console.error('Failed to reorder images:', error);
      
      toast.error('Failed to reorder images', {
        position: 'top-right',
        autoClose: 5000
      });
      
      return false;
    } finally {
      setOperationLoading(prev => {
        const { [loadingKey]: _, ...rest } = prev;
        return rest;
      });
    }
  }, [propertyId]);

  // Retry upload for failed images
  const retryUpload = useCallback(async (imageId: string): Promise<boolean> => {
    const failedImage = images.find(img => img.id === imageId && img.status === 'error');
    if (!failedImage || !isPendingImage(failedImage)) return false;

    const results = await uploadImages([imageId]);
    return results.length > 0;
  }, [images, uploadImages]);

  // Clear pending images with cleanup
  const clearPendingImages = useCallback(() => {
    const pendingImages = images.filter(isPendingImage);
    
    // Clean up preview URLs
    pendingImages.forEach(img => {
      if (img.preview) {
        URL.revokeObjectURL(img.preview);
        previewRefs.current.delete(img.preview);
      }
    });

    setImages(prev => prev.filter(img => !isPendingImage(img)));
    
    toast.info('Pending images cleared', {
      position: 'top-right',
      autoClose: 2000
    });
  }, [images]);

  // Utility functions
  const getPendingImages = useCallback(() => images.filter(isPendingImage), [images]);
  const getUploadedImages = useCallback(() => images.filter(isUploadedImage), [images]);
  const getImageById = useCallback((id: string | number) => images.find(img => img.id === id), [images]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      previewRefs.current.forEach(url => {
        URL.revokeObjectURL(url);
      });
      previewRefs.current.clear();
    };
  }, []);

  return {
    // State
    images,
    isUploading,
    operationLoading,
    uploadProgress,
    
    // Actions
    addPendingImages,
    uploadImages,
    deleteImage,
    setPrimaryImage,
    reorderImages,
    retryUpload,
    clearPendingImages,
    
    // Utilities
    getPendingImages,
    getUploadedImages,
    getImageById,
    validateFiles
  };
};
import { useState, useCallback } from 'react';
import { uploadMaintenancePhoto } from '../../utils/api/maintenance';
import type { PhotoFileWithId, PhotoUploadProgress, MaintenancePhotoState } from '../../types/tenant';

/**
 * Custom hook for managing maintenance request photo uploads
 *
 * Features:
 * - Multi-file upload with progress tracking
 * - Client-side validation (size, type)
 * - Error handling per file
 * - Remove uploaded photos
 * - Reset state
 *
 * Follows the same pattern as useReceiptUpload from SharedModalComponents
 */
export const useMaintenancePhotos = () => {
  const [selectedFiles, setSelectedFiles] = useState<PhotoFileWithId[]>([]);
  const [uploadingPhotos, setUploadingPhotos] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<PhotoUploadProgress[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);

  /**
   * Handle file selection - just creates previews, doesn't upload yet
   * Returns array of preview URLs (object URLs for local display)
   */
  const handleFileChange = useCallback((files: FileList | File[]): string[] => {
    const fileArray = Array.from(files);

    if (fileArray.length === 0) return [];

    // Validate files
    const maxFileSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf'];
    const allowedExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf'];

    const invalidFiles = fileArray.filter(file => {
      const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
      return (
        file.size > maxFileSize ||
        !allowedTypes.includes(file.type) ||
        !allowedExtensions.includes(fileExtension)
      );
    });

    if (invalidFiles.length > 0) {
      setUploadError(
        'Some files are too large (max 10MB) or have invalid formats (JPG, PNG, GIF, PDF only)'
      );
      return [];
    }

    // Create preview URLs for the files
    const filesWithPreviews: PhotoFileWithId[] = fileArray.map((file) => {
      const previewUrl = URL.createObjectURL(file);
      return {
        id: crypto.randomUUID(),
        file,
        name: file.name,
        size: file.size,
        preview: previewUrl,
      };
    });

    setSelectedFiles(prev => [...prev, ...filesWithPreviews]);
    setUploadError(null);

    // Return preview URLs for display
    return filesWithPreviews.map(f => f.preview!);
  }, []);

  /**
   * Upload all pending files to Azure
   * Called when form is submitted
   * Returns array of successfully uploaded URLs
   */
  const uploadAllPendingFiles = useCallback(async (): Promise<string[]> => {
    if (selectedFiles.length === 0) return [];

    setUploadingPhotos(true);
    setUploadError(null);

    try {
      // Upload files in parallel
      const uploadPromises = selectedFiles.map((fileObj) =>
        uploadMaintenancePhoto(fileObj.file)
          .then((url) => ({ id: fileObj.id, url, success: true }))
          .catch((err) => ({
            id: fileObj.id,
            error: err.message || 'Failed to upload',
            success: false,
          }))
      );

      const results = await Promise.all(uploadPromises);

      // Process results
      const successfulUploads: string[] = [];
      const uploadErrors: string[] = [];

      results.forEach((result) => {
        if (result.success && 'url' in result) {
          successfulUploads.push(result.url);
        } else if ('error' in result) {
          uploadErrors.push(result.error || 'Unknown error');
        }
      });

      // Show errors if any
      if (uploadErrors.length > 0) {
        setUploadError(`Upload errors: ${uploadErrors.join(', ')}`);
      }

      return successfulUploads;
    } catch (error: any) {
      setUploadError(error.message || 'Unexpected error during upload');
      return [];
    } finally {
      setUploadingPhotos(false);
    }
  }, [selectedFiles]);

  /**
   * Remove a photo by ID or preview URL
   * Also revokes the object URL to prevent memory leaks
   */
  const removePhoto = useCallback((identifier: string) => {
    // Find the file to revoke its preview URL
    const fileToRemove = selectedFiles.find(f => f.preview === identifier || f.id === identifier);
    if (fileToRemove?.preview) {
      URL.revokeObjectURL(fileToRemove.preview);
    }
    
    setSelectedFiles(prev => prev.filter(f => f.id !== identifier && f.preview !== identifier));
    setUploadProgress(prev => prev.filter(p => p.id !== identifier));
  }, [selectedFiles]);

  /**
   * Reset all state and clean up preview URLs
   */
  const resetState = useCallback(() => {
    // Revoke all preview URLs to prevent memory leaks
    selectedFiles.forEach(file => {
      if (file.preview) {
        URL.revokeObjectURL(file.preview);
      }
    });
    
    setSelectedFiles([]);
    setUploadProgress([]);
    setUploadError(null);
    setUploadingPhotos(false);
  }, [selectedFiles]);

  /**
   * Get upload status for a specific file
   */
  const getFileStatus = useCallback((fileId: string): PhotoUploadProgress | undefined => {
    return uploadProgress.find(p => p.id === fileId);
  }, [uploadProgress]);

  /**
   * Retry uploading a failed file
   */
  const retryUpload = useCallback(async (fileId: string): Promise<string | null> => {
    const fileToRetry = selectedFiles.find(f => f.id === fileId);
    if (!fileToRetry?.file) return null;

    // Update status to uploading
    setUploadProgress(prev => 
      prev.map(p => p.id === fileId ? { id: fileId, status: 'pending' as const } : p)
    );
    setUploadingPhotos(true);

    try {
      const url = await uploadMaintenancePhoto(fileToRetry.file);
      
      // Update to success
      setUploadProgress(prev =>
        prev.map(p => p.id === fileId ? { id: fileId, status: 'done' as const } : p)
      );
      
      return url;
    } catch (err: any) {
      // Update to error
      setUploadProgress(prev =>
        prev.map(p => 
          p.id === fileId 
            ? { id: fileId, status: 'error' as const, error: err.message || 'Upload failed' } 
            : p
        )
      );
      return null;
    } finally {
      setUploadingPhotos(false);
    }
  }, [selectedFiles]);

  const photoState: MaintenancePhotoState = {
    selectedFiles,
    uploadingPhotos,
    uploadProgress,
    uploadError,
  };

  return {
    // State
    photoState,
    selectedFiles,
    uploadingPhotos,
    uploadProgress,
    uploadError,

    // Actions
    handleFileChange,
    uploadAllPendingFiles,
    removePhoto,
    resetState,
    getFileStatus,
    retryUpload,
  };
};

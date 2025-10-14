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
   * Handle file selection and upload
   * Returns array of successfully uploaded URLs
   */
  const handleFileChange = useCallback(async (files: FileList | File[]): Promise<string[]> => {
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

    // Assign unique IDs to files
    const filesWithIds: PhotoFileWithId[] = fileArray.map((file) => ({
      id: crypto.randomUUID(),
      file,
      name: file.name,
      size: file.size,
    }));

    setSelectedFiles(prev => [...prev, ...filesWithIds]);
    setUploadError(null);
    setUploadProgress(prev => [
      ...prev,
      ...filesWithIds.map((f) => ({ id: f.id, status: 'pending' as const })),
    ]);
    setUploadingPhotos(true);

    try {
      // Upload files in parallel
      const uploadPromises = filesWithIds.map((fileObj) =>
        uploadMaintenancePhoto(fileObj.file)
          .then((url) => ({ id: fileObj.id, url, status: 'done' as const }))
          .catch((err) => ({
            id: fileObj.id,
            error: err.message || 'Failed to upload',
            status: 'error' as const,
          }))
      );

      const results = await Promise.all(uploadPromises);

      // Process results
      const successfulUploads: string[] = [];
      const uploadErrors: string[] = [];

      setUploadProgress(prevProgress => {
        const updatedProgress = [...prevProgress];
        results.forEach((result) => {
          const progressIndex = updatedProgress.findIndex(p => p.id === result.id);
          if (progressIndex >= 0) {
            if (result.status === 'done') {
              updatedProgress[progressIndex] = { id: result.id, status: 'done' };
              successfulUploads.push(result.url);
            } else if (result.status === 'error') {
              updatedProgress[progressIndex] = {
                id: result.id,
                status: 'error',
                error: result.error
              };
              uploadErrors.push(result.error || 'Unknown error');
            }
          }
        });
        return updatedProgress;
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
  }, []);

  /**
   * Remove a photo by ID or URL
   */
  const removePhoto = useCallback((identifier: string) => {
    setSelectedFiles(prev => prev.filter(f => f.id !== identifier));
    setUploadProgress(prev => prev.filter(p => p.id !== identifier));
  }, []);

  /**
   * Reset all state
   */
  const resetState = useCallback(() => {
    setSelectedFiles([]);
    setUploadProgress([]);
    setUploadError(null);
    setUploadingPhotos(false);
  }, []);

  /**
   * Get upload status for a specific file
   */
  const getFileStatus = useCallback((fileId: string): PhotoUploadProgress | undefined => {
    return uploadProgress.find(p => p.id === fileId);
  }, [uploadProgress]);

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
    removePhoto,
    resetState,
    getFileStatus,
  };
};

import React, { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion, Reorder } from 'framer-motion';
import { Upload, X, Eye, AlertCircle, Move } from 'lucide-react';
import PhotoPreviewModal from './PhotoPreviewModal';
import type { MaintenancePhotoState } from '../../types/tenant';
import { getSecurePhotoUrl } from '../../utils/api/maintenance';

interface MaintenancePhotoUploadProps {
  photos: string[];
  photoState: MaintenancePhotoState;
  onFileChange: (files: File[]) => void;
  onRemovePhoto: (url: string) => void;
  onReorderPhotos?: (newOrder: string[]) => void;
  disabled?: boolean;
  viewOnly?: boolean; // If true, hide dropzone and actions, just show photos
}

/**
 * Simplified single-section photo upload component with drag-and-drop
 * - Drag-and-drop zone with visual feedback
 * - Single unified photo gallery
 * - Reorder by dragging
 * - Full-screen preview modal
 * - Upload progress and error states
 */
const MaintenancePhotoUpload: React.FC<MaintenancePhotoUploadProps> = ({
  photos,
  photoState,
  onFileChange,
  onRemovePhoto,
  onReorderPhotos,
  disabled = false,
  viewOnly = false,
}) => {
  const [selectedPhotoIndex, setSelectedPhotoIndex] = useState<number | null>(null);
  const [securePhotoUrls, setSecurePhotoUrls] = useState<Record<string, string>>({});

  // Fetch secure URLs for existing Azure photos (not preview URLs)
  useEffect(() => {
    const fetchSecureUrls = async () => {
      // Filter for Azure URLs (existing uploaded photos) that need SAS tokens
      const azurePhotos = photos.filter(url => 
        url.startsWith('https://') && url.includes('blob.core.windows.net')
      );

      if (azurePhotos.length === 0) return;

      const urlMap: Record<string, string> = {};

      try {
        // Fetch secure URLs for Azure photos in parallel
        const secureUrlPromises = azurePhotos.map(async (photoUrl) => {
          try {
            const { secure_url } = await getSecurePhotoUrl(photoUrl);
            return { original: photoUrl, secure: secure_url };
          } catch (error) {
            console.error(`Failed to get secure URL for photo: ${photoUrl}`, error);
            // Keep original URL as fallback
            return { original: photoUrl, secure: photoUrl };
          }
        });

        const results = await Promise.all(secureUrlPromises);
        results.forEach(({ original, secure }) => {
          urlMap[original] = secure;
        });

        setSecurePhotoUrls(urlMap);
      } catch (error) {
        console.error('Failed to fetch secure photo URLs:', error);
      }
    };

    fetchSecureUrls();
  }, [photos]);

  // Dropzone configuration
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        onFileChange(acceptedFiles);
      }
    },
    [onFileChange]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
      'application/pdf': ['.pdf'],
    },
    maxSize: 10 * 1024 * 1024, // 10MB
    multiple: true,
    disabled: disabled || photoState.uploadingPhotos || viewOnly,
  });

  // Handle photo reorder
  const handleReorder = (newOrder: string[]) => {
    if (onReorderPhotos) {
      onReorderPhotos(newOrder);
    }
  };

  // Open preview modal
  const openPreview = (index: number) => {
    setSelectedPhotoIndex(index);
  };

  const isUploading = photoState.uploadingPhotos;
  const hasError = photoState.uploadError;
  const hasPhotos = photos.length > 0;

  return (
    <div className="space-y-4">
      {/* Drag-and-Drop Zone - Hidden in view-only mode */}
      {!viewOnly && (
        <div
          {...getRootProps()}
          className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 ${
            isUploading
              ? 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50 cursor-not-allowed opacity-50'
              : isDragActive
              ? 'border-blue-500 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20 cursor-pointer'
              : isDragReject
              ? 'border-red-500 dark:border-red-400 bg-red-50 dark:bg-red-900/20 cursor-pointer'
              : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500 bg-gray-50/50 dark:bg-gray-800/30 cursor-pointer'
          }`}
        >
        <input {...getInputProps()} disabled={disabled || isUploading} />

        {/* Backdrop blur effect */}
        <div className="absolute inset-0 bg-white/30 dark:bg-gray-800/30 backdrop-blur-sm rounded-xl" />

        {/* Content */}
        <div className="relative z-10">
          <motion.div
            animate={{
              scale: isDragActive ? 1.1 : 1,
              rotate: isDragActive ? 5 : 0,
            }}
            transition={{ duration: 0.2 }}
            className="inline-flex p-3 bg-gradient-to-br from-purple-100 to-purple-200 dark:from-purple-900/40 dark:to-purple-800/40 rounded-xl mb-3"
          >
            {isUploading ? (
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-600" />
            ) : isDragReject ? (
              <AlertCircle className="h-10 w-10 text-red-500" />
            ) : (
              <Upload className="h-10 w-10 text-purple-600 dark:text-purple-400" />
            )}
          </motion.div>

          <p className="text-base font-medium text-gray-900 dark:text-gray-100 mb-2">
            {isDragActive
              ? 'Drop your photos here...'
              : isDragReject
              ? 'Some files are not valid'
              : 'Drag & drop photos or PDFs here'}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
            or click to browse from your computer
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500">
            Supports: JPG, PNG, GIF, WebP, PDF (max 10MB per file)
          </p>
        </div>
      </div>
      )}

      {/* Error Messages Only - Hidden in view-only mode */}
      {!viewOnly && hasError && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center space-x-2 text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-3 rounded-lg border border-red-200 dark:border-red-700"
        >
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <span className="text-sm">{hasError}</span>
        </motion.div>
      )}

      {/* Photo Gallery */}
      {hasPhotos && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-200">
              {viewOnly ? `Photos (${photos.length})` : `Selected Photos (${photos.length})`}
            </h4>
            {!viewOnly && onReorderPhotos && photos.length > 1 && (
              <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center">
                <Move className="h-3 w-3 mr-1" />
                Drag to reorder
              </p>
            )}
          </div>

          <Reorder.Group
            axis="x"
            values={photos}
            onReorder={handleReorder}
            className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3"
          >
            {photos.map((url, index) => {
              const isPdf = url.toLowerCase().includes('.pdf');
              // Use secure URL for Azure photos, original URL for preview URLs (blob:)
              const displayUrl = securePhotoUrls[url] || url;

              return (
                <Reorder.Item
                  key={url}
                  value={url}
                  className="relative group"
                  whileDrag={{ scale: 1.05, zIndex: 100 }}
                >
                  <motion.div
                    layoutId={url}
                    className="relative aspect-square rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700 shadow-md hover:shadow-lg transition-shadow duration-300 border-2 border-gray-200 dark:border-gray-600"
                  >
                    {/* Image/PDF Display */}
                    {isPdf ? (
                      <div className="w-full h-full flex items-center justify-center bg-gray-100 dark:bg-gray-700">
                        <svg
                          className="w-8 h-8 text-gray-400 dark:text-gray-500"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                          />
                        </svg>
                      </div>
                    ) : (
                      <img
                        src={displayUrl}
                        alt={`Photo ${index + 1}`}
                        className="w-full h-full object-cover cursor-pointer"
                        onClick={() => openPreview(index)}
                      />
                    )}

                    {/* Hover Actions Overlay - Hidden in view-only mode */}
                    {!viewOnly && (
                      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                        <div className="absolute bottom-2 left-2 right-2 flex justify-between items-center">
                          {/* View Button */}
                          <button
                            type="button"
                            onClick={() => openPreview(index)}
                            className="p-1.5 bg-white/90 dark:bg-gray-800/90 rounded-lg hover:bg-white dark:hover:bg-gray-800 transition-colors"
                            aria-label="View photo"
                          >
                            <Eye className="h-4 w-4 text-gray-700 dark:text-gray-200" />
                          </button>

                          {/* Delete Button */}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              onRemovePhoto(url);
                            }}
                            className="p-1.5 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                            aria-label="Delete photo"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Drag Handle - Hidden in view-only mode */}
                    {!viewOnly && onReorderPhotos && photos.length > 1 && (
                      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                        <div className="p-1 bg-white/90 dark:bg-gray-800/90 rounded-lg cursor-move">
                          <Move className="h-4 w-4 text-gray-700 dark:text-gray-200" />
                        </div>
                      </div>
                    )}
                  </motion.div>
                </Reorder.Item>
              );
            })}
          </Reorder.Group>
        </div>
      )}

      {/* Photo Preview Modal */}
      {selectedPhotoIndex !== null && (
        <PhotoPreviewModal
          photos={photos.map(url => securePhotoUrls[url] || url)}
          initialIndex={selectedPhotoIndex}
          isOpen={selectedPhotoIndex !== null}
          onClose={() => setSelectedPhotoIndex(null)}
        />
      )}
    </div>
  );
};

export default MaintenancePhotoUpload;


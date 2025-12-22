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

  // Compact inline dropzone component
  const InlineDropzone = () => (
    <div
      {...getRootProps()}
      className={`relative aspect-square rounded-lg overflow-hidden transition-all duration-300 border-2 border-dashed flex items-center justify-center ${
        isUploading
          ? 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50 cursor-not-allowed opacity-50'
          : isDragActive
          ? 'border-blue-500 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20 cursor-pointer'
          : isDragReject
          ? 'border-red-500 dark:border-red-400 bg-red-50 dark:bg-red-900/20 cursor-pointer'
          : 'border-gray-300 dark:border-gray-600 hover:border-purple-400 dark:hover:border-purple-500 bg-gray-50/50 dark:bg-gray-800/30 cursor-pointer hover:bg-purple-50 dark:hover:bg-purple-900/20'
      }`}
    >
      <input {...getInputProps()} disabled={disabled || isUploading} />
      <div className="flex flex-col items-center justify-center p-2 text-center">
        <motion.div
          animate={{
            scale: isDragActive ? 1.1 : 1,
            rotate: isDragActive ? 5 : 0,
          }}
          transition={{ duration: 0.2 }}
        >
          {isUploading ? (
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-600" />
          ) : isDragReject ? (
            <AlertCircle className="h-6 w-6 text-red-500" />
          ) : (
            <Upload className="h-6 w-6 text-purple-500 dark:text-purple-400" />
          )}
        </motion.div>
        <p className="text-xs font-medium text-gray-600 dark:text-gray-300 mt-1.5">
          {isDragActive ? 'Drop here' : 'Add Photo'}
        </p>
      </div>
    </div>
  );

  return (
    <div className="space-y-3">
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

      {/* Photo Gallery with Inline Dropzone */}
      <div className="space-y-2">
        {!viewOnly && (
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              JPG, PNG, GIF, WebP, PDF (max 10MB)
            </p>
            {onReorderPhotos && photos.length > 1 && (
              <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center">
                <Move className="h-3 w-3 mr-1" />
                Drag to reorder
              </p>
            )}
          </div>
        )}

        {/* Grid with photos + inline dropzone */}
        <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {/* Existing Photos */}
          {hasPhotos && (
            <Reorder.Group
              axis="x"
              values={photos}
              onReorder={handleReorder}
              className="contents"
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
          )}

          {/* Inline Dropzone - appears after photos */}
          {!viewOnly && <InlineDropzone />}
        </div>
      </div>

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


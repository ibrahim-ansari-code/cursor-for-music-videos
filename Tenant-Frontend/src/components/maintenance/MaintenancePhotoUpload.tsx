import React, { useState, useCallback } from 'react';
import { motion, Reorder } from 'framer-motion';
import { Upload, X, Eye, AlertCircle, Move } from 'lucide-react';
import PhotoPreviewModal from './PhotoPreviewModal';

interface MaintenancePhotoUploadProps {
  photos: string[];
  onFileChange: (files: File[]) => void;
  onRemovePhoto: (url: string) => void;
  onReorderPhotos?: (newOrder: string[]) => void;
  disabled?: boolean;
  uploadError?: string | null;
  isUploading?: boolean;
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
  onFileChange,
  onRemovePhoto,
  onReorderPhotos,
  disabled = false,
  uploadError = null,
  isUploading = false,
}) => {
  const [selectedPhotoIndex, setSelectedPhotoIndex] = useState<number | null>(null);
  const [isDragActive, setIsDragActive] = useState(false);

  // Handle file drop
  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragActive(false);
      
      if (disabled || isUploading) return;
      
      const files = Array.from(e.dataTransfer.files).filter(file =>
        file.type.startsWith('image/') || file.type === 'application/pdf'
      );
      
      if (files.length > 0) {
        onFileChange(files);
      }
    },
    [disabled, isUploading, onFileChange]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled && !isUploading) {
      setIsDragActive(true);
    }
  };

  const handleDragLeave = () => {
    setIsDragActive(false);
  };

  // Handle file input
  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onFileChange(Array.from(files));
    }
  };

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

  const hasPhotos = photos.length > 0;

  return (
    <div className="space-y-4">
      {/* Drag-and-Drop Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !disabled && !isUploading && document.getElementById('photo-upload-input')?.click()}
        className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 cursor-pointer ${
          isUploading
            ? 'border-gray-200 bg-gray-50 cursor-not-allowed opacity-50'
            : isDragActive
            ? 'border-teal-500 bg-teal-50 cursor-pointer'
            : 'border-gray-300 hover:border-gray-400 bg-gray-50/50'
        }`}
      >
        <input
          id="photo-upload-input"
          type="file"
          multiple
          accept="image/*,application/pdf"
          onChange={handleFileInput}
          disabled={disabled || isUploading}
          className="hidden"
        />

        {/* Content */}
        <div className="relative z-10">
          <motion.div
            animate={{
              scale: isDragActive ? 1.1 : 1,
              rotate: isDragActive ? 5 : 0,
            }}
            transition={{ duration: 0.2 }}
            className="inline-flex p-3 bg-linear-to-br from-teal-100 to-teal-200 rounded-xl mb-3"
          >
            {isUploading ? (
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-teal-600" />
            ) : (
              <Upload className="h-10 w-10 text-teal-600" />
            )}
          </motion.div>

          <p className="text-base font-medium text-gray-900 mb-2">
            {isDragActive
              ? 'Drop your photos here...'
              : isUploading
              ? 'Uploading photos...'
              : 'Drag & drop photos or PDFs here'}
          </p>
          <p className="text-sm text-gray-500 mb-3">
            or click to browse from your computer
          </p>
          <p className="text-xs text-gray-400">
            Supports: JPG, PNG, GIF, WebP, PDF (max 10MB per file)
          </p>
        </div>
      </div>

      {/* Error Messages */}
      {uploadError && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center space-x-2 text-red-600 bg-red-50 p-3 rounded-lg border border-red-200"
        >
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span className="text-sm">{uploadError}</span>
        </motion.div>
      )}

      {/* Photo Gallery */}
      {hasPhotos && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-gray-700">
              Selected Photos ({photos.length})
            </h4>
            {onReorderPhotos && photos.length > 1 && (
              <p className="text-xs text-gray-500 flex items-center">
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

              return (
                <Reorder.Item
                  key={url}
                  value={url}
                  className="relative group"
                  whileDrag={{ scale: 1.05, zIndex: 100 }}
                >
                  <motion.div
                    layoutId={url}
                    className="relative aspect-square rounded-lg overflow-hidden bg-gray-100 shadow-md hover:shadow-lg transition-shadow duration-300 border-2 border-gray-200"
                  >
                    {/* Image/PDF Display */}
                    {isPdf ? (
                      <div className="w-full h-full flex items-center justify-center bg-gray-100">
                        <svg
                          className="w-8 h-8 text-gray-400"
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
                        src={url}
                        alt={`Photo ${index + 1}`}
                        className="w-full h-full object-cover cursor-pointer"
                        onClick={() => openPreview(index)}
                      />
                    )}

                    {/* Hover Actions Overlay */}
                    <div className="absolute inset-0 bg-linear-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                      <div className="absolute bottom-2 left-2 right-2 flex justify-between items-center">
                        {/* View Button */}
                        {!isPdf && (
                          <button
                            type="button"
                            onClick={() => openPreview(index)}
                            className="p-1.5 bg-white/90 rounded-lg hover:bg-white transition-colors"
                            aria-label="View photo"
                          >
                            <Eye className="h-4 w-4 text-gray-700" />
                          </button>
                        )}

                        {/* Delete Button */}
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onRemovePhoto(url);
                          }}
                          className="p-1.5 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors ml-auto"
                          aria-label="Delete photo"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    </div>

                    {/* Drag Handle */}
                    {onReorderPhotos && photos.length > 1 && (
                      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                        <div className="p-1 bg-white/90 rounded-lg cursor-move">
                          <Move className="h-4 w-4 text-gray-700" />
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
          photos={photos}
          initialIndex={selectedPhotoIndex}
          isOpen={selectedPhotoIndex !== null}
          onClose={() => setSelectedPhotoIndex(null)}
        />
      )}
    </div>
  );
};

export default MaintenancePhotoUpload;


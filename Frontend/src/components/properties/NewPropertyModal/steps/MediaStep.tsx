import * as React from 'react';
import { useState, useCallback, useEffect } from 'react';
import { useFormContext } from 'react-hook-form';
import { useDropzone } from 'react-dropzone';
import { PropertyFormData } from '../../../../types/property';
import { 
  Upload, X, Image as ImageIcon, Star, Move, AlertCircle, 
  Trash2, Eye, CheckCircle, XCircle, RotateCcw
} from 'lucide-react';
import { motion, AnimatePresence, Reorder } from 'framer-motion';
import { usePropertyImages } from '../hooks/usePropertyImages';
import { useSecureImageUrls } from '../../../../hooks/useSecureImageUrl';

interface MediaStepProps {
  onNext?: () => void;
  propertyId?: number;
  onPropertyCreated?: (uploadCallback: (propertyId: number) => Promise<void>) => void;
}

const MediaStep: React.FC<MediaStepProps> = ({ propertyId, onPropertyCreated }) => {
  const { setValue } = useFormContext<PropertyFormData>();
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  // Use unified image state management
  const {
    images,
    isUploading,
    operationLoading,
    addPendingImages,
    uploadImages,
    deleteImage,
    setPrimaryImage,
    reorderImages,
    retryUpload,
    clearPendingImages,
    getPendingImages,
    getUploadedImages
  } = usePropertyImages({
    propertyId,
    maxFiles: 20,
    maxFileSize: 10 * 1024 * 1024, // 10MB
    allowedTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif']
  });

  // Handle file drop with new unified system
  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const newImageIds = await addPendingImages(acceptedFiles);
    
    // If we have a propertyId, upload immediately
    if (propertyId && newImageIds.length > 0) {
      try {
        await uploadImages(newImageIds);
      } catch (error) {
        console.error('Failed to upload images:', error);
        // TODO: Add user notification for upload failure
        // For now, images will remain in pending state which user can retry
      }
    }
  }, [addPendingImages, uploadImages, propertyId]);

  // Dropzone configuration
  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.webp']
    },
    maxSize: 10 * 1024 * 1024, // 10MB
    multiple: true,
    disabled: isUploading
  });

  // Helper functions for component logic
  const pendingImages = getPendingImages();
  const uploadedImages = getUploadedImages();

  // Fetch secure URLs for uploaded images (for private Azure containers)
  const uploadedImageUrls = uploadedImages.map(img => img.imageUrl).filter((url): url is string => !!url);
  const secureImageUrls = useSecureImageUrls(uploadedImageUrls);

  // Post-creation upload handler
  const handlePostCreationUpload = useCallback(async (newPropertyId: number) => {
    if (pendingImages.length === 0) return;
    
    try {
      const results = await uploadImages();
      if (results.length > 0) {
        console.log(`Successfully uploaded ${results.length} images to property ${newPropertyId}`);
      }
    } catch (error) {
      console.error('Post-creation upload failed:', error);
      // Don't re-throw - property was created successfully, only upload failed
      // Images remain in pending state and user can retry upload manually
    }
  }, [pendingImages.length, uploadImages]);

  // Expose post-creation upload to parent component  
  useEffect(() => {
    if (onPropertyCreated && pendingImages.length > 0) {
      onPropertyCreated(handlePostCreationUpload);
    }
  }, [onPropertyCreated, handlePostCreationUpload, pendingImages.length]);

  // Save images to form whenever they change
  useEffect(() => {
    // For new properties, save pending files and upload callback
    if (!propertyId) {
      setValue('images_to_upload', pendingImages.map(img => img.file!).filter(Boolean));
      setValue('post_creation_image_upload', handlePostCreationUpload);
    }
    
    // Always save uploaded images info
    setValue('uploaded_images', uploadedImages.map(img => ({
      id: img.id as number,
      propertyId: img.propertyId!,
      imageUrl: img.imageUrl!,
      isPrimary: img.isPrimary,
      displayOrder: img.displayOrder,
      status: 'completed' as const
    })));
  }, [pendingImages, uploadedImages, setValue, propertyId, handlePostCreationUpload]);

  // Calculate total size and stats
  const totalSize = pendingImages.reduce((acc, img) => acc + (img.file?.size || 0), 0);
  const totalSizeMB = (totalSize / (1024 * 1024)).toFixed(2);
  const hasImages = images.length > 0;

  return (
    <div className="space-y-3 max-h-[calc(100vh-12rem)] overflow-hidden">

      {/* Upload Status */}
      {isUploading && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4 flex items-center space-x-2 text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg"
        >
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          <span className="text-sm font-medium">Uploading images...</span>
        </motion.div>
      )}

      {/* Dropzone */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3, delay: 0.1 }}
      >
        <div
          {...getRootProps()}
          className={`relative border-2 border-dashed rounded-xl p-6 text-center transition-all duration-300 ${
            isUploading 
              ? 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50 cursor-not-allowed opacity-50'
              : isDragActive 
              ? 'border-blue-500 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20 cursor-pointer' 
              : isDragReject
              ? 'border-red-500 dark:border-red-400 bg-red-50 dark:bg-red-900/20 cursor-pointer'
              : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500 bg-gray-50/50 dark:bg-gray-800/30 cursor-pointer'
          }`}
        >
          <input {...getInputProps()} disabled={isUploading} />
          
          {/* Backdrop blur effect */}
          <div className="absolute inset-0 bg-white/30 dark:bg-gray-800/30 backdrop-blur-sm rounded-xl" />
          
          {/* Content */}
          <div className="relative z-10">
            <motion.div
              animate={{ 
                scale: isDragActive ? 1.1 : 1,
                rotate: isDragActive ? 5 : 0
              }}
              transition={{ duration: 0.2 }}
              className="inline-flex p-3 bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-blue-900/40 dark:to-indigo-900/40 rounded-xl mb-3"
            >
              {isUploading ? (
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
              ) : isDragReject ? (
                <AlertCircle className="h-10 w-10 text-red-500" />
              ) : (
                <Upload className="h-10 w-10 text-blue-600" />
              )}
            </motion.div>
            
            <p className="text-base font-medium text-gray-900 dark:text-gray-100 mb-2">
              {isUploading
                ? 'Uploading images...'
                : isDragActive 
                ? 'Drop your images here...'
                : isDragReject
                ? 'Some files are not valid images'
                : 'Drag & drop images of your property here'}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
              {isUploading ? 'Please wait while we upload your images' : 'or click to browse from your computer'}
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500">
              Supports: JPG, PNG, GIF, WebP (max 10MB per file, 20 images max)
            </p>
          </div>
        </div>
      </motion.div>

      {/* Image Gallery */}
      {hasImages && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="space-y-3"
        >
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Images ({images.length})
              </h4>
              <div className="flex items-center space-x-3 text-xs text-gray-500 dark:text-gray-400 mt-1">
                {uploadedImages.length > 0 && (
                  <span className="flex items-center">
                    <CheckCircle className="h-3 w-3 text-green-500 mr-1" />
                    {uploadedImages.length} uploaded
                  </span>
                )}
                {pendingImages.length > 0 && (
                  <span>• {pendingImages.length} pending</span>
                )}
                {totalSize > 0 && (
                  <span>• Total: {totalSizeMB} MB</span>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-2 text-sm">
              {pendingImages.length > 0 && propertyId && (
                <button
                  type="button"
                  onClick={() => uploadImages(pendingImages.map(img => String(img.id)))}
                  disabled={isUploading}
                  className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 flex items-center text-xs disabled:opacity-50"
                >
                  <Upload className="h-4 w-4 mr-1" />
                  Upload All
                </button>
              )}
              <button
                type="button"
                onClick={clearPendingImages}
                className="text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 flex items-center text-xs"
              >
                <Trash2 className="h-4 w-4 mr-1" />
                Clear Pending
              </button>
            </div>
          </div>

          {/* Uploaded Images Grid */}
          {uploadedImages.length > 0 && (
            <div>
              <h5 className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-2 flex items-center">
                <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                Uploaded Images
              </h5>
              <Reorder.Group
                axis="x"
                values={uploadedImages}
                onReorder={operationLoading['reorder-uploaded'] ? () => {} : reorderImages}
                className={`grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-3 ${
                  operationLoading['reorder-uploaded'] ? 'pointer-events-none opacity-75' : ''
                }`}
              >
                {uploadedImages.map((image) => (
                  <Reorder.Item
                    key={image.id}
                    value={image}
                    id={String(image.id)}
                    className="relative group"
                    whileDrag={{ scale: 1.05, zIndex: 100 }}
                  >
                    <motion.div
                      layoutId={String(image.id)}
                      className="relative aspect-square rounded-lg overflow-hidden bg-gray-100 shadow-md hover:shadow-lg transition-shadow duration-300 border-2 border-green-200"
                    >
                      {/* Status Badge */}
                      <div className="absolute top-2 right-2 z-10">
                        <div className="bg-green-500 text-white rounded-full p-1">
                          <CheckCircle className="h-3 w-3" /> 
                        </div>
                      </div>

                      {/* Image */}
                      <img
                        src={secureImageUrls[image.imageUrl!] || image.imageUrl!}
                        alt="Property"
                        className="w-full h-full object-cover"
                        onClick={() => setSelectedImage(secureImageUrls[image.imageUrl!] || image.imageUrl!)}
                      />

                      {/* Primary Badge */}
                      {image.isPrimary && (
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          className="absolute top-2 left-2 bg-yellow-500 text-white px-2 py-1 rounded-lg text-xs font-semibold flex items-center shadow-lg"
                        >
                          <Star className="h-3 w-3 mr-1 fill-current" />
                          Primary
                        </motion.div>
                      )}

                      {/* Hover Actions */}
                      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                        <div className="absolute bottom-2 left-2 right-2 flex justify-between">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setPrimaryImage(image.id);
                            }}
                            className={`px-2 py-1 rounded-lg text-xs font-medium transition-colors flex items-center ${
                              image.isPrimary
                                ? 'bg-yellow-500 text-white cursor-default'
                                : operationLoading[`primary-${image.id}`]
                                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                : 'bg-white/90 text-gray-700 hover:bg-white'
                            }`}
                            disabled={image.isPrimary || operationLoading[`primary-${image.id}`]}
                          >
                            {operationLoading[`primary-${image.id}`] ? (
                              <>
                                <div className="animate-spin rounded-full h-3 w-3 border-b border-current mr-1"></div>
                                Setting...
                              </>
                            ) : image.isPrimary ? (
                              'Primary'
                            ) : (
                              'Set as Primary'
                            )}
                          </button>
                          
                          <div className="flex space-x-1">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedImage(secureImageUrls[image.imageUrl!] || image.imageUrl!);
                              }}
                              className="p-1 bg-white/90 rounded-lg hover:bg-white transition-colors"
                              disabled={operationLoading[`delete-${image.id}`]}
                            >
                              <Eye className="h-4 w-4 text-gray-700" />
                            </button>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                deleteImage(image.id);
                              }}
                              className={`p-1 rounded-lg transition-colors flex items-center ${
                                operationLoading[`delete-${image.id}`]
                                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                  : 'bg-red-500 text-white hover:bg-red-600'
                              }`}
                              disabled={operationLoading[`delete-${image.id}`]}
                            >
                              {operationLoading[`delete-${image.id}`] ? (
                                <div className="animate-spin rounded-full h-4 w-4 border-b border-current"></div>
                              ) : (
                                <X className="h-4 w-4" />
                              )}
                            </button>
                          </div>
                        </div>
                      </div>

                      {/* Drag Handle */}
                      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                        <div className={`p-1 bg-white/90 rounded-lg ${
                          operationLoading['reorder-uploaded'] ? 'cursor-not-allowed' : 'cursor-move'
                        }`}>
                          {operationLoading['reorder-uploaded'] ? (
                            <div className="animate-spin rounded-full h-4 w-4 border-b border-gray-700"></div>
                          ) : (
                            <Move className="h-4 w-4 text-gray-700" />
                          )}
                        </div>
                      </div>
                    </motion.div>
                  </Reorder.Item>
                ))}
              </Reorder.Group>
            </div>
          )}

          {/* Pending Images Grid */}
          {pendingImages.length > 0 && (
            <div>
              <h5 className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-2 flex items-center">
                <Upload className="h-4 w-4 text-blue-500 mr-2" />
                Pending Images
                {!propertyId && (
                  <span className="text-xs text-gray-500 ml-2">
                    (will upload when property is created)
                  </span>
                )}
              </h5>
              <Reorder.Group
                axis="x"
                values={pendingImages}
                onReorder={reorderImages}
                className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3"
              >
                {pendingImages.map((image) => {
                  const isUploading = image.status === 'uploading';
                  const hasError = image.status === 'error';
                  const isCompleted = image.status === 'completed';
                  
                  return (
                    <Reorder.Item
                      key={image.id}
                      value={image}
                      id={String(image.id)}
                      className="relative group"
                      whileDrag={{ scale: 1.05, zIndex: 100 }}
                    >
                      <motion.div
                        layoutId={String(image.id)}
                        className={`relative aspect-square rounded-lg overflow-hidden bg-gray-100 shadow-md hover:shadow-lg transition-shadow duration-300 border-2 ${
                          hasError 
                            ? 'border-red-300' 
                            : isCompleted 
                            ? 'border-green-300' 
                            : isUploading 
                            ? 'border-blue-300' 
                            : 'border-gray-200'
                        }`}
                      >
                        {/* Upload Progress */}
                        {isUploading && (
                          <div className="absolute inset-0 bg-black/50 flex items-center justify-center z-20">
                            <div className="text-center">
                              <div className="w-16 h-16 relative mb-2">
                                <div className="animate-spin rounded-full h-16 w-16 border-4 border-white/30 border-t-white"></div>
                                <span className="absolute inset-0 flex items-center justify-center text-white font-semibold text-sm">
                                  {image.progress}%
                                </span>
                              </div>
                              <p className="text-white text-xs">Uploading...</p>
                            </div>
                          </div>
                        )}

                        {/* Error Overlay */}
                        {hasError && (
                          <div className="absolute inset-0 bg-red-500/20 flex items-center justify-center z-20">
                            <div className="text-center">
                              <XCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
                              <p className="text-red-700 text-xs font-medium">Upload Failed</p>
                              <button
                                onClick={() => retryUpload(String(image.id))}
                                className="mt-1 bg-red-500 text-white px-2 py-1 rounded text-xs hover:bg-red-600 transition-colors flex items-center mx-auto"
                              >
                                <RotateCcw className="h-3 w-3 mr-1" />
                                Retry
                              </button>
                            </div>
                          </div>
                        )}

                        {/* Status Badge */}
                        <div className="absolute top-2 right-2 z-10">
                          {hasError ? (
                            <div className="bg-red-500 text-white rounded-full p-1">
                              <XCircle className="h-3 w-3" />
                            </div>
                          ) : isUploading ? (
                            <div className="bg-blue-500 text-white rounded-full p-1 animate-pulse">
                              <Upload className="h-3 w-3" />
                            </div>
                          ) : (
                            <div className="bg-gray-400 text-white rounded-full p-1">
                              <Upload className="h-3 w-3" />
                            </div>
                          )}
                        </div>

                        {/* Image */}
                        <img
                          src={image.preview!}
                          alt="Property"
                          className={`w-full h-full object-cover transition-opacity duration-300 ${
                            isUploading || hasError ? 'opacity-60' : 'opacity-100'
                          }`}
                          onClick={() => !isUploading && setSelectedImage(image.preview!)}
                        />

                        {/* Primary Badge */}
                        {image.isPrimary && (
                          <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            className="absolute top-2 left-2 bg-yellow-500 text-white px-2 py-1 rounded-lg text-xs font-semibold flex items-center shadow-lg"
                          >
                            <Star className="h-3 w-3 mr-1 fill-current" />
                            Primary
                          </motion.div>
                        )}

                        {/* Hover Actions */}
                        {!isUploading && (
                          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                            <div className="absolute bottom-2 left-2 right-2 flex justify-between">
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setPrimaryImage(image.id);
                                }}
                                className={`px-2 py-1 rounded-lg text-xs font-medium transition-colors ${
                                  image.isPrimary
                                    ? 'bg-yellow-500 text-white cursor-default'
                                    : 'bg-white/90 text-gray-700 hover:bg-white'
                                }`}
                                disabled={image.isPrimary || hasError}
                              >
                                {image.isPrimary ? 'Primary' : 'Set as Primary'}
                              </button>
                              
                              <div className="flex space-x-1">
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedImage(image.preview!);
                                  }}
                                  className="p-1 bg-white/90 rounded-lg hover:bg-white transition-colors"
                                >
                                  <Eye className="h-4 w-4 text-gray-700" />
                                </button>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    deleteImage(image.id);
                                  }}
                                  className="p-1 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                                >
                                  <X className="h-4 w-4" />
                                </button>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Drag Handle */}
                        {!isUploading && (
                          <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                            <div className="p-1 bg-white/90 rounded-lg cursor-move">
                              <Move className="h-4 w-4 text-gray-700" />
                            </div>
                          </div>
                        )}
                      </motion.div>

                      {/* Error Message Only */}
                      {hasError && image.errorMessage && (
                        <div className="mt-1">
                          <p className="text-xs text-red-500 truncate" title={image.errorMessage}>
                            {image.errorMessage}
                          </p>
                        </div>
                      )}
                    </Reorder.Item>
                  );
                })}
              </Reorder.Group>
            </div>
          )}
        </motion.div>
      )}


      {/* No images message */}
      {!hasImages && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="text-center py-4"
        >
          <ImageIcon className="h-12 w-12 text-gray-300 mx-auto mb-2" />
          <p className="text-gray-500 dark:text-gray-400 text-sm">No images uploaded yet</p>
        </motion.div>
      )}

      {/* Image Preview Modal */}
      <AnimatePresence>
        {selectedImage && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/80 flex items-center justify-center z-50"
            onClick={() => setSelectedImage(null)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="relative max-w-4xl max-h-[90vh] bg-white rounded-2xl overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <img
                src={selectedImage}
                alt="Preview"
                className="max-w-full max-h-[80vh] object-contain"
              />
              <button
                onClick={() => setSelectedImage(null)}
                className="absolute top-4 right-4 p-2 bg-white/90 rounded-full hover:bg-white transition-colors"
              >
                <X className="h-6 w-6 text-gray-700" />
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
};

export default MediaStep;
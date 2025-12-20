import React, { useState, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import * as Sentry from "@sentry/react";
import {
  MaintenanceRequestCreate,
  MaintenancePriority,
} from "../../utils/api/maintenance/types";
import { uploadMaintenancePhoto } from "../../utils/api/maintenance";
import MaintenancePhotoUpload from "./MaintenancePhotoUpload";
import { X, Clock, Wrench } from "lucide-react";

interface MaintenanceRequestFormProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: MaintenanceRequestCreate) => Promise<void>;
  isLoading?: boolean;
}

const MaintenanceRequestForm = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading = false,
}: MaintenanceRequestFormProps) => {
  const [formData, setFormData] = useState<Partial<MaintenanceRequestCreate>>({
    issue_title: "",
    description: "",
    priority: MaintenancePriority.MEDIUM,
    // property_id auto-inferred by backend for tenant users
    preferred_time: "",
  });
  const [uploadedPhotos, setUploadedPhotos] = useState<string[]>([]);
  const [previewPhotos, setPreviewPhotos] = useState<string[]>([]); // For blob URLs
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Cleanup blob URLs on unmount
  useEffect(() => {
    return () => {
      previewPhotos.forEach(url => URL.revokeObjectURL(url));
    };
  }, [previewPhotos]);

  const handleInputChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    // Clear error when user starts typing
    if (errors[name]) {
      setErrors((prev) => ({
        ...prev,
        [name]: "",
      }));
    }
  };

  const handleFileChange = async (files: File[]) => {
    if (files.length === 0) return;

    setIsUploading(true);
    setUploadError(null);

    // Create preview URLs immediately for display
    const newPreviewUrls = files.map(file => URL.createObjectURL(file));

    try {
      setPreviewPhotos((prev) => [...prev, ...newPreviewUrls]);

      // Upload files to Azure in the background
      const uploadPromises = files.map((file) => uploadMaintenancePhoto(file));
      const urls = await Promise.all(uploadPromises);

      // Keep blob URLs for preview, but track Azure URLs for submission
      setUploadedPhotos((prev) => [...prev, ...urls]);
    } catch (error) {
      Sentry.captureException(error, {
        tags: {
          component: 'MaintenanceRequestForm',
          action: 'upload_photos',
        },
      });
      setUploadError("Failed to upload photos. Please try again.");
      
      // Remove failed preview URLs (reuse the ones we created, don't create new ones)
      setPreviewPhotos((prev) => prev.filter(url => !newPreviewUrls.includes(url)));
      newPreviewUrls.forEach(url => URL.revokeObjectURL(url));
    } finally {
      setIsUploading(false);
    }
  };

  const removePhoto = (url: string) => {
    // We only display blob URLs, so find the index and remove both preview and Azure URL
    const index = previewPhotos.indexOf(url);
    if (index >= 0) {
      // Remove from preview URLs
      setPreviewPhotos((prev) => prev.filter((u) => u !== url));
      URL.revokeObjectURL(url); // Clean up blob URL
      
      // Also remove the corresponding Azure URL at the same index
      if (index < uploadedPhotos.length) {
        setUploadedPhotos((prev) => prev.filter((_, i) => i !== index));
      }
    }
  };

  const reorderPhotos = (newOrder: string[]) => {
    // We only display blob URLs for preview, so just update their order
    // The Azure URLs remain in the same order they were uploaded
    setPreviewPhotos(newOrder);
    
    // Reorder Azure URLs to match the new preview order
    const newUploadedOrder = newOrder.map(previewUrl => {
      const index = previewPhotos.indexOf(previewUrl);
      return uploadedPhotos[index];
    }).filter(Boolean);
    setUploadedPhotos(newUploadedOrder);
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.issue_title?.trim()) {
      newErrors.issue_title = "Title is required";
    }

    if (!formData.description?.trim()) {
      newErrors.description = "Description is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    try {
      const submitData: MaintenanceRequestCreate = {
        issue_title: formData.issue_title!,
        description: formData.description!,
        priority: formData.priority!,
        // property_id and tenant_id auto-inferred by backend for tenant users
        photos: uploadedPhotos.length > 0 ? uploadedPhotos : undefined,
        preferred_time: formData.preferred_time || undefined,
      };

      await onSubmit(submitData);

      // Reset form
      setFormData({
        issue_title: "",
        description: "",
        priority: MaintenancePriority.MEDIUM,
        // property_id auto-inferred by backend
        preferred_time: "",
      });
      setUploadedPhotos([]);
      // Clean up any remaining blob URLs
      previewPhotos.forEach(url => URL.revokeObjectURL(url));
      setPreviewPhotos([]);
      setUploadError(null);
      setErrors({});
    } catch (error) {
      Sentry.captureException(error, {
        tags: {
          component: 'MaintenanceRequestForm',
          action: 'submit_request',
        },
      });
      // Error is already handled by the mutation hook
    }
  };

  const handleClose = () => {
    // Clean up blob URLs
    previewPhotos.forEach(url => URL.revokeObjectURL(url));
    
    setFormData({
      issue_title: "",
      description: "",
      priority: MaintenancePriority.MEDIUM,
      // property_id auto-inferred by backend
      preferred_time: "",
    });
    setUploadedPhotos([]);
    setPreviewPhotos([]);
    setUploadError(null);
    setErrors({});
    onClose();
  };

  // Use only preview (blob) URLs for display since Azure URLs may not be directly accessible
  // The uploadedPhotos array contains Azure URLs for submission only
  const allPhotos = previewPhotos;

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-9999 flex items-center justify-center p-4"
        onClick={handleClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="relative w-full max-w-2xl bg-white rounded-xl shadow-2xl max-h-[calc(100vh-4rem)] overflow-hidden flex flex-col z-10000"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Clean Header */}
          <div className="relative bg-white border-b border-gray-200 px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-teal-50 rounded-lg">
                  <Wrench className="h-5 w-5 text-teal-600" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Submit a request for maintenance</h2>
                  <p className="text-sm text-gray-500 mt-0.5">
                    Report an issue to your landlord
                  </p>
                </div>
              </div>
              <button
                onClick={handleClose}
                className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
                disabled={isLoading || isUploading}
                aria-label="Close"
              >
                <X className="h-5 w-5 text-gray-500" />
              </button>
            </div>
          </div>

          {/* Content area */}
          <div className="flex-1 overflow-y-auto bg-gray-50/50 p-6">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Photos */}
              <div className="bg-white rounded-lg p-4 border border-gray-200">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Photos (Optional)
                </label>
                <p className="text-xs text-gray-500 mb-3">
                  Upload photos to help your landlord understand the issue
                </p>
                <MaintenancePhotoUpload
                  photos={allPhotos}
                  onFileChange={handleFileChange}
                  onRemovePhoto={removePhoto}
                  onReorderPhotos={reorderPhotos}
                  disabled={isLoading}
                  uploadError={uploadError}
                  isUploading={isUploading}
                />
              </div>

              {/* Issue Title */}
              <div className="bg-white rounded-lg p-4 border border-gray-200">
                <label htmlFor="issue_title" className="block text-sm font-medium text-gray-700 mb-2">
                  Issue Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  id="issue_title"
                  name="issue_title"
                  value={formData.issue_title || ""}
                  onChange={handleInputChange}
                  placeholder="e.g., Leaky faucet in the kitchen"
                  className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition-all text-sm ${
                    errors.issue_title ? "border-red-300 bg-red-50" : "border-gray-200"
                  }`}
                />
                {errors.issue_title && (
                  <p className="mt-2 text-sm text-red-600">{errors.issue_title}</p>
                )}
              </div>

              {/* Description */}
              <div className="bg-white rounded-lg p-4 border border-gray-200">
                <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
                  Description <span className="text-red-500">*</span>
                </label>
                <textarea
                  id="description"
                  name="description"
                  value={formData.description || ""}
                  onChange={handleInputChange}
                  rows={4}
                  placeholder="Please provide as much detail as possible about the issue."
                  className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition-all resize-none text-sm ${
                    errors.description ? "border-red-300 bg-red-50" : "border-gray-200"
                  }`}
                />
                {errors.description && (
                  <p className="mt-2 text-sm text-red-600">{errors.description}</p>
                )}
              </div>

              {/* Availability Preference */}
              <div className="bg-white rounded-lg p-4 border border-gray-200">
                <label htmlFor="preferred_time" className="flex items-center text-sm font-medium text-gray-700 mb-2">
                  <Clock className="w-4 h-4 mr-2 text-teal-600" />
                  When are you usually available? (Optional)
                </label>
                <p className="text-xs text-gray-500 mb-3">
                  Help your landlord schedule maintenance at a convenient time for you
                </p>
                <textarea
                  id="preferred_time"
                  name="preferred_time"
                  value={formData.preferred_time || ""}
                  onChange={handleInputChange}
                  rows={2}
                  placeholder="e.g., Weekdays after 6pm, Weekends only, Anytime works"
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition-all resize-none text-sm"
                />
              </div>
            </form>
          </div>

          {/* Clean Footer */}
          <div className="border-t border-gray-200 px-6 py-3 flex justify-between items-center bg-white shrink-0">
            <div className="text-sm text-gray-500 flex items-center">
              <svg className="w-4 h-4 mr-2 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-red-600 font-bold">*</span>
              <span className="ml-1">Required fields</span>
            </div>
            
            <div className="flex items-center space-x-3">
              <button
                type="button"
                onClick={handleClose}
                disabled={isLoading || isUploading}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50 transition-colors cursor-pointer disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              
              <button
                type="submit"
                onClick={handleSubmit}
                disabled={isLoading || isUploading}
                className={`px-5 py-2 text-sm font-medium text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-900 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 ${
                  isLoading || isUploading
                    ? 'bg-gray-400' 
                    : 'bg-gray-900 hover:bg-gray-800 cursor-pointer'
                }`}
              >
                {isLoading || isUploading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>{isUploading ? 'Uploading...' : 'Submitting...'}</span>
                  </>
                ) : (
                  'Submit Request'
                )}
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default MaintenanceRequestForm;

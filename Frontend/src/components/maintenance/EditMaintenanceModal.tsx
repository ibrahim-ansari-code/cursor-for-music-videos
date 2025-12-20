import React, { useState, useEffect, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X, Wrench } from "lucide-react";
import {
  fetchProperties,
  fetchPropertyUnits,
  fetchTenantsByProperty,
} from "../../utils/api";
import { useMaintenanceForm } from "../../hooks/maintenance/useMaintenanceForm";
import { useMaintenancePhotos } from "../../hooks/maintenance/useMaintenancePhotos";
import { useVendors } from "../../hooks/useVendorQueries";
import MaintenanceFormFields from "./MaintenanceFormFields";
import type {
  MaintenanceRequest,
  Property,
  PropertyUnit,
  Tenant,
} from "../../types/tenant";

interface EditMaintenanceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: any) => Promise<void>;
  request: MaintenanceRequest;
  isViewing?: boolean;
  isSubmitting?: boolean;
}

/**
 * EditMaintenanceModal - For editing and viewing existing maintenance requests
 *
 * Split from MaintenanceRequestModal to allow independent evolution
 * of create vs edit/view functionality
 */
const EditMaintenanceModal: React.FC<EditMaintenanceModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  request,
  isViewing,
  isSubmitting: externalSubmitting,
}) => {
  // Data state
  const [properties, setProperties] = useState<Property[]>([]);
  const [units, setUnits] = useState<PropertyUnit[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [isLoadingProperties, setIsLoadingProperties] = useState(false);
  const [isLoadingUnits, setIsLoadingUnits] = useState(false);
  const [isLoadingTenants, setIsLoadingTenants] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch active vendors for dropdown (only when modal is open)
  const { data: vendorsData, isLoading: isLoadingVendors } = useVendors(
    isOpen
      ? {
          is_active: true,
          limit: 100,
        }
      : undefined
  );

  // Form management hook
  const {
    formData,
    errors,
    isSubmitting: formSubmitting,
    updateField,
    resetForm,
    validateForm,
  } = useMaintenanceForm({
    mode: "edit",
    initialData: request,
    onSuccess: async (payload) => {
      await onSubmit(payload);
      onClose();
      resetForm();
    },
  });

  // Photo upload hook - destructure to extract stable function references
  const photoState = useMaintenancePhotos();
  const { resetState: resetPhotoState, uploadAllPendingFiles } = photoState;

  // Load properties on mount - memoized to prevent infinite loops
  const loadProperties = useCallback(async () => {
    setIsLoadingProperties(true);
    try {
      const props = await fetchProperties();
      setProperties(props);
    } catch (error) {
      console.error("Failed to load properties", error);
      setError("Failed to load properties. Please try again.");
    } finally {
      setIsLoadingProperties(false);
    }
  }, []); // No dependencies - fetchProperties is stable

  // Initialize form data when modal opens
  useEffect(() => {
    if (isOpen) {
      loadProperties();
      setError(null);
    } else {
      resetForm();
      resetPhotoState();
      setUnits([]);
      setTenants([]);
    }
    // Only run when modal opens/closes or request changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, request]);

  // Load units and tenants when property changes
  useEffect(() => {
    const loadUnitsAndTenants = async () => {
      if (!formData.property_id) {
        setUnits([]);
        setTenants([]);
        return;
      }

      setIsLoadingUnits(true);
      setIsLoadingTenants(true);

      try {
        const propertyIdNum = Number(formData.property_id);
        const [unitData, tenantData] = await Promise.all([
          fetchPropertyUnits(propertyIdNum),
          fetchTenantsByProperty(propertyIdNum),
        ]);

        setUnits(unitData as PropertyUnit[]);
        setTenants(tenantData as Tenant[]);

        // Reset unit and tenant if property changed (check both nested and direct property ID)
        const prevPropId = String(
          request?.property?.id || request?.property_id || ""
        );

        // Only reset if property actually changed
        if (prevPropId !== String(formData.property_id)) {
          updateField("unit_id", "");
          updateField("tenant_id", "");
        }
      } catch (error) {
        console.error("Failed to load units or tenants", error);
        setUnits([]);
        setTenants([]);
      } finally {
        setIsLoadingUnits(false);
        setIsLoadingTenants(false);
      }
    };

    if (isOpen && formData.property_id) {
      loadUnitsAndTenants();
    }
    // Only run when modal opens or property selection changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, formData.property_id, request]);

  // Handle file selection - just add preview URLs, don't upload yet
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;

    const previewUrls = photoState.handleFileChange(e.target.files);
    if (previewUrls.length > 0) {
      updateField("photos", [...(formData.photos || []), ...previewUrls]);
    }
  };

  // Handle photo removal
  const handleRemovePhoto = (identifier: string) => {
    photoState.removePhoto(identifier);
    updateField(
      "photos",
      (formData.photos || []).filter((url) => url !== identifier)
    );
  };

  // Handle photo reorder
  const handleReorderPhotos = (newOrder: string[]) => {
    updateField("photos", newOrder);
  };

  // Handle form submission - upload photos first, then submit form
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    try {
      // Validate form first
      if (!validateForm()) {
        setError("Please correct the highlighted fields.");
        return;
      }

      // Upload any pending photos first (photos with blob: preview URLs)
      const uploadedUrls = await uploadAllPendingFiles();

      // Build final photo array: existing Azure URLs + newly uploaded URLs
      let finalPhotos = formData.photos || [];

      if (uploadedUrls.length > 0) {
        // Get existing photos that are already uploaded to Azure (not preview URLs)
        const existingUploadedPhotos = (formData.photos || []).filter(
          (url) => !url.startsWith("blob:")
        );

        // Combine existing Azure URLs with newly uploaded ones
        finalPhotos = [...existingUploadedPhotos, ...uploadedUrls];

        console.log(
          "[MaintenanceEdit] Replaced preview URLs with Azure URLs:",
          {
            original: formData.photos,
            final: finalPhotos,
            uploadedCount: uploadedUrls.length,
          }
        );
      }

      // Build the final payload with proper type conversions
      const payload = {
        issue_title: formData.issue_title.trim(),
        description:
          formData.description && formData.description.trim() !== ""
            ? formData.description.trim()
            : null,
        priority: formData.priority,
        status: formData.status,
        property_id: formData.property_id ? Number(formData.property_id) : null,
        unit_id:
          formData.unit_id &&
          formData.unit_id !== "" &&
          formData.unit_id !== "common_area"
            ? Number(formData.unit_id)
            : null,
        tenant_id:
          formData.tenant_id && formData.tenant_id !== ""
            ? Number(formData.tenant_id)
            : null,
        vendor_id:
          formData.vendor_id && formData.vendor_id !== ""
            ? Number(formData.vendor_id)
            : null,
        notify_tenant: formData.notify_tenant || false,
        start_date:
          formData.start_date && formData.start_date.trim() !== ""
            ? formData.start_date
            : null,
        end_date:
          formData.end_date && formData.end_date.trim() !== ""
            ? formData.end_date
            : null,
        // CRITICAL: Use finalPhotos (Azure URLs) not formData.photos (preview URLs)
        photos: finalPhotos.length > 0 ? finalPhotos : null,
      };

      // Call parent's onSubmit with the corrected payload
      await onSubmit(payload);
    } catch (err: any) {
      setError(err?.message || "Failed to update the request.");
      throw err; // Re-throw so parent can handle if needed
    }
  };

  const isSubmitting = formSubmitting || externalSubmitting || false;

  // Determine modal title based on mode
  const modalTitle = isViewing
    ? "View Maintenance Request"
    : "Edit Maintenance Request";

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm z-[9999] flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          transition={{ type: "spring", damping: 25, stiffness: 400 }}
          className="relative w-full max-w-4xl bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-h-[90vh] overflow-hidden flex flex-col z-[10000] transition-colors duration-300"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="relative bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <Wrench className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    {modalTitle}
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                    {isViewing
                      ? "View maintenance request details"
                      : "Update maintenance request information"}
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                disabled={isSubmitting}
                aria-label="Close"
              >
                <X className="h-5 w-5 text-gray-500 dark:text-gray-400" />
              </button>
            </div>
          </div>

          {/* Content area */}
          <div className="flex-1 overflow-y-auto bg-gray-50/50 dark:bg-gray-800/50 transition-colors duration-300">
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mx-6 mt-6 mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 text-red-700 dark:text-red-300 rounded-xl shadow-sm transition-colors duration-300"
              >
                <div className="flex">
                  <svg
                    className="h-5 w-5 text-red-500 mr-3 flex-shrink-0 mt-0.5"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span className="text-sm">{error}</span>
                </div>
              </motion.div>
            )}

            {isLoadingProperties ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div className="w-8 h-8 border-4 border-blue-200 dark:border-blue-800 border-t-blue-600 dark:border-t-blue-400 rounded-full animate-spin mb-4" />
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Loading properties...
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} id="edit-maintenance-request-form">
                <MaintenanceFormFields
                  formData={formData}
                  errors={errors}
                  properties={properties}
                  units={units}
                  tenants={tenants}
                  vendors={vendorsData?.vendors || []}
                  photoState={photoState}
                  onUpdateField={updateField}
                  onFileChange={handleFileChange}
                  onRemovePhoto={handleRemovePhoto}
                  onReorderPhotos={handleReorderPhotos}
                  isViewing={isViewing}
                  isLoadingUnits={isLoadingUnits}
                  isLoadingTenants={isLoadingTenants}
                  isLoadingVendors={isLoadingVendors}
                />
              </form>
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-gray-200 dark:border-gray-700 px-6 py-3 flex justify-between items-center bg-white dark:bg-gray-800 flex-shrink-0">
            {/* Info text on left */}
            {!isViewing && (
              <div className="text-sm text-gray-500 dark:text-gray-400 flex items-center">
                <svg
                  className="w-4 h-4 mr-2 text-gray-400 flex-shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span className="text-red-600 font-bold">*</span>
                <span className="ml-1">Required fields</span>
              </div>
            )}
            {isViewing && <div></div>}

            {/* Buttons on right */}
            <div className="flex items-center space-x-3">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 dark:focus:ring-offset-gray-800 disabled:opacity-50 transition-colors"
              >
                {isViewing ? "Close" : "Cancel"}
              </button>

              {!isViewing && (
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className={`px-5 py-2 text-sm font-medium text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 dark:focus:ring-offset-gray-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 ${
                    isSubmitting
                      ? "bg-gray-400 dark:bg-gray-600"
                      : "bg-green-600 dark:bg-green-700 hover:bg-green-700 dark:hover:bg-green-600"
                  }`}
                >
                  {isSubmitting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>Updating...</span>
                    </>
                  ) : (
                    "Update Request"
                  )}
                </button>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default EditMaintenanceModal;

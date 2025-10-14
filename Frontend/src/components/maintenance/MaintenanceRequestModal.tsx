import React, { useState, useEffect, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { fetchProperties, fetchPropertyUnits, fetchTenantsByProperty } from '../../utils/api';
import { useMaintenanceForm } from '../../hooks/maintenance/useMaintenanceForm';
import { useMaintenancePhotos } from '../../hooks/maintenance/useMaintenancePhotos';
import MaintenanceFormFields from './MaintenanceFormFields';
import type { MaintenanceRequest, Property, PropertyUnit, Tenant } from '../../types/tenant';

interface MaintenanceRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: any) => Promise<void>;
  request?: MaintenanceRequest | null;
  isViewing?: boolean;
  isSubmitting?: boolean;
}

/**
 * Refactored MaintenanceRequestModal with modular TypeScript architecture
 * - Business logic extracted to useMaintenanceForm and useMaintenancePhotos hooks
 * - UI presentation delegated to MaintenanceFormFields component
 * - Follows NewExpenseModal pattern for consistency
 * - Supports create, edit, and view modes
 */
const MaintenanceRequestModal: React.FC<MaintenanceRequestModalProps> = ({
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

  // Form management hook
  const {
    formData,
    errors,
    isSubmitting: formSubmitting,
    updateField,
    submitForm,
    resetForm,
  } = useMaintenanceForm({
    mode: request?.id ? 'edit' : 'create',
    initialData: request,
    onSuccess: async (payload) => {
      await onSubmit(payload);
      onClose();
      resetForm();
    },
  });

  // Photo upload hook - destructure to extract stable function references
  const photoState = useMaintenancePhotos();
  const { resetState: resetPhotoState } = photoState;

  // Load properties on mount - memoized to prevent infinite loops
  const loadProperties = useCallback(async () => {
    setIsLoadingProperties(true);
    try {
      const props = await fetchProperties();
      setProperties(props);
    } catch (error) {
      console.error('Failed to load properties', error);
      setError('Failed to load properties. Please try again.');
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
  }, [isOpen, request, loadProperties, resetForm, resetPhotoState]);

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
        const prevPropId = String(request?.property?.id || request?.property_id || '');
        const hasInitialTenant = request?.tenant_id;

        // Only reset if property actually changed AND there was no pre-populated tenant
        if (prevPropId !== String(formData.property_id) && !hasInitialTenant) {
          updateField('unit_id', '');
          updateField('tenant_id', '');
        }
      } catch (error) {
        console.error('Failed to load units or tenants', error);
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
  }, [isOpen, formData.property_id, request, updateField]);

  // Handle file upload
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;

    const urls = await photoState.handleFileChange(e.target.files);
    if (urls.length > 0) {
      updateField('photos', [...(formData.photos || []), ...urls]);
    }
  };

  // Handle photo removal
  const handleRemovePhoto = (identifier: string) => {
    photoState.removePhoto(identifier);
    updateField(
      'photos',
      (formData.photos || []).filter((url) => url !== identifier)
    );
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (photoState.uploadingPhotos) {
      setError('Please wait for all photos to finish uploading.');
      return;
    }

    try {
      await submitForm();
    } catch (err: any) {
      setError(err?.message || 'Failed to save the request.');
    }
  };

  const isSubmitting = formSubmitting || externalSubmitting || false;

  const modalTitle = isViewing
    ? 'View Maintenance Request'
    : request && request.id
    ? 'Edit Maintenance Request'
    : 'New Maintenance Request';

  const submitLabel = request && request.id ? 'Update Request' : 'Create Request';

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
          transition={{ type: 'spring', damping: 25, stiffness: 400 }}
          className="relative w-full max-w-4xl bg-white dark:bg-gray-800 rounded-xl shadow-xl max-h-[90vh] overflow-hidden flex flex-col z-[10000] transition-colors duration-300"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="relative px-6 py-4 bg-gradient-to-br from-brand-green to-brand-teal dark:from-gray-700 dark:to-gray-600 text-white transition-colors duration-300">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-xl font-semibold text-white">{modalTitle}</h2>
                <p className="text-white/80 mt-0.5 text-sm">
                  {isViewing
                    ? 'View maintenance request details'
                    : request
                    ? 'Update maintenance request information'
                    : 'Create a new maintenance request for your property'}
                </p>
              </div>
              <button
                onClick={onClose}
                className="text-white/70 hover:text-white hover:bg-white/10 p-1.5 rounded-lg transition-all"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mx-6 mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-700 text-red-700 dark:text-red-300 rounded-lg transition-colors duration-300"
              >
                <div className="flex">
                  <svg className="h-5 w-5 text-red-400 mr-2 flex-shrink-0 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
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
                <p className="text-sm text-gray-500 dark:text-gray-400">Loading properties...</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} id="maintenance-request-form">
                <MaintenanceFormFields
                  formData={formData}
                  errors={errors}
                  properties={properties}
                  units={units}
                  tenants={tenants}
                  photoState={photoState}
                  onUpdateField={updateField}
                  onFileChange={handleFileChange}
                  onRemovePhoto={handleRemovePhoto}
                  isViewing={isViewing}
                  isLoadingUnits={isLoadingUnits}
                  isLoadingTenants={isLoadingTenants}
                />
              </form>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-5 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-600 transition-colors duration-300">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="text-sm text-gray-500 dark:text-gray-400 flex items-start flex-1 sm:max-w-md transition-colors duration-300">
                <svg className="w-4 h-4 mr-2 text-gray-400 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>
                  {isViewing ? (
                    'Viewing maintenance request details'
                  ) : (
                    <>
                      <span className="text-red-600 font-bold">*</span> Required fields. Unit selection is optional for common area
                      maintenance.
                    </>
                  )}
                </span>
              </div>
              <div className="flex gap-3 flex-shrink-0 sm:items-center">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-all text-sm font-medium"
                  disabled={isSubmitting}
                >
                  {isViewing ? 'Close' : 'Cancel'}
                </button>
                {!isViewing && (
                  <button
                    onClick={handleSubmit}
                    className="px-5 py-2.5 bg-gradient-to-br from-brand-green to-brand-teal text-white rounded-md hover:from-brand-green/90 hover:to-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-brand-green focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium flex items-center gap-2 min-w-[140px] justify-center shadow-sm"
                    disabled={isSubmitting || photoState.uploadingPhotos}
                  >
                    {isSubmitting ? (
                      <>
                        <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        {request && request.id ? 'Updating...' : 'Creating...'}
                      </>
                    ) : (
                      submitLabel
                    )}
                  </button>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default MaintenanceRequestModal;

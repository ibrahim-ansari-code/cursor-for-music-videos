import React, { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import TenantModal from "../../tenants/TenantModal";
import { Button, ErrorMessage } from "../../ui/SharedModalComponents";
import type { Tenant } from "../../../types/tenant";
import type { ImportLeaseModalProps } from "./types";

// Hooks
import { usePropertyData } from "./hooks/usePropertyData";
import { useLeaseForm } from "./hooks/useLeaseForm";
import { useLeaseFileParser } from "./hooks/useLeaseFileParser";

// Components
import { ModeSelector } from "./components/ModeSelector";
import { FileUploadSection } from "./components/FileUploadSection";
import { LeaseFormFields } from "./components/LeaseFormFields";

const ImportLeaseModal: React.FC<ImportLeaseModalProps> = ({
  isOpen,
  onClose,
  onImport,
  initialMode = 'file',
  propertyId: initialPropertyId = null,
  unitId: initialUnitId = null,
  unitName: initialUnitName = "",
}) => {
  const [mode, setMode] = useState<'file' | 'manual'>(initialMode);
  const [showParsedResults, setShowParsedResults] = useState(false);
  const [showTenantModal, setShowTenantModal] = useState(false);

  // Custom hooks
  const {
    properties,
    availableUnits,
    availableTenants,
    isLoadingUnits,
    isLoadingTenants,
    loadProperties,
    loadUnitsForProperty,
    loadTenantsForProperty,
  } = usePropertyData();

  const {
    formData,
    fieldErrors,
    error,
    isLoading,
    selectedTenant,
    setFieldErrors,
    setError,
    setSelectedTenant,
    handleFormChange,
    handlePropertyChange,
    handleUnitChange,
    handleTenantChange,
    updateFormData,
    submitLease,
    resetForm,
  } = useLeaseForm({
    initialPropertyId,
    initialUnitId,
    initialUnitName,
    mode,
    onSuccess: (lease) => {
      onImport(lease);
      onClose();
    },
  });

  const {
    file,
    parsedFileUrl,
    isAnalyzing,
    analyzeError,
    setFile,
    analyzeLease,
  } = useLeaseFileParser();

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setMode(initialMode);
      setFile(null);
      setShowParsedResults(false);
      setError(null);
      setFieldErrors({});
      setSelectedTenant(null);
      resetForm();
      loadProperties();
      if (initialPropertyId) {
        loadTenantsForProperty(initialPropertyId);
        loadUnitsForProperty(initialPropertyId);
      }
    }
  }, [isOpen, initialMode, initialPropertyId]);

  // Handle property change
  const onPropertyChangeHandler = (propertyId: number) => {
    loadTenantsForProperty(propertyId);
    loadUnitsForProperty(propertyId);
  };

  // Handle file upload and analysis
  const handleAnalyzeLease = async () => {
    const result = await analyzeLease(
      formData.property_id,
      availableUnits,
      loadTenantsForProperty
    );

    if (result) {
      updateFormData(result.formUpdates);
      if (result.matchedTenant) {
        setSelectedTenant(result.matchedTenant);
      }
      setShowParsedResults(true);
    }
  };

  // Handle tenant creation
  const handleTenantSaved = (newTenant: Tenant) => {
    setShowTenantModal(false);
    setSelectedTenant(newTenant);
    updateFormData({ tenant_id: newTenant.id });
    
    // Reload tenants to include the new one
    if (formData.property_id) {
      loadTenantsForProperty(parseInt(formData.property_id));
    }
  };

  // Handle mode change
  const handleModeChange = (newMode: 'file' | 'manual') => {
    setMode(newMode);
    setShowParsedResults(false);
  };

  // Combined error display
  const displayError = error || analyzeError;

  return (
    <>
      <AnimatePresence>
        {isOpen && !showTenantModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm z-[9999] flex items-center justify-center p-4"
            onClick={onClose}
          >
            <motion.div 
              className="relative w-full max-w-3xl bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-h-[90vh] overflow-hidden flex flex-col z-[10000]"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Create New Lease</h2>
                <button
                  onClick={onClose}
                  type="button"
                  aria-label="Close"
                  className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 rounded-full p-1"
                >
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" role="img">
                    <title>Close modal</title>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Mode Selector - Only show if not locked to a specific mode */}
              {!initialPropertyId && (
                <ModeSelector mode={mode} onModeChange={handleModeChange} />
              )}
              
              {/* Form Area */}
              <div className="flex-1 overflow-y-auto p-6 bg-white dark:bg-gray-800">
                {displayError && <ErrorMessage message={displayError} />}

                {/* File Upload Mode */}
                {mode === 'file' && !showParsedResults && (
                  <FileUploadSection
                    properties={properties}
                    selectedPropertyId={formData.property_id}
                    file={file}
                    fieldErrors={fieldErrors}
                    onPropertyChange={(value) => handlePropertyChange(value, onPropertyChangeHandler)}
                    onFileChange={setFile}
                  />
                )}

                {/* Show parsed results or manual entry form */}
                {(mode === 'manual' || showParsedResults) && (
                  <LeaseFormFields
                    formData={formData}
                    fieldErrors={fieldErrors}
                    properties={properties}
                    availableUnits={availableUnits}
                    availableTenants={availableTenants}
                    selectedTenant={selectedTenant}
                    isLoadingUnits={isLoadingUnits}
                    isLoadingTenants={isLoadingTenants}
                    mode={mode}
                    initialPropertyId={initialPropertyId}
                    initialUnitId={initialUnitId}
                    initialUnitName={initialUnitName}
                    onFormChange={handleFormChange}
                    onPropertyChange={(value) => handlePropertyChange(value, onPropertyChangeHandler)}
                    onUnitChange={handleUnitChange}
                    onTenantChange={(value) => handleTenantChange(value, availableTenants)}
                    onCreateNewTenant={() => setShowTenantModal(true)}
                  />
                )}
              </div>

              {/* Footer */}
              <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700 border-t border-gray-200 dark:border-gray-600 flex justify-end space-x-3">
                <Button variant="secondary" onClick={onClose}>Cancel</Button>
                {mode === 'file' && !showParsedResults ? (
                  <Button 
                    variant="primary" 
                    onClick={handleAnalyzeLease} 
                    disabled={!file || !formData.property_id || isAnalyzing}
                    isLoading={isAnalyzing}
                  >
                    Parse Lease
                  </Button>
                ) : (
                  <Button 
                    variant="primary" 
                    onClick={() => submitLease(parsedFileUrl)} 
                    disabled={!formData.tenant_id || isLoading}
                    isLoading={isLoading}
                  >
                    Create Lease
                  </Button>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Tenant Modal */}
      <AnimatePresence>
        {showTenantModal && (
          <TenantModal
            isOpen={true} 
            onClose={() => setShowTenantModal(false)}
            onSave={handleTenantSaved}
            source="importLeaseModal"
            propertyId={formData.property_id ? parseInt(formData.property_id) as any : null}
          />
        )}
      </AnimatePresence>
    </>
  );
};

export default ImportLeaseModal;


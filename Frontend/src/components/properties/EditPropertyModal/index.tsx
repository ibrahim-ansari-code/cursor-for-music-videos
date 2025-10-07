import React, { useState, useEffect } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { motion, AnimatePresence } from 'framer-motion';
import { FormProvider } from 'react-hook-form';
import { X, Save, Building, MapPin, Wrench } from 'lucide-react';
import { Property } from '../../../types/property';
import { useEditPropertyForm } from './hooks/useEditPropertyForm';
import { BasicInfoSection } from './sections/BasicInfoSection';
import { LocationSection } from './sections/LocationSection';
import { TypeSpecificSection } from './sections/TypeSpecificSection';

interface EditPropertyModalProps {
  isOpen: boolean;
  onClose: () => void;
  propertyData: Property;
  onSuccess?: () => void;
}

type TabId = 'basic' | 'location' | 'details';

const TABS = [
  { id: 'basic' as TabId, label: 'Basic Info', Icon: Building },
  { id: 'location' as TabId, label: 'Location', Icon: MapPin },
  { id: 'details' as TabId, label: 'Property Details', Icon: Wrench },
];

const EditPropertyModal: React.FC<EditPropertyModalProps> = ({
  isOpen,
  onClose,
  propertyData,
  onSuccess,
}) => {
  const [activeTab, setActiveTab] = useState<TabId>('basic');
  const [showCloseConfirmation, setShowCloseConfirmation] = useState(false);

  const { methods, onSubmit, isSubmitting, isDirty, propertyType, errors } = useEditPropertyForm({
    propertyData,
    onSuccess: () => {
      onSuccess?.();
    },
    onClose,
  });

  // Debug: Log validation errors in development
  useEffect(() => {
    if (import.meta.env.DEV && Object.keys(errors).length > 0) {
      console.error('[EditPropertyModal] Validation errors preventing submission:', errors);
    }
  }, [errors]);

  const handleClose = () => {
    if (isDirty && !showCloseConfirmation) {
      setShowCloseConfirmation(true);
      return;
    }
    setShowCloseConfirmation(false);
    setActiveTab('basic');
    methods.reset();
    onClose();
  };

  const handleConfirmClose = () => {
    setShowCloseConfirmation(false);
    setActiveTab('basic');
    methods.reset();
    onClose();
  };

  const handleCancelClose = () => {
    setShowCloseConfirmation(false);
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'basic':
        return <BasicInfoSection />;
      case 'location':
        return <LocationSection />;
      case 'details':
        return <TypeSpecificSection propertyType={propertyType} />;
      default:
        return null;
    }
  };

  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0"
          />
        </Dialog.Overlay>

        <Dialog.Content className="fixed left-[50%] top-[50%] translate-x-[-50%] translate-y-[-50%] z-50">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.3, type: 'spring', stiffness: 300, damping: 30 }}
            className="w-[90vw] max-w-4xl bg-white dark:bg-gray-800 rounded-2xl shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-600 px-6 py-4">
              <div className="flex items-center justify-between">
                <div>
                  <Dialog.Title className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                    Edit Property
                  </Dialog.Title>
                  <Dialog.Description className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    Update property information
                  </Dialog.Description>
                </div>
                <Dialog.Close asChild>
                  <button
                    className="rounded-lg p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    aria-label="Close"
                  >
                    <X className="h-5 w-5 text-gray-500 dark:text-gray-400" />
                  </button>
                </Dialog.Close>
              </div>

              {/* Tabs */}
              <div className="mt-4 flex space-x-1 border-b border-gray-200 dark:border-gray-700">
                {TABS.map((tab) => {
                  const Icon = tab.Icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`flex items-center space-x-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                        activeTab === tab.id
                          ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                          : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Content */}
            <FormProvider {...methods}>
              <form onSubmit={onSubmit}>
                <div className="p-6 max-h-[60vh] overflow-y-auto">
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={activeTab}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      transition={{ duration: 0.2 }}
                    >
                      {renderTabContent()}
                    </motion.div>
                  </AnimatePresence>
                </div>

                {/* Footer */}
                <div className="border-t border-gray-200 dark:border-gray-600 px-6 py-4 bg-gray-50 dark:bg-gray-900 flex justify-between items-center">
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    {isDirty && (
                      <span className="text-amber-600 dark:text-amber-400">● Unsaved changes</span>
                    )}
                    {Object.keys(errors).length > 0 && (
                      <span className="text-red-600 dark:text-red-400 ml-3">
                        ● {Object.keys(errors).length} validation error{Object.keys(errors).length > 1 ? 's' : ''}
                      </span>
                    )}
                  </div>

                  <div className="flex space-x-3">
                    <button
                      type="button"
                      onClick={handleClose}
                      className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting || !isDirty}
                      className={`flex items-center space-x-2 px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                        isSubmitting || !isDirty
                          ? 'bg-gray-200 dark:bg-gray-600 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                          : 'bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600'
                      }`}
                    >
                      <Save className="h-4 w-4" />
                      <span>{isSubmitting ? 'Saving...' : 'Save Changes'}</span>
                    </button>
                  </div>
                </div>
              </form>
            </FormProvider>
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>

      {/* Unsaved Changes Confirmation Dialog */}
      {showCloseConfirmation && (
        <Dialog.Root open={showCloseConfirmation} onOpenChange={handleCancelClose}>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 bg-black/40 z-[60]" />
            <Dialog.Content className="fixed left-[50%] top-[50%] translate-x-[-50%] translate-y-[-50%] z-[70] bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md">
              <Dialog.Title className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Unsaved Changes
              </Dialog.Title>
              <Dialog.Description className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                You have unsaved changes. Are you sure you want to close without saving?
              </Dialog.Description>
              <div className="flex justify-end space-x-3">
                <button
                  onClick={handleCancelClose}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  Keep Editing
                </button>
                <button
                  onClick={handleConfirmClose}
                  className="px-4 py-2 text-sm font-medium bg-red-600 text-white hover:bg-red-700 rounded-lg transition-colors"
                >
                  Discard Changes
                </button>
              </div>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>
      )}
    </Dialog.Root>
  );
};

export default EditPropertyModal;

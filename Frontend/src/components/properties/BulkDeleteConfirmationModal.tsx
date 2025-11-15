import React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { motion } from "framer-motion";
import { X, AlertTriangle, Trash2 } from "lucide-react";
import { Property } from "../../types/property";

interface BulkDeleteConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  properties: Property[];
  isDeleting?: boolean;
}

export const BulkDeleteConfirmationModal: React.FC<
  BulkDeleteConfirmationModalProps
> = ({ isOpen, onClose, onConfirm, properties, isDeleting = false }) => {
  const propertyCount = properties.length;
  const [failedImages, setFailedImages] = React.useState<Set<number>>(new Set());

  // Reset failed images when modal opens with new properties
  React.useEffect(() => {
    setFailedImages(new Set());
  }, [properties]);

  const handleImageError = (propertyId: number) => {
    setFailedImages((prev) => new Set(prev).add(propertyId));
  };

  if (propertyCount === 0) return null;

  return (
    <Dialog.Root open={isOpen} onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60]">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0"
          />
        </Dialog.Overlay>

        <Dialog.Content className="fixed left-[50%] top-[50%] translate-x-[-50%] translate-y-[-50%] z-[70]">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{
              duration: 0.2,
              type: "spring",
              stiffness: 300,
              damping: 30,
            }}
            className="w-full max-w-md bg-white dark:bg-gray-800 rounded-2xl shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800 px-6 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/40 flex items-center justify-center">
                    <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
                  </div>
                  <div>
                    <Dialog.Title className="text-lg font-semibold text-red-900 dark:text-red-100">
                      Delete {propertyCount}{" "}
                      {propertyCount === 1 ? "Property" : "Properties"}
                    </Dialog.Title>
                    <Dialog.Description className="text-sm text-red-700 dark:text-red-300">
                      This action cannot be undone
                    </Dialog.Description>
                  </div>
                </div>
                <Dialog.Close asChild>
                  <button
                    className="rounded-lg p-1.5 hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors"
                    aria-label="Close"
                    disabled={isDeleting}
                  >
                    <X className="h-5 w-5 text-red-600 dark:text-red-400" />
                  </button>
                </Dialog.Close>
              </div>
            </div>

            {/* Content */}
            <div className="p-6">
              {/* Properties List */}
              <div className="mb-4 max-h-48 overflow-y-auto space-y-2">
                {properties.slice(0, 5).map((property) => (
                  <div
                    key={property.id}
                    className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600"
                  >
                    <div className="flex items-center space-x-3">
                      {/* Property Image/Initial */}
                      <div className="relative flex-shrink-0 h-8 w-8 rounded-lg overflow-hidden">
                        {property.images &&
                        property.images.length > 0 &&
                        property.id !== undefined &&
                        !failedImages.has(property.id) ? (
                          <img
                            src={property.images[0]?.image_url || ""}
                            alt={property.name}
                            className="h-full w-full object-cover"
                            onError={() => handleImageError(property.id!)}
                          />
                        ) : (
                          <div className="h-full w-full bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center text-blue-600 dark:text-blue-400 font-bold text-xs">
                            {property.name?.charAt(0).toUpperCase() || "?"}
                          </div>
                        )}
                      </div>

                      {/* Property Details */}
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">
                          {property.name}
                        </h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                          {[property.address, property.city, property.province]
                            .filter(Boolean)
                            .join(", ") || "No address"}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
                {propertyCount > 5 && (
                  <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-2">
                    and {propertyCount - 5} more{" "}
                    {propertyCount - 5 === 1 ? "property" : "properties"}
                  </div>
                )}
              </div>

              {/* Warning Message */}
              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3 mb-4">
                <p className="text-sm text-amber-800 dark:text-amber-200">
                  <strong className="font-semibold">Important:</strong> Properties
                  with active leases, rented units, or current tenants cannot be
                  deleted and will be skipped.
                </p>
                <p className="mt-2 text-sm text-amber-700 dark:text-amber-300">
                  Only properties that are completely vacant and have no active
                  associations will be permanently deleted. This action cannot be
                  undone.
                </p>
              </div>

              {/* Confirmation Question */}
              <p className="text-sm text-gray-700 dark:text-gray-300">
                Are you sure you want to permanently delete{" "}
                <strong className="font-semibold text-gray-900 dark:text-gray-100">
                  {propertyCount}{" "}
                  {propertyCount === 1 ? "property" : "properties"}
                </strong>
                ?
              </p>
            </div>

            {/* Footer */}
            <div className="border-t border-gray-200 dark:border-gray-700 px-6 py-4 bg-gray-50 dark:bg-gray-900 flex justify-end space-x-3">
              <button
                type="button"
                onClick={onClose}
                disabled={isDeleting}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={onConfirm}
                disabled={isDeleting}
                className="flex items-center space-x-2 px-4 py-2 text-sm font-medium bg-red-600 text-white hover:bg-red-700 dark:bg-red-500 dark:hover:bg-red-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isDeleting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="h-4 w-4" />
                    <span>
                      Delete {propertyCount}{" "}
                      {propertyCount === 1 ? "Property" : "Properties"}
                    </span>
                  </>
                )}
              </button>
            </div>
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};

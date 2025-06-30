import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

const EditUnitModal = ({
  isOpen,
  onClose,
  onSubmit,
  unit,
  isLoading,
}) => {
  const [formData, setFormData] = useState({
    name: "",
    floor: "",
    description: "",
    size: "",
    bedrooms: "",
    bathrooms: "",
  });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Initialize form when modal opens with unit data
  useEffect(() => {
    if (isOpen && unit) {
      setError("");
      setHasUnsavedChanges(false);
      setFormData({
        name: unit.name || "",
        floor: unit.floor !== null && unit.floor !== undefined ? unit.floor.toString() : "",
        description: unit.description || "",
        size: unit.size !== null && unit.size !== undefined ? unit.size.toString() : "",
        bedrooms: unit.bedrooms !== null && unit.bedrooms !== undefined ? unit.bedrooms.toString() : "",
        bathrooms: unit.bathrooms !== null && unit.bathrooms !== undefined ? unit.bathrooms.toString() : "",
      });
    }
  }, [isOpen, unit]);

  // Handle form input changes
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    setHasUnsavedChanges(true);
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      // Validate required fields
      if (!formData.name) {
        setError("Unit name/number is required");
        setIsSubmitting(false);
        return;
      }

      // Format data for submission - only include physical characteristics
      const formattedData = {
        name: formData.name,
        floor: formData.floor ? parseInt(formData.floor, 10) : null,
        description: formData.description || null,
        size: formData.size ? parseFloat(formData.size) : null,
        bedrooms: formData.bedrooms ? parseInt(formData.bedrooms, 10) : null,
        bathrooms: formData.bathrooms ? parseFloat(formData.bathrooms) : null,
      };

      // Call the parent component's submit handler
      await onSubmit(unit.id, formattedData);

      // Reset unsaved changes flag on successful submit
      setHasUnsavedChanges(false);

      // Close the modal on success (force close to skip confirmation)
      handleClose(true);
    } catch (error) {
      console.error("Error updating unit:", error);
      setError(error.message || "Failed to update unit");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle modal close
  const handleClose = (force = false) => {
    if (!force && hasUnsavedChanges) {
      const confirmed = window.confirm(
        "You have unsaved changes. Are you sure you want to close without saving?"
      );
      if (!confirmed) {
        return;
      }
    }
    
    setFormData({
      name: "",
      floor: "",
      description: "",
      size: "",
      bedrooms: "",
      bathrooms: "",
    });
    setError("");
    setHasUnsavedChanges(false);
    onClose();
  };

  // Handle backdrop click
  const handleBackdropClick = (e) => {
    // Only close if clicking the backdrop directly, not its children
    if (e.target === e.currentTarget) {
      handleClose();
    }
  };

  if (!isOpen || !unit) return null;

  // Format currency for display
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount || 0);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black bg-opacity-30 backdrop-blur-sm overflow-y-auto h-full w-full z-[9999] flex items-center justify-center p-4"
      onClick={handleBackdropClick}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="relative w-full max-w-2xl bg-white rounded-xl shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 bg-white border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-900">
            Edit Unit Details
          </h2>
          <button
            onClick={handleClose}
            className="text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-full p-1 transition-colors duration-200"
            aria-label="Close modal"
          >
            <svg
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          {/* Display rental status info if unit is rented */}
          {unit.is_rented && (
            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center gap-3">
                <svg
                  className="h-5 w-5 text-blue-600 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <div className="text-sm">
                  <p className="font-medium text-blue-900">This unit is currently rented</p>
                  {unit.tenant && (
                    <p className="text-blue-700">
                      Tenant: {unit.tenant.first_name} {unit.tenant.last_name}
                      {unit.monthly_rent && (
                        <span className="ml-2">• Rent: {formatCurrency(unit.monthly_rent)}</span>
                      )}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="mb-6 p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg flex items-start gap-2"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-5 w-5 mt-0.5 flex-shrink-0"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zm-1 9a1 1 0 100-2 1 1 0 000 2z"
                    clipRule="evenodd"
                  />
                </svg>
                <span>{error}</span>
              </motion.div>
            )}
          </AnimatePresence>

          <form onSubmit={handleSubmit} id="edit-unit-form" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Unit Number */}
              <div>
                <label
                  htmlFor="name"
                  className="block text-sm font-medium text-gray-700 mb-1 after:content-['*'] after:ml-0.5 after:text-red-500"
                >
                  Unit Number
                </label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  className="w-full px-4 py-2.5 text-gray-900 bg-white border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 focus:outline-none transition-all duration-200"
                  placeholder="e.g., 101"
                />
              </div>

              {/* Floor */}
              <div>
                <label
                  htmlFor="floor"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Floor
                </label>
                <input
                  id="floor"
                  name="floor"
                  type="number"
                  value={formData.floor}
                  onChange={handleChange}
                  min="0"
                  className="w-full px-4 py-2.5 text-gray-900 bg-white border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 focus:outline-none transition-all duration-200"
                  placeholder="e.g., 1"
                />
              </div>

              {/* Size */}
              <div>
                <label
                  htmlFor="size"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Size (sq ft)
                </label>
                <input
                  id="size"
                  name="size"
                  type="number"
                  value={formData.size}
                  onChange={handleChange}
                  min="0"
                  step="0.01"
                  className="w-full px-4 py-2.5 text-gray-900 bg-white border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 focus:outline-none transition-all duration-200"
                  placeholder="e.g., 850"
                />
              </div>

              {/* Bedrooms */}
              <div>
                <label
                  htmlFor="bedrooms"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Bedrooms
                </label>
                <input
                  id="bedrooms"
                  name="bedrooms"
                  type="number"
                  value={formData.bedrooms}
                  onChange={handleChange}
                  min="0"
                  className="w-full px-4 py-2.5 text-gray-900 bg-white border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 focus:outline-none transition-all duration-200"
                  placeholder="e.g., 2"
                />
              </div>

              {/* Bathrooms */}
              <div>
                <label
                  htmlFor="bathrooms"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Bathrooms
                </label>
                <input
                  id="bathrooms"
                  name="bathrooms"
                  type="number"
                  value={formData.bathrooms}
                  onChange={handleChange}
                  min="0"
                  step="0.5"
                  className="w-full px-4 py-2.5 text-gray-900 bg-white border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 focus:outline-none transition-all duration-200"
                  placeholder="e.g., 1.5"
                />
              </div>
            </div>

            {/* Description */}
            <div>
              <label
                htmlFor="description"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Description
              </label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                rows={3}
                className="w-full px-4 py-2.5 text-gray-900 bg-white border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 focus:outline-none transition-all duration-200"
                placeholder="Optional description of the unit..."
              />
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end space-x-3">
          <button
            type="button"
            onClick={handleClose}
            className="px-4 py-2 border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="edit-unit-form"
            disabled={isLoading || isSubmitting}
            className="px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            {isLoading || isSubmitting ? (
              <>
                <svg
                  className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Updating...
              </>
            ) : (
              "Update Unit"
            )}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default EditUnitModal;
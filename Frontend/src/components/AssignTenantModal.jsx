import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { fetchTenantsByProperty, updateUnit } from "../utils/api";

const AssignTenantModal = ({
  isOpen,
  onClose,
  onSubmit,
  propertyId,
  unitId,
  unitName,
  isLoading,
}) => {
  const [tenants, setTenants] = useState([]);
  const [selectedTenant, setSelectedTenant] = useState("");
  const [monthlyRent, setMonthlyRent] = useState("");
  const [error, setError] = useState("");
  const [isLoadingTenants, setIsLoadingTenants] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  // Fetch tenants when the modal opens
  useEffect(() => {
    if (isOpen && propertyId) {
      fetchTenants();
      setMonthlyRent("");
      setSelectedTenant("");
      setError("");
    }
  }, [isOpen, propertyId]);

  // Fetch tenants for the property
  const fetchTenants = async () => {
    try {
      setIsLoadingTenants(true);
      setError("");
      console.log(`Fetching tenants for property ID: ${propertyId}`);
      const tenantsData = await fetchTenantsByProperty(propertyId);
      console.log("Tenants fetched:", tenantsData);
      setTenants(tenantsData);
    } catch (err) {
      console.error("Error fetching tenants:", err);
      setError("Failed to load tenants. Please try again.");
    } finally {
      setIsLoadingTenants(false);
    }
  };

  // Handle form input changes
  const handleTenantSelect = (e) => {
    setSelectedTenant(e.target.value);
  };

  // Handle rent input changes
  const handleRentChange = (e) => {
    // Allow only numbers and decimal point
    const value = e.target.value;
    if (value === "" || /^\d*\.?\d*$/.test(value)) {
      setMonthlyRent(value);
    }
  };

  // Handle search input
  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
  };

  // Filter tenants based on search term
  const filteredTenants = tenants.filter((tenant) => {
    const fullName = `${tenant.first_name} ${tenant.last_name}`.toLowerCase();
    const email = (tenant.email || "").toLowerCase();
    const searchTermLower = searchTerm.toLowerCase();

    return (
      fullName.includes(searchTermLower) || email.includes(searchTermLower)
    );
  });

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    // Validate required fields
    if (!selectedTenant) {
      setError("Please select a tenant");
      return;
    }

    if (!monthlyRent || parseFloat(monthlyRent) <= 0) {
      setError("Please enter a valid monthly rent amount");
      return;
    }

    try {
      const updateData = {
        tenant_id: parseInt(selectedTenant, 10),
        monthly_rent: parseFloat(monthlyRent),
        is_rented: true,
      };

      console.log(
        `Assigning tenant (ID: ${selectedTenant}) to unit (ID: ${unitId}) with rent: ${monthlyRent}`
      );
      await updateUnit(unitId, updateData);

      // Call onSubmit to refresh data
      if (onSubmit) {
        await onSubmit();
      }

      // Close modal
      onClose();
    } catch (err) {
      console.error("Error assigning tenant:", err);
      setError(err.message || "Failed to assign tenant");
    }
  };

  // Clear error and state when modal closes
  const handleClose = () => {
    setError("");
    setSelectedTenant("");
    setMonthlyRent("");
    onClose();
  };

  // Don't render anything if modal is not open
  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black bg-opacity-30 backdrop-blur-sm overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4"
      onClick={handleClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="relative w-full max-w-md bg-white rounded-xl shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 bg-white border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-900">
            Assign Tenant to Unit {unitName}
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

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Search Input */}
            <div>
              <label
                htmlFor="search"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Search Tenants
              </label>
              <input
                id="search"
                type="text"
                value={searchTerm}
                onChange={handleSearchChange}
                className="w-full px-4 py-2.5 text-gray-900 bg-white border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 focus:outline-none transition-all duration-200"
                placeholder="Search by name or email"
              />
            </div>

            {/* Tenant Dropdown */}
            <div>
              <label
                htmlFor="tenant"
                className="block text-sm font-medium text-gray-700 mb-1 after:content-['*'] after:ml-0.5 after:text-red-500"
              >
                Select Tenant
              </label>

              {isLoadingTenants ? (
                <div className="flex items-center justify-center py-4">
                  <svg
                    className="animate-spin h-5 w-5 text-blue-500"
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
                  <span className="ml-2 text-sm text-gray-600">
                    Loading tenants...
                  </span>
                </div>
              ) : filteredTenants.length > 0 ? (
                <select
                  id="tenant"
                  name="tenant"
                  value={selectedTenant}
                  onChange={handleTenantSelect}
                  required
                  className="w-full px-4 py-2.5 text-gray-900 bg-white border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 focus:outline-none transition-all duration-200"
                >
                  <option value="">Select a tenant</option>
                  {filteredTenants.map((tenant) => (
                    <option key={tenant.id} value={tenant.id}>
                      {tenant.first_name} {tenant.last_name}{" "}
                      {tenant.email ? `(${tenant.email})` : ""}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="p-4 text-center text-gray-500 border border-gray-200 rounded-lg">
                  {searchTerm
                    ? "No tenants match your search"
                    : "No tenants available for this property"}
                </div>
              )}
            </div>

            {/* Monthly Rent Input */}
            <div>
              <label
                htmlFor="monthlyRent"
                className="block text-sm font-medium text-gray-700 mb-1 after:content-['*'] after:ml-0.5 after:text-red-500"
              >
                Monthly Rent
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <span className="text-gray-500 sm:text-sm">$</span>
                </div>
                <input
                  id="monthlyRent"
                  name="monthlyRent"
                  type="text"
                  required
                  value={monthlyRent}
                  onChange={handleRentChange}
                  placeholder="0.00"
                  className="w-full pl-7 pr-4 py-2.5 text-gray-900 bg-white border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 focus:outline-none transition-all duration-200"
                />
              </div>
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
            onClick={handleSubmit}
            disabled={isLoading || !selectedTenant || !monthlyRent}
            className="px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            {isLoading ? (
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
                Assigning...
              </>
            ) : (
              "Assign Tenant"
            )}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default AssignTenantModal;

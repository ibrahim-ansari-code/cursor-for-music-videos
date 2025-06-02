import React, { useState, useEffect } from "react";
import { toast } from "react-toastify";
import {
  fetchProperties,
  fetchTenantsByProperty,
  createPayment,
  fetchLeases,
} from "../utils/api";

const PAYMENT_METHODS = [
  "Credit Card",
  "Bank Transfer",
  "Cash",
  "Check",
  "Other",
];

const PAYMENT_STATUSES = [
  "Pending",
  "Paid",
  "Partial",
  "Overdue",
  "Cancelled",
  "Refunded",
];

const NewPaymentModal = ({ isOpen, onClose, onSuccess }) => {
  // Form state
  const [formData, setFormData] = useState({
    property_id: "",
    tenant_id: "",
    amount: "",
    payment_date: new Date().toISOString().split("T")[0],
    payment_method: "",
    status: "Paid",
    notes: "",
  });

  // UI state
  const [properties, setProperties] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lease, setLease] = useState(null);

  // Dropdown states
  const [dropdownOpen, setDropdownOpen] = useState("");
  const [propertySearchTerm, setPropertySearchTerm] = useState("");
  const [tenantSearchTerm, setTenantSearchTerm] = useState("");

  // Load properties on mount
  useEffect(() => {
    const loadProperties = async () => {
      try {
        const data = await fetchProperties();
        setProperties(data);
      } catch (err) {
        console.error("Failed to load properties:", err);
        setError("Failed to load properties. Please try again.");
      }
    };

    if (isOpen) {
      loadProperties();
    }
  }, [isOpen]);

  // Load tenants when property is selected
  useEffect(() => {
    const loadTenants = async () => {
      if (formData.property_id) {
        try {
          const data = await fetchTenantsByProperty(formData.property_id);
          console.log("Fetched tenants:", data); // Log tenant data
          setTenants(data);
          // Clear tenant selection when property changes
          setFormData((prev) => ({ ...prev, tenant_id: "" }));
          setLease(null);
        } catch (err) {
          console.error("Failed to load tenants:", err);
          setError("Failed to load tenants. Please try again.");
        }
      }
    };

    loadTenants();
  }, [formData.property_id]);

  // Find active lease when tenant is selected
  useEffect(() => {
    const findActiveLease = async () => {
      if (formData.property_id && formData.tenant_id) {
        try {
          const leases = await fetchLeases(); // Fetch all leases
          console.log("Fetched leases:", leases); // Log fetched leases

          const activeLease = leases.find(
            (lease) =>
              lease.tenant_id === formData.tenant_id &&
              lease.property_id === formData.property_id &&
              lease.status?.toLowerCase() === "active" // Filter client-side
          );

          console.log("Active lease found:", activeLease); // Log active lease

          if (activeLease) {
            setLease(activeLease);
            setError(null);

            // Log the tenant details
            console.log("Selected tenant ID:", formData.tenant_id);
            console.log("Lease tenant ID (user_id):", activeLease.tenant_id);
          } else {
            setError("No active lease found for this tenant.");
            setLease(null);
          }
        } catch (err) {
          console.error("Failed to find active lease:", err);
          setError("Failed to verify lease information.");
        }
      }
    };

    findActiveLease();
  }, [formData.property_id, formData.tenant_id]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!lease) {
      setError("No active lease found. Cannot create payment.");
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      // Get the selected tenant from the tenants array
      const selectedTenant = tenants.find(
        (tenant) => tenant.id === formData.tenant_id
      );

      // Properly format the payment data to match backend expectations
      const paymentData = {
        lease_id: lease.id,
        // Include the tenant's name to display in the payment list
        tenant_name: selectedTenant?.full_name || "Unknown Tenant",
        // Remove tenant_id as we'll use the current user's ID on the backend
        amount: parseFloat(formData.amount),
        // Create a timezone-naive datetime string in ISO format without the 'Z' at the end
        payment_date: formData.payment_date
          ? `${formData.payment_date}T00:00:00`
          : null,
        payment_method: formData.payment_method,
        // Make sure status is a valid enum value
        status: formData.status,
        // Add transaction_reference as empty string to avoid null issues
        transaction_reference: "",
        notes: formData.notes || "",
      };

      console.log("Submitting payment with data:", paymentData);
      await createPayment(paymentData);
      // Success notification is now handled by the parent component
      onSuccess?.();
      handleClose();
    } catch (err) {
      console.error("Failed to create payment:", err);
      setError(err.message || "Failed to create payment. Please try again.");
      toast.error("Failed to create payment");
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setFormData({
      property_id: "",
      tenant_id: "",
      amount: "",
      payment_date: new Date().toISOString().split("T")[0],
      payment_method: "",
      status: "Paid",
      notes: "",
    });
    setError(null);
    setLease(null);
    setPropertySearchTerm("");
    setTenantSearchTerm("");
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-md shadow-lg rounded-lg bg-white">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-800">New Payment</h2>
          <button
            onClick={handleClose}
            className="text-gray-600 hover:text-gray-800"
          >
            <i className="fas fa-times"></i>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Property Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Property *
            </label>
            <div className="relative">
              <input
                type="text"
                placeholder="Search properties..."
                value={propertySearchTerm}
                onChange={(e) => {
                  setPropertySearchTerm(e.target.value);
                  setDropdownOpen("property");
                }}
                className="block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              />
              {dropdownOpen === "property" && (
                <div className="absolute z-10 mt-1 w-full bg-white shadow-lg rounded-md">
                  <ul className="max-h-60 overflow-auto rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
                    {properties
                      .filter((property) =>
                        property.name
                          .toLowerCase()
                          .includes(propertySearchTerm.toLowerCase())
                      )
                      .map((property) => (
                        <li
                          key={property.id}
                          className="cursor-pointer select-none relative py-2 pl-3 pr-9 hover:bg-blue-100"
                          onClick={() => {
                            setFormData((prev) => ({
                              ...prev,
                              property_id: property.id,
                            }));
                            setPropertySearchTerm(property.name);
                            setDropdownOpen("");
                          }}
                        >
                          <span className="font-normal block truncate">
                            {property.name}
                          </span>
                        </li>
                      ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* Tenant Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tenant *
            </label>
            <div className="relative">
              <input
                type="text"
                placeholder="Search tenants..."
                value={tenantSearchTerm}
                onChange={(e) => {
                  setTenantSearchTerm(e.target.value);
                  setDropdownOpen("tenant");
                }}
                disabled={!formData.property_id}
                className="block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm disabled:bg-gray-100"
              />
              {dropdownOpen === "tenant" && (
                <div className="absolute z-10 mt-1 w-full bg-white shadow-lg rounded-md">
                  <ul className="max-h-60 overflow-auto rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
                    {tenants
                      .filter((tenant) =>
                        (tenant.full_name || "")
                          .toLowerCase()
                          .includes(tenantSearchTerm.toLowerCase())
                      )
                      .map((tenant) => (
                        <li
                          key={tenant.id}
                          className="cursor-pointer select-none relative py-2 pl-3 pr-9 hover:bg-blue-100"
                          onClick={() => {
                            console.log("Selected tenant:", tenant);
                            setFormData((prev) => ({
                              ...prev,
                              tenant_id: tenant.id,
                            }));
                            setTenantSearchTerm(tenant.full_name);
                            setDropdownOpen("");
                          }}
                        >
                          <span className="font-normal block truncate">
                            {tenant.full_name}
                          </span>
                        </li>
                      ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* Amount */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Amount *
            </label>
            <div className="relative rounded-md shadow-sm">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <span className="text-gray-500 sm:text-sm">$</span>
              </div>
              <input
                type="number"
                name="amount"
                value={formData.amount}
                onChange={handleInputChange}
                min="0"
                step="0.01"
                required
                className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-7 pr-3 py-2 border-gray-300 rounded-md text-sm"
                placeholder="0.00"
              />
            </div>
          </div>

          {/* Payment Date */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Payment Date *
            </label>
            <input
              type="date"
              name="payment_date"
              value={formData.payment_date}
              onChange={handleInputChange}
              required
              className="focus:ring-blue-500 focus:border-blue-500 block w-full py-2 px-3 border-gray-300 rounded-md text-sm"
            />
          </div>

          {/* Payment Method */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Payment Method *
            </label>
            <select
              name="payment_method"
              value={formData.payment_method}
              onChange={handleInputChange}
              required
              className="block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            >
              <option value="">Select a method</option>
              {PAYMENT_METHODS.map((method) => (
                <option key={method} value={method}>
                  {method}
                </option>
              ))}
            </select>
          </div>

          {/* Status */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Status *
            </label>
            <select
              name="status"
              value={formData.status}
              onChange={handleInputChange}
              required
              className="block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            >
              {PAYMENT_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes
            </label>
            <textarea
              name="notes"
              value={formData.notes}
              onChange={handleInputChange}
              rows="2"
              className="focus:ring-blue-500 focus:border-blue-500 block w-full py-2 px-3 border-gray-300 rounded-md text-sm"
              placeholder="Optional payment notes..."
            />
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative">
              <span className="block sm:inline">{error}</span>
            </div>
          )}

          {/* Form Actions */}
          <div className="mt-6 flex justify-end space-x-3">
            <button
              type="button"
              onClick={handleClose}
              className="inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !lease}
              className="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <svg
                    className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
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
                  Creating...
                </>
              ) : (
                "Create Payment"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default NewPaymentModal;

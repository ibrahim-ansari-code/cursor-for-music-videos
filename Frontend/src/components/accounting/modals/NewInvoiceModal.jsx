import React, { useState, useEffect, useRef, useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { toast } from "react-toastify";
import { fetchProperties } from "../../../utils/api/properties";
import { fetchTenants } from "../../../utils/api/tenants";
import { createInvoice } from "../../../utils/api/accounting";
import { INVOICE_STATUSES } from "../../../utils/constants";

const NewInvoiceModal = ({ isOpen, onClose, onSuccess }) => {
  const initialFormData = {
    invoice_number: "",
    amount: "",
    description: "",
    issue_date: new Date().toISOString().split("T")[0],
    due_date: "",
    status: "Pending",
    property_id: "",
    property_name: "",
    tenant_id: "",
    tenant_name: "",
  };

  const [formData, setFormData] = useState(initialFormData);
  const [properties, setProperties] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dropdownOpen, setDropdownOpen] = useState("");
  const [filteredProperties, setFilteredProperties] = useState([]);
  const [filteredTenants, setFilteredTenants] = useState([]);

  const propertyDropdownRef = useRef(null);
  const tenantDropdownRef = useRef(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [propertiesData, tenantsData] = await Promise.all([
          fetchProperties(),
          fetchTenants(),
        ]);
        setProperties(propertiesData || []);
        setTenants(tenantsData || []);
        setFilteredProperties(propertiesData || []);
        setFilteredTenants(tenantsData || []);
      } catch (err) {
        console.error("Failed to load data:", err);
        toast.error("Failed to load properties and tenants.");
      }
    };

    if (isOpen) {
      loadData();
      setFormData(initialFormData);
      setError(null);
      setDropdownOpen("");
      
      // Generate default invoice number with robust collision-resistant ID
      const now = new Date();
      const datePrefix = `${now.getFullYear()}${(now.getMonth() + 1)
        .toString()
        .padStart(2, "0")}${now.getDate().toString().padStart(2, "0")}`;
      
      // Generate a more robust unique identifier using crypto.randomUUID or fallback
      const generateUniqueId = () => {
        if (typeof crypto !== 'undefined' && crypto.randomUUID) {
          // Use crypto.randomUUID for better uniqueness
          return crypto.randomUUID().split('-')[0].toUpperCase();
        } else {
          // Fallback: timestamp + multiple random components
          const timestamp = now.getTime().toString(36);
          const random1 = Math.random().toString(36).substring(2, 6);
          const random2 = Math.random().toString(36).substring(2, 6);
          return (timestamp + random1 + random2).toUpperCase();
        }
      };
      
      const invoiceNumber = `INV-${datePrefix}-${generateUniqueId()}`;
      
      setFormData(prev => ({
        ...prev,
        invoice_number: invoiceNumber,
      }));
    }
  }, [isOpen]);

  useEffect(() => {
    // Set default due date 30 days from issue date
    if (formData.issue_date && !formData.due_date) {
      const issueDate = new Date(formData.issue_date);
      const dueDate = new Date(issueDate);
      dueDate.setDate(dueDate.getDate() + 30);
      setFormData(prev => ({
        ...prev,
        due_date: dueDate.toISOString().split("T")[0],
      }));
    }
  }, [formData.issue_date, formData.due_date]);

  // Memoize the property-filtered tenants to avoid recalculation on every render
  const propertyFilteredTenants = useMemo(() => {
    return formData.property_id 
      ? tenants.filter(tenant => 
          tenant.property_units?.some(unit => 
            unit.property_id === parseInt(formData.property_id, 10)
          )
        )
      : tenants;
  }, [formData.property_id, tenants]);

  // Update filtered tenants when property changes and reset tenant selection if needed
  useEffect(() => {
    setFilteredTenants(propertyFilteredTenants);
    
    // Reset tenant selection if not in filtered list
    if (formData.tenant_id && !propertyFilteredTenants.some(t => t.id === parseInt(formData.tenant_id, 10))) {
      setFormData(prev => ({ ...prev, tenant_id: "", tenant_name: "" }));
    }
  }, [propertyFilteredTenants, formData.tenant_id]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        dropdownOpen === "property" &&
        propertyDropdownRef.current &&
        !propertyDropdownRef.current.contains(event.target)
      ) {
        setDropdownOpen("");
      }
      if (
        dropdownOpen === "tenant" &&
        tenantDropdownRef.current &&
        !tenantDropdownRef.current.contains(event.target)
      ) {
        setDropdownOpen("");
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [dropdownOpen]);

  const handleInputChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setError(null);
  };

  const handlePropertySelect = (property) => {
    setFormData((prev) => ({
      ...prev,
      property_id: property.id,
      property_name: property.name,
      tenant_id: "", // Reset tenant selection
      tenant_name: "",
    }));
    setDropdownOpen("");
  };

  const handleTenantSelect = (tenant) => {
    setFormData((prev) => ({
      ...prev,
      tenant_id: tenant.id,
      tenant_name: tenant.full_name,
    }));
    setDropdownOpen("");
  };

  const handlePropertySearch = (searchTerm) => {
    const filtered = properties.filter((property) =>
      property.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredProperties(filtered);
    setFormData((prev) => ({ ...prev, property_name: searchTerm }));
  };

  const handleTenantSearch = (searchTerm) => {
    const tenantsToFilter = propertyFilteredTenants;
      
    const filtered = tenantsToFilter.filter((tenant) =>
      tenant.full_name.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredTenants(filtered);
    setFormData((prev) => ({ ...prev, tenant_name: searchTerm }));
  };

  const validateForm = () => {
    if (!formData.invoice_number?.trim()) {
      setError("Invoice number is required.");
      return false;
    }
    if (!formData.amount || parseFloat(formData.amount) <= 0) {
      setError("Amount must be greater than 0.");
      return false;
    }
    if (!formData.description?.trim()) {
      setError("Description is required.");
      return false;
    }
    if (!formData.issue_date) {
      setError("Issue date is required.");
      return false;
    }
    if (!formData.due_date) {
      setError("Due date is required.");
      return false;
    }
    if (new Date(formData.due_date) < new Date(formData.issue_date)) {
      setError("Due date cannot be earlier than issue date.");
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setIsLoading(true);
    setError(null);

    try {
      const invoiceData = {
        invoice_number: formData.invoice_number.trim(),
        amount: parseFloat(formData.amount),
        description: formData.description.trim(),
        issue_date: formData.issue_date,
        due_date: formData.due_date,
        status: formData.status,
        property_id: formData.property_id ? parseInt(formData.property_id, 10) : null,
        tenant_id: formData.tenant_id ? parseInt(formData.tenant_id, 10) : null,
      };

      await createInvoice(invoiceData);
      
      onSuccess?.();
    } catch (err) {
      console.error("Failed to create invoice:", err);
      setError(
        err.message || "Failed to create invoice. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
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
            className="relative w-full max-w-2xl bg-white rounded-xl shadow-xl max-h-[85vh] overflow-hidden flex flex-col z-[10000]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="relative px-6 py-4 bg-gradient-to-br from-brand-green to-brand-teal text-white">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-xl font-semibold text-white">Create New Invoice</h2>
                  <p className="text-white/80 mt-0.5 text-sm">
                    Generate an invoice for your clients or tenants
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
            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto bg-gray-50">
              {error && (
                <motion.div 
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mx-6 mt-4 p-3 bg-red-50 border border-red-100 text-red-700 rounded-lg"
                >
                  <div className="flex">
                    <svg className="h-5 w-5 text-red-400 mr-2 flex-shrink-0 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm">{error}</span>
                  </div>
                </motion.div>
              )}

              <div className="p-6 space-y-4">
                {/* Invoice Details */}
                <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                  <div className="flex items-center mb-3">
                    <div className="w-9 h-9 bg-blue-50 rounded-lg flex items-center justify-center mr-3">
                      <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <h3 className="text-base font-medium text-gray-900">Invoice Details</h3>
                  </div>

                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Invoice Number <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={formData.invoice_number}
                          onChange={(e) => handleInputChange("invoice_number", e.target.value)}
                          placeholder="INV-2024-001"
                          required
                          className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Amount <span className="text-red-500">*</span>
                        </label>
                        <div className="relative">
                          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <span className="text-gray-500 sm:text-sm">$</span>
                          </div>
                          <input
                            type="number"
                            step="0.01"
                            min="0.01"
                            value={formData.amount}
                            onChange={(e) => handleInputChange("amount", e.target.value)}
                            placeholder="0.00"
                            required
                            className="w-full px-4 py-2.5 pl-7 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                          />
                        </div>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Description <span className="text-red-500">*</span>
                      </label>
                      <textarea
                        value={formData.description}
                        onChange={(e) => handleInputChange("description", e.target.value)}
                        placeholder="Brief description of the invoice..."
                        rows={3}
                        required
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white resize-none"
                      />
                    </div>
                  </div>
                </div>

                {/* Dates & Status */}
                <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                  <div className="flex items-center mb-3">
                    <div className="w-9 h-9 bg-green-50 rounded-lg flex items-center justify-center mr-3">
                      <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <h3 className="text-base font-medium text-gray-900">Dates & Status</h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Issue Date <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="date"
                        value={formData.issue_date}
                        onChange={(e) => handleInputChange("issue_date", e.target.value)}
                        required
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Due Date <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="date"
                        value={formData.due_date}
                        onChange={(e) => handleInputChange("due_date", e.target.value)}
                        required
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
                      <select
                        value={formData.status}
                        onChange={(e) => handleInputChange("status", e.target.value)}
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                      >
                        {INVOICE_STATUSES.map((status) => (
                          <option key={status} value={status}>
                            {status.charAt(0).toUpperCase() + status.slice(1).toLowerCase()}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                {/* Property & Tenant Selection */}
                <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                  <div className="flex items-center mb-3">
                    <div className="w-9 h-9 bg-purple-50 rounded-lg flex items-center justify-center mr-3">
                      <svg className="w-4 h-4 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-base font-medium text-gray-900">Property & Tenant</h3>
                      <p className="text-sm text-gray-500 mt-0.5">Optional - Select associated property and tenant</p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    {/* Property Selection */}
                    <div className="relative" ref={propertyDropdownRef}>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Property (Optional)</label>
                      <input
                        type="text"
                        value={formData.property_name}
                        onChange={(e) => {
                          handlePropertySearch(e.target.value);
                          if (!e.target.value) {
                            setFormData(prev => ({ ...prev, property_id: "", property_name: "" }));
                          }
                        }}
                        onFocus={() => setDropdownOpen("property")}
                        placeholder="Search properties..."
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                      />
                      {dropdownOpen === "property" && filteredProperties.length > 0 && (
                        <div className="absolute z-20 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                          {filteredProperties.map((property) => (
                            <div
                              key={property.id}
                              className="px-4 py-2.5 text-sm text-gray-700 hover:bg-blue-500 hover:text-white cursor-pointer transition-colors duration-150"
                              onClick={() => handlePropertySelect(property)}
                            >
                              <div className="font-medium">{property.name}</div>
                              {property.address && (
                                <div className="text-xs opacity-75 mt-0.5">{property.address}</div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Tenant Selection */}
                    <div className="relative" ref={tenantDropdownRef}>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Tenant (Optional)</label>
                      <input
                        type="text"
                        value={formData.tenant_name}
                        onChange={(e) => {
                          handleTenantSearch(e.target.value);
                          if (!e.target.value) {
                            setFormData(prev => ({ ...prev, tenant_id: "", tenant_name: "" }));
                          }
                        }}
                        onFocus={() => setDropdownOpen("tenant")}
                        placeholder="Search tenants..."
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                      />
                      {dropdownOpen === "tenant" && filteredTenants.length > 0 && (
                        <div className="absolute z-20 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                          {filteredTenants.map((tenant) => (
                            <div
                              key={tenant.id}
                              className="px-4 py-2.5 text-sm text-gray-700 hover:bg-blue-500 hover:text-white cursor-pointer transition-colors duration-150"
                              onClick={() => handleTenantSelect(tenant)}
                            >
                              <div className="font-medium">{tenant.full_name}</div>
                              {tenant.email && (
                                <div className="text-xs opacity-75 mt-0.5">{tenant.email}</div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </form>

            {/* Footer */}
            <div className="px-6 py-5 bg-gray-50 border-t border-gray-200">
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2.5 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-all text-sm font-medium"
                  disabled={isLoading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  className="px-5 py-2.5 bg-gradient-to-br from-brand-green to-brand-teal text-white rounded-md hover:from-brand-green/90 hover:to-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-brand-green focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium flex items-center gap-2 min-w-[140px] justify-center shadow-sm"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Creating...
                    </>
                  ) : (
                    'Create Invoice'
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default NewInvoiceModal;
import { AnimatePresence, motion } from "framer-motion";
import React, { useState, useEffect } from "react";
import { createTenant } from "../../utils/api";

// Status transformation mapping
const STATUS_MAPPING = {
  'active': 'Active',
  'inactive': 'Inactive',
  'pending': 'Pending',
  'evicted': 'Evicted',
  'moved out': 'Moved Out',
  'moved_out': 'Moved Out'
};

const TenantModal = ({
  isOpen,
  onClose,
  onSave,
  source,
  tenant = {},
  propertyId = null,
  unitId = null,
  unitName = "",
}) => {
  const [formData, setFormData] = useState({
    tenant_type: "Individual",
    first_name: "",
    last_name: "",
    company_name: "",
    contact_person: "",
    phone: "",
    email: "",
    status: "Active",
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const [touched, setTouched] = useState({});

  // Populate form when tenant data is provided
  useEffect(() => {
    if (isOpen) {
      let firstName = tenant?.first_name || "";
      let lastName = tenant?.last_name || "";

      if (tenant?.full_name && (!firstName || !lastName)) {
        const nameParts = tenant.full_name.split(" ");
        firstName = nameParts[0] || "";
        lastName = nameParts.slice(1).join(" ") || "";
      }

      setFormData({
        tenant_type: tenant?.tenant_type || "Individual",
        first_name: firstName,
        last_name: lastName,
        company_name: tenant?.company_name || "",
        contact_person: tenant?.contact_person || "",
        phone: tenant?.phone || "",
        email: tenant?.email || "",
        status: tenant?.status || "Active",
      });

      setFieldErrors({});
      setError(null);
      setTouched({});
    }
  }, [
    isOpen,
    tenant?.id,
    tenant?.first_name,
    tenant?.last_name,
    tenant?.full_name,
    tenant?.tenant_type,
    tenant?.company_name,
    tenant?.contact_person,
    tenant?.phone,
    tenant?.email,
    tenant?.status
  ]);
  
  const validateField = (name, value) => {
    const tenantType = formData.tenant_type;
    
    switch (name) {
      case "first_name":
        if (tenantType === "Individual" && (!value || value.trim() === "")) {
          return "First name is required for individual tenants";
        }
        break;
      case "last_name":
        if (tenantType === "Individual" && (!value || value.trim() === "")) {
          return "Last name is required for individual tenants";
        }
        break;
      case "company_name":
        if (tenantType === "Company" && (!value || value.trim() === "")) {
          return "Company name is required for company tenants";
        }
        break;
      case "email":
        if (!value || value.trim() === "") return "Email is required";
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        if (!emailRegex.test(value.trim())) {
          return "Please enter a valid email address";
        }
        break;
      case "phone":
        if (value && value.trim() !== "") {
          const digitsOnly = value.replace(/[^0-9]/g, "");
          if (digitsOnly.length < 10 || digitsOnly.length > 15) {
            return "Phone number must contain 10-15 digits";
          }
        }
        break;
      default:
        break;
    }
    return null;
  };

  const handleBlur = (e) => {
    const { name, value } = e.target;
    setTouched((prev) => ({
      ...prev,
      [name]: true,
    }));
    
    const error = validateField(name, value);
    if (error) {
      setFieldErrors((prev) => ({ ...prev, [name]: error }));
    } else {
      setFieldErrors((prev) => {
        const updated = { ...prev };
        delete updated[name];
        return updated;
      });
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    
    setFormData((prev) => ({ ...prev, [name]: value }));
    
    // Clear error when user starts typing if field was touched
    if (touched[name]) {
      const error = validateField(name, value);
      if (error) {
        setFieldErrors((prev) => ({ ...prev, [name]: error }));
      } else {
        setFieldErrors((prev) => {
          const updated = { ...prev };
          delete updated[name];
          return updated;
        });
      }
    }
    
    // If tenant type changed, clear related field errors
    if (name === "tenant_type") {
      setFieldErrors((prev) => {
        const updated = { ...prev };
        delete updated.first_name;
        delete updated.last_name;
        delete updated.company_name;
        return updated;
      });
    }
  };

  const validateForm = () => {
    let isValid = true;
    const newErrors = {};

    // Validate based on tenant type
    if (formData.tenant_type === "Individual") {
      for (const fieldName of ["first_name", "last_name", "email"]) {
        const error = validateField(fieldName, formData[fieldName]);
        if (error) {
          newErrors[fieldName] = error;
          isValid = false;
        }
      }
    } else {
      for (const fieldName of ["company_name", "email"]) {
        const error = validateField(fieldName, formData[fieldName]);
        if (error) {
          newErrors[fieldName] = error;
          isValid = false;
        }
      }
    }
    
    // Validate phone if provided
    if (formData.phone) {
      const phoneError = validateField("phone", formData.phone);
      if (phoneError) {
        newErrors.phone = phoneError;
        isValid = false;
      }
    }
    
    setFieldErrors(newErrors);
    if (!isValid) {
      setError("Please correct the highlighted fields.");
    } else {
      setError(null);
    }
    return isValid;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }
    
    setIsLoading(true);
    try {
      // Build tenant object with only relevant fields based on tenant type
      const tenantToCreate = {
        tenant_type: formData.tenant_type,
        email: formData.email.trim(),
        status: STATUS_MAPPING[formData.status.toLowerCase()] || formData.status,
        phone: formData.phone?.trim() || null,
      };

      if (formData.tenant_type === "Individual") {
        // For individual tenants, only include first_name and last_name
        tenantToCreate.first_name = formData.first_name.trim();
        tenantToCreate.last_name = formData.last_name.trim();
        // Explicitly exclude company fields
      } else {
        // For company tenants, only include company_name and optionally contact_person
        tenantToCreate.company_name = formData.company_name.trim();
        tenantToCreate.contact_person = formData.contact_person?.trim() || null;
        // Explicitly exclude individual name fields
      }
      
      const response = await createTenant(tenantToCreate);
      if (onSave) {
        const tenantResponse = {
          ...response,
          // Preserve any context data for the calling component
          unit: unitName || "",
          unit_id: unitId || null,
          current_property_id: propertyId || null,
        };
        onSave(tenantResponse);
      }
      if (!source || source !== "importLeaseModal") {
        onClose();
      }
    } catch (err) {
      console.error("Failed to create tenant:", err);
      let errorMessage = "Failed to create tenant. Please try again.";

      if (err.status === 409) {
        errorMessage = err.data?.detail || "A tenant with this email already exists.";
        setFieldErrors((prev) => ({
          ...prev,
          email: "This email is already in use.",
        }));
        setTouched((prev) => ({ ...prev, email: true }));
      } else if (err.data?.detail && Array.isArray(err.data.detail)) {
        const validationErrors = {};
        const generalErrors = [];
        
        err.data.detail.forEach((errorItem) => {
          if (errorItem.loc && errorItem.loc.length > 1) {
            const fieldName = errorItem.loc[errorItem.loc.length - 1];
            validationErrors[fieldName] = errorItem.msg;
          } else {
            generalErrors.push(errorItem.msg || errorItem);
          }
        });
        
        if (Object.keys(validationErrors).length > 0) {
          setFieldErrors((prev) => ({ ...prev, ...validationErrors }));
          errorMessage = "Please correct the validation errors below.";
        }
        
        if (generalErrors.length > 0) {
          errorMessage = generalErrors.join(". ");
        }
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
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
            className="relative w-full max-w-2xl bg-white dark:bg-gray-800 rounded-xl shadow-xl max-h-[85vh] overflow-hidden flex flex-col z-[10000]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="relative px-6 py-4 bg-gradient-to-br from-brand-green to-brand-teal text-white">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-xl font-semibold text-white">Add New Tenant</h2>
                  <p className="text-white/80 mt-0.5 text-sm">
                    Create a new {formData.tenant_type.toLowerCase()} tenant profile
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
            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-900">
              {error && (
                <motion.div 
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mx-6 mt-4 p-3 bg-red-50 dark:bg-red-900/50 border border-red-100 dark:border-red-800 text-red-700 dark:text-red-400 rounded-lg"
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
                {/* Tenant Type Section */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700">
                  <div className="flex items-center mb-3">
                    <div className="w-9 h-9 bg-purple-50 dark:bg-purple-900/30 rounded-lg flex items-center justify-center mr-3">
                      <svg className="w-4 h-4 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                      </svg>
                    </div>
                    <h3 className="text-base font-medium text-gray-900 dark:text-gray-100">Tenant Type</h3>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3">
                    <label className="flex items-center cursor-pointer">
                      <input
                        type="radio"
                        name="tenant_type"
                        value="Individual"
                        checked={formData.tenant_type === "Individual"}
                        onChange={handleChange}
                        className="mr-3 text-blue-600 dark:text-blue-500 focus:ring-blue-500"
                      />
                      <div className="flex items-center">
                        <svg className="w-5 h-5 text-gray-400 dark:text-gray-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Individual</span>
                      </div>
                    </label>
                    <label className="flex items-center cursor-pointer">
                      <input
                        type="radio"
                        name="tenant_type"
                        value="Company"
                        checked={formData.tenant_type === "Company"}
                        onChange={handleChange}
                        className="mr-3 text-blue-600 dark:text-blue-500 focus:ring-blue-500"
                      />
                      <div className="flex items-center">
                        <svg className="w-5 h-5 text-gray-400 dark:text-gray-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                        </svg>
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Company</span>
                      </div>
                    </label>
                  </div>
                </div>

                {/* Conditional Name/Company Section */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700">
                  <div className="flex items-center mb-3">
                    <div className="w-9 h-9 bg-blue-50 dark:bg-blue-900/30 rounded-lg flex items-center justify-center mr-3">
                      <svg className="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                    </div>
                    <h3 className="text-base font-medium text-gray-900 dark:text-gray-100">
                      {formData.tenant_type === "Individual" ? "Personal Information" : "Company Information"}
                    </h3>
                  </div>

                  {formData.tenant_type === "Individual" ? (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          First Name <span className="text-red-500 dark:text-red-400">*</span>
                        </label>
                        <input
                          name="first_name"
                          value={formData.first_name}
                          onChange={handleChange}
                          onBlur={handleBlur}
                          placeholder="Enter first name"
                          className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 ${
                            fieldErrors.first_name && touched.first_name ? 'border-red-300 dark:border-red-600' : 'border-gray-200 dark:border-gray-600'
                          }`}
                          required
                        />
                        {fieldErrors.first_name && touched.first_name && (
                          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{fieldErrors.first_name}</p>
                        )}
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Last Name <span className="text-red-500 dark:text-red-400">*</span>
                        </label>
                        <input
                          name="last_name"
                          value={formData.last_name}
                          onChange={handleChange}
                          onBlur={handleBlur}
                          placeholder="Enter last name"
                          className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 ${
                            fieldErrors.last_name && touched.last_name ? 'border-red-300 dark:border-red-600' : 'border-gray-200 dark:border-gray-600'
                          }`}
                          required
                        />
                        {fieldErrors.last_name && touched.last_name && (
                          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{fieldErrors.last_name}</p>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Company Name <span className="text-red-500 dark:text-red-400">*</span>
                        </label>
                        <input
                          name="company_name"
                          value={formData.company_name}
                          onChange={handleChange}
                          onBlur={handleBlur}
                          placeholder="Enter company name"
                          className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 ${
                            fieldErrors.company_name && touched.company_name ? 'border-red-300 dark:border-red-600' : 'border-gray-200 dark:border-gray-600'
                          }`}
                          required
                        />
                        {fieldErrors.company_name && touched.company_name && (
                          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{fieldErrors.company_name}</p>
                        )}
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Contact Person
                        </label>
                        <input
                          name="contact_person"
                          value={formData.contact_person}
                          onChange={handleChange}
                          onBlur={handleBlur}
                          placeholder="Enter contact person name"
                          className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Contact Information Section */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700">
                  <div className="flex items-center mb-3">
                    <div className="w-9 h-9 bg-green-50 dark:bg-green-900/30 rounded-lg flex items-center justify-center mr-3">
                      <svg className="w-4 h-4 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <h3 className="text-base font-medium text-gray-900 dark:text-gray-100">Contact Information</h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Email <span className="text-red-500 dark:text-red-400">*</span>
                      </label>
                      <input
                        name="email"
                        type="email"
                        value={formData.email}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        placeholder="Enter email address"
                        className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 ${
                          fieldErrors.email && touched.email ? 'border-red-300 dark:border-red-600' : 'border-gray-200 dark:border-gray-600'
                        }`}
                        required
                      />
                      {fieldErrors.email && touched.email && (
                        <p className="mt-2 text-sm text-red-600 dark:text-red-400">{fieldErrors.email}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Phone Number
                      </label>
                      <input
                        name="phone"
                        type="tel"
                        value={formData.phone}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        placeholder="Enter phone number"
                        className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 ${
                          fieldErrors.phone && touched.phone ? 'border-red-300 dark:border-red-600' : 'border-gray-200 dark:border-gray-600'
                        }`}
                      />
                      {fieldErrors.phone && touched.phone && (
                        <p className="mt-2 text-sm text-red-600 dark:text-red-400">{fieldErrors.phone}</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </form>

            {/* Footer */}
            <div className="px-6 py-5 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div className="text-sm text-gray-500 dark:text-gray-400 flex items-start flex-1 sm:max-w-md">
                  <svg className="w-4 h-4 mr-2 text-gray-400 dark:text-gray-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>
                    <span className="text-red-600 dark:text-red-400 font-bold">*</span> Required fields. 
                    Phone number is optional but recommended for communication.
                  </span>
                </div>
                <div className="flex gap-3 flex-shrink-0 sm:items-center">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 transition-all text-sm font-medium"
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
                      'Save Tenant'
                    )}
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default TenantModal;

import React, { useState, useEffect, useRef } from "react";
import { updateTenant } from "../../utils/api";
import { motion, AnimatePresence } from "framer-motion";

// UI Components
const Label = ({ htmlFor, required, children }) => (
  <label
    htmlFor={htmlFor}
    className={`block text-sm font-medium text-gray-700 mb-1.5 ${
      required ? 'after:content-["*"] after:ml-0.5 after:text-red-500' : ""
    }`}
  >
    {children}
  </label>
);

const Input = ({
  id,
  name,
  value,
  onChange,
  placeholder,
  required,
  type = "text",
  className = "",
  onBlur,
  ...props
}) => (
  <input
    id={id || name}
    name={name}
    type={type}
    value={value}
    onChange={onChange}
    onBlur={onBlur}
    placeholder={placeholder}
    required={required}
    className={`w-full px-4 py-2.5 text-gray-900 bg-white border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 focus:outline-none transition-all duration-200 ${className}`}
    {...props}
  />
);

const ErrorMessage = ({ message }) => (
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
    <span>{message}</span>
  </motion.div>
);

const Button = ({
  type,
  onClick,
  variant = "primary",
  disabled,
  children,
  className = "",
  ...props
}) => {
  const baseClasses =
    "px-4 py-2.5 rounded-lg font-medium text-sm focus:outline-none focus:ring-2 focus:ring-offset-2 transition-all duration-200 inline-flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed";

  const variants = {
    primary:
      "bg-gradient-to-br from-brand-green to-brand-teal hover:from-brand-green/90 hover:to-brand-teal/90 text-white border border-transparent focus:ring-brand-green shadow-sm",
    secondary:
      "bg-white hover:bg-gray-50 text-gray-700 border border-gray-300 focus:ring-blue-500",
    danger:
      "bg-red-600 hover:bg-red-700 text-white border border-transparent focus:ring-red-500",
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${baseClasses} ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};

const UpdateTenantModal = ({ isOpen, onClose, tenant, onSave }) => {
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
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const modalRef = useRef(null);

  // Sync tenant prop to formData state
  useEffect(() => {
    if (tenant && isOpen) {
      setFormData({
        tenant_type: tenant.tenant_type || "Individual",
        first_name: tenant.first_name || "",
        last_name: tenant.last_name || "",
        company_name: tenant.company_name || "",
        contact_person: tenant.contact_person || "",
        phone: tenant.phone || "",
        email: tenant.email || "",
        status: tenant.status || "Active",
        current_property_id: tenant.current_property_id || null,
      });

      // Clear any previous errors
      setFieldErrors({});
      setError(null);
      setTouched({});
      setSubmitAttempted(false);
    }
  }, [tenant, isOpen]);

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

  // Handle form field changes
  const handleChange = (e) => {
    const { name, value } = e.target;

    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    // Mark field as touched
    setTouched((prev) => ({
      ...prev,
      [name]: true,
    }));

    // Clear field-specific error when user changes the field
    if (fieldErrors[name]) {
      setFieldErrors((prev) => {
        const updated = { ...prev };
        delete updated[name];
        return updated;
      });
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
    const newErrors = {};
    let isValid = true;

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
    setTouched({
      first_name: true,
      last_name: true,
      company_name: true,
      email: true,
      phone: true,
    });
    setSubmitAttempted(true);

    return isValid;
  };

  // Click outside modal to close it
  useEffect(() => {
    function handleClickOutsideModal(event) {
      if (modalRef.current && !modalRef.current.contains(event.target)) {
        onClose();
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutsideModal);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutsideModal);
    };
  }, [isOpen, onClose]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setFieldErrors({});

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      const response = await updateTenant(tenant.id, formData);

      if (onSave) {
        onSave(response);
      }

      onClose();
    } catch (err) {
      console.error("Failed to update tenant:", err);

      if (err.data?.detail && Array.isArray(err.data.detail)) {
        const validationErrors = {};
        err.data.detail.forEach((error) => {
          if (error.loc && error.loc.length > 1) {
            validationErrors[error.loc[1]] = error.msg;
          }
        });

        setFieldErrors(validationErrors);
        setError("Please correct the validation errors below.");
      } else {
        setError(err.message || "Failed to update tenant. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm overflow-y-auto h-full w-full z-[9999] flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        ref={modalRef}
        className="relative w-full max-w-lg bg-white rounded-xl shadow-2xl overflow-hidden"
      >
        {/* Header */}
        <div className="px-6 py-4 bg-gradient-to-br from-brand-green to-brand-teal text-white">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold text-white">Edit Tenant</h2>
              <p className="text-white/80 mt-0.5 text-sm">
                Update {formData.tenant_type.toLowerCase()} tenant information
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-white/70 hover:text-white hover:bg-white/10 p-1.5 rounded-lg transition-all"
              aria-label="Close modal"
            >
              <svg
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="p-6 max-h-[calc(100vh-12rem)] overflow-y-auto bg-gray-50">
          <AnimatePresence>
            {error && <ErrorMessage message={error} />}
          </AnimatePresence>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Tenant Type Section */}
            <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-100">
              <h3 className="text-sm font-medium text-gray-900 mb-3">Tenant Type</h3>
              <div className="grid grid-cols-2 gap-3">
                <label className="flex items-center cursor-pointer">
                  <input
                    type="radio"
                    name="tenant_type"
                    value="Individual"
                    checked={formData.tenant_type === "Individual"}
                    onChange={handleChange}
                    className="mr-3 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm font-medium text-gray-700">Individual</span>
                </label>
                <label className="flex items-center cursor-pointer">
                  <input
                    type="radio"
                    name="tenant_type"
                    value="Company"
                    checked={formData.tenant_type === "Company"}
                    onChange={handleChange}
                    className="mr-3 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm font-medium text-gray-700">Company</span>
                </label>
              </div>
            </div>

            {/* Conditional Name/Company Fields */}
            <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-100">
              <h3 className="text-sm font-medium text-gray-900 mb-3">
                {formData.tenant_type === "Individual" ? "Personal Information" : "Company Information"}
              </h3>
              
              {formData.tenant_type === "Individual" ? (
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="first_name" required>
                      First Name
                    </Label>
                    <Input
                      id="first_name"
                      name="first_name"
                      value={formData.first_name}
                      onChange={handleChange}
                      onBlur={handleBlur}
                      placeholder="Enter first name"
                      required
                      className={
                        fieldErrors.first_name && touched.first_name
                          ? "border-red-500"
                          : ""
                      }
                    />
                    {fieldErrors.first_name && touched.first_name && (
                      <p className="mt-1 text-sm text-red-600">
                        {fieldErrors.first_name}
                      </p>
                    )}
                  </div>

                  <div>
                    <Label htmlFor="last_name" required>
                      Last Name
                    </Label>
                    <Input
                      id="last_name"
                      name="last_name"
                      value={formData.last_name}
                      onChange={handleChange}
                      onBlur={handleBlur}
                      placeholder="Enter last name"
                      required
                      className={
                        fieldErrors.last_name && touched.last_name
                          ? "border-red-500"
                          : ""
                      }
                    />
                    {fieldErrors.last_name && touched.last_name && (
                      <p className="mt-1 text-sm text-red-600">
                        {fieldErrors.last_name}
                      </p>
                    )}
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="company_name" required>
                      Company Name
                    </Label>
                    <Input
                      id="company_name"
                      name="company_name"
                      value={formData.company_name}
                      onChange={handleChange}
                      onBlur={handleBlur}
                      placeholder="Enter company name"
                      required
                      className={
                        fieldErrors.company_name && touched.company_name
                          ? "border-red-500"
                          : ""
                      }
                    />
                    {fieldErrors.company_name && touched.company_name && (
                      <p className="mt-1 text-sm text-red-600">
                        {fieldErrors.company_name}
                      </p>
                    )}
                  </div>

                  <div>
                    <Label htmlFor="contact_person">
                      Contact Person
                    </Label>
                    <Input
                      id="contact_person"
                      name="contact_person"
                      value={formData.contact_person}
                      onChange={handleChange}
                      onBlur={handleBlur}
                      placeholder="Enter contact person name"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Contact Information */}
            <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-100">
              <h3 className="text-sm font-medium text-gray-900 mb-3">Contact Information</h3>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="email" required>
                    Email
                  </Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    value={formData.email}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    placeholder="Enter email"
                    required
                    className={
                      fieldErrors.email && touched.email ? "border-red-500" : ""
                    }
                  />
                  {fieldErrors.email && touched.email && (
                    <p className="mt-1 text-sm text-red-600">
                      {fieldErrors.email}
                    </p>
                  )}
                </div>

                <div>
                  <Label htmlFor="phone">
                    Phone Number
                  </Label>
                  <Input
                    id="phone"
                    name="phone"
                    type="tel"
                    value={formData.phone}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    placeholder="Enter phone number"
                    className={
                      fieldErrors.phone && touched.phone ? "border-red-500" : ""
                    }
                  />
                  {fieldErrors.phone && touched.phone && (
                    <p className="mt-1 text-sm text-red-600">
                      {fieldErrors.phone}
                    </p>
                  )}
                </div>
              </div>
            </div>

            <div className="mt-2 mb-4 text-sm text-gray-500">
              <span className="text-red-600 font-bold">*</span> Required fields. 
              Phone number is optional but recommended.
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end space-x-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            onClick={handleSubmit}
            disabled={isLoading}
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
                Updating...
              </>
            ) : (
              "Save Changes"
            )}
          </Button>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default UpdateTenantModal; 